import csv,json,os
from io import StringIO
import pandas as pd
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse,Response
from settings import cfg
from schemas.payloads import PredictPayload,CommitsPayload,RefsPayload,ExportPayload,FeedbackPayload
from core.pipeline import DefectPipeline
from core.feedback_store import FeedbackStore
from core.job_runner import JobRunner
from core.history_store import HistoryStore

app=FastAPI(title="Aether Backend",description="Backend API for GitHub-based software defect prediction",version="1.0.0")

app.add_middleware(CORSMiddleware,allow_origins=cfg.cors_origins,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

history_store=HistoryStore()
feedback_store=FeedbackStore(history_store.db_path)
pipe=DefectPipeline()
jobs=JobRunner(pipe,history_store,workers=cfg.max_workers)
SRV_DIR=os.path.dirname(os.path.abspath(__file__))
ML_DIR=cfg.ml_dir

@app.get("/")
def index():
  return {"message":"Aether Backend is running"}

@app.get("/favicon.ico",include_in_schema=False)
def icon():
  p=os.path.join(SRV_DIR,"assets","favicon.png")
  if os.path.exists(p):
    return FileResponse(p,media_type="image/png")
  return Response(status_code=204)

@app.get("/health")
def health():
  req_files={
    "model":pipe.predictor.model_file,
    "features":pipe.predictor.feats_file,
    "threshold":pipe.predictor.thresh_file,
    "feature_transform_stats":pipe.predictor.stats_file
  }
  status_map={k:os.path.exists(v) for k,v in req_files.items()}
  return {
    "status":"ok" if all(status_map.values()) else "degraded",
    "model_files":status_map,
    "history_storage":history_store.db_path,
    "feedback_storage":feedback_store.db_path,
    "database_backend":"postgresql" if cfg.db_url else "sqlite",
    "allowed_origins":cfg.cors_origins,
    "local_cache_mode_enabled":cfg.local_cache_ok,
    "history_delete_enabled":cfg.history_delete_ok,
    "max_source_files_per_run":cfg.max_files,
    "git_shallow_history_depth":cfg.shallow_depth,
    "git_command_timeout_seconds":cfg.git_timeout,
    "prediction_jobs":jobs.summary()
  }

@app.post("/predict")
def run_predict(req:PredictPayload):
  try:
    _ensure_mode(req.use_personal_access_token)
    rows=pipe.execute(repo_url=req.repo_url,commit_sha=req.commit_sha,thresh=req.prediction_threshold,use_pat=req.use_personal_access_token,tok=req.github_token)
    out={
      "repo_url":req.repo_url,
      "commit_sha":req.commit_sha,
      "prediction_threshold":_get_thresh(req.prediction_threshold),
      "clone_mode":"pat_temporary" if req.use_personal_access_token else "local_cache",
      "total_files_scanned":len(rows),
      "results":rows
    }
    history_store.save_run(out)
    return out
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500,detail=str(e))

@app.post("/prediction-jobs")
def create_job(req:PredictPayload):
  try:
    _ensure_mode(req.use_personal_access_token)
    return jobs.enqueue(repo_url=req.repo_url,commit_sha=req.commit_sha,thresh=req.prediction_threshold,use_pat=req.use_personal_access_token,tok=req.github_token)
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500,detail=str(e))

@app.get("/prediction-jobs/{job_id}")
def poll_job(job_id:str):
  j=jobs.get_status(job_id)
  if not j:raise HTTPException(status_code=404,detail="Prediction job not found")
  return j

@app.post("/prediction-jobs/{job_id}/cancel")
def stop_job(job_id:str):
  j=jobs.abort(job_id)
  if not j:raise HTTPException(status_code=404,detail="Prediction job not found")
  return j

@app.get("/prediction-history")
def get_history():
  return {"history":history_store.list_runs()}

@app.get("/prediction-history/{history_id}")
def get_history_detail(history_id:str):
  item=history_store.get_run(history_id)
  if not item:raise HTTPException(status_code=404,detail="Prediction history item not found")
  return item

@app.delete("/prediction-history/{history_id}")
def remove_history(history_id:str):
  if not cfg.history_delete_ok:
    raise HTTPException(status_code=403,detail="Prediction history deletion is disabled for this deployment.")
  if not history_store.remove_run(history_id):
    raise HTTPException(status_code=404,detail="Prediction history item not found")
  return {"deleted":True,"history_id":history_id}

@app.get("/feedback")
def get_feedback():
  return {"feedback":feedback_store.all_entries()}

@app.post("/feedback")
def post_feedback(req:FeedbackPayload):
  try:
    rec=feedback_store.add_entry(name=req.name,role=req.role,rating=req.rating,message=req.message)
    return {"feedback":rec}
  except ValueError as err:
    raise HTTPException(status_code=400,detail=str(err))

