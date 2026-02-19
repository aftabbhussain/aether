import os,shutil,pandas as pd
from collect_dataset import collect_repo,load_repos

DS="datasets/github_defect_dataset.csv"
APP="datasets/repositories_append.txt"
BAK="datasets/github_defect_dataset_before_append.csv"

def append_repos(mc:int,mr:int):
  if not os.path.exists(DS):raise FileNotFoundError(f"Dataset not found: {DS}")
  old=pd.read_csv(DS)
  repos=load_repos(APP)
  if not repos:raise ValueError(f"No repositories found in {APP}.")
  seen=set(old.get("repo_url",pd.Series(dtype=str)).dropna())
  new_rows=[]
  for u in repos:
    if u in seen:continue
    try:new_rows.extend(collect_repo(u,mc,mr))
    except Exception as e:print(f"Failed repository {u}: {e}")
  if not new_rows:raise ValueError("No new rows were collected.")
  comb=pd.concat([old,pd.DataFrame(new_rows)],ignore_index=True).drop_duplicates(subset=["repo_url","commit_sha","file_path","defect"],keep="first")
  shutil.copy2(DS,BAK)
  comb.to_csv(DS,index=False)
  print("Combined shape:",comb.shape)

if __name__=="__main__":
  mc=int(input("Enter max commits per new repo, example 300: ").strip() or 300)
  mr=int(input("Enter max rows per new repo, example 500: ").strip() or 500)
  append_repos(mc,mr)
