import pandas as pd

df=pd.read_csv("datasets/github_defect_dataset.csv")
print("Shape:",df.shape)
print(df["defect"].value_counts())
print(df["repo_url"].value_counts())
if "language" in df.columns:
  print(df["language"].value_counts())
  print(pd.crosstab(df["language"],df["defect"]))
cols=["nosi","dit","cbo","rfc","loc","comparisonsQty","returnQty","wmc","lcom","totalMethods","file_change_count","file_bug_fix_count","recent_file_change_count","days_since_last_change","last_change_lines_added","last_change_lines_deleted","last_change_churn","last_change_file_count","author_file_change_count"]
print(df.groupby("defect")[[c for c in cols if c in df.columns]].mean())
print("Duplicates:",df.duplicated(subset=["repo_url","commit_sha","file_path","defect"]).sum())
df.to_csv("datasets/github_defect_dataset_analysis.csv",index=False)
