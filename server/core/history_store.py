import uuid
from datetime import datetime,timezone
from settings import cfg
from core.db import DbStore,DbSession

EXTRA_COLS=[
  ("file_change_count","INTEGER DEFAULT 0"),
  ("file_bug_fix_count","INTEGER DEFAULT 0"),
  ("recent_file_change_count","INTEGER DEFAULT 0"),
  ("days_since_last_change","INTEGER DEFAULT 0"),
  ("last_change_churn","INTEGER DEFAULT 0"),
  ("author_file_change_count","INTEGER DEFAULT 0"),
  ("confidence_warning","TEXT"),
  ("is_potential_test_file","INTEGER DEFAULT 0"),
  ("test_file_reason","TEXT")
]

class HistoryStore:
  def __init__(self,db_file=None):
    self.db=DbStore(db_file or cfg.history_db_file)
    self.db_path=self.db.storage_label
    self._init_schema()

  def save_run(self,payload:dict)->str:
   rid=str(uuid.uuid4())
   rows=payload.get("results",[])
   agg=self._summarize(rows)
   ts=datetime.now(timezone.utc).isoformat()
   with self.db.open() as s:
     s.execute(
       "INSERT INTO prediction_runs (id,repo_url,commit_sha,prediction_threshold,scanned_at,total_files_scanned,high_risk_count,medium_risk_count,low_risk_count,defective_count,average_risk_probability) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
       (rid,payload.get("repo_url",""),payload.get("commit_sha",""),payload.get("prediction_threshold"),ts,
        payload.get("total_files_scanned",len(rows)),agg["high_risk_count"],agg["medium_risk_count"],
        agg["low_risk_count"],agg["defective_count"],agg["average_risk_probability"])
     )
     s.executemany(
       "INSERT INTO prediction_results (id,run_id,file_path,language,prediction_label,defect_risk_probability,risk_level,recommendation,file_change_count,file_bug_fix_count,recent_file_change_count,days_since_last_change,last_change_churn,author_file_change_count,top_contributing_metrics,readable_explanation,confidence_warning,is_potential_test_file,test_file_reason) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
       [(str(uuid.uuid4()),rid,r.get("file_path",""),r.get("language",""),r.get("prediction_label",""),
         r.get("defect_risk_probability",0),r.get("risk_level",""),r.get("recommendation",""),
         r.get("file_change_count",0),r.get("file_bug_fix_count",0),r.get("recent_file_change_count",0),
         r.get("days_since_last_change",0),r.get("last_change_churn",0),r.get("author_file_change_count",0),
         r.get("top_contributing_metrics",""),r.get("readable_explanation",""),r.get("confidence_warning",""),
         1 if r.get("is_potential_test_file",False) else 0,r.get("test_file_reason","")) for r in rows]
     )
   return rid

  def list_runs(self)->list:
   with self.db.open() as s:
     rows=s.execute("SELECT id,repo_url,commit_sha,prediction_threshold,scanned_at,total_files_scanned,high_risk_count,medium_risk_count,low_risk_count,defective_count,average_risk_probability FROM prediction_runs ORDER BY scanned_at DESC").fetchall()
   return [dict(r) for r in rows]

  def get_run(self,rid:str)->dict:
   with self.db.open() as s:
     run=s.execute("SELECT id,repo_url,commit_sha,prediction_threshold,scanned_at,total_files_scanned FROM prediction_runs WHERE id = ?",(rid,)).fetchone()
     if not run:
       return None
     items=s.execute("SELECT file_path,language,prediction_label,defect_risk_probability,risk_level,recommendation,file_change_count,file_bug_fix_count,recent_file_change_count,days_since_last_change,last_change_churn,author_file_change_count,top_contributing_metrics,readable_explanation,confidence_warning,is_potential_test_file,test_file_reason FROM prediction_results WHERE run_id = ? ORDER BY defect_risk_probability DESC",(rid,)).fetchall()
   d=dict(run)
   return {
     "history_id":d["id"],"repo_url":d["repo_url"],"commit_sha":d["commit_sha"],
     "prediction_threshold":d["prediction_threshold"],"scanned_at":d["scanned_at"],
     "total_files_scanned":d["total_files_scanned"],"results":[dict(r) for r in items]
   }

  def remove_run(self,rid:str)->bool:
   with self.db.open() as s:
     cur=s.execute("DELETE FROM prediction_runs WHERE id = ?",(rid,))
   return cur.rowcount>0

  def _init_schema(self):
   with self.db.open() as s:
     s.execute("CREATE TABLE IF NOT EXISTS prediction_runs (id TEXT PRIMARY KEY,repo_url TEXT NOT NULL,commit_sha TEXT NOT NULL,prediction_threshold REAL,scanned_at TEXT NOT NULL,total_files_scanned INTEGER NOT NULL,high_risk_count INTEGER NOT NULL,medium_risk_count INTEGER NOT NULL,low_risk_count INTEGER NOT NULL,defective_count INTEGER NOT NULL,average_risk_probability REAL NOT NULL)")
     s.execute("CREATE TABLE IF NOT EXISTS prediction_results (id TEXT PRIMARY KEY,run_id TEXT NOT NULL,file_path TEXT NOT NULL,language TEXT,prediction_label TEXT NOT NULL,defect_risk_probability REAL NOT NULL,risk_level TEXT NOT NULL,recommendation TEXT,file_change_count INTEGER DEFAULT 0,file_bug_fix_count INTEGER DEFAULT 0,recent_file_change_count INTEGER DEFAULT 0,days_since_last_change INTEGER DEFAULT 0,last_change_churn INTEGER DEFAULT 0,author_file_change_count INTEGER DEFAULT 0,top_contributing_metrics TEXT,readable_explanation TEXT,confidence_warning TEXT,is_potential_test_file INTEGER DEFAULT 0,test_file_reason TEXT,FOREIGN KEY (run_id) REFERENCES prediction_runs (id) ON DELETE CASCADE)")
     self._add_col(s,"prediction_runs","prediction_threshold","REAL")
     for col,ctype in EXTRA_COLS:
       self._add_col(s,"prediction_results",col,ctype)
     s.execute("CREATE INDEX IF NOT EXISTS idx_prediction_results_run_id ON prediction_results (run_id)")

  def _add_col(self,s:DbSession,tbl:str,col:str,cdef:str):
   if col not in self.db.table_cols(s,tbl):
     s.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {cdef}")

  def _summarize(self,rows:list)->dict:
   n=len(rows)
   prob_sum=sum(r.get("defect_risk_probability",0) for r in rows)
   return {
     "high_risk_count":sum(1 for r in rows if r.get("risk_level")=="High"),
     "medium_risk_count":sum(1 for r in rows if r.get("risk_level")=="Medium"),
     "low_risk_count":sum(1 for r in rows if r.get("risk_level")=="Low"),
     "defective_count":sum(1 for r in rows if r.get("prediction_label")=="Defective"),
     "average_risk_probability":prob_sum/n if n else 0
   }
