import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from threading import RLock

class JobAbortedError(Exception):
  pass

class JobRunner:
  def __init__(self,pipe,hist=None,workers:int=2):
    self.pipe=pipe
    self.hist=hist
    self.workers=workers
    self.pool=ThreadPoolExecutor(max_workers=workers)
    self.tasks={}
    self.mux=RLock()

  def enqueue(self,repo_url:str,commit_sha:str,thresh:float=None,use_pat:bool=False,tok:str=None)->dict:
   jid=str(uuid.uuid4())
   ts=self._ts()
   eff_t=self._thresh(thresh)
   cmode="pat_temporary" if use_pat else "local_cache"
   with self.mux:
     if self._running_cnt()>=self.workers:
       return {
         "job_id":jid,"status":"failed","stage":"busy","progress_percent":0,
         "message":"The demo server is currently busy. Please try again in a few minutes.",
         "repo_url":repo_url,"commit_sha":commit_sha,"prediction_threshold":eff_t,
         "clone_mode":cmode,"created_at":ts,"updated_at":ts,"result":None,
         "error":"The demo server is currently busy. Please try again in a few minutes."
       }
     self.tasks[jid]={
       "job_id":jid,"status":"queued","stage":"queued","progress_percent":0,
       "message":"Prediction job is queued","repo_url":repo_url,"commit_sha":commit_sha,
       "prediction_threshold":eff_t,"clone_mode":cmode,"created_at":ts,"updated_at":ts,
       "result":None,"error":None,"cancel_flag":False
     }
   fut=self.pool.submit(self._exec,jid,repo_url,commit_sha,thresh,use_pat,tok)
   with self.mux:
     if jid in self.tasks:
       self.tasks[jid]["fut"]=fut
   return self.get_status(jid)

  def abort(self,jid:str)->dict:
   with self.mux:
     t=self.tasks.get(jid)
     if not t:return None
     if t.get("status") in {"completed","failed","cancelled"}:
       return self._view(t)
     t["cancel_flag"]=True
     t["status"]="cancelled"
     t["stage"]="cancelled"
     t["progress_percent"]=100
     t["message"]="Prediction job was cancelled"
     t["error"]="Prediction job was cancelled by the user."
     t["updated_at"]=self._ts()
     if t.get("fut"):
       t["fut"].cancel()
     return self._view(t)

  def get_status(self,jid:str)->dict:
   with self.mux:
     t=self.tasks.get(jid)
     return self._view(t) if t else None

  def summary(self)->dict:
   with self.mux:
     act=self._running_cnt()
     q=sum(1 for t in self.tasks.values() if t.get("status")=="queued")
     return {"max_workers":self.workers,"active_jobs":act,"queued_jobs":q,"busy":act>=self.workers}

  def _running_cnt(self)->int:
   return sum(1 for t in self.tasks.values() if t.get("status")=="running")

  def _exec(self,jid:str,repo_url:str,commit_sha:str,thresh:float=None,use_pat:bool=False,tok:str=None):
   try:
     self._check_abort(jid)
     self._patch(jid,status="running",stage="starting",progress_percent=5,message="Starting prediction job")
     def on_prog(st:str,pct:int,msg:str):
       self._check_abort(jid)
       self._patch(jid,status="running",stage=st,progress_percent=pct,message=msg)
     res=self.pipe.execute(repo_url=repo_url,commit_sha=commit_sha,thresh=thresh,use_pat=use_pat,tok=tok,on_progress=on_prog)
     self._check_abort(jid)
     resp={
       "repo_url":repo_url,"commit_sha":commit_sha,"prediction_threshold":self._thresh(thresh),
       "clone_mode":"pat_temporary" if use_pat else "local_cache",
       "total_files_scanned":len(res),"results":res
     }
     hid=self.hist.save_run(resp) if self.hist else None
     self._patch(jid,status="completed",stage="completed",progress_percent=100,message="Prediction completed",result=resp,history_id=hid)
   except JobAbortedError:
     self._patch(jid,status="cancelled",stage="cancelled",progress_percent=100,message="Prediction job was cancelled",error="Prediction job was cancelled by the user.")
   except Exception as e:
     self._patch(jid,status="failed",stage="failed",progress_percent=100,message="Prediction failed",error=str(e))

  def _check_abort(self,jid:str):
   with self.mux:
     t=self.tasks.get(jid)
     if t and t.get("cancel_flag"):
       raise JobAbortedError()

  def _patch(self,jid:str,**kv):
   with self.mux:
     t=self.tasks.get(jid)
     if not t:return
     if t.get("status")=="cancelled" and kv.get("status")!="cancelled":return
     t.update(kv)
     t["updated_at"]=self._ts()

  def _view(self,t:dict)->dict:
   v=t.copy()
   v.pop("fut",None)
   v.pop("cancel_flag",None)
   return v

  def _ts(self)->str:
   return datetime.now(timezone.utc).isoformat()

  def _thresh(self,t:float=None)->float:
   return float(t) if t is not None else float(self.pipe.predictor.default_thresh)
