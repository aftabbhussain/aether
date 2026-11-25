import os,shutil,re,uuid,stat,time,hashlib,tempfile,gc,json,subprocess
from threading import RLock
from urllib.parse import quote,urlparse,urlunparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from git import Git,Repo
from settings import cfg

class GitClient:
  def __init__(self,root_dir=None,ttl:int=300):
    self.root_dir=root_dir or cfg.temp_repo_dir or os.path.join(tempfile.gettempdir(),"sdp_github_temp_repos")
    self.trees_dir=os.path.join(self.root_dir,"worktrees")
    self.cache_dir=os.path.join(self.root_dir,"repo_cache")
    self.ttl=ttl
    self._meta_cache={}
    self._fetch_ts={}
    self._mux=RLock()
    os.makedirs(self.root_dir,exist_ok=True)
    os.makedirs(self.trees_dir,exist_ok=True)
    os.makedirs(self.cache_dir,exist_ok=True)

  def _slug(self,url:str)->str:
    nm=url.rstrip("/").replace(".git","").split("/")[-1]
    return re.sub(r"[^a-zA-Z0-9_-]","_",nm)

  def _mirror_dir(self,url:str)->str:
    h=hashlib.sha1(url.strip().lower().encode("utf-8")).hexdigest()[:12]
    return os.path.join(self.cache_dir,f"{self._slug(url)}_{h}.git")

  def _split_owner_repo(self,url:str)->tuple:
    parts=[p for p in urlparse(url).path.strip("/").split("/") if p]
    if len(parts)<2:
      raise ValueError("Repository URL must include both owner and repository name.")
    return parts[0],parts[1].removesuffix(".git")

  def _ckey(self,*items)->tuple:
    return tuple(str(x).strip().lower() for x in items)

  def _auth_url(self,url:str,tok:str=None)->str:
    if not tok:
      return url
    u=urlparse(url)
    return urlunparse((u.scheme,f"x-access-token:{quote(tok,safe='')}@{u.netloc}",u.path,u.params,u.query,u.fragment))

  def _scrub_err(self,err:Exception,url:str,tok:str=None)->Exception:
    msg=str(err)
    if tok:
      msg=msg.replace(tok,"***")
      msg=re.sub(r"https://x-access-token:[^@\s]+@github\.com/","https://github.com/",msg)
      msg=msg.replace(self._auth_url(url,tok),url)
    msg=re.sub(r"POST git-upload-pack[^\n\r]*","",msg)
    msg=re.sub(r"Updating files:\s*\d+%[^\n\r]*","",msg)
    msg=re.sub(r"Authorization:\s*Bearer\s+[^\s'\"]+","Authorization: Bearer ***",msg)
    msg=re.sub(r"\s+"," ",msg).strip()
    if "unable to create file" in msg and "Filename too long" in msg:
      return Exception("Git checkout failed because this repository contains file paths that are too long for the current Windows Git configuration. The backend requests Git long-path support, but Windows may still need long paths enabled system-wide.")
    low=msg.lower()
    if any(k in low for k in ["authentication failed","could not read username","repository not found"]):
      if tok:
        return Exception("GitHub authentication failed. Your Personal Access Token may be invalid, expired, or missing access to this repository. Check the token and try again.")
      return Exception("GitHub authentication failed or the repository is not accessible. Use a valid Personal Access Token or check the repository URL.")
    return Exception(msg)

  def _git_exec(self,args:list[str],url:str,tok:str=None,cwd:str=None):
    try:
      return subprocess.run(["git",*args],cwd=cwd,check=True,capture_output=True,text=True,timeout=cfg.git_timeout)
    except subprocess.TimeoutExpired:
      raise self._scrub_err(Exception("Git operation timed out. The repository may be too large or the hosting server may be slow. Try again later or use a smaller commit."),url,tok)
    except subprocess.CalledProcessError as e:
      out="\n".join(x for x in [e.stdout,e.stderr] if x)
      raise self._scrub_err(Exception(out or str(e)),url,tok)

  def _shallow_fetch(self,url:str,dest:str,sha:str,tok:str=None)->bool:
    d=max(2,int(cfg.shallow_depth))
    auth=["-c",f"http.extraHeader=Authorization: Bearer {tok}"] if tok else []
    os.makedirs(dest,exist_ok=True)
    self._git_exec(["-C",dest,"-c","core.longpaths=true","init"],url,tok)
    self._git_exec(["-C",dest,"remote","add","origin",url],url,tok)
    self._git_exec(["-C",dest,*auth,"fetch","--no-tags",f"--depth={d}","origin",sha],url,tok)
    self._git_exec(["-C",dest,"-c","core.longpaths=true","checkout","--force","FETCH_HEAD"],url,tok)
    return True

  def _gh_get(self,path:str,tok:str=None):
    hdrs={"Accept":"application/vnd.github+json","User-Agent":"Aether","X-GitHub-Api-Version":"2022-11-28"}
    if tok:
      hdrs["Authorization"]=f"Bearer {tok}"
    req=Request(f"https://api.github.com{path}",headers=hdrs)
    try:
      with urlopen(req,timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
      body=e.read().decode("utf-8",errors="ignore")
      if e.code in {401,403}:
        raise Exception("Your GitHub Personal Access Token may be invalid, expired, or missing access to this repository. Check the token and make sure it has read access to repository contents and metadata." if tok else "GitHub denied the request. Add a valid Personal Access Token or try again later.")
      if e.code==404:
        raise Exception("GitHub could not find this repository, branch, tag, or commit. Check the repository URL and selected reference.")
      raise Exception(f"GitHub API request failed with status {e.code}. {body}")
    except URLError as e:
      raise Exception(f"GitHub API request failed: {e.reason}")

  def _cache_get(self,k:tuple):
    hit=self._meta_cache.get(k)
    if not hit:return None
    ts,val=hit
    if time.time()-ts>self.ttl:
      self._meta_cache.pop(k,None)
      return None
    return val

  def _cache_put(self,k:tuple,v):
    self._meta_cache[k]=(time.time(),v)

  def _ensure_mirror(self,url:str)->str:
    mdir=self._mirror_dir(url)
    with self._mux:
      exists=os.path.exists(mdir)
      fresh=time.time()-self._fetch_ts.get(mdir,0)<=self.ttl
      if not exists:
        print(f"Creating repository cache: {url}")
        Repo.clone_from(url,mdir,multi_options=["--mirror","-c","core.longpaths=true"],allow_unsafe_options=True)
        self._fetch_ts[mdir]=time.time()
        return mdir
      if fresh:
        return mdir
      r=None
      try:
        print(f"Refreshing repository cache: {url}")
        r=Repo(mdir)
        r.git.fetch("--prune","--tags","origin")
        self._fetch_ts[mdir]=time.time()
      except Exception as e:
        print(f"Warning: failed to refresh cache for {url}: {e}")
      finally:
        self._close(r)
      return mdir

  def _chmod_rm(self,fn,p,exc):
    try:
      os.chmod(p,stat.S_IWRITE)
      fn(p)
    except PermissionError:
      time.sleep(0.2)
      os.chmod(p,stat.S_IWRITE)
      fn(p)

  def checkout_commit(self,url:str,sha:str,use_pat:bool=False,tok:str=None)->str:
    dest=os.path.join(self.trees_dir,f"{self._slug(url)}_{str(uuid.uuid4())[:8]}")
    if use_pat:
      print(f"Fetching selected commit into temporary worktree: {url}")
      try:
        self._shallow_fetch(url,dest,sha,tok)
        return dest
      except Exception as e:
        if "timed out" in str(e).lower():
          raise self._scrub_err(e,url,tok)
        print("Warning: shallow commit fetch failed. Falling back to normal temporary clone.")
        self.remove_tree(dest)
        try:
          r=Repo.clone_from(self._auth_url(url,tok),dest,multi_options=["-c","core.longpaths=true"],allow_unsafe_options=True)
        except Exception as fb_err:
          raise self._scrub_err(fb_err,url,tok)
    else:
      mdir=self._ensure_mirror(url)
      print(f"Cloning repository from local cache: {url}")
      try:
        r=Repo.clone_from(mdir,dest,multi_options=["-c","core.longpaths=true"],allow_unsafe_options=True)
      except Exception as e:
        raise self._scrub_err(e,url,tok)
    try:
      print(f"Checking out commit: {sha}")
      r.git.checkout(sha)
    finally:
      self._close(r)
    return dest

  def remove_tree(self,dest:str):
    if not dest or not os.path.exists(dest):
      return
    last_err=None
    for i in range(1,6):
      try:
        gc.collect()
        shutil.rmtree(dest,onerror=self._chmod_rm)
        print(f"Cleaned up temp repo: {dest}")
        return
      except Exception as e:
        last_err=e
        time.sleep(0.35*i)
    try:
      os.rename(dest,f"{dest}_cleanup_pending_{int(time.time())}")
    except Exception:
      print(f"Warning: failed to clean temp repo {dest}: {last_err}")

  def fetch_commits(self,url:str,ref:str,limit:int=20,offset:int=0,use_pat:bool=False,tok:str=None)->list:
    k=self._ckey("commits",url,ref,limit,offset,"pat" if use_pat else "cache")
    if not use_pat:
      with self._mux:
        hit=self._cache_get(k)
      if hit is not None:
        return hit
    try:
      owner,name=self._split_owner_repo(url)
      pg=(offset//limit)+1 if limit>0 else 1
      data=self._gh_get(f"/repos/{quote(owner)}/{quote(name)}/commits?sha={quote(ref,safe='')}&per_page={limit}&page={pg}",tok)
      out=[]
      for it in data:
        c=it.get("commit",{})
        au=c.get("author") or {}
        out.append({
          "sha":it.get("sha",""),
          "short_sha":it.get("sha","")[:8],
          "message":(c.get("message") or "").strip().replace("\n"," "),
          "author":au.get("name") or "Unknown",
          "date":au.get("date") or ""
        })
      if not use_pat:
        with self._mux:
          self._cache_put(k,out)
      return out
    except Exception as e:
      raise self._scrub_err(e,url,tok)

  def fetch_branches(self,url:str,use_pat:bool=False,tok:str=None)->list:
    k=self._ckey("branches",url,"pat" if use_pat else "cache")
    if not use_pat:
      with self._mux:
        hit=self._cache_get(k)
      if hit is not None:
        return hit
    remote=self._auth_url(url,tok)
    def_br=self._default_branch(remote)
    try:
      raw=Git().ls_remote("--heads",remote)
    except Exception as e:
      raise self._scrub_err(e,url,tok)
    out=[]
    for ln in raw.splitlines():
      pts=ln.split()
      if len(pts)>=2 and pts[1].startswith("refs/heads/"):
        bn=pts[1].replace("refs/heads/","",1)
        out.append({"name":bn,"type":"branch","is_default":bn==def_br})
    out.sort(key=lambda b:(not b.get("is_default",False),b["name"].lower()))
    if not use_pat:
      with self._mux:
        self._cache_put(k,out)
    return out

  def _default_branch(self,remote:str)->str:
    try:
      raw=Git().ls_remote("--symref",remote,"HEAD")
    except Exception:
      return ""
    for ln in raw.splitlines():
      pts=ln.split()
      if len(pts)>=3 and pts[0]=="ref:" and pts[1].startswith("refs/heads/"):
        return pts[1].replace("refs/heads/","",1)
    return ""

  def fetch_tags(self,url:str,use_pat:bool=False,tok:str=None)->list:
    k=self._ckey("tags",url,"pat" if use_pat else "cache")
    if not use_pat:
      with self._mux:
        hit=self._cache_get(k)
      if hit is not None:
        return hit
    remote=self._auth_url(url,tok)
    try:
      raw=Git().ls_remote("--tags",remote)
    except Exception as e:
      raise self._scrub_err(e,url,tok)
    out=[]
    for ln in raw.splitlines():
      pts=ln.split()
      if len(pts)>=2 and pts[1].startswith("refs/tags/") and not pts[1].endswith("^{}"):
        out.append({"name":pts[1].replace("refs/tags/","",1),"type":"tag"})
    out.sort(key=lambda t:t["name"].lower())
    if not use_pat:
      with self._mux:
        self._cache_put(k,out)
    return out

  def _close(self,r):
    if not r:return
    try:r.close()
    except Exception:pass
    try:r.git.clear_cache()
    except Exception:pass
