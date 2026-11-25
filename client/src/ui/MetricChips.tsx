const LABELS:Record<string,string>={
  rfc:"Method interactions",comparisonsQty:"Conditional checks",nosi:"Static calls",
  lcom:"Cohesion complexity",totalMethods:"Methods",loc:"File size",
  cbo:"Class dependencies",wmc:"Method complexity",returnQty:"Return paths",
  dit:"Inheritance depth",file_change_count:"File changes",file_bug_fix_count:"Bug-fix history",
  recent_file_change_count:"Recent changes",days_since_last_change:"Days since change",
  last_change_lines_added:"Last added lines",last_change_lines_deleted:"Last deleted lines",
  last_change_churn:"Last churn",last_change_file_count:"Files changed together",
  author_file_change_count:"Author file changes"
};

function fmtVal(v:string){
  const n=Number(v);
  if(Number.isNaN(n))return v.trim();
  return Number.isInteger(n)?String(n):n.toFixed(2);
}

function parseSignals(txt:string){
  const rx=/\(([A-Za-z_][A-Za-z0-9_]*)=([^)]+)\)/g;
  const out:{kw:string;val:string;raw:string;dir:"higher"|"lower"|"neutral"}[]=[];
  const seen=new Set<string>();
  txt.split(".").map(s=>s.trim()).filter(Boolean).forEach(s=>{
    const low=s.toLowerCase();
    const dir=low.includes("score higher")?"higher":low.includes("score lower")?"lower":"neutral";
    for(const m of s.matchAll(rx)){
      const k=m[1];
      if(seen.has(k))continue;
      seen.add(k);
      out.push({kw:LABELS[k]||k,val:fmtVal(m[2]),raw:k,dir});
    }
  });
  return out;
}

export default function MetricChips({explanation}:{explanation:string}){
  const items=parseSignals(explanation);
  if(items.length===0){
    return <span className="compact-explanation-empty" title={explanation}>No metric values available</span>;
  }
  return (
    <div className="compact-explanation-list">
      {items.map(it=>(
        <div className={`compact-explanation-item ${it.dir}`} key={it.raw} title={it.raw}>
          <span className="compact-explanation-keyword">
            <span className="compact-explanation-direction">
              {it.dir==="higher"?"Increases score":it.dir==="lower"?"Lowers score":"Model signal"}
            </span>
            {it.kw}
          </span>
          <span className="compact-explanation-value">{it.val}</span>
        </div>
      ))}
    </div>
  );
}
