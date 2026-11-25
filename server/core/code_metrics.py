import os,re,pandas as pd
from settings import cfg

LANG_MAP={".java":"Java",".py":"Python",".cpp":"C++",".cc":"C++",".cxx":"C++",".hpp":"C++",".h":"C++",".hh":"C++"}
SKIP_DIRS=["/.git/","/target/","/build/","/generated/","/vendor/","/third_party/","/node_modules/","/dist/"]

class CodeMetricsExtractor:
  MAX_FILES=cfg.max_files

  def scan_repo(self,repo_dir:str,only_files:list[str]=None)->pd.DataFrame:
   if only_files is not None:
     return self._scan_subset(repo_dir,only_files)
   rows=[]
   for root,dirs,files in os.walk(repo_dir):
     dirs[:]=[d for d in dirs if not self._is_excluded(d)]
     for fn in files:
       if self.MAX_FILES is not None and len(rows)>=self.MAX_FILES:
         return pd.DataFrame(rows)
       ext=os.path.splitext(fn)[1].lower()
       if ext not in LANG_MAP:
         continue
       full=os.path.join(root,fn)
       rel=self._clean_rel(os.path.relpath(full,repo_dir))
       if not self.is_valid_file(rel) or not os.path.isfile(full):
         continue
       try:
         m=self._parse_file(full,ext)
       except OSError as err:
         print(f"Skipped unreadable file {rel}: {err}")
         continue
       m["file_path"]=rel
       m["language"]=LANG_MAP[ext]
       rows.append(m)
   return pd.DataFrame(rows)

  def _scan_subset(self,repo_dir:str,paths:list[str])->pd.DataFrame:
   rows=[]
   root_abs=os.path.abspath(repo_dir)
   for raw in paths:
     rel=self._clean_rel(raw)
     if not self.is_valid_file(rel):
       continue
     safe=rel.replace("/",os.sep).lstrip(os.sep)
     full=os.path.normpath(os.path.join(repo_dir,safe))
     if not os.path.abspath(full).startswith(root_abs) or not os.path.isfile(full):
       continue
     ext=os.path.splitext(full)[1].lower()
     try:
       m=self._parse_file(full,ext)
     except OSError as err:
       print(f"Skipped unreadable file {rel}: {err}")
       continue
     m["file_path"]=rel
     m["language"]=LANG_MAP[ext]
     rows.append(m)
   return pd.DataFrame(rows)

  def is_valid_file(self,fpath:str)->bool:
   np=self._norm(fpath)
   if os.path.splitext(np)[1] not in LANG_MAP:
     return False
   return not self._is_excluded(np)

  def _is_excluded(self,p:str)->bool:
   np=self._norm(p)
   return any(k in np for k in SKIP_DIRS)

  def _norm(self,p:str)->str:
   return f"/{self._clean_rel(p).lower().strip('/')}"

  def _clean_rel(self,p:str)->str:
   return str(p or "").replace("\\","/").replace(os.sep,"/").strip("/")

  def _parse_file(self,fpath:str,ext:str)->dict:
   with open(fpath,"r",encoding="utf-8",errors="ignore") as fh:
     src=fh.read()
   if ext==".java":
     return self._brace_metrics(
       src,("//","*","/*"),
       r"(public|private|protected|static|\s)+[\w\<\>\[\]]+\s+\w+\s*\([^)]*\)\s*\{",
       r"\bimport\s+",r"\bnew\s+[A-Z][A-Za-z0-9_]*\s*\(",r"\bextends\b",
       r"(private|protected|public)\s+[\w\<\>\[\]]+\s+\w+\s*;",
       r"\b[A-Z][A-Za-z0-9_]*\.[a-zA-Z_][A-Za-z0-9_]*\s*\("
     )
   if ext==".py":
     return self._python_metrics(src)
   return self._brace_metrics(
     src,("//","*","/*"),
     r"(?:^|[;\n}])\s*(?:[\w:<>\*&]+\s+)+[A-Za-z_][A-Za-z0-9_:]*\s*\([^;{}]*\)\s*(?:const\s*)?\{",
     r"^\s*#\s*include\b|^\s*using\s+namespace\b",r"\bnew\s+[A-Z][A-Za-z0-9_:]*\s*(?:\(|;)",
     r"\bclass\s+\w+\s*:\s*(public|private|protected)\s+",
     r"(private|protected|public)\s*:\s*(?:[\s\S]*?;)",
     r"\b[A-Z][A-Za-z0-9_]*::[a-zA-Z_][A-Za-z0-9_]*\s*\("
   )

  def _python_metrics(self,src:str)->dict:
   clean=[ln.strip() for ln in src.splitlines() if ln.strip() and not ln.strip().startswith(("#",'"""',"'''"))]
   loc=len(clean)
   n_meth=len(re.findall(r"^\s*(def|async\s+def)\s+\w+\s*\(",src,re.MULTILINE))
   branches=sum(len(re.findall(pat,src)) for pat in [r"\bif\b",r"\bfor\b",r"\bwhile\b",r"\bexcept\b",r"\bmatch\b"])
   cmp_q=len(re.findall(r"==|!=|<=|>=|<|>|(?:\bis\b)|(?:\bin\b)",src))
   ret_q=len(re.findall(r"\breturn\b",src))
   imp_q=len(re.findall(r"^\s*(import|from)\s+",src,re.MULTILINE))
   clss=re.findall(r"^\s*class\s+([A-Z][A-Za-z0-9_]*)",src,re.MULTILINE)
   new_q=len(re.findall(rf"\b({'|'.join(re.escape(c) for c in clss)})\s*\(",src)) if clss else 0
   cbo=imp_q+new_q
   rfc=len(re.findall(r"\.\s*[a-zA-Z_][A-Za-z0-9_]*\s*\(",src))
   nosi=len(re.findall(r"\b[A-Z][A-Za-z0-9_]*\.[a-zA-Z_][A-Za-z0-9_]*\s*\(",src))
   dit=2 if re.search(r"^\s*class\s+\w+\s*\([^)]",src,re.MULTILINE) else 1
   wmc=n_meth+branches
   fields=len(re.findall(r"\bself\.[a-zA-Z_][A-Za-z0-9_]*\s*=",src))
   lcom=max(0,n_meth-fields) if n_meth>0 else 0
   return {"nosi":nosi,"dit":dit,"cbo":cbo,"rfc":rfc,"loc":loc,"comparisonsQty":cmp_q,"returnQty":ret_q,"wmc":wmc,"lcom":lcom,"totalMethods":n_meth}

  def _brace_metrics(self,src:str,cmt:tuple,meth_re:str,imp_re:str,new_re:str,inh_re:str,fld_re:str,stat_re:str)->dict:
   clean=[ln.strip() for ln in src.splitlines() if ln.strip() and not ln.strip().startswith(cmt)]
   loc=len(clean)
   n_meth=len(re.findall(meth_re,src))
   branches=sum(len(re.findall(p,src)) for p in [r"\bif\s*\(",r"\bfor\s*\(",r"\bwhile\s*\(",r"\bswitch\s*\(",r"\bcatch\s*\("])
   cmp_q=len(re.findall(r"==|!=|<=|>=|<|>",src))
   ret_q=len(re.findall(r"\breturn\b",src))
   nosi=len(re.findall(stat_re,src))
   dit=2 if re.search(inh_re,src) else 1
   cbo=len(re.findall(imp_re,src,re.MULTILINE))+len(re.findall(new_re,src))
   rfc=len(re.findall(r"(?:\.|->|::)\s*[a-zA-Z_][A-Za-z0-9_]*\s*\(",src))
   wmc=n_meth+branches
   fields=len(re.findall(fld_re,src))
   lcom=max(0,n_meth-fields) if n_meth>0 else 0
   return {"nosi":nosi,"dit":dit,"cbo":cbo,"rfc":rfc,"loc":loc,"comparisonsQty":cmp_q,"returnQty":ret_q,"wmc":wmc,"lcom":lcom,"totalMethods":n_meth}
