import type {CommitItem} from "../models/api_types";

interface Props {
  isOpen:boolean;loading:boolean;commits:CommitItem[];errorMessage:string;
  currentPage:number;pageSize:number;hasNextPage:boolean;
  onClose:()=>void;onSelectCommit:(c:CommitItem)=>void;onNextPage:()=>void;onPreviousPage:()=>void;
}

function splitMsg(raw:string){
  const norm=raw.replace(/\s+/g," ").trim();
  const sBreak=norm.search(/(?<=\.)\s/);
  const br=sBreak>0?sBreak:norm.indexOf(" -- ");
  const cut=br>0&&br<140?br:110;
  if(norm.length<=cut)return {sub:norm,rest:""};
  return {sub:`${norm.slice(0,cut).trim()}...`,rest:norm.slice(cut).trim()};
}

export default function CommitDrawer(p:Props){
  if(!p.isOpen)return null;
  const from=(p.currentPage-1)*p.pageSize+1;
  const to=from+p.commits.length-1;
  return (
    <div className="side-panel-overlay">
      <div className="side-panel">
        <div className="side-panel-sticky-header">
          <div className="side-panel-header">
            <div>
              <h2>Select Commit</h2>
              <p>Showing commits {p.commits.length>0?from:0}{p.commits.length>0?` - ${to}`:""}.</p>
            </div>
            <button className="close-button" onClick={p.onClose}>×</button>
          </div>
          <div className="commit-pagination">
            <button className="small-button" onClick={p.onPreviousPage} disabled={p.loading||p.currentPage===1}>Previous</button>
            <span>Page {p.currentPage}</span>
            <button className="small-button" onClick={p.onNextPage} disabled={p.loading||!p.hasNextPage}>Next</button>
          </div>
        </div>
        <div className="side-panel-scroll-body">
          {p.loading&&(
            <div className="loading-section">
              <div className="progress-bar"><div className="progress-bar-fill"></div></div>
              <p>Loading commits from GitHub...</p>
            </div>
          )}
          {p.errorMessage&&<div className="error-box">{p.errorMessage}</div>}
          {!p.loading&&p.commits.length>0&&(
            <div className="commit-list">
              {p.commits.map(c=>{
                const m=splitMsg(c.message);
                return (
                  <div key={c.sha} className="commit-item">
                    <div className="commit-top-row">
                      <span className="commit-sha">{c.short_sha}</span>
                      <span className="commit-date">{new Date(c.date).toLocaleDateString()}</span>
                    </div>
                    <div className="commit-message" title={c.message}>{m.sub}</div>
                    {m.rest&&(
                      <details className="commit-details">
                        <summary>Show full message</summary>
                        <p>{c.message}</p>
                      </details>
                    )}
                    <div className="commit-footer-row">
                      <div className="commit-author">By {c.author}</div>
                      <button className="select-commit-button" onClick={()=>p.onSelectCommit(c)}>Select</button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {!p.loading&&p.commits.length===0&&!p.errorMessage&&<div className="empty-box">No commits found.</div>}
        </div>
      </div>
    </div>
  );
}
