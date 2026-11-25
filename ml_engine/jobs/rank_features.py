import os,joblib,numpy as np,pandas as pd

clf=joblib.load("artifacts/github_defect_prediction_model.pkl")
feats=joblib.load("artifacts/github_model_features.pkl")
est=clf.named_steps.get("classifier",clf) if hasattr(clf,"named_steps") else clf
if hasattr(est,"feature_importances_"):imp=est.feature_importances_
elif hasattr(est,"coef_"):imp=np.abs(est.coef_[0])
else:raise ValueError("Model does not expose feature importances or coefficients.")
if imp.sum()>0:imp=imp/imp.sum()
out=pd.DataFrame({"feature":feats,"importance":imp}).sort_values(by="importance",ascending=False)
os.makedirs("outputs",exist_ok=True)
out.to_csv("outputs/github_feature_importance.csv",index=False)
out.head(10).to_csv("outputs/github_top_10_features.csv",index=False)
print(out)
