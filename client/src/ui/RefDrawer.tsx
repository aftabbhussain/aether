import type {GitRefItem} from "../models/api_types";

interface Props {
  isOpen:boolean;title:string;loading:boolean;refs:GitRefItem[];errorMessage:string;
  onClose:()=>void;onSelectRef:(r:GitRefItem)=>void;
}

export default function RefDrawer({isOpen,title,loading,refs,errorMessage,onClose,onSelectRef}:Props){
  if(!isOpen)return null;
  return (
    <div className="side-panel-overlay">
      <div className="side-panel">
        <div className="side-panel-sticky-header">
          <div className="side-panel-header">
            <div>
              <h2>{title}</h2>
              <p>Select a branch or tag to analyze.</p>
            </div>
            <button className="close-button" onClick={onClose}>×</button>
          </div>
        </div>
        <div className="side-panel-scroll-body">
          {loading&&(
            <div className="loading-section">
              <div className="progress-bar"><div className="progress-bar-fill"></div></div>
              <p>Loading branch/tag names from GitHub...</p>
            </div>
          )}
          {errorMessage&&<div className="error-box">{errorMessage}</div>}
          {!loading&&refs.length>0&&(
            <>
              {refs.some(r=>r.is_default)&&(
                <div className="default-branch-caption">
                  <strong>Default branch shown first</strong>
                  <span>The default branch is the repository's main working branch on GitHub. Choose it if you are unsure which branch to analyze.</span>
                </div>
              )}
              <div className="commit-list">
                {refs.map(r=>(
                  <button key={`${r.type}-${r.name}`} className="commit-item" onClick={()=>onSelectRef(r)}>
                    <div className="commit-top-row">
                      <span className="commit-sha">{r.type}</span>
                      {r.is_default&&<span className="default-branch-badge">Default</span>}
                    </div>
                    <div className="commit-message">{r.name}</div>
                  </button>
                ))}
              </div>
            </>
          )}
          {!loading&&refs.length===0&&!errorMessage&&<div className="empty-box">No branches or tags found.</div>}
        </div>
      </div>
    </div>
  );
}
