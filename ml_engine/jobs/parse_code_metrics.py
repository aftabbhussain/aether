import os,re,pandas as pd

EXTS={".java",".py",".cpp",".cc",".cxx",".hpp",".h",".hh"}

def java_metrics(fp):
  with open(fp,"r",encoding="utf-8",errors="ignore") as f:src=f.read()
  clean=[l.strip() for l in src.splitlines() if l.strip() and not l.strip().startswith(("//","*","/*"))]
  n_m=len(re.findall(r"(public|private|protected|static|\s)+[\w\<\>\[\]]+\s+\w+\s*\([^)]*\)\s*\{",src))
  if_q=len(re.findall(r"\bif\s*\(",src))
  for_q=len(re.findall(r"\bfor\s*\(",src))
  whl_q=len(re.findall(r"\bwhile\s*\(",src))
  sw_q=len(re.findall(r"\bswitch\s*\(",src))
  cat_q=len(re.findall(r"\bcatch\s*\(",src))
  cmp_q=len(re.findall(r"==|!=|<=|>=|<|>",src))
  asg_q=len(re.findall(r"(?<![=!<>])=(?!=)",src))
  ret_q=len(re.findall(r"\breturn\b",src))
  nosi=len(re.findall(r"\b[A-Z][A-Za-z0-9_]*\.[a-zA-Z_][A-Za-z0-9_]*\s*\(",src))
  dit=2 if re.search(r"\bextends\b",src) else 1
  cbo=len(re.findall(r"\bimport\s+",src))+len(re.findall(r"\bnew\s+[A-Z][A-Za-z0-9_]*\s*\(",src))
  rfc=len(re.findall(r"\.\s*[a-zA-Z_][A-Za-z0-9_]*\s*\(",src))
  wmc=n_m+if_q+for_q+whl_q+sw_q+cat_q
  flds=len(re.findall(r"(private|protected|public)\s+[\w\<\>\[\]]+\s+\w+\s*;",src))
  lcom=max(0,n_m-flds) if n_m>0 else 0
  return {"file_path":fp,"language":"Java","nosi":nosi,"dit":dit,"cbo":cbo,"rfc":rfc,"loc":len(clean),"comparisonsQty":cmp_q,"returnQty":ret_q,"wmc":wmc,"lcom":lcom,"totalMethods":n_m,"loopQty":for_q+whl_q,"assignmentsQty":asg_q,"maxNestedBlocks":brace_depth(src)}

def python_metrics(fp):
  with open(fp,"r",encoding="utf-8",errors="ignore") as f:src=f.read()
  lines=src.splitlines()
  clean=[l.strip() for l in lines if l.strip() and not l.strip().startswith(("#",'"""',"'''"))]
  n_m=len(re.findall(r"^\s*(def|async\s+def)\s+\w+\s*\(",src,re.MULTILINE))
  if_q=len(re.findall(r"\bif\b",src))
  for_q=len(re.findall(r"\bfor\b",src))
  whl_q=len(re.findall(r"\bwhile\b",src))
  exc_q=len(re.findall(r"\bexcept\b",src))
  mat_q=len(re.findall(r"\bmatch\b",src))
  cmp_q=len(re.findall(r"==|!=|<=|>=|<|>|(?:\bis\b)|(?:\bin\b)",src))
  asg_q=len(re.findall(r"(?<![=!<>])=(?!=)",src))
  ret_q=len(re.findall(r"\breturn\b",src))
  imp=len(re.findall(r"^\s*(import|from)\s+",src,re.MULTILINE))
  clss=re.findall(r"^\s*class\s+([A-Z][A-Za-z0-9_]*)",src,re.MULTILINE)
  obj=len(re.findall(rf"\b({'|'.join(re.escape(c) for c in clss)})\s*\(",src)) if clss else 0
  nosi=len(re.findall(r"\b[A-Z][A-Za-z0-9_]*\.[a-zA-Z_][A-Za-z0-9_]*\s*\(",src))
  dit=2 if re.search(r"^\s*class\s+\w+\s*\([^)]",src,re.MULTILINE) else 1
  rfc=len(re.findall(r"\.\s*[a-zA-Z_][A-Za-z0-9_]*\s*\(",src))
  wmc=n_m+if_q+for_q+whl_q+exc_q+mat_q
  flds=len(re.findall(r"\bself\.[a-zA-Z_][A-Za-z0-9_]*\s*=",src))
  lcom=max(0,n_m-flds) if n_m>0 else 0
  return {"file_path":fp,"language":"Python","nosi":nosi,"dit":dit,"cbo":imp+obj,"rfc":rfc,"loc":len(clean),"comparisonsQty":cmp_q,"returnQty":ret_q,"wmc":wmc,"lcom":lcom,"totalMethods":n_m,"loopQty":for_q+whl_q,"assignmentsQty":asg_q,"maxNestedBlocks":indent_depth(lines)}

