import {useMemo,useState} from "react";
import {useLocation,Link} from "react-router-dom";
import type {PredictionResponse,PredictionResult} from "../models/api_types";
import ResultsGrid from "../ui/ResultsGrid";
import MetricsModal from "../ui/MetricsModal";
import {exportPredictionReport} from "../net/http";

export type ProbSortOrder="desc"|"asc";
export type RiskTierFilter="All"|"High"|"Medium"|"Low";
export type LabelFilter="All"|"Defective"|"Non-defective";
type ExportFmt="csv"|"pdf";

export interface ResultFilterState {
  fileSearch:string;languageFilter:string;riskFilter:RiskTierFilter;
  predictionFilter:LabelFilter;minProbability:string;maxProbability:string;
}

const fmtPct=(v:number)=>`${(v*100).toFixed(1)}%`;
const rowKey=(r:PredictionResult)=>[r.file_path,r.language,r.prediction_label,r.defect_risk_probability].join("|");
const isTestHint=(r:PredictionResult)=>r.is_potential_test_file===true||r.is_potential_test_file===1||r.is_potential_test_file==="true"||r.is_potential_test_file==="1";
const esc=(v:unknown)=>String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
const svgN=(v:number)=>Number(v.toFixed(3));
const topDir=(fp:string)=>{const p=fp.replaceAll("\\","/").split("/").filter(Boolean);return p.length<=1?"Repository root":p[0];};

function summarizeRows(rows:PredictionResult[]){
  const langs=new Map<string,{count:number;sum:number}>();
  const agg=rows.reduce((acc,r)=>{
    const p=r.defect_risk_probability;
    const lg=r.language||"Unknown";
    if(r.risk_level==="High")acc.highRiskCount+=1;
    else if(r.risk_level==="Medium")acc.mediumRiskCount+=1;
    else acc.lowRiskCount+=1;
    if(r.prediction_label==="Defective")acc.defectiveCount+=1;
    acc.probabilitySum+=p;
    if(!acc.highestRiskFile||p>acc.highestRiskFile.defect_risk_probability)acc.highestRiskFile=r;
    const cur=langs.get(lg)||{count:0,sum:0};
    cur.count+=1;cur.sum+=p;langs.set(lg,cur);
    return acc;
  },{highRiskCount:0,mediumRiskCount:0,lowRiskCount:0,defectiveCount:0,probabilitySum:0,highestRiskFile:null as PredictionResult|null});
  return {
    ...agg,totalFiles:rows.length,
    averageProbability:rows.length?agg.probabilitySum/rows.length:0,
    languageBreakdown:Array.from(langs.entries()).map(([language,v])=>({language,count:v.count,averageProbability:v.sum/v.count})).sort((a,b)=>b.count-a.count)
  };
}

export const filterPredictionResults=(rows:PredictionResult[],f:ResultFilterState)=>{
  const q=f.fileSearch.trim().toLowerCase();
  const minP=f.minProbability.trim()===""?null:Number(f.minProbability)/100;
  const maxP=f.maxProbability.trim()===""?null:Number(f.maxProbability)/100;
  return rows.filter(r=>(
    (!q||r.file_path.toLowerCase().includes(q))&&
    (f.languageFilter==="All"||r.language===f.languageFilter)&&
    (f.riskFilter==="All"||r.risk_level===f.riskFilter)&&
    (f.predictionFilter==="All"||r.prediction_label===f.predictionFilter)&&
    (minP===null||r.defect_risk_probability>=minP)&&
    (maxP===null||r.defect_risk_probability<=maxP)
  ));
};

