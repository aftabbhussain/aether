import os,re
from datetime import datetime,timezone
import pandas as pd
from git import Repo

FIX_WORDS=["fix","fixed","fixes","bug","bugfix","defect","fault","crash","exception","error","failure","broken","incorrect"]

class GitProcessMetrics:
  def __init__(self,max_hist:int=200,window_days:int=90):
    self.max_hist=max_hist
    self.window_days=window_days

  def attach(self,df:pd.DataFrame,repo_dir:str,sha:str)->pd.DataFrame:
   if df.empty:
     return df
   repo=Repo(repo_dir)
   try:
     tgt=repo.commit(sha)
     out=[]
     for _,r in df.iterrows():
       p=str(r["file_path"]).replace(os.sep,"/")
       pm=self._file_metrics(repo,tgt,p)
       d=r.to_dict()
       d.update(pm)
       out.append(d)
     return pd.DataFrame(out)
   finally:
     try:repo.close()
     except Exception:pass
     try:repo.git.clear_cache()
     except Exception:pass

  def _file_metrics(self,repo:Repo,tgt,fpath:str)->dict:
   try:
     commits=list(repo.iter_commits(rev=tgt.hexsha,paths=fpath,max_count=self.max_hist))
   except Exception:
     commits=[]
   prior=[c for c in commits if c.hexsha!=tgt.hexsha]
   rec_cnt=0
   fix_cnt=0
   auth_cnt=0
   days_gap=9999
   add_l=0
   del_l=0
   churn=0
   f_cnt=0
   tgt_auth=f"{tgt.author.name} {tgt.author.email}".strip().lower()
   tgt_dt=self._utc(tgt.committed_datetime)
   for c in prior:
     c_dt=self._utc(c.committed_datetime)
     if max(0,(tgt_dt-c_dt).days)<=self.window_days:
       rec_cnt+=1
     msg=(c.message or "").lower()
     if any(re.search(rf"\b{re.escape(w)}\b",msg) for w in FIX_WORDS):
       fix_cnt+=1
     if f"{c.author.name} {c.author.email}".strip().lower()==tgt_auth:
       auth_cnt+=1
   if prior:
     prev=prior[0]
     days_gap=max(0,(tgt_dt-self._utc(prev.committed_datetime)).days)
     st=self._diff_stats(prev,fpath)
     add_l=st["ins"]
     del_l=st["dels"]
     churn=add_l+del_l
     f_cnt=len(prev.stats.files)
   return {
     "file_change_count":len(prior),
     "file_bug_fix_count":fix_cnt,
     "recent_file_change_count":rec_cnt,
     "days_since_last_change":days_gap,
     "last_change_lines_added":add_l,
     "last_change_lines_deleted":del_l,
     "last_change_churn":churn,
     "last_change_file_count":f_cnt,
     "author_file_change_count":auth_cnt
   }

  def _diff_stats(self,commit,fpath:str)->dict:
   files=commit.stats.files
   norm=str(fpath).replace(os.sep,"/")
   hit=files.get(norm)
   if not hit:
     cand=[k for k in files if str(k).replace(os.sep,"/").endswith(norm) or norm.endswith(str(k).replace(os.sep,"/"))]
     hit=files.get(cand[0],{}) if cand else {}
   return {"ins":int(hit.get("insertions",0) or 0),"dels":int(hit.get("deletions",0) or 0)}

  def _utc(self,dt:datetime)->datetime:
   return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
