import shap,pandas as pd
from core.transforms import apply_feature_transforms

FEAT_LABELS={
  "rfc":"Method interaction complexity",
  "comparisonsQty":"Number of conditional checks",
  "nosi":"Static method usage",
  "lcom":"Class cohesion complexity",
  "totalMethods":"Number of methods",
  "loc":"File size",
  "cbo":"Dependency between classes",
  "wmc":"Overall method complexity",
  "returnQty":"Number of return paths",
  "dit":"Inheritance depth",
  "file_change_count":"Historical file change frequency",
  "file_bug_fix_count":"Previous bug-fix activity for this file",
  "recent_file_change_count":"Recent file change activity",
  "days_since_last_change":"Time since the file was last changed",
  "last_change_lines_added":"Lines added in the previous file change",
  "last_change_lines_deleted":"Lines deleted in the previous file change",
  "last_change_churn":"Code churn in the previous file change",
  "last_change_file_count":"Files changed together in the previous commit",
  "author_file_change_count":"Selected commit author's prior changes to this file"
}

HIST_FEATS={
  "file_change_count","file_bug_fix_count","recent_file_change_count",
  "days_since_last_change","last_change_lines_added","last_change_lines_deleted",
  "last_change_churn","last_change_file_count","author_file_change_count"
}

class ShapExplainer:
  def __init__(self,clf,feat_cols,scale_stats=None):
    self.clf=clf
    self.feat_cols=feat_cols
    self.scale_stats=scale_stats or {}
    try:
      self.exp=shap.TreeExplainer(self.clf)
      self.mode="tree"
    except Exception:
      self.exp=None
      self.mode="fallback"

  def explain_rows(self,df:pd.DataFrame)->pd.DataFrame:
   if df.empty:
     return df
   x_mat=apply_feature_transforms(df[self.feat_cols],self.scale_stats)
   if self.mode=="tree":
     sv=self.exp.shap_values(x_mat)
     if isinstance(sv,list):
       cls1=sv[1]
     else:
       cls1=sv[:,:,1] if len(sv.shape)==3 else sv
   else:
     fb=shap.Explainer(self.clf.predict_proba,x_mat)
     sv=fb(x_mat)
     cls1=sv.values[:,:,1] if len(sv.values.shape)==3 else sv.values

   summaries=[]
   warnings=[]
   for idx in range(len(x_mat)):
     tbl=pd.DataFrame({"feature":self.feat_cols,"val":x_mat.iloc[idx].values,"sv":cls1[idx]})
     tbl["abs_sv"]=tbl["sv"].abs()
     top5=tbl.sort_values(by="abs_sv",ascending=False).head(5)
     tot=top5["abs_sv"].sum()
     lead=top5.iloc[0]
     ratio=(lead["abs_sv"]/tot) if tot>0 else 0
     pts=[]
     for _,r in top5.iterrows():
       f=r["feature"]
       raw_v=df.iloc[idx][f]
       lbl=FEAT_LABELS.get(f,f)
       if r["sv"]>0:
         pts.append(f"{lbl} ({f}={raw_v}) pushed the model score higher for this file")
       else:
         pts.append(f"{lbl} ({f}={raw_v}) pushed the model score lower for this file")
     summaries.append(". ".join(pts)+".")
     warnings.append(self._warn(lead["feature"],ratio))

   df["top_contributing_metrics"]=summaries
   df["confidence_warning"]=warnings
   return df

  def _warn(self,feat:str,ratio:float)->str:
   if ratio<0.6:
     return ""
   lbl=FEAT_LABELS.get(feat,feat)
   pct=round(ratio*100)
   if feat in HIST_FEATS:
     return f"Confidence note: {pct}% of the top explanation impact comes from one commit-history signal ({lbl}). Use this as a review hint and also inspect the source code metrics before deciding."
   return f"Confidence note: {pct}% of the top explanation impact comes from one metric ({lbl}). The prediction may be sensitive to this single signal, so review the file context as well."
