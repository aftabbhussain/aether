import {useEffect,useState} from "react";
import {useNavigate} from "react-router-dom";
import {deletePredictionHistoryItem,fetchPredictionHistory,fetchPredictionHistoryDetail,getApiErrorMessage} from "../net/http";
import type {PredictionHistorySummary} from "../models/api_types";

const pct=(v:number)=>`${(v*100).toFixed(1)}%`;
export const isHistoryDeleteEnabled=()=>import.meta.env.VITE_ENABLE_HISTORY_DELETE!=="false";
const shortRepo=(u:string)=>u.replace(/\.git$/,"").split("/").filter(Boolean).slice(-2).join("/");

export default function HistoryView(){
  const nav=useNavigate();
  const [items,setItems]=useState<PredictionHistorySummary[]>([]);
  const [busy,setBusy]=useState(true);
  const [err,setErr]=useState("");
  const [openId,setOpenId]=useState("");
  const [delId,setDelId]=useState("");

  const load=async()=>{
    setBusy(true);setErr("");
    try{
      const r=await fetchPredictionHistory();
      setItems(r.history);
    }catch(e){
      setErr(getApiErrorMessage(e,"Failed to load prediction history. Please check the backend server."));
    }finally{
      setBusy(false);
    }
  };
  useEffect(()=>{load();},[]);

  const onOpen=async(id:string)=>{
    setOpenId(id);setErr("");
    try{
      const det=await fetchPredictionHistoryDetail(id);
      nav("/prediction-result",{state:{predictionResponse:det}});
    }catch(e){
      setErr(getApiErrorMessage(e,"Failed to open the selected prediction."));
    }finally{
      setOpenId("");
    }
  };

  const onDelete=async(id:string)=>{
    setDelId(id);setErr("");
    try{
      await deletePredictionHistoryItem(id);
      setItems(prev=>prev.filter(x=>x.id!==id));
    }catch(e){
      setErr(getApiErrorMessage(e,"Failed to delete the selected prediction."));
    }finally{
      setDelId("");
    }
  };

  return (
    <div className="page">
      <section className="history-header">
        <div><h1>Prediction History</h1><p>View everyone's predictions here!</p></div>
        <button className="secondary-button" onClick={load} disabled={busy}>{busy?"Refreshing...":"Refresh"}</button>
      </section>
      {err&&<div className="error-box history-error">{err}</div>}
      {busy&&<div className="history-card"><p className="history-muted">Loading prediction history (may take 1 minute)...</p></div>}
      {!busy&&items.length===0&&(
        <div className="history-card"><h2>No History Yet</h2><p className="history-muted">Completed predictions will appear here automatically.</p></div>
      )}
      {!busy&&items.length>0&&(
        <div className="history-list">
          {items.map(it=>(
            <article className="history-card" key={it.id}>
              <div className="history-card-main">
                <div><h2>{shortRepo(it.repo_url)}</h2><p className="history-muted">{it.repo_url}</p></div>
                <div className="history-meta-grid">
                  <div><span>Commit</span><strong>{it.commit_sha.slice(0,8)}</strong></div>
                  <div><span>Scanned</span><strong>{new Date(it.scanned_at).toLocaleString()}</strong></div>
                  <div><span>Files</span><strong>{it.total_files_scanned}</strong></div>
                  <div><span>Threshold</span><strong>{it.prediction_threshold!==null&&it.prediction_threshold!==undefined?pct(it.prediction_threshold):"Default"}</strong></div>
                  <div><span>Avg Risk</span><strong>{pct(it.average_risk_probability)}</strong></div>
                </div>
              </div>
              <div className="history-risk-row">
                <span className="history-risk high">High {it.high_risk_count}</span>
                <span className="history-risk medium">Medium {it.medium_risk_count}</span>
                <span className="history-risk low">Low {it.low_risk_count}</span>
                <span className="history-risk defective">Defective {it.defective_count}</span>
              </div>
              <div className="history-actions">
                <button className="primary-button" onClick={()=>onOpen(it.id)} disabled={openId===it.id||delId===it.id}>
                  {openId===it.id?"Opening...":"Open Result"}
                </button>
                {isHistoryDeleteEnabled()&&(
                  <button className="history-delete-button" onClick={()=>onDelete(it.id)} disabled={openId===it.id||delId===it.id}>
                    {delId===it.id?"Deleting...":"Delete"}
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
