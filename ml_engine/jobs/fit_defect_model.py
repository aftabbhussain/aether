import os,json,joblib,numpy as np,pandas as pd
from sklearn.model_selection import RandomizedSearchCV,StratifiedKFold,train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score,precision_score,recall_score,f1_score,roc_auc_score,average_precision_score,confusion_matrix,classification_report
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

SEED=42
PFEATS=["file_change_count","file_bug_fix_count","recent_file_change_count","days_since_last_change","last_change_lines_added","last_change_lines_deleted","last_change_churn","last_change_file_count","author_file_change_count"]
CAPS={"file_change_count":50,"file_bug_fix_count":20,"recent_file_change_count":20,"days_since_last_change":3650,"last_change_lines_added":1000,"last_change_lines_deleted":1000,"last_change_churn":1500,"last_change_file_count":30,"author_file_change_count":30}

def xform(df:pd.DataFrame,stats:dict=None)->pd.DataFrame:
  out=df.copy()
  for c in PFEATS:
    if c not in out.columns:continue
    v=pd.to_numeric(out[c],errors="coerce").fillna(0).clip(lower=0)
    if c in CAPS:v=v.clip(upper=CAPS[c])
    out[c]=np.log1p(v)
  if stats:
    for c,s in stats.get("process_metric_scaling",{}).items():
      if c in out.columns:out[c]=(out[c]-float(s.get("mean",0)))/(float(s.get("std",1)) or 1)
  return out

def fit_stats(df:pd.DataFrame)->dict:
  sc={}
  for c in PFEATS:
    if c not in df.columns:continue
    sd=float(df[c].std(ddof=0))
    sc[c]={"mean":float(df[c].mean()),"std":sd if sd>0 else 1.0}
  return {"process_metric_scaling":sc}

df=pd.read_csv("datasets/github_defect_dataset.csv").drop_duplicates().dropna(subset=["defect"]).fillna(0)
df["defect"]=df["defect"].astype(int)
df=df[df["defect"].isin([0,1])]
if df.empty:raise ValueError("Dataset is empty.")

FEATS=["nosi","dit","cbo","rfc","loc","comparisonsQty","returnQty","wmc","lcom","totalMethods"]+PFEATS
X=df[FEATS];y=df["defect"]
if y.nunique()<2:raise ValueError("Need both classes before training.")

X_tr_f,X_te_r,y_tr_f,y_te=train_test_split(X,y,test_size=0.2,random_state=SEED,stratify=y)
X_tr_r,X_va_r,y_tr,y_va=train_test_split(X_tr_f,y_tr_f,test_size=0.2,random_state=SEED,stratify=y_tr_f)
tstats=fit_stats(xform(X_tr_f))
X_tr_full=xform(X_tr_f,tstats);X_te=xform(X_te_r,tstats);X_tr=xform(X_tr_r,tstats);X_va=xform(X_va_r,tstats)

pos=(y_tr_f==1).sum();neg=(y_tr_f==0).sum()
spw=neg/pos if pos>0 else 1

algos={
  "Logistic Regression":Pipeline([("scaler",StandardScaler()),("classifier",LogisticRegression(max_iter=3000,class_weight="balanced",random_state=SEED))]),
  "Random Forest":RandomForestClassifier(random_state=SEED,class_weight="balanced"),
  "XGBoost":XGBClassifier(scale_pos_weight=spw,eval_metric="logloss",random_state=SEED)
}
grids={
  "Logistic Regression":{"classifier__C":[0.01,0.05,0.1,0.5,1,2,5,10],"classifier__solver":["lbfgs","liblinear"]},
  "Random Forest":{"n_estimators":[200,300,500,700],"max_depth":[None,6,10,14,20],"min_samples_split":[2,5,10],"min_samples_leaf":[1,2,4],"max_features":["sqrt","log2",None]},
  "XGBoost":{"n_estimators":[200,300,500],"learning_rate":[0.01,0.03,0.05,0.08,0.1],"max_depth":[3,4,5,6],"subsample":[0.75,0.85,1.0],"colsample_bytree":[0.75,0.85,1.0],"min_child_weight":[1,3,5],"gamma":[0,0.1,0.3]}
}
cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=SEED)

def probs(m,x):return m.predict_proba(x)[:,1] if hasattr(m,"predict_proba") else m.predict(x)