export const buildPdfReportHtml=(resp:PredictionResponse,rows:PredictionResult[])=>{
  const st=summarizeRows(rows);
  const hp=st.totalFiles?(st.highRiskCount/st.totalFiles)*100:0;
  const mp=st.totalFiles?(st.mediumRiskCount/st.totalFiles)*100:0;
  const lp=st.totalFiles?(st.lowRiskCount/st.totalFiles)*100:0;
  const C=339.292;
  const ha=(hp/100)*C,ma=(mp/100)*C,la=(lp/100)*C;
  const donut=`<svg class="donut-svg" viewBox="0 0 150 150" aria-label="Risk distribution"><circle class="donut-track" cx="75" cy="75" r="54"></circle><circle class="donut-segment low" cx="75" cy="75" r="54" stroke-dasharray="${la} ${C-la}" stroke-dashoffset="-${ha+ma}"></circle><circle class="donut-segment medium" cx="75" cy="75" r="54" stroke-dasharray="${ma} ${C-ma}" stroke-dashoffset="-${ha}"></circle><circle class="donut-segment high" cx="75" cy="75" r="54" stroke-dasharray="${ha} ${C-ha}" stroke-dashoffset="0"></circle><text x="75" y="71" text-anchor="middle" class="donut-value">${fmtPct(st.averageProbability)}</text><text x="75" y="91" text-anchor="middle" class="donut-label">Avg risk</text></svg>`;
  const thresh=resp.prediction_threshold!==null&&resp.prediction_threshold!==undefined?fmtPct(resp.prediction_threshold):"Model default";
  const langCards=st.languageBreakdown.map(it=>{
    const ch=Math.max(12,(it.count/Math.max(st.totalFiles,1))*82);
    const rh=Math.max(12,it.averageProbability*82);
    return `<div class="language-card"><strong>${esc(it.language)}</strong><span>${it.count} files</span><svg class="mini-bars" viewBox="0 0 78 92" aria-label="Language risk"><line x1="8" y1="88" x2="70" y2="88"></line><rect class="count-bar" x="22" y="${88-ch}" width="16" height="${ch}" rx="5"></rect><rect class="risk-bar" x="42" y="${88-rh}" width="16" height="${rh}" rx="5"></rect></svg><small>${fmtPct(it.averageProbability)} avg risk</small></div>`;
  }).join("");
  const maxLC=Math.max(...st.languageBreakdown.map(x=>x.count),1);
  const cw=760,ch=260,pt=24,pb=204,ph=pb-pt;
  const lItems=st.languageBreakdown.slice(0,8);
  const slot=lItems.length?cw/lItems.length:cw;
  const bars=lItems.map((it,i)=>{
    const bh=Math.max(8,(it.count/maxLC)*ph);
    const rh=Math.max(8,it.averageProbability*ph);
    const gx=i*slot+slot/2-26;
    const cx=svgN(i*slot+slot/2);
    return `<g><rect x="${svgN(gx)}" y="${svgN(pb-bh)}" width="20" height="${svgN(bh)}" rx="5" fill="#2563eb"></rect><rect x="${svgN(gx+28)}" y="${svgN(pb-rh)}" width="20" height="${svgN(rh)}" rx="5" fill="#dc2626"></rect><text x="${cx}" y="230" text-anchor="middle" class="chart-label">${esc(it.language)}</text><text x="${cx}" y="248" text-anchor="middle" class="chart-sub-label">${it.count} files | ${fmtPct(it.averageProbability)}</text></g>`;
  }).join("");
  const langSvg=`<svg class="report-chart language-report-chart" viewBox="0 0 ${cw} ${ch}" role="img" aria-label="Language risk overview"><line x1="24" y1="${pb}" x2="${cw-24}" y2="${pb}" stroke="#cbd5e1" stroke-width="1"></line>${bars}</svg>`;
  const topRows=[...rows].sort((a,b)=>b.defect_risk_probability-a.defect_risk_probability).slice(0,8).map(r=>{
    const p=svgN(Math.max(0.03,r.defect_risk_probability)*100);
    return `<div class="top-risk-row"><div><strong>${esc(r.file_path)}</strong><span>${esc(r.language||"Unknown")} | ${esc(r.prediction_label)}</span></div><div class="top-risk-track"><span class="${esc(r.risk_level.toLowerCase())}" style="width: ${p}%"></span></div><b>${fmtPct(r.defect_risk_probability)}</b></div>`;
  }).join("");
  const tblRows=rows.map((r,i)=>`<tr><td>${i+1}</td><td class="file-path">${esc(r.file_path)}</td><td>${isTestHint(r)?"Potential test file":"Normal code"}</td><td>${esc(r.language||"Unknown")}</td><td>${esc(r.prediction_label)}</td><td>${fmtPct(r.defect_risk_probability)}</td><td><span class="risk-badge ${esc(r.risk_level.toLowerCase())}">${esc(r.risk_level)}</span></td><td>${esc(r.recommendation)}</td></tr><tr class="explanation-row"><td></td><td colspan="7">${esc(r.readable_explanation||r.top_contributing_metrics||"No explanation available.")}${isTestHint(r)?`<div class="pdf-test-note"><strong>Potential test file</strong>${esc(r.test_file_reason||"Matched a common test-file naming pattern.")}</div>`:""}${r.confidence_warning?`<div class="pdf-confidence-warning"><strong>Confidence note</strong>${esc(r.confidence_warning)}</div>`:""}</td></tr>`).join("");
  return `<!doctype html><html><head><title>Aether Prediction Report</title><style>*{box-sizing:border-box}html,body,*{print-color-adjust:exact;-webkit-print-color-adjust:exact}body{margin:0;padding:28px;background:#f5f7fb;color:#111827;font-family:Arial,Helvetica,sans-serif}.report-shell{max-width:1120px;margin:0 auto}.hero,.panel,.stat-card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;box-shadow:0 8px 22px rgba(15,23,42,.08)}.hero{padding:24px;margin-bottom:18px}h1{margin:0 0 10px;font-size:28px}h2{margin:0 0 12px;font-size:18px}p{margin:6px 0;color:#4b5563;line-height:1.45}.meta-grid,.stat-grid,.detail-grid,.language-grid{display:grid;gap:12px}.meta-grid{grid-template-columns:repeat(2,minmax(0,1fr));margin-top:16px}.meta-item{background:#f8fafc;border:1px solid #e5e7eb;border-radius:10px;padding:11px;overflow-wrap:anywhere}.meta-item span,.stat-card span{color:#64748b;display:block;font-size:12px;font-weight:700;text-transform:uppercase}.meta-item strong{display:block;margin-top:5px}.stat-grid{grid-template-columns:repeat(5,minmax(0,1fr));margin-bottom:14px}.stat-card{min-height:96px;padding:15px;border-top:4px solid #2563eb}.stat-card.high{border-top-color:#dc2626}.stat-card.medium{border-top-color:#d97706}.stat-card.low{border-top-color:#16a34a}.stat-card.defective{border-top-color:#7c3aed}.stat-card strong{display:block;font-size:26px;margin:8px 0 4px}.stat-card small{color:#64748b;font-weight:700}.detail-grid{grid-template-columns:1.2fr 1fr;margin-bottom:14px}.panel{padding:18px}.risk-layout{align-items:center;display:grid;grid-template-columns:150px 1fr;gap:20px}.donut,.donut-svg{height:150px;width:150px}.donut-track{fill:#fff;stroke:#e5e7eb;stroke-width:22}.donut-segment{fill:none;stroke-linecap:butt;stroke-width:22;transform:rotate(-90deg);transform-origin:75px 75px}.donut-segment.high{stroke:#dc2626}.donut-segment.medium{stroke:#d97706}.donut-segment.low{stroke:#16a34a}.donut-value{fill:#111827;font-size:18px;font-weight:800}.donut-label{fill:#64748b;font-size:10px;font-weight:700}.risk-list{display:grid;gap:8px}.risk-list div{align-items:center;background:#f8fafc;border:1px solid #e5e7eb;border-radius:10px;display:grid;grid-template-columns:1fr auto auto;gap:10px;padding:9px}.highest-file{color:#111827;font-family:Consolas,monospace;overflow-wrap:anywhere}.visual-grid{display:grid;gap:14px;grid-template-columns:1.2fr 1fr;margin-bottom:14px}.report-chart{display:block;height:auto;max-width:100%;width:100%}.chart-label{fill:#111827;font-size:12px;font-weight:800}.chart-sub-label{fill:#64748b;font-size:10px;font-weight:700}.chart-legend{align-items:center;display:flex;flex-wrap:wrap;gap:14px;margin-top:10px}.chart-legend span{align-items:center;color:#475569;display:inline-flex;font-size:12px;font-weight:800;gap:7px}.legend-box{border-radius:4px;display:inline-block;height:11px;width:18px}.legend-box.count{background:#2563eb}.legend-box.risk{background:#dc2626}.top-risk-list{display:grid;gap:10px}.top-risk-row{align-items:center;display:grid;gap:10px;grid-template-columns:minmax(0,1.4fr) minmax(140px,.9fr) auto}.top-risk-row strong,.top-risk-row span{display:block;overflow-wrap:anywhere}.top-risk-row strong{font-family:Consolas,monospace;font-size:12px}.top-risk-row span{color:#64748b;font-size:11px;margin-top:3px}.top-risk-row b{font-size:12px}.top-risk-track{background:#e5e7eb;border-radius:999px;height:12px;overflow:hidden}.top-risk-track span{display:block;height:100%}.top-risk-track .high{background:#dc2626}.top-risk-track .medium{background:#d97706}.top-risk-track .low{background:#16a34a}.language-grid{grid-template-columns:repeat(auto-fit,minmax(160px,1fr));margin-bottom:14px}.language-card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:12px}.language-card strong,.language-card span,.language-card small{display:block}.language-card span,.language-card small{color:#64748b;margin-top:5px}.mini-bars{height:92px;margin:8px 0;width:78px}.mini-bars line{stroke:#cbd5e1;stroke-width:1}.mini-bars .count-bar{fill:#2563eb}.mini-bars .risk-bar{fill:#dc2626}table{border-collapse:collapse;width:100%;background:#fff}th,td{border:1px solid #e5e7eb;font-size:12px;padding:9px;text-align:left;vertical-align:top}th{background:#f3f4f6;font-weight:800}.file-path{font-family:Consolas,monospace;overflow-wrap:anywhere}.risk-badge{border-radius:999px;display:inline-block;font-weight:800;padding:4px 8px}.risk-badge.high{background:#fee2e2;color:#991b1b}.risk-badge.medium{background:#fef3c7;color:#92400e}.risk-badge.low{background:#dcfce7;color:#166534}.explanation-row td{background:#f8fafc;color:#475569;line-height:1.45}.pdf-confidence-warning{background:#fffbeb;border:1px solid #fde68a;border-left:4px solid #d97706;border-radius:8px;color:#78350f;margin-top:8px;padding:8px}.pdf-confidence-warning strong,.pdf-test-note strong{display:block;font-size:11px;margin-bottom:3px;text-transform:uppercase}.pdf-test-note{background:#fefce8;border:1px solid #fde68a;border-left:4px solid #ca8a04;border-radius:8px;color:#713f12;margin-top:8px;padding:8px}@media print{body{background:#fff;padding:0}.hero,.panel,.stat-card{box-shadow:none}.panel,.hero,.stat-card,tr{break-inside:avoid}}</style></head><body><main class="report-shell"><section class="hero"><h1>Aether - Prediction Report</h1><p>This report summarizes the selected prediction results and their risk distribution.</p><div class="meta-grid"><div class="meta-item"><span>Repository</span><strong>${esc(resp.repo_url)}</strong></div><div class="meta-item"><span>Commit</span><strong>${esc(resp.commit_sha)}</strong></div><div class="meta-item"><span>Threshold</span><strong>${thresh}</strong></div><div class="meta-item"><span>Exported Files</span><strong>${st.totalFiles}</strong></div></div></section><section class="stat-grid"><div class="stat-card high"><span>High Risk</span><strong>${st.highRiskCount}</strong><small>${fmtPct(hp/100)}</small></div><div class="stat-card medium"><span>Medium Risk</span><strong>${st.mediumRiskCount}</strong><small>${fmtPct(mp/100)}</small></div><div class="stat-card low"><span>Low Risk</span><strong>${st.lowRiskCount}</strong><small>${fmtPct(lp/100)}</small></div><div class="stat-card defective"><span>Defective</span><strong>${st.defectiveCount}</strong><small>${fmtPct(st.totalFiles?st.defectiveCount/st.totalFiles:0)}</small></div><div class="stat-card"><span>Average Risk</span><strong>${fmtPct(st.averageProbability)}</strong><small>Mean probability</small></div></section><section class="detail-grid"><div class="panel"><h2>Risk Distribution</h2><div class="risk-layout"><div class="donut">${donut}</div><div class="risk-list"><div><span>High</span><strong>${st.highRiskCount}</strong><small>${fmtPct(hp/100)}</small></div><div><span>Medium</span><strong>${st.mediumRiskCount}</strong><small>${fmtPct(mp/100)}</small></div><div><span>Low</span><strong>${st.lowRiskCount}</strong><small>${fmtPct(lp/100)}</small></div></div></div></div><div class="panel"><h2>Highest Risk File</h2><p class="highest-file">${esc(st.highestRiskFile?.file_path||"No file available")}</p><p>${esc(st.highestRiskFile?.language||"Unknown")} | ${esc(st.highestRiskFile?.risk_level||"No risk")} | ${fmtPct(st.highestRiskFile?.defect_risk_probability||0)}</p></div></section><section class="visual-grid"><div class="panel"><h2>Language Risk Overview</h2>${langSvg}<div class="chart-legend"><span><i class="legend-box count"></i>File volume</span><span><i class="legend-box risk"></i>Average risk</span></div></div><div class="panel"><h2>Top Risk Files</h2><div class="top-risk-list">${topRows}</div></div></section><section class="language-grid">${langCards}</section><section class="panel"><h2>Selected Results</h2><table><thead><tr><th>No.</th><th>File</th><th>Code Type</th><th>Language</th><th>Prediction</th><th>Probability</th><th>Risk</th><th>Recommendation</th></tr></thead><tbody>${tblRows}</tbody></table></section></main><script>window.addEventListener("load",()=>{setTimeout(()=>window.print(),250);});</script></body></html>`;
};

