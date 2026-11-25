from core.git_client import GitClient
from core.code_metrics import CodeMetricsExtractor
from core.git_metrics import GitProcessMetrics
from core.predictor import DefectPredictor
from core.shap_explainer import ShapExplainer
from core.report_builder import ReportBuilder

class DefectPipeline:
  def __init__(self):
    self.git=GitClient()
    self.extractor=CodeMetricsExtractor()
    self.proc=GitProcessMetrics()
    self.predictor=DefectPredictor()
    self.explainer=ShapExplainer(self.predictor.clf,self.predictor.feat_cols,self.predictor.scale_stats)
    self.reporter=ReportBuilder()

  def execute(self,repo_url:str,commit_sha:str,thresh:float=None,use_pat:bool=False,tok:str=None,on_progress=None)->list:
   repo_dir=None
   try:
     self._emit(on_progress,"cloning",15,"Cloning repository and checking out the selected commit")
     repo_dir=self.git.checkout_commit(repo_url,commit_sha,use_pat=use_pat,tok=tok)
     self._emit(on_progress,"extracting_metrics",40,"Scanning all supported source files in the selected commit")
     df=self.extractor.scan_repo(repo_dir)
     if df.empty:
       self._emit(on_progress,"completed",100,"No supported source files were found")
       return []
     self._emit(on_progress,"extracting_process_metrics",55,"Extracting commit-history process metrics for each file")
     df=self.proc.attach(df,repo_dir,commit_sha)
     self._emit(on_progress,"predicting",72,"Running the trained defect prediction model")
     df=self.predictor.score(df,thresh=thresh)
     self._emit(on_progress,"explaining",86,"Generating SHAP-based metric explanations")
     df=self.explainer.explain_rows(df)
     self._emit(on_progress,"generating_report",95,"Preparing prediction report")
     out=self.reporter.build(df)
     self._emit(on_progress,"completed",100,"Prediction completed")
     return out
   finally:
     if repo_dir:
       self.git.remove_tree(repo_dir)

  def _emit(self,cb,st:str,pct:int,msg:str):
   if cb:cb(st,pct,msg)
