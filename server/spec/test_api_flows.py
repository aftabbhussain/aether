import csv,os,sys,tempfile,unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch
SRV_DIR=Path(__file__).resolve().parents[1]
if str(SRV_DIR) not in sys.path:sys.path.insert(0,str(SRV_DIR))
os.environ.pop("DATABASE_URL",None)
from fastapi.testclient import TestClient
from settings import cfg
from core.feedback_store import FeedbackStore
from core.code_metrics import CodeMetricsExtractor
from core.history_store import HistoryStore
from core.predictor import DefectPredictor
from core.report_builder import ReportBuilder
cfg.db_url=""
import app as srv_app

REPO_URL="https://github.com/sclorg/s2i-python-container.git"
SHA="1234567890abcdef1234567890abcdef12345678"

def sample_resp()->dict:
  return {
    "repo_url":REPO_URL,"commit_sha":SHA,"prediction_threshold":0.5,"total_files_scanned":2,
    "results":[
      {"file_path":"src/main.py","language":"Python","prediction_label":"Defective","defect_risk_probability":0.82,"risk_level":"High","recommendation":"Review immediately before release","top_contributing_metrics":"conditional checks","readable_explanation":"This file should receive closer review."},
      {"file_path":"tests/test_main.py","language":"Python","prediction_label":"Non-defective","defect_risk_probability":0.31,"risk_level":"Low","recommendation":"Low priority monitor if modified later","top_contributing_metrics":"file size","readable_explanation":"This file has a lower estimated risk.","is_potential_test_file":True,"test_file_reason":"The path matches a common test folder."}
    ]
  }

class ApiFlowTests(unittest.TestCase):
  def setUp(self):
    self.td=tempfile.TemporaryDirectory()
    self.dbf=str(Path(self.td.name)/"integration.db")
    self.hs=HistoryStore(self.dbf)
    self.fs=FeedbackStore(self.dbf)
    self.client=TestClient(srv_app.app)
    self.p_h=patch.object(srv_app,"history_store",self.hs)
    self.p_f=patch.object(srv_app,"feedback_store",self.fs)
    self.p_h.start()
    self.p_f.start()
  def tearDown(self):
    self.p_f.stop()
    self.p_h.stop()
    self.td.cleanup()
  def test_feedback_flow(self):
    r1=self.client.post("/feedback",json={"name":"Integration Tester","role":"Software developer","rating":5,"message":"The result dashboard is understandable."})
    self.assertEqual(r1.status_code,200)
    fid=r1.json()["feedback"]["id"]
    r2=self.client.get("/feedback")
    self.assertEqual(r2.status_code,200)
    items=r2.json()["feedback"]
    self.assertEqual(len(items),1)
    self.assertEqual(items[0]["id"],fid)
    self.assertEqual(FeedbackStore(self.dbf).all_entries()[0]["id"],fid)
  def test_history_flow(self):
    hid=self.hs.save_run(sample_resp())
    r1=self.client.get("/prediction-history")
    r2=self.client.get(f"/prediction-history/{hid}")
    self.assertEqual(r1.status_code,200)
    self.assertEqual(r2.status_code,200)
    self.assertEqual(r1.json()["history"][0]["id"],hid)
    self.assertEqual(r2.json()["results"][0]["file_path"],"src/main.py")
    self.assertEqual(len(HistoryStore(self.dbf).get_run(hid)["results"]),2)
  def test_export_csv(self):
    resp=self.client.post("/export-report",json=sample_resp())
    self.assertEqual(resp.status_code,200)
    self.assertEqual(resp.headers["content-type"],"text/csv; charset=utf-8")
    self.assertIn("defect_prediction_report_12345678.csv",resp.headers["content-disposition"])
    rows=list(csv.reader(StringIO(resp.text)))
    hits=[r for r in rows if r and r[0] in {"src/main.py","tests/test_main.py"}]
    self.assertEqual(len(hits),2)
    self.assertEqual(hits[0][4],"High")
    self.assertEqual(hits[1][15],"True")

class PipelineSmokeTests(unittest.TestCase):
  def test_end_to_end_scoring(self):
    with tempfile.TemporaryDirectory() as td:
      p=Path(td)
      (p/"src").mkdir()
      (p/"src"/"calculator.py").write_text("class Calculator:\n    def calculate(self, value):\n        if value > 0:\n            return value * 2\n        return 0\n",encoding="utf-8")
      (p/"tests").mkdir()
      (p/"tests"/"test_calculator.py").write_text("def test_calculate():\n    assert True\n",encoding="utf-8")
      df=CodeMetricsExtractor().scan_repo(str(p))
    pred=DefectPredictor()
    for c in pred.feat_cols:
      if c not in df.columns:df[c]=0
    scored=pred.score(df,thresh=0.5)
    scored["top_contributing_metrics"]="integration test metrics"
    scored["confidence_warning"]=""
    rep=ReportBuilder().build(scored)
    self.assertEqual(len(rep),2)
    self.assertTrue(all(0<=r["defect_risk_probability"]<=1 for r in rep))
    self.assertTrue(all(r["risk_level"] in {"High","Medium","Low"} for r in rep))
    trow=next(r for r in rep if r["file_path"]=="tests/test_calculator.py")
    self.assertTrue(trow["is_potential_test_file"])

if __name__=="__main__":
  unittest.main()