@app.post("/export-report")
def download_csv(req:ExportPayload):
  buf=StringIO()
  w=csv.writer(buf)
  w.writerow(["Repository URL",req.repo_url])
  w.writerow(["Commit SHA",req.commit_sha])
  w.writerow(["Prediction Threshold",req.prediction_threshold if req.prediction_threshold is not None else "Model default"])
  w.writerow(["Total Files Scanned",req.total_files_scanned])
  w.writerow([])
  w.writerow(["File Path","Language","Prediction","Risk Probability","Risk Level","Recommendation","File Change Count","File Bug-fix Count","Recent File Change Count","Days Since Last Change","Previous Change Churn","Author File Change Count","Top Contributing Metrics","Readable Explanation","Confidence Warning","Potential Test File","Test File Reason"])
  for r in req.results:
    w.writerow([r.file_path,r.language,r.prediction_label,r.defect_risk_probability,r.risk_level,r.recommendation,r.file_change_count,r.file_bug_fix_count,r.recent_file_change_count,r.days_since_last_change,r.last_change_churn,r.author_file_change_count,r.top_contributing_metrics,r.readable_explanation,r.confidence_warning,r.is_potential_test_file,r.test_file_reason])
  fname=f"defect_prediction_report_{req.commit_sha[:8]}.csv"
  return Response(content=buf.getvalue(),media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="{fname}"'})

@app.get("/model-transparency")
def model_info():
  cmp_rows=_load_csv(os.path.join(ML_DIR,"outputs","github_model_comparison.csv"))
  imp_rows=_load_csv(os.path.join(ML_DIR,"outputs","github_feature_importance.csv"))
  ds_sum=_dataset_stats(os.path.join(ML_DIR,"datasets","github_defect_dataset.csv"))
  meta=_load_json(os.path.join(ML_DIR,"outputs","github_training_metadata.json"))
  cm=_load_csv(os.path.join(ML_DIR,"outputs","github_confusion_matrix.csv"))
  rep=_load_txt(os.path.join(ML_DIR,"outputs","github_classification_report.txt"))
  best=max(cmp_rows,key=lambda x:float(x.get("f1",0) or 0)) if cmp_rows else None
  return {
    "model_name":best.get("model") if best else "Unknown",
    "selected_features":pipe.predictor.feat_cols,
    "model_comparison":cmp_rows,
    "feature_importance":imp_rows,
    "dataset_summary":ds_sum,
    "training_metadata":meta,
    "confusion_matrix":cm,
    "classification_report":rep,
    "limitations":[
      "Metrics combine static code approximations with Git commit-history process metrics, but still may not capture runtime behavior.",
      "Python and C++ support maps language-specific patterns into the existing shared feature set.",
      "Prediction quality depends on how representative the training dataset is for the analyzed repository.",
      "Generated explanations identify influential metrics, not guaranteed root causes."
    ]
  }

@app.post("/commits")
def list_commits(req:CommitsPayload):
  try:
    _ensure_mode(req.use_personal_access_token)
    items=pipe.git.fetch_commits(url=req.repo_url,ref=req.git_ref,limit=req.max_commits,offset=req.skip,use_pat=req.use_personal_access_token,tok=req.github_token)
    return {"repo_url":req.repo_url,"git_ref":req.git_ref,"skip":req.skip,"max_commits":req.max_commits,"total_commits":len(items),"commits":items}
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500,detail=str(e))

@app.post("/branches")
def list_branches(req:RefsPayload):
  try:
    _ensure_mode(req.use_personal_access_token)
    items=pipe.git.fetch_branches(url=req.repo_url,use_pat=req.use_personal_access_token,tok=req.github_token)
    return {"repo_url":req.repo_url,"total_branches":len(items),"branches":items}
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500,detail=str(e))

@app.post("/tags")
def list_tags(req:RefsPayload):
  try:
    _ensure_mode(req.use_personal_access_token)
    items=pipe.git.fetch_tags(url=req.repo_url,use_pat=req.use_personal_access_token,tok=req.github_token)
    return {"repo_url":req.repo_url,"total_tags":len(items),"tags":items}
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500,detail=str(e))

def _load_csv(p:str)->list:
  return pd.read_csv(p).fillna("").to_dict(orient="records") if os.path.exists(p) else []

def _load_json(p:str)->dict:
  if not os.path.exists(p):return {}
  with open(p,"r",encoding="utf-8") as f:return json.load(f)

def _load_txt(p:str)->str:
  if not os.path.exists(p):return ""
  with open(p,"r",encoding="utf-8") as f:return f.read()

def _get_thresh(t:float=None)->float:
  return float(t) if t is not None else float(pipe.predictor.default_thresh)

def _ensure_mode(use_pat:bool):
  if not use_pat and not cfg.local_cache_ok:
    raise HTTPException(status_code=403,detail="Local cache mode is disabled on this deployment. Use Personal Token request mode instead.")

def _dataset_stats(p:str)->dict:
  if not os.path.exists(p):
    return {"total_rows":0,"defective_rows":0,"non_defective_rows":0,"repositories":0,"languages":[]}
  df=pd.read_csv(p)
  return {
    "total_rows":int(len(df)),
    "defective_rows":int((df["defect"]==1).sum()) if "defect" in df else 0,
    "non_defective_rows":int((df["defect"]==0).sum()) if "defect" in df else 0,
    "repositories":int(df["repo_url"].nunique()) if "repo_url" in df else 0,
    "languages":sorted(df["language"].dropna().unique().tolist()) if "language" in df else ["Java"]
  }
