import os

class AppConfig:
  def __init__(self):
    self.server_dir=os.path.dirname(os.path.abspath(__file__))
    self.root_dir=os.path.dirname(self.server_dir)
    self.ml_dir=os.path.join(self.root_dir,"ml_engine")

    self.cors_origins=self._csv_env("ALLOWED_ORIGINS",["http://127.0.0.1:5173","http://localhost:5173","https://sdp-for-git-hub.vercel.app"])
    self.db_url=os.getenv("DATABASE_URL","").strip()
    self.history_db_file=os.getenv("PREDICTION_HISTORY_DB_PATH",os.path.join(self.server_dir,"storage","prediction_history.db"))
    self.temp_repo_dir=os.getenv("SDP_TEMP_REPO_DIR")
    self.local_cache_ok=self._bool_env("ALLOW_LOCAL_CACHE_MODE",True)
    self.history_delete_ok=self._bool_env("ALLOW_HISTORY_DELETE",True)
    self.max_files=self._opt_int_env("MAX_SOURCE_FILES_PER_RUN")
    self.max_workers=self._int_env("MAX_PREDICTION_WORKERS",2)
    self.shallow_depth=self._int_env("GIT_SHALLOW_HISTORY_DEPTH",80)
    self.git_timeout=self._int_env("GIT_COMMAND_TIMEOUT_SECONDS",420)

  def _csv_env(self,key:str,fallback:list[str])->list[str]:
   raw=os.getenv(key)
   if not raw:
     return fallback
   out=[x.strip().rstrip("/") for x in raw.split(",") if x.strip()]
   return out or fallback

  def _bool_env(self,key:str,fallback:bool)->bool:
   raw=os.getenv(key)
   if raw is None:
     return fallback
   return raw.strip().lower() in {"1","true","yes","on"}

  def _int_env(self,key:str,fallback:int)->int:
   raw=os.getenv(key)
   if not raw:
     return fallback
   return int(raw)

  def _opt_int_env(self,key:str)->int|None:
   raw=os.getenv(key)
   if not raw:
     return None
   return int(raw)

cfg=AppConfig()
