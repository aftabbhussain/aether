from typing import Optional
from pydantic import BaseModel

class RepoPayload(BaseModel):
    repo_url: str
    use_pat: bool = False
    github_token: Optional[str] = None

class PredictPayload(RepoPayload):
    commit_sha: str
    threshold: Optional[float] = None