def cpp_metrics(fp):
  with open(fp,"r",encoding="utf-8",errors="ignore") as f:src=f.read()
  clean=[l.strip() for l in src.splitlines() if l.strip() and not l.strip().startswith(("//","*","/*"))]
  n_m=len(re.findall(r"(?:^|[;\n}])\s*(?:[\w:<>\*&]+\s+)+[A-Za-z_][A-Za-z0-9_:]*\s*\([^;{}]*\)\s*(?:const\s*)?\{",src))
  if_q=len(re.findall(r"\bif\s*\(",src))
  for_q=len(re.findall(r"\bfor\s*\(",src))
  whl_q=len(re.findall(r"\bwhile\s*\(",src))
  sw_q=len(re.findall(r"\bswitch\s*\(",src))
  cat_q=len(re.findall(r"\bcatch\s*\(",src))
  cmp_q=len(re.findall(r"==|!=|<=|>=|<|>",src))
  asg_q=len(re.findall(r"(?<![=!<>])=(?!=)",src))
  ret_q=len(re.findall(r"\breturn\b",src))
  nosi=len(re.findall(r"\b[A-Z][A-Za-z0-9_]*::[a-zA-Z_][A-Za-z0-9_]*\s*\(",src))
  dit=2 if re.search(r"\bclass\s+\w+\s*:\s*(public|private|protected)\s+",src) else 1
  imp=len(re.findall(r"^\s*#\s*include\b|^\s*using\s+namespace\b",src,re.MULTILINE))
  obj=len(re.findall(r"\bnew\s+[A-Z][A-Za-z0-9_:]*\s*(?:\(|;)",src))
  rfc=len(re.findall(r"(?:\.|->|::)\s*[a-zA-Z_][A-Za-z0-9_]*\s*\(",src))
  wmc=n_m+if_q+for_q+whl_q+sw_q+cat_q
  flds=len(re.findall(r"(private|protected|public)\s*:\s*(?:[\s\S]*?;)",src))
  lcom=max(0,n_m-flds) if n_m>0 else 0
  return {"file_path":fp,"language":"C++","nosi":nosi,"dit":dit,"cbo":imp+obj,"rfc":rfc,"loc":len(clean),"comparisonsQty":cmp_q,"returnQty":ret_q,"wmc":wmc,"lcom":lcom,"totalMethods":n_m,"loopQty":for_q+whl_q,"assignmentsQty":asg_q,"maxNestedBlocks":brace_depth(src)}

def extract_source_metrics(fp):
  ext=os.path.splitext(fp)[1].lower()
  if ext==".java":return java_metrics(fp)
  if ext==".py":return python_metrics(fp)
  if ext in {".cpp",".cc",".cxx",".hpp",".h",".hh"}:return cpp_metrics(fp)
  raise ValueError(f"Unsupported source file extension: {ext}")

def brace_depth(src):
  mx=0;cur=0
  for ch in src:
    if ch=="{":cur+=1;mx=max(mx,cur)
    elif ch=="}":cur=max(0,cur-1)
  return mx

def indent_depth(lines):
  mx=0
  for l in lines:
    s=l.strip()
    if not s or s.startswith("#"):continue
    mx=max(mx,(len(l)-len(l.lstrip(" ")))//4)
  return mx

def scan_dir(proj_dir):
  rows=[]
  for r,_,files in os.walk(proj_dir):
    for f in files:
      if os.path.splitext(f)[1].lower() in EXTS:
        rows.append(extract_source_metrics(os.path.join(r,f)))
  return pd.DataFrame(rows)

if __name__=="__main__":
  df=scan_dir("sample_java_project")
  if df.empty:
    print("No supported Java, Python, or C++ files found.")
  else:
    os.makedirs("datasets",exist_ok=True)
    df.to_csv("datasets/prediction_input_source_sample.csv",index=False)
    print(df.head())
