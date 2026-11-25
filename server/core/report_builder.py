import re,pandas as pd
from core.text_summary import TextSummaryBuilder

TEST_DIRS={"test","tests","__tests__","spec","specs","testing"}
TEST_PATTERNS=[
  (r"(^|[_\-.])test[_\-.]","Filename contains a test prefix"),
  (r"[_\-.]test\.","Filename contains .test pattern"),
  (r"[_\-.]spec\.","Filename contains .spec pattern"),
  (r"test\.(py|js|jsx|ts|tsx|java|cpp|cc|cxx|h|hpp)$","Filename ends with a test pattern"),
  (r"spec\.(py|js|jsx|ts|tsx|java|cpp|cc|cxx|h|hpp)$","Filename ends with a spec pattern"),
  (r"test(case)?\.(py|cpp|cc|cxx|h|hpp)$","Filename uses a common test file name"),
  (r".+test\.(java|cpp|cc|cxx|h|hpp)$","Filename ends with Test"),
  (r".+tests\.(py|cpp|cc|cxx|h|hpp)$","Filename ends with tests")
]
COLS=[
  "file_path","language","prediction_label","defect_risk_probability",
  "risk_level","recommendation","file_change_count","file_bug_fix_count",
  "recent_file_change_count","days_since_last_change","last_change_churn",
  "author_file_change_count","top_contributing_metrics","readable_explanation",
  "confidence_warning","is_potential_test_file","test_file_reason"
]

class ReportBuilder:
  def __init__(self):
    self.summary_builder=TextSummaryBuilder()

  def build(self,df:pd.DataFrame)->list:
    if df.empty:
      return []
    df["risk_level"]=df["defect_risk_probability"].apply(self._risk_tier)
    df["recommendation"]=df.apply(lambda r:self._advice(r["prediction_label"],r["risk_level"]),axis=1)
    df["readable_explanation"]=df.apply(lambda r:self.summary_builder.make_summary(r["top_contributing_metrics"],r["risk_level"],r["defect_risk_probability"]),axis=1)
    df["is_potential_test_file"]=df["file_path"].apply(lambda p:bool(self._test_reason(p)))
    df["test_file_reason"]=df["file_path"].apply(self._test_reason)
    for c in COLS:
      if c not in df.columns:
        df[c]=""
    out=df[COLS].copy()
    out["defect_risk_probability"]=out["defect_risk_probability"].round(4)
    out["is_potential_test_file"]=out["is_potential_test_file"].apply(bool)
    return out.to_dict(orient="records")

  def _risk_tier(self,p:float)->str:
    if p>=0.7:return "High"
    if p>=0.4:return "Medium"
    return "Low"

  def _advice(self,lbl:str,tier:str)->str:
    if tier=="High" or lbl=="Defective":
      return "Review immediately before release"
    if tier=="Medium":
      return "Review key logic when time permits"
    return "Low priority, monitor if modified later"

  def _test_reason(self,fpath:str)->str:
    norm=str(fpath or "").replace("\\","/").lower()
    parts=[x for x in norm.split("/") if x]
    fname=parts[-1] if parts else norm
    for seg in parts[:-1]:
      if seg in TEST_DIRS:
        return f"Path contains a common test folder: {seg}"
    for pat,msg in TEST_PATTERNS:
      if re.search(pat,fname):
        return msg
    return ""
