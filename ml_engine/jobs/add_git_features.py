import os,shutil,pandas as pd
from git import Repo
from collect_dataset import clone_repo,git_process_feats,slug_repo

DS="datasets/github_defect_dataset.csv"
BAK="datasets/github_defect_dataset_before_process_metrics.csv"
PCOLS=["file_change_count","file_bug_fix_count","recent_file_change_count","days_since_last_change","last_change_lines_added","last_change_lines_deleted","last_change_churn","last_change_file_count","author_file_change_count"]

def run_enrichment():
  if not os.path.exists(DS):raise FileNotFoundError(f"Dataset not found: {DS}")
  df=pd.read_csv(DS)
  for c in PCOLS:
    if c not in df.columns:df[c]=pd.NA
  if not (any(c not in df.columns for c in PCOLS) or df[PCOLS].isna().any().any()):
    print("Dataset already contains process metrics.")
    return
  shutil.copy2(DS,BAK)
  for u in df["repo_url"].dropna().unique().tolist():
    rdir=os.path.join("datasets","process_metric_repos",slug_repo(u))
    if os.path.exists(rdir):
      r=Repo(rdir);r.git.fetch("--all","--tags","--prune")
    else:
      r=clone_repo(u,rdir)
    for idx,row in df[df["repo_url"]==u].iterrows():
      if not pd.isna(row.get("file_change_count")):continue
      try:
        pm=git_process_feats(r,r.commit(row["commit_sha"]),row["file_path"])
        for k,v in pm.items():df.at[idx,k]=v
      except Exception as e:
        print(f"Skipped {str(row.get('commit_sha',''))[:8]} {row.get('file_path','')}: {e}")
  df[PCOLS]=df[PCOLS].fillna(0)
  df.to_csv(DS,index=False)
  print("Updated dataset:",DS,df.shape)

if __name__=="__main__":
  run_enrichment()
