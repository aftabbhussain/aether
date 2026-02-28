import uuid
from datetime import datetime,timezone
from core.db import DbStore

class FeedbackStore:
  def __init__(self,db_file:str):
    self.db=DbStore(db_file)
    self.db_path=self.db.storage_label
    self._init_tbl()

  def add_entry(self,name:str="",role:str="",rating:int=5,message:str="")->dict:
    nm=(name or "").strip()[:80]
    rl=(role or "").strip()[:80]
    msg=(message or "").strip()
    if not msg:
      raise ValueError("Feedback message is required.")
    if rating<1 or rating>5:
      raise ValueError("Rating must be between 1 and 5.")
    rec={
      "id":str(uuid.uuid4()),
      "name":nm,
      "role":rl,
      "rating":int(rating),
      "message":msg[:1200],
      "submitted_at":datetime.now(timezone.utc).isoformat()
    }
    with self.db.open() as s:
      s.execute("INSERT INTO feedback_entries (id,name,role,rating,message,submitted_at) VALUES (?,?,?,?,?,?)",
        (rec["id"],rec["name"],rec["role"],rec["rating"],rec["message"],rec["submitted_at"]))
    return rec

  def all_entries(self)->list:
    with self.db.open() as s:
      rows=s.execute("SELECT id,name,role,rating,message,submitted_at FROM feedback_entries ORDER BY submitted_at DESC").fetchall()
    return [dict(r) for r in rows]

  def _init_tbl(self):
    with self.db.open() as s:
      s.execute("CREATE TABLE IF NOT EXISTS feedback_entries (id TEXT PRIMARY KEY,name TEXT,role TEXT,rating INTEGER NOT NULL,message TEXT NOT NULL,submitted_at TEXT NOT NULL)")
