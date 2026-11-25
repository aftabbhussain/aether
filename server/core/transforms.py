import numpy as np
import pandas as pd

LOG_COLS=[
  "file_change_count",
  "file_bug_fix_count",
  "recent_file_change_count",
  "days_since_last_change",
  "last_change_lines_added",
  "last_change_lines_deleted",
  "last_change_churn",
  "last_change_file_count",
  "author_file_change_count"
]

COL_CAPS={
  "file_change_count":50,
  "file_bug_fix_count":20,
  "recent_file_change_count":20,
  "days_since_last_change":3650,
  "last_change_lines_added":1000,
  "last_change_lines_deleted":1000,
  "last_change_churn":1500,
  "last_change_file_count":30,
  "author_file_change_count":30
}

def apply_feature_transforms(df:pd.DataFrame,stats:dict=None)->pd.DataFrame:
  out=df.copy()
  for col in LOG_COLS:
    if col not in out.columns:
      continue
    cap=COL_CAPS.get(col)
    vals=pd.to_numeric(out[col],errors="coerce").fillna(0).clip(lower=0)
    if cap is not None:
      vals=vals.clip(upper=cap)
    out[col]=np.log1p(vals)
  if stats:
    out=zscore_process_cols(out,stats)
  return out

def zscore_process_cols(df:pd.DataFrame,stats:dict)->pd.DataFrame:
  out=df.copy()
  scaling=stats.get("process_metric_scaling",{})
  for col,st in scaling.items():
    if col not in out.columns:
      continue
    mu=float(st.get("mean",0))
    sd=float(st.get("std",1)) or 1
    out[col]=(out[col]-mu)/sd
  return out
