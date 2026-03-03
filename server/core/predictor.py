import os,joblib,pandas as pd
from settings import cfg
from core.transforms import apply_feature_transforms

class DefectPredictor:
  def __init__(self):
    art_dir=os.path.join(cfg.ml_dir,"artifacts")
    self.model_file=os.path.join(art_dir,"github_defect_prediction_model.pkl")
    self.feats_file=os.path.join(art_dir,"github_model_features.pkl")
    self.thresh_file=os.path.join(art_dir,"github_prediction_threshold.pkl")
    self.stats_file=os.path.join(art_dir,"github_feature_transform_stats.pkl")
    self.clf=joblib.load(self.model_file)
    self.feat_cols=joblib.load(self.feats_file)
    self.default_thresh=float(joblib.load(self.thresh_file)) if os.path.exists(self.thresh_file) else 0.5
    self.scale_stats=joblib.load(self.stats_file) if os.path.exists(self.stats_file) else {}

  def score(self,df:pd.DataFrame,thresh:float=None)->pd.DataFrame:
   if df.empty:
     return df
   missing=[c for c in self.feat_cols if c not in df.columns]
   if missing:
     raise ValueError(f"Missing required features: {missing}")
   x_mat=apply_feature_transforms(df[self.feat_cols],self.scale_stats)
   t=self.default_thresh if thresh is None else max(0.05,min(0.95,float(thresh)))
   probs=self.clf.predict_proba(x_mat)[:,1]
   df["defect_risk_probability"]=probs
   df["defect_prediction"]=(probs>=t).astype(int)
   df["prediction_threshold"]=t
   df["prediction_label"]=df["defect_prediction"].map({0:"Non-defective",1:"Defective"})
   return df