export default function ResultsView(){
  const loc=useLocation();
  const resp=loc.state?.predictionResponse as PredictionResponse|undefined;
  const [sortDir,setSortDir]=useState<ProbSortOrder>("desc");
  const [guideOpen,setGuideOpen]=useState(false);
  const [search,setSearch]=useState("");
  const [langF,setLangF]=useState("All");
  const [riskF,setRiskF]=useState<RiskTierFilter>("All");
  const [predF,setPredF]=useState<LabelFilter>("All");
  const [minP,setMinP]=useState("");
  const [maxP,setMaxP]=useState("");
  const [expFmt,setExpFmt]=useState<ExportFmt|"">("");
  const [picked,setPicked]=useState<Set<string>>(()=>new Set());

  const langs=useMemo(()=>resp?Array.from(new Set(resp.results.map(r=>r.language).filter(Boolean))).sort():[],[resp]);
  const dash=useMemo(()=>{
    const base={
      totalFiles:0,highRiskCount:0,mediumRiskCount:0,lowRiskCount:0,defectiveCount:0,averageProbability:0,
      highestRiskFile:null as PredictionResult|null,riskiestFolder:"No folder",riskiestFolderAverage:0,
      languageBreakdown:[] as Array<{language:string;count:number;averageProbability:number}>,
      riskDistribution:[] as Array<{label:string;count:number;percent:number;className:string}>
    };
    if(!resp||resp.results.length===0)return base;
    const fMap=new Map<string,{count:number;sum:number}>();
    const s=summarizeRows(resp.results);
    resp.results.forEach(r=>{
      const d=topDir(r.file_path);
      const cur=fMap.get(d)||{count:0,sum:0};
      cur.count+=1;cur.sum+=r.defect_risk_probability;fMap.set(d,cur);
    });
    const topFolder=Array.from(fMap.entries()).sort((a,b)=>(b[1].sum/b[1].count)-(a[1].sum/a[1].count))[0];
    const n=resp.results.length;
    return {
      ...s,
      riskiestFolder:topFolder?topFolder[0]:"No folder",
      riskiestFolderAverage:topFolder?topFolder[1].sum/topFolder[1].count:0,
      riskDistribution:[
        {label:"High",count:s.highRiskCount,percent:n?s.highRiskCount/n:0,className:"high"},
        {label:"Medium",count:s.mediumRiskCount,percent:n?s.mediumRiskCount/n:0,className:"medium"},
        {label:"Low",count:s.lowRiskCount,percent:n?s.lowRiskCount/n:0,className:"low"}
      ]
    };
  },[resp]);

  const donutBg=useMemo(()=>{
    if(dash.totalFiles===0)return "#e5e7eb";
    const h=dash.riskDistribution[0].percent*100;
    const m=h+dash.riskDistribution[1].percent*100;
    return `conic-gradient(#dc2626 0 ${h}%, #d97706 ${h}% ${m}%, #16a34a ${m}% 100%)`;
  },[dash]);

  const filtered=useMemo(()=>resp?filterPredictionResults(resp.results,{fileSearch:search,languageFilter:langF,riskFilter:riskF,predictionFilter:predF,minProbability:minP,maxProbability:maxP}):[],[resp,search,langF,riskF,predF,minP,maxP]);
  const sorted=useMemo(()=>[...filtered].sort((a,b)=>sortDir==="desc"?b.defect_risk_probability-a.defect_risk_probability:a.defect_risk_probability-b.defect_risk_probability),[filtered,sortDir]);
  const chosen=useMemo(()=>resp?resp.results.filter(r=>picked.has(rowKey(r))):[],[resp,picked]);
  const allShown=sorted.length>0&&sorted.every(r=>picked.has(rowKey(r)));
  const normalRows=useMemo(()=>sorted.filter(r=>!isTestHint(r)),[sorted]);
  const testRows=useMemo(()=>sorted.filter(isTestHint),[sorted]);
  const allNormal=normalRows.length>0&&normalRows.every(r=>picked.has(rowKey(r)));
  const allTest=testRows.length>0&&testRows.every(r=>picked.has(rowKey(r)));
  const hasFilters=search.trim()!==""||langF!=="All"||riskF!=="All"||predF!=="All"||minP.trim()!==""||maxP.trim()!=="";

  const toggleKey=(k:string)=>setPicked(prev=>{const nxt=new Set(prev);if(nxt.has(k))nxt.delete(k);else nxt.add(k);return nxt;});
  const toggleGroup=(grp:PredictionResult[],allOn:boolean)=>setPicked(prev=>{const nxt=new Set(prev);grp.forEach(r=>allOn?nxt.delete(rowKey(r)):nxt.add(rowKey(r)));return nxt;});

  const doExport=async(fmt:ExportFmt)=>{
    if(!resp||chosen.length===0)return;
    const payload:PredictionResponse={...resp,total_files_scanned:chosen.length,results:chosen};
    setExpFmt(fmt);
    if(fmt==="pdf"){
      const html=buildPdfReportHtml(payload,chosen);
      const u=URL.createObjectURL(new Blob([html],{type:"text/html;charset=utf-8"}));
      const w=window.open(u,"_blank");
      if(!w)URL.revokeObjectURL(u);
      else window.setTimeout(()=>URL.revokeObjectURL(u),30000);
      window.setTimeout(()=>setExpFmt(""),600);
      return;
    }
    try{
      const blob=await exportPredictionReport(payload);
      const u=URL.createObjectURL(blob);
      const a=document.createElement("a");
      a.href=u;a.download=`defect_prediction_report_${resp.commit_sha.slice(0,8)}.${fmt}`;
      document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(u);
    }finally{setExpFmt("");}
  };

  if(!resp){
    return (
      <div className="page">
        <div className="form-card">
          <h1>No Prediction Result</h1><p>Please run a prediction first.</p>
          <Link to="/repository-input" className="primary-button">Go to Repository Input</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="result-header">
        <div className="result-header-top">
          <div>
            <h1>Prediction Result</h1>
            <p className="result-header-description">This page summarizes the model output for the selected commit. Use it to identify files that may need earlier review, then check the metric values and explanation before making a decision.</p>
            <p>Repository: <strong>{resp.repo_url}</strong></p>
            <p>Commit: <strong>{resp.commit_sha}</strong></p>
            <p>Prediction Threshold: <strong>{resp.prediction_threshold!==null&&resp.prediction_threshold!==undefined?fmtPct(resp.prediction_threshold):"Model default"}</strong></p>
            <p className="result-helper-text">Threshold means the cut-off for marking a file as defective. A file with risk probability equal to or above this value is labelled defective by the app.</p>
            <p>Total Supported Files Scanned: <strong>{resp.total_files_scanned}</strong></p>
          </div>
          <div className="result-header-actions">
            <button className="metric-guide-open-button" onClick={()=>setGuideOpen(true)}>Metric Explanation Guide</button>
          </div>
        </div>
      </div>
      <section className="result-explainer-grid" aria-label="Result explanation">
        <div className="result-explainer-card"><span>Risk probability</span><p>The percentage score for a file. Higher means the file looks more similar to files that were defective in the training data.</p></div>
        <div className="result-explainer-card"><span>Risk level</span><p>A simpler grouping of the probability into high, medium, or low so the result can be scanned quickly.</p></div>
        <div className="result-explainer-card"><span>SHAP / metric values</span><p>SHAP is used to explain the model decision. The metric values show which code or commit-history measurements pushed the prediction.</p></div>
        <div className="result-explainer-card"><span>Recommendation</span><p>A review priority suggestion based on the predicted risk. It should support code review, not replace developer judgement.</p></div>
      </section>
      <section className="risk-dashboard" aria-label="Risk dashboard">
        <div className="dashboard-summary-grid">
          <div className="dashboard-stat high-risk-stat"><span>High Risk</span><strong>{dash.highRiskCount}</strong><small>{fmtPct(dash.riskDistribution[0]?.percent||0)} of files</small></div>
          <div className="dashboard-stat medium-risk-stat"><span>Medium Risk</span><strong>{dash.mediumRiskCount}</strong><small>{fmtPct(dash.riskDistribution[1]?.percent||0)} of files</small></div>
          <div className="dashboard-stat low-risk-stat"><span>Low Risk</span><strong>{dash.lowRiskCount}</strong><small>{fmtPct(dash.riskDistribution[2]?.percent||0)} of files</small></div>
          <div className="dashboard-stat defective-stat"><span>Defective</span><strong>{dash.defectiveCount}</strong><small>{fmtPct(dash.totalFiles?dash.defectiveCount/dash.totalFiles:0)} labelled defective</small></div>
          <div className="dashboard-stat average-risk-stat"><span>Average Risk</span><strong>{fmtPct(dash.averageProbability)}</strong><small>Mean probability across files</small></div>
        </div>
        <div className="dashboard-detail-grid">
          <div className="risk-panel risk-distribution-panel">
            <div className="risk-panel-header"><h2>Risk Distribution</h2><span>{dash.totalFiles} files</span></div>
            <p className="risk-panel-note">This chart shows how the scanned files are split across high, medium, and low risk categories.</p>
            <div className="risk-chart-layout">
              <div className="risk-donut" style={{background:donutBg}} aria-hidden="true">
                <div className="risk-donut-center"><strong>{fmtPct(dash.averageProbability)}</strong><span>Avg risk</span></div>
              </div>
              <div className="risk-breakdown-list">
                {dash.riskDistribution.map(it=>(
                  <div className="risk-breakdown-row" key={it.label}>
                    <span><i className={`legend-dot ${it.className}-dot`}/>{it.label}</span>
                    <strong>{it.count}</strong><small>{fmtPct(it.percent)}</small>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="risk-panel">
            <div className="risk-panel-header"><h2>Highest Risk File</h2><span>{dash.highestRiskFile?fmtPct(dash.highestRiskFile.defect_risk_probability):"0.0%"}</span></div>
            <p className="dashboard-file-path">{dash.highestRiskFile?.file_path||"No file available"}</p>
            <p className="dashboard-muted">{dash.highestRiskFile?.language||"No language"} | {dash.highestRiskFile?.risk_level||"No risk"}</p>
            <p className="dashboard-muted">Start here if you only have time to inspect one file.</p>
          </div>
          <div className="risk-panel">
            <div className="risk-panel-header"><h2>Riskiest Folder</h2><span>{fmtPct(dash.riskiestFolderAverage)}</span></div>
            <p className="dashboard-file-path">{dash.riskiestFolder}</p>
            <p className="dashboard-muted">Folder with the highest average defect probability among scanned files.</p>
          </div>
        </div>
        {dash.languageBreakdown.length>0&&(
          <div className="risk-panel language-chart-panel">
            <div className="risk-panel-header"><h2>Language Risk Overview</h2><span>Count and average risk</span></div>
            <p className="risk-panel-note">Blue bars show how many files were scanned for each language. Red bars show the average risk score for that language.</p>
            <div className="language-column-chart">
              {dash.languageBreakdown.map(it=>(
                <div className="language-column-item" key={it.language}>
                  <div className="language-column-bars">
                    <span className="language-count-bar" style={{height:`${Math.max(12,(it.count/dash.totalFiles)*100)}%`}}/>
                    <span className="language-risk-bar" style={{height:`${Math.max(12,it.averageProbability*100)}%`}}/>
                  </div>
                  <div className="language-column-label"><strong>{it.language}</strong><span>{it.count} files</span><small>{fmtPct(it.averageProbability)} avg</small></div>
                </div>
              ))}
            </div>
            <div className="chart-legend">
              <span><i className="legend-line count-line"/> File volume</span>
              <span><i className="legend-line risk-line"/> Average risk</span>
            </div>
          </div>
        )}
      </section>
      <div className="result-filters">
        <div className="result-section-heading">
          <div><h2>File-Level Results</h2><p>Filter, sort, select, and export the files that matter for your review. The backend scans all supported source files in the selected commit, then separates potential test files below.</p></div>
        </div>
        <div className="filter-summary">
          <strong>{sorted.length}</strong> of <strong>{resp.results.length}</strong> files shown
          <span className="selection-summary"><strong>{chosen.length}</strong> selected</span>
        </div>
        <div className="filter-grid">
          <label className="filter-field filter-field-wide"><span>Search File Path</span><input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search by folder or file name"/></label>
          <label className="filter-field"><span>Language</span><select value={langF} onChange={e=>setLangF(e.target.value)}><option value="All">All languages</option>{langs.map(l=><option key={l} value={l}>{l}</option>)}</select></label>
          <label className="filter-field"><span>Risk Level</span><select value={riskF} onChange={e=>setRiskF(e.target.value as RiskTierFilter)}><option value="All">All risks</option><option value="High">High</option><option value="Medium">Medium</option><option value="Low">Low</option></select></label>
          <label className="filter-field"><span>Prediction</span><select value={predF} onChange={e=>setPredF(e.target.value as LabelFilter)}><option value="All">All predictions</option><option value="Defective">Defective</option><option value="Non-defective">Non-defective</option></select></label>
          <label className="filter-field"><span>Min Probability %</span><input type="number" value={minP} min="0" max="100" onChange={e=>setMinP(e.target.value)} placeholder="0"/></label>
          <label className="filter-field"><span>Max Probability %</span><input type="number" value={maxP} min="0" max="100" onChange={e=>setMaxP(e.target.value)} placeholder="100"/></label>
        </div>
        <button className="filter-reset-button" onClick={()=>{setSearch("");setLangF("All");setRiskF("All");setPredF("All");setMinP("");setMaxP("");}} disabled={!hasFilters}>Reset Filters</button>
        <div className="export-selection-panel">
          <div><strong>Export Selection</strong><span>Select rows in the table, then export them as CSV or PDF.</span></div>
          <div className="export-selection-actions">
            <button className="secondary-export-button" onClick={()=>toggleGroup(sorted,allShown)} disabled={sorted.length===0}>{allShown?"Unselect Shown":"Select Shown"}</button>
            <button className="secondary-export-button" onClick={()=>setPicked(new Set())} disabled={chosen.length===0}>Clear</button>
            <button className="export-report-button" onClick={()=>doExport("csv")} disabled={chosen.length===0||expFmt!==""}>{expFmt==="csv"?"Exporting CSV...":"Export CSV"}</button>
            <button className="export-report-button" onClick={()=>doExport("pdf")} disabled={chosen.length===0||expFmt!==""}>{expFmt==="pdf"?"Exporting PDF...":"Export PDF"}</button>
          </div>
        </div>
      </div>
      <section className="result-group-section">
        <div className="result-group-heading">
          <div><h2>Normal Code Files</h2><p>Supported source files that did not match common test-folder or test-file naming patterns.</p></div>
          <span>{normalRows.length} files</span>
        </div>
        {normalRows.length>0?(
          <ResultsGrid results={normalRows} probabilitySortDirection={sortDir} selectedResultKeys={picked} getResultKey={rowKey}
            onToggleResultSelection={toggleKey} onToggleAllShown={()=>toggleGroup(normalRows,allNormal)} allShownSelected={allNormal}
            onToggleProbabilitySort={()=>setSortDir(d=>d==="desc"?"asc":"desc")}/>
        ):<div className="empty-result-group">No normal code files match the current filters.</div>}
      </section>
      {testRows.length>0&&(
        <section className="result-group-section potential-test-section">
          <div className="result-group-heading">
            <div><h2>Potential Test Files</h2><p>These files are still scanned and predicted. They are separated because their path or filename matched conservative test hints such as test folders, spec names, or common test filename patterns.</p></div>
            <span>{testRows.length} files</span>
          </div>
          <ResultsGrid results={testRows} probabilitySortDirection={sortDir} selectedResultKeys={picked} getResultKey={rowKey}
            onToggleResultSelection={toggleKey} onToggleAllShown={()=>toggleGroup(testRows,allTest)} allShownSelected={allTest}
            onToggleProbabilitySort={()=>setSortDir(d=>d==="desc"?"asc":"desc")}/>
        </section>
      )}
      <MetricsModal isOpen={guideOpen} onClose={()=>setGuideOpen(false)}/>
    </div>
  );
}
