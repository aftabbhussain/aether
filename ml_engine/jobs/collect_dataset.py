import os,shutil,re,tempfile
from datetime import timezone
import pandas as pd
from git import Repo
from parse_code_metrics import EXTS,extract_source_metrics

BUG_KWS=["fix","fixed","fixes","bug","bugfix","defect","fault","crash","exception","error","failure","broken","incorrect"]
NON_BUG_KWS=["feature","refactor","docs","style","cleanup","rename","format","comment","update","add","remove","improve"]
SKIP_PATHS=["/test/","\\test\\","/tests/","\\tests\\","/target/","\\target\\","/build/","\\build\\","/generated/","\\generated\\","/vendor/","\\vendor\\","/third_party/","\\third_party\\","/node_modules/","\\node_modules\\","/dist/","\\dist\\"]
BOT_KWS=["dependabot","renovate","github-actions","pre-commit-ci"]

def is_fix_msg(m):
  m=m.lower()
  return any(re.search(rf"\b{re.escape(k)}\b",m) for k in BUG_KWS)

def is_feat_msg(m):
  m=m.lower()
  return any(re.search(rf"\b{re.escape(k)}\b",m) for k in NON_BUG_KWS)

def is_merge(c,m):
  if len(c.parents)>1:return True
  ml=m.lower()
  return any(k in ml for k in ["merge branch","merge pull request","merge remote","merge origin","merge main","merge master","merged","resolving conflicts","resolved conflict","conflict"])

def is_bot(c):
  who=f"{c.author.name} {c.author.email}".lower()
  return any(k in who for k in BOT_KWS)

def skip_file(fp):
  lp=fp.lower()
  if os.path.splitext(lp)[1] not in EXTS:return True
  if any(k in lp for k in SKIP_PATHS):return True
  fn=os.path.basename(lp)
  if fn.startswith("test") or fn.endswith(("_test.py","_test.cpp","_test.cc","_test.cxx")):return True
  return False

def slug_repo(u):
  return re.sub(r"[^a-zA-Z0-9_-]","_",u.rstrip("/").replace(".git","").split("/")[-1])[:24]

def clone_repo(url,out_dir):
  if os.path.exists(out_dir):shutil.rmtree(out_dir)
  r=Repo.clone_from(url,out_dir,multi_options=["--config","core.longpaths=true"],allow_unsafe_options=True)
  r.git.config("core.longpaths","true")
  return r

def utc_dt(v):
  return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)

def git_process_feats(repo,c,fp):
  gp=str(fp).replace(os.sep,"/")
  try:hist=list(repo.iter_commits(rev=c.hexsha,paths=gp,max_count=200))
  except Exception:hist=[]
  prior=[x for x in hist if x.hexsha!=c.hexsha]
  rec=0;fixes=0;auth=0;gap=9999;ins=0;dels=0;churn=0;fcnt=0
  au_key=f"{c.author.name} {c.author.email}".strip().lower()
  cdt=utc_dt(c.committed_datetime)
  for h in prior:
    if max(0,(cdt-utc_dt(h.committed_datetime)).days)<=90:rec+=1
    if is_fix_msg(h.message):fixes+=1
    if f"{h.author.name} {h.author.email}".strip().lower()==au_key:auth+=1
  if prior:
    prev=prior[0]
    gap=max(0,(cdt-utc_dt(prev.committed_datetime)).days)
    st=prev.stats.files
    hit=st.get(gp)
    if not hit:
      m=[k for k in st if str(k).replace(os.sep,"/").endswith(gp) or gp.endswith(str(k).replace(os.sep,"/"))]
      hit=st.get(m[0],{}) if m else {}
    ins=int(hit.get("insertions",0) or 0)
    dels=int(hit.get("deletions",0) or 0)
    churn=ins+dels
    fcnt=len(st)
  return {"file_change_count":len(prior),"file_bug_fix_count":fixes,"recent_file_change_count":rec,"days_since_last_change":gap,"last_change_lines_added":ins,"last_change_lines_deleted":dels,"last_change_churn":churn,"last_change_file_count":fcnt,"author_file_change_count":auth}

def collect_repo(url,max_commits=500,max_rows=800):
  rname=slug_repo(url)
  rdir=os.path.join(tempfile.gettempdir(),"sdpds",rname)
  repo=clone_repo(url,rdir)
  rows=[];seen=set()
  for idx,c in enumerate(list(repo.iter_commits("--all",max_count=max_commits)),start=1):
    try:
      if len(rows)>=max_rows:break
      sha=c.hexsha
      msg=c.message.strip().replace("\n"," ")
      if is_merge(c,msg) or is_bot(c):continue
      lbl=1 if is_fix_msg(msg) else (0 if is_feat_msg(msg) else None)
      if lbl is None or not c.parents:continue
      changed=[d.b_path for d in c.parents[0].diff(c) if d.b_path and not skip_file(d.b_path)]
      if not changed:continue
      print(f"[{rname}] [{idx}] {sha[:8]} | defect={lbl}")
      for fp in changed:
        try:
          if len(rows)>=max_rows:break
          if (sha,fp) in seen:continue
          seen.add((sha,fp))
          co=c.parents[0].hexsha if lbl==1 and c.parents else sha
          repo.git.reset("--hard");repo.git.clean("-fd");repo.git.checkout(co)
          full=os.path.join(rdir,fp)
          if not os.path.exists(full):continue
          m=extract_source_metrics(full)
          m.update(git_process_feats(repo,c,fp))
          m.update({"repo_name":rname,"repo_url":url,"commit_sha":sha,"source_commit_used":co,"file_path":fp,"commit_message":msg,"defect":lbl})
          rows.append(m)
        except Exception as e:print(f"Skipped file {fp}: {e}")
    except Exception as e:print(f"Skipped commit {c.hexsha[:8]}: {e}")
  return rows

def load_repos(path="datasets/repositories.txt"):
  with open(path,"r",encoding="utf-8") as f:
    return [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]

if __name__=="__main__":
  mc=int(input("Enter max commits per repo, example 500: ").strip() or 500)
  mr=int(input("Enter max rows per repo, example 800: ").strip() or 800)
  all_rows=[]
  for u in load_repos():
    try:all_rows.extend(collect_repo(u,mc,mr))
    except Exception as e:print(f"Failed repository {u}: {e}")
  df=pd.DataFrame(all_rows)
  if df.empty:raise ValueError("No dataset rows were collected.")
  os.makedirs("datasets",exist_ok=True)
  out="datasets/github_defect_dataset.csv"
  if os.path.exists(out):shutil.copy2(out,"datasets/github_defect_dataset_latest_backup.csv")
  df.drop_duplicates(subset=["repo_url","commit_sha","file_path","defect"],keep="first").to_csv(out,index=False)
  print("Saved:",out,df.shape)
