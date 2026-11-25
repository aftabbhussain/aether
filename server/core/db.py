import os,sqlite3
from contextlib import AbstractContextManager
from settings import cfg

try:
  import psycopg
  from psycopg.rows import dict_row
except ImportError:
  psycopg=None
  dict_row=None

class DbSession(AbstractContextManager):
  def __init__(self,conn,pg:bool):
    self.conn=conn
    self.pg=pg
  def __enter__(self):
    return self
  def __exit__(self,exc_t,exc_v,tb):
    try:
      if exc_t is None:
        self.conn.commit()
      else:
        self.conn.rollback()
    finally:
      self.conn.close()
  def execute(self,q:str,params=None):
    return self.conn.execute(self._sql(q),params or ())
  def executemany(self,q:str,rows):
    if self.pg:
      c=self.conn.cursor()
      c.executemany(self._sql(q),rows)
      return c
    return self.conn.executemany(self._sql(q),rows)
  def _sql(self,q:str)->str:
    return q.replace("?","%s") if self.pg else q

class DbStore:
  def __init__(self,sqlite_file:str):
    self.sqlite_file=sqlite_file
    self.db_url=cfg.db_url
    self.pg=bool(self.db_url)
    if self.pg and psycopg is None:
      raise RuntimeError("DATABASE_URL is set but psycopg is not installed. Install psycopg[binary].")
    if not self.pg:
      os.makedirs(os.path.dirname(self.sqlite_file),exist_ok=True)
  @property
  def storage_label(self)->str:
    return "postgresql" if self.pg else self.sqlite_file
  def open(self):
    if self.pg:
      return DbSession(psycopg.connect(self.db_url,row_factory=dict_row),True)
    c=sqlite3.connect(self.sqlite_file)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return DbSession(c,False)
  def table_cols(self,sess:DbSession,tbl:str)->set[str]:
    if self.pg:
      rows=sess.execute("SELECT column_name FROM information_schema.columns WHERE table_name = ?",(tbl,)).fetchall()
      return {r["column_name"] for r in rows}
    rows=sess.execute(f"PRAGMA table_info({tbl})").fetchall()
    return {r["name"] for r in rows}