def tune_thresh(yt,yp):
  bt=0.5;bf=-1
  for t in np.arange(0.25,0.76,0.01):
    s=f1_score(yt,(yp>=t).astype(int),zero_division=0)
    if s>bf:bf=s;bt=t
  return round(float(bt),2),bf

rows=[];best_m=None;best_nm=None;best_f1=-1;best_t=0.5;best_ev=None
for nm,est in algos.items():
  rs=RandomizedSearchCV(estimator=est,param_distributions=grids[nm],n_iter=15,scoring="f1",cv=cv,random_state=SEED,n_jobs=-1,verbose=1)
  rs.fit(X_tr,y_tr)
  m=rs.best_estimator_
  t,vf1=tune_thresh(y_va,probs(m,X_va))
  m.fit(X_tr_full,y_tr_f)
  yp=probs(m,X_te);yhat=(yp>=t).astype(int)
  ev={"accuracy":accuracy_score(y_te,yhat),"precision":precision_score(y_te,yhat,zero_division=0),"recall":recall_score(y_te,yhat,zero_division=0),"f1":f1_score(y_te,yhat,zero_division=0),"roc_auc":roc_auc_score(y_te,yp),"pr_auc":average_precision_score(y_te,yp),"confusion_matrix":confusion_matrix(y_te,yhat),"classification_report":classification_report(y_te,yhat,digits=3,zero_division=0)}
  rows.append({"model":nm,"best_params":json.dumps(rs.best_params_),"threshold":t,"validation_f1":vf1,"accuracy":ev["accuracy"],"precision":ev["precision"],"recall":ev["recall"],"f1":ev["f1"],"roc_auc":ev["roc_auc"],"pr_auc":ev["pr_auc"]})
  if ev["f1"]>best_f1:best_f1=ev["f1"];best_m=m;best_nm=nm;best_t=t;best_ev=ev

os.makedirs("artifacts",exist_ok=True);os.makedirs("outputs",exist_ok=True)
pd.DataFrame(rows).to_csv("outputs/github_model_comparison.csv",index=False)
b_est=best_m.named_steps.get("classifier",best_m) if hasattr(best_m,"named_steps") else best_m
imp=b_est.feature_importances_ if hasattr(b_est,"feature_importances_") else (np.abs(b_est.coef_[0]) if hasattr(b_est,"coef_") else np.zeros(len(FEATS)))
if imp.sum()>0:imp=imp/imp.sum()
fi=pd.DataFrame({"feature":FEATS,"importance":imp}).sort_values(by="importance",ascending=False)
fi.to_csv("outputs/github_feature_importance.csv",index=False)
fi.head(10).to_csv("outputs/github_top_10_features.csv",index=False)
if best_ev:
  pd.DataFrame(best_ev["confusion_matrix"],index=["actual_non_defective","actual_defective"],columns=["predicted_non_defective","predicted_defective"]).to_csv("outputs/github_confusion_matrix.csv")
  with open("outputs/github_classification_report.txt","w",encoding="utf-8") as f:f.write(best_ev["classification_report"])
joblib.dump(best_m,"artifacts/github_defect_prediction_model.pkl")
joblib.dump(FEATS,"artifacts/github_model_features.pkl")
joblib.dump(best_t,"artifacts/github_prediction_threshold.pkl")
joblib.dump(tstats,"artifacts/github_feature_transform_stats.pkl")
meta={"best_model_name":best_nm,"best_f1":best_f1,"prediction_threshold":best_t,"selected_features":FEATS,"random_state":SEED,"optimization":"RandomizedSearchCV with 5-fold StratifiedKFold and validation threshold tuning","feature_transformations":{"process_metric_compression":{"method":"clip raw value to configured cap, apply log1p, then standard-scale process metrics using training-set mean/std","reason":"Reduce dominance of large process-history counts such as files changed together and place process metrics on a more comparable scale","caps":CAPS},"process_metric_scaling":{"method":"standard scaling after compression","stats_source":"training split only","stats":tstats["process_metric_scaling"]}},"feature_groups":{"static_code_metrics":["nosi","dit","cbo","rfc","loc","comparisonsQty","returnQty","wmc","lcom","totalMethods"],"process_metrics":PFEATS}}
with open("outputs/github_training_metadata.json","w",encoding="utf-8") as f:json.dump(meta,f,indent=2)
print("Done:",best_nm,round(best_f1,4))
