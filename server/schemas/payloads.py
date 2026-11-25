from typing import List,Optional
from urllib.parse import urlparse
from pydantic import BaseModel,validator

def clean_github_url(url:str)->str:
  s=url.strip()
  u=urlparse(s)
  if u.scheme not in {"http","https"}:
    raise ValueError("Repository URL must start with http:// or https://.")
  if u.netloc.lower()!="github.com":
    raise ValueError("Only github.com repository URLs are supported.")
  segs=[p for p in u.path.strip("/").split("/") if p]
  if len(segs)!=2:
    raise ValueError("Repository URL must use the format https://github.com/owner/repository.")
  owner,repo=segs
  if not owner or not repo:
    raise ValueError("Repository URL must include both owner and repository name.")
  repo=repo.removesuffix(".git")
  if not repo:
    raise ValueError("Repository name cannot be empty.")
  return f"https://github.com/{owner}/{repo}.git"

class RepoPayload(BaseModel):
  repo_url:str
  use_personal_access_token:bool=False
  github_token:Optional[str]=None

  @validator("repo_url")
  def check_repo_url(cls,v:str)->str:
   return clean_github_url(v)

  @validator("github_token")
  def check_token(cls,v:Optional[str])->Optional[str]:
   if v is None:
     return v
   t=v.strip()
   return t or None

class PredictPayload(RepoPayload):
  commit_sha:str
  prediction_threshold:Optional[float]=None

  @validator("prediction_threshold")
  def check_thresh(cls,v:Optional[float])->Optional[float]:
   if v is None:
     return v
   if v<0.05 or v>0.95:
     raise ValueError("Prediction threshold must be between 0.05 and 0.95.")
   return v

class CommitsPayload(RepoPayload):
  git_ref:str
  max_commits:int=20
  skip:int=0

class RefsPayload(RepoPayload):
  pass

class FeedbackPayload(BaseModel):
  name:Optional[str]=""
  role:Optional[str]=""
  rating:int
  message:str

  @validator("rating")
  def check_rating(cls,v:int)->int:
   if v<1 or v>5:
     raise ValueError("Rating must be between 1 and 5.")
   return v

  @validator("message")
  def check_msg(cls,v:str)->str:
   txt=v.strip()
   if not txt:
     raise ValueError("Feedback message is required.")
   if len(txt)>1200:
     raise ValueError("Feedback message must be 1200 characters or fewer.")
   return txt

class ExportRow(BaseModel):
  file_path:str
  language:Optional[str]=""
  prediction_label:str
  defect_risk_probability:float
  risk_level:str
  recommendation:str
  file_change_count:Optional[int]=0
  file_bug_fix_count:Optional[int]=0
  recent_file_change_count:Optional[int]=0
  days_since_last_change:Optional[int]=0
  last_change_churn:Optional[int]=0
  author_file_change_count:Optional[int]=0
  top_contributing_metrics:str
  readable_explanation:Optional[str]=""
  confidence_warning:Optional[str]=""
  is_potential_test_file:Optional[bool]=False
  test_file_reason:Optional[str]=""

class ExportPayload(RepoPayload):
  commit_sha:str
  prediction_threshold:Optional[float]=None
  total_files_scanned:int
  results:List[ExportRow]
