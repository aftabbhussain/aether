import {useEffect,useState} from "react";
import {fetchFeedback,getApiErrorMessage,submitFeedback} from "../net/http";
import type {FeedbackEntry} from "../models/api_types";

const ROLES=["Student","Developer","Evaluator","Other"];
const fmtTs=(v:string)=>v?new Date(v).toLocaleString():"Unknown date";

export default function FeedbackView(){
  const [rows,setRows]=useState<FeedbackEntry[]>([]);
  const [name,setName]=useState("");
  const [role,setRole]=useState("Student");
  const [rating,setRating]=useState(5);
  const [msg,setMsg]=useState("");
  const [busy,setBusy]=useState(true);
  const [sending,setSending]=useState(false);
  const [okTxt,setOkTxt]=useState("");
  const [errTxt,setErrTxt]=useState("");

  const refreshList=async()=>{
    setBusy(true);setErrTxt("");
    try{
      const res=await fetchFeedback();
      setRows(res.feedback);
    }catch(e){
      setErrTxt(getApiErrorMessage(e,"Feedback could not be loaded from the backend. This may happen because the application runs on Render's free plan. Please wait approximately 1 minute and try again."));
    }finally{
      setBusy(false);
    }
  };

  useEffect(()=>{refreshList();},[]);

  const onSend=async()=>{
    const txt=msg.trim();
    if(!txt){setErrTxt("Please write your feedback before submitting.");return;}
    setSending(true);setErrTxt("");setOkTxt("");
    try{
      const res=await submitFeedback({name:name.trim(),role,rating,message:txt});
      setRows(prev=>[res.feedback,...prev]);
      setName("");setRole("Student");setRating(5);setMsg("");
      setOkTxt("Thank you. Your feedback is now visible on this page.");
    }catch(e){
      setErrTxt(getApiErrorMessage(e,"Feedback could not be submitted. This may happen because the application runs on Render's free plan. Please wait approximately 1 minute and try again."));
    }finally{
      setSending(false);
    }
  };

  return (
    <div className="page feedback-page">
      <section className="feedback-hero">
        <span>Public Feedback</span>
        <h1>Share feedback about Aether</h1>
        <p>This page helps collect real user feedback for the project. Submitted feedback is public and can be viewed by anyone who opens this page.</p>
      </section>
      <section className="feedback-layout">
        <div className="feedback-form-card">
          <h2>Leave Feedback</h2>
          <p className="feedback-note">Please do not include passwords, GitHub tokens, private repository details, or other sensitive information.</p>
          <label htmlFor="feedback-name">Name</label>
          <input id="feedback-name" type="text" value={name} onChange={e=>setName(e.target.value)} placeholder="Optional" maxLength={80}/>
          <label htmlFor="feedback-role">Role</label>
          <select id="feedback-role" value={role} onChange={e=>setRole(e.target.value)}>
            {ROLES.map(r=><option key={r} value={r}>{r}</option>)}
          </select>
          <label>Rating</label>
          <div className="rating-row" aria-label="Feedback rating">
            {[1,2,3,4,5].map(n=>(
              <button key={n} type="button" className={rating===n?"active":""} onClick={()=>setRating(n)}>{n}</button>
            ))}
          </div>
          <label htmlFor="feedback-message">Feedback</label>
          <textarea id="feedback-message" value={msg} onChange={e=>setMsg(e.target.value)} placeholder="What worked well? What was confusing? What should be improved?" maxLength={1200} rows={6}/>
          <div className="feedback-character-count">{msg.length}/1200 characters</div>
          {okTxt&&<div className="success-box">{okTxt}</div>}
          {errTxt&&<div className="error-box">{errTxt}</div>}
          <button type="button" className="primary-button full-width" onClick={onSend} disabled={sending}>
            {sending?"Submitting...":"Submit Feedback"}
          </button>
        </div>
        <div className="feedback-list-card">
          <div className="feedback-list-header">
            <div><h2>Public Feedback</h2><p>Newest responses appear first.</p></div>
            <button type="button" className="secondary-button" onClick={refreshList}>{busy?"Loading...":"Refresh"}</button>
          </div>
          {busy?(
            <div className="empty-feedback">Loading feedback... This may take approximately 1 minute when the Render free-plan server is waking up.</div>
          ):rows.length===0?(
            <div className="empty-feedback">No feedback has been submitted yet.</div>
          ):(
            <div className="feedback-list">
              {rows.map(it=>(
                <article className="feedback-item" key={it.id}>
                  <div className="feedback-item-header">
                    <div><strong>{it.name||"Anonymous"}</strong><span>{it.role||"User"}</span></div>
                    <div className="feedback-rating">{it.rating}/5</div>
                  </div>
                  <p>{it.message}</p>
                  <time>{fmtTs(it.submitted_at)}</time>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
