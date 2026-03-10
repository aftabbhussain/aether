import os,sys,tempfile,unittest
from pathlib import Path
SRV_DIR=Path(__file__).resolve().parents[1]
if str(SRV_DIR) not in sys.path:sys.path.insert(0,str(SRV_DIR))
os.environ.pop("DATABASE_URL",None)
import pandas as pd
from pydantic import ValidationError
from settings import cfg
from schemas.payloads import FeedbackPayload,RepoPayload,PredictPayload
from core.feedback_store import FeedbackStore
from core.code_metrics import CodeMetricsExtractor
from core.history_store import HistoryStore
from core.report_builder import ReportBuilder
cfg.db_url=""

class PayloadTests(unittest.TestCase):
  def test_url_norm(self):
    r=RepoPayload(repo_url=" https://github.com/sclorg/s2i-python-container.git ")
    self.assertEqual(r.repo_url,"https://github.com/sclorg/s2i-python-container.git")
  def test_bad_host(self):
    with self.assertRaises(ValidationError):
      RepoPayload(repo_url="https://gitlab.com/example/project")
  def test_thresh_bounds(self):
    ok=PredictPayload(repo_url="https://github.com/sclorg/s2i-python-container.git",commit_sha="1234567890abcdef1234567890abcdef12345678",prediction_threshold=0.5)
    self.assertEqual(ok.prediction_threshold,0.5)
    with self.assertRaises(ValidationError):
      PredictPayload(repo_url="https://github.com/sclorg/s2i-python-container.git",commit_sha="1234567890abcdef1234567890abcdef12345678",prediction_threshold=0.99)
  def test_feedback_validation(self):
    req=FeedbackPayload(rating=5,message="Useful application for review")
    self.assertEqual(req.message,"Useful application for review")
    with self.assertRaises(ValidationError):
      FeedbackPayload(rating=0,message="Bad rating")
    with self.assertRaises(ValidationError):
      FeedbackPayload(rating=4,message="   ")

class MetricsTests(unittest.TestCase):
  def test_multi_lang(self):
    with tempfile.TemporaryDirectory() as td:
      p=Path(td)
      (p/"sample.py").write_text("import os\n\nclass Worker:\n    def run(self, value):\n        if value > 0:\n            return os.path.join('a', 'b')\n        return 'none'\n",encoding="utf-8")
      (p/"Sample.java").write_text("import java.util.List;\npublic class Sample { private int total; public int run(int value) { if (value > 0) { return value; } return 0; } }\n",encoding="utf-8")
      (p/"sample.cpp").write_text("#include <iostream>\nclass Sample { public: int run(int value) { if (value > 0) { return value; } return 0; } };\n",encoding="utf-8")
      (p/"node_modules").mkdir()
      (p/"node_modules"/"ignored.py").write_text("def ignored():\n    return 1\n",encoding="utf-8")
      df=CodeMetricsExtractor().scan_repo(str(p))
    self.assertEqual(set(df["language"].tolist()),{"Python","Java","C++"})
    self.assertNotIn("node_modules/ignored.py",set(df["file_path"].tolist()))
    self.assertTrue((df["loc"]>0).all())
    self.assertTrue((df["totalMethods"]>=0).all())
  def test_subset_files(self):
    with tempfile.TemporaryDirectory() as td:
      p=Path(td)
      (p/"src").mkdir()
      (p/"src"/"feature.py").write_text("def ok():\n    return True\n",encoding="utf-8")
      (p/"README.md").write_text("not source",encoding="utf-8")
      df=CodeMetricsExtractor().scan_repo(str(p),["src/feature.py","README.md","../outside.py"])
    self.assertEqual(df["file_path"].tolist(),["src/feature.py"])
    self.assertEqual(df.iloc[0]["language"],"Python")

class ReportTests(unittest.TestCase):
  def test_risk_and_test_flag(self):
    df=pd.DataFrame([
      {"file_path":"src/main.py","language":"Python","prediction_label":"Defective","defect_risk_probability":0.82,"top_contributing_metrics":"number of conditional checks","confidence_warning":""},
      {"file_path":"tests/test_main.py","language":"Python","prediction_label":"Non-defective","defect_risk_probability":0.31,"top_contributing_metrics":"file size","confidence_warning":""}
    ])
    rep=ReportBuilder().build(df)
    self.assertEqual(rep[0]["risk_level"],"High")
    self.assertEqual(rep[0]["recommendation"],"Review immediately before release")
    self.assertFalse(rep[0]["is_potential_test_file"])
    self.assertTrue(rep[1]["is_potential_test_file"])
    self.assertIn("test folder",rep[1]["test_file_reason"])

class FeedbackTests(unittest.TestCase):
  def test_save_and_order(self):
    with tempfile.TemporaryDirectory() as td:
      st=FeedbackStore(str(Path(td)/"feedback.db"))
      a=st.add_entry("Alice","Student",4,"The dashboard is clear")
      b=st.add_entry("Bob","Developer",5,"The feedback page works")
      rows=st.all_entries()
    self.assertEqual(len(rows),2)
    self.assertEqual(rows[0]["id"],b["id"])
    self.assertEqual(rows[1]["id"],a["id"])
  def test_invalid_inputs(self):
    with tempfile.TemporaryDirectory() as td:
      st=FeedbackStore(str(Path(td)/"feedback.db"))
      with self.assertRaises(ValueError):st.add_entry(rating=6,message="Invalid rating")
      with self.assertRaises(ValueError):st.add_entry(rating=5,message="   ")

class HistoryTests(unittest.TestCase):
  def test_crud(self):
    sample={
      "repo_url":"https://github.com/sclorg/s2i-python-container.git",
      "commit_sha":"1234567890abcdef1234567890abcdef12345678",
      "prediction_threshold":0.5,"total_files_scanned":2,
      "results":[
        {"file_path":"src/main.py","language":"Python","prediction_label":"Defective","defect_risk_probability":0.8,"risk_level":"High","recommendation":"Review immediately before release","top_contributing_metrics":"conditional checks"},
        {"file_path":"src/helper.py","language":"Python","prediction_label":"Non-defective","defect_risk_probability":0.2,"risk_level":"Low","recommendation":"Low priority monitor if modified later","top_contributing_metrics":"file size"}
      ]
    }
    with tempfile.TemporaryDirectory() as td:
      hs=HistoryStore(str(Path(td)/"history.db"))
      hid=hs.save_run(sample)
      lst=hs.list_runs()
      det=hs.get_run(hid)
      ok=hs.remove_run(hid)
      gone=hs.get_run(hid)
    self.assertEqual(len(lst),1)
    self.assertEqual(lst[0]["high_risk_count"],1)
    self.assertEqual(lst[0]["low_risk_count"],1)
    self.assertAlmostEqual(lst[0]["average_risk_probability"],0.5)
    self.assertEqual(det["history_id"],hid)
    self.assertEqual(len(det["results"]),2)
    self.assertTrue(ok)
    self.assertIsNone(gone)

if __name__=="__main__":
  unittest.main()
