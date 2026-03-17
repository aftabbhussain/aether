import {useState} from "react";
import {useNavigate} from "react-router-dom";
import {cancelPredictionJob,fetchBranches,fetchCommits,fetchPredictionJob,fetchTags,getApiErrorMessage,startPredictionJob} from "../net/http";
import type {CommitItem,GitRefItem} from "../models/api_types";
import CommitDrawer from "../ui/CommitDrawer";
import RefDrawer from "../ui/RefDrawer";
import {formatEstimatedTime,MAX_SOURCE_FILES_PER_RUN} from "../helpers/eta";

type ThreshMode="balanced"|"aggressive"|"conservative"|"custom";
type GuideKey="repo-url"|"pat"|null;

const LOCAL_CACHE_OK=import.meta.env.VITE_ENABLE_LOCAL_CACHE_MODE!=="false";
const THRESH_OPTS:Array<{mode:ThreshMode;label:string;value:number|null;description:string}>=[
  {mode:"balanced",label:"Balanced",value:null,description:"Use trained model threshold"},
  {mode:"aggressive",label:"Aggressive",value:0.35,description:"Flag more files"},
  {mode:"conservative",label:"Conservative",value:0.65,description:"Flag fewer files"},
  {mode:"custom",label:"Custom",value:null,description:"Choose threshold"}
];

function checkRepoUrl(raw:string){
  const s=raw.trim();
  if(!s)return "Please enter a GitHub repository URL first.";
  let u:URL;
  try{u=new URL(s);}catch{return "Repository URL is not valid. Use https://github.com/owner/repository.";}
  if(!["http:","https:"].includes(u.protocol))return "Repository URL must start with http:// or https://.";
  if(u.hostname.toLowerCase()!=="github.com")return "Only github.com repository URLs are supported.";
  const segs=u.pathname.replace(/\/$/,"").split("/").filter(Boolean);
  if(segs.length!==2)return "Repository URL must use the format https://github.com/owner/repository.";
  if(!segs[0]||!segs[1].replace(/\.git$/,""))return "Repository URL must include both owner and repository name.";
  return "";
}

export default function ScanInputView(){
  const nav=useNavigate();
  const [repoUrl,setRepoUrl]=useState("");
  const [gitRef,setGitRef]=useState("");
  const [gitRefType,setGitRefType]=useState("");
  const [sha,setSha]=useState("");
  const [tMode,setTMode]=useState<ThreshMode>("balanced");
  const [customT,setCustomT]=useState("0.50");
  const [usePat,setUsePat]=useState(true);
  const [pat,setPat]=useState("");
  const [guide,setGuide]=useState<GuideKey>(null);
  const [running,setRunning]=useState(false);
  const [jobId,setJobId]=useState("");
  const [loadingCommits,setLoadingCommits]=useState(false);
  const [loadingRefs,setLoadingRefs]=useState(false);
  const [prog,setProg]=useState({percent:0,stage:"idle",message:""});
  const [err,setErr]=useState("");
  const [commitErr,setCommitErr]=useState("");
  const [refErr,setRefErr]=useState("");
  const [commitOpen,setCommitOpen]=useState(false);
  const [refOpen,setRefOpen]=useState(false);
  const [refTitle,setRefTitle]=useState("Select Branch / Tag");
  const [commits,setCommits]=useState<CommitItem[]>([]);
  const [refs,setRefs]=useState<GitRefItem[]>([]);
  const [pg,setPg]=useState(1);
  const [hasNext,setHasNext]=useState(false);
  const pgSize=20;

  const okUrl=()=>{const m=checkRepoUrl(repoUrl);if(m){setErr(m);return false;}return true;};
  const okRef=()=>{if(!gitRef.trim()){setErr("Please select a branch or tag first.");return false;}return true;};
  const okPat=()=>{
    if(!usePat){
      if(!LOCAL_CACHE_OK){setErr("Local cache mode is disabled on this deployment. Use Personal Token request mode instead.");return false;}
      return true;
    }
    if(!pat.trim()){setErr("Please enter a GitHub Personal Access Token, or switch to local cache mode.");return false;}
    return true;
  };
  const resolveThresh=()=>{
    if(tMode==="balanced")return null;
    if(tMode==="custom"){
      const v=Number(customT);
      if(Number.isNaN(v)||v<0.05||v>0.95){setErr("Custom threshold must be between 0.05 and 0.95.");return undefined;}
      return v;
    }
    return THRESH_OPTS.find(o=>o.mode===tMode)?.value??null;
  };

  const openBranches=async()=>{
    if(!okUrl()||!okPat())return;
    setErr("");setRefErr("");setRefs([]);setRefTitle("Select Branch");setRefOpen(true);setLoadingRefs(true);
    try{const r=await fetchBranches(repoUrl.trim(),usePat,pat.trim());setRefs(r.branches);}
    catch(e){setRefErr(getApiErrorMessage(e,"Failed to load branches. Please check the repository URL or backend server."));}
    finally{setLoadingRefs(false);}
  };

  const openTags=async()=>{
    if(!okUrl()||!okPat())return;
    setErr("");setRefErr("");setRefs([]);setRefTitle("Select Tag");setRefOpen(true);setLoadingRefs(true);
    try{const r=await fetchTags(repoUrl.trim(),usePat,pat.trim());setRefs(r.tags);}
    catch(e){setRefErr(getApiErrorMessage(e,"Failed to load tags. Please check the repository URL or backend server."));}
    finally{setLoadingRefs(false);}
  };

  const pickRef=(r:GitRefItem)=>{
    setGitRef(r.name);setGitRefType(r.type);setSha("");setCommits([]);setPg(1);setHasNext(false);setRefOpen(false);
  };

  const loadCommitsPage=async(targetPg:number)=>{
    if(!okUrl()||!okRef()||!okPat())return;
    setErr("");setCommitErr("");setCommits([]);setCommitOpen(true);setLoadingCommits(true);
    try{
      const r=await fetchCommits(repoUrl.trim(),gitRef.trim(),pgSize,(targetPg-1)*pgSize,usePat,pat.trim());
      setCommits(r.commits);setPg(targetPg);setHasNext(r.commits.length===pgSize);
    }catch(e){
      setCommitErr(getApiErrorMessage(e,"Failed to load commits for the selected branch/tag. Please check the repository URL or backend server."));
    }finally{setLoadingCommits(false);}
  };

  const startScan=async()=>{
    if(!repoUrl.trim()||!sha.trim()){setErr("Please enter repository URL, select a branch/tag, and select a commit.");return;}
    if(!okPat())return;
    const t=resolveThresh();
    if(t===undefined)return;
    setRunning(true);setJobId("");setErr("");
    setProg({percent:0,stage:"queued",message:"Submitting prediction job"});
    try{
      const job=await startPredictionJob({
        repo_url:repoUrl.trim(),commit_sha:sha.trim(),prediction_threshold:t,
        use_personal_access_token:usePat,github_token:usePat?pat.trim():null
      });
      setJobId(job.job_id);
      setProg({percent:job.progress_percent,stage:job.stage,message:job.message});
      let cur=job;
      while(cur.status!=="completed"&&cur.status!=="failed"&&cur.status!=="cancelled"){
        await new Promise(res=>setTimeout(res,900));
        cur=await fetchPredictionJob(cur.job_id);
        setProg({percent:cur.progress_percent,stage:cur.stage,message:cur.message});
      }
      if(cur.status==="cancelled")throw new Error("Prediction job was cancelled.");
      if(cur.status==="failed"||!cur.result)throw new Error(cur.error||"Prediction failed");
      nav("/prediction-result",{state:{predictionResponse:cur.result}});
    }catch(e){
      setErr(getApiErrorMessage(e,"Prediction failed. Please check the backend server and input values."));
    }finally{setRunning(false);setJobId("");}
  };

  const stopScan=async()=>{
    if(!jobId)return;
    try{
      const j=await cancelPredictionJob(jobId);
      setProg({percent:j.progress_percent,stage:j.stage,message:j.message});
      setErr("Prediction job was cancelled.");
    }catch(e){setErr(getApiErrorMessage(e,"Failed to cancel prediction job."));}
    finally{setRunning(false);setJobId("");}
  };

  return (
    <div className="page">
      <div className="scan-workbench">
        <div className="form-card scan-left-card">
          <span className="scan-kicker">Repository Setup</span>
          <h1>Scan a <em className="accent-italic">GitHub</em> Commit</h1>
          <p className="page-description">Enter a repository URL, select a branch or tag, and choose a commit to score defect risk.</p>

          <div className="field-label-row">
            <label>GitHub Repository URL</label>
            <button type="button" className="field-help-button" aria-label="Open GitHub repository URL guide" onClick={()=>setGuide("repo-url")}>?</button>
          </div>
          <input type="text" value={repoUrl} placeholder="https://github.com/apache/commons-lang.git"
            onChange={e=>{setRepoUrl(e.target.value);setErr("");setRefErr("");setCommitErr("");setGitRef("");setGitRefType("");setSha("");setCommits([]);}}/>
          <p className="input-hint">Public GitHub URL, e.g. https://github.com/owner/repository</p>

          {usePat&&(
            <>
              <div className="field-label-row">
                <label>GitHub Personal Access Token</label>
                <button type="button" className="field-help-button" aria-label="Open GitHub PAT guide" onClick={()=>setGuide("pat")}>?</button>
              </div>
              <input type="password" value={pat} placeholder="ghp_xxxxxxxxxxxxxxxxxxxx" autoComplete="off"
                onChange={e=>{setPat(e.target.value);setErr("");setRefErr("");setCommitErr("");}}/>
              <p className="input-hint">Used only for this request and never saved in prediction history.</p>
            </>
          )}

          <div className="button-row two-columns">
            <button className="secondary-button" onClick={openBranches} disabled={loadingRefs||loadingCommits||running}>Load Branches</button>
            <button className="secondary-button" onClick={openTags} disabled={loadingRefs||loadingCommits||running}>Load Tags</button>
          </div>

          <label>Selected Branch / Tag</label>
          <input type="text" value={gitRef?`${gitRefType}: ${gitRef}`:""} readOnly placeholder="Select a branch or tag first"/>
          <button className="secondary-button full-width" onClick={()=>loadCommitsPage(1)} disabled={loadingRefs||loadingCommits||running||!gitRef}>
            {loadingCommits?"Loading Commits...":"Load Commits from Selected Branch/Tag"}
          </button>

          <div className="field-label-row">
            <label>Selected Commit SHA</label>
            <span className="help-tooltip">
              <button type="button" aria-label="Commit SHA guide">?</button>
              <span className="help-tooltip-content">Pick a commit from the drawer or paste a 40-character commit SHA from GitHub.</span>
            </span>
          </div>
          <input type="text" value={sha} onChange={e=>setSha(e.target.value)} placeholder="Select from commit panel or paste commit SHA"/>

          <div className="field-label-row">
            <label>Prediction Sensitivity</label>
            <span className="help-tooltip">
              <button type="button" aria-label="Prediction sensitivity guide">?</button>
              <span className="help-tooltip-content">Controls the probability cutoff for marking a file as defective.</span>
            </span>
          </div>
          <div className="threshold-control">
            {THRESH_OPTS.map(o=>(
              <button key={o.mode} type="button" className={tMode===o.mode?"threshold-option active":"threshold-option"} disabled={running}
                onClick={()=>{setTMode(o.mode);setErr("");}}>
                <strong>{o.label}</strong><span>{o.description}</span>
              </button>
            ))}
          </div>
          {tMode==="custom"&&(
            <div className="threshold-custom-row">
              <input type="number" min="0.05" max="0.95" step="0.01" value={customT} disabled={running}
                onChange={e=>{setCustomT(e.target.value);setErr("");}}/>
              <span>{(Number(customT||0)*100).toFixed(0)}% cutoff</span>
            </div>
          )}

          {err&&<div className="error-box">{err}</div>}
        </div>

        <div className="scan-right-console">
          <div className={usePat?"clone-mode-panel pat-mode":"clone-mode-panel"}>
            <div className="clone-mode-content">
              <div className="clone-mode-heading">
                <strong>{usePat?"Hosted Token Cloning":"Local Cache Mode"}</strong>
                <span>{usePat?"Temporary clone":"Reusable cache"}</span>
              </div>
              <p>{usePat?"Creates an isolated temporary clone for this commit and cleans it up immediately after scoring.":"Uses a local bare mirror cache for faster repeated repository scans."}</p>
              <div className="clone-storage-list">
                {!usePat&&<div><span>Local Cache</span><code>%TEMP%\sdp_github_temp_repos\repo_cache</code></div>}
                <div><span>Worktree</span><code>Temporary server work folder</code></div>
                <div><span>Cleanup</span><code>{usePat?"Removed after run; PAT not stored":"Worktree removed after run"}</code></div>
              </div>
            </div>
            {LOCAL_CACHE_OK&&(
              <div className="clone-mode-action">
                <span>{usePat?"Switch to reusable local mirror cache?":"Switch back to token-scoped cloning?"}</span>
                <button type="button" className="clone-mode-toggle" disabled={loadingRefs||loadingCommits||running}
                  onClick={()=>{setUsePat(v=>!v);setErr("");setRefErr("");setCommitErr("");setGitRef("");setGitRefType("");setSha("");setCommits([]);}}>
                  {usePat?"Use local cache":"Use Personal Token"}
                </button>
              </div>
            )}
          </div>

          <div className="console-run-panel">
            <div className="console-run-head">
              <span className="console-label">EXECUTION CONSOLE</span>
              <span className="idle-pill">{running?prog.stage.toUpperCase():"READY"}</span>
            </div>

            <button className="primary-button full-width scan-launch-btn" onClick={startScan} disabled={running||loadingCommits||loadingRefs}>
              {running?"Analyzing Repository...":"Run Prediction"}
            </button>

            <div className="loading-box">
              <div className="progress-status-header">
                <strong>{running?prog.message:"Waiting for repository and commit"}</strong>
                <span>{running?prog.percent:0}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-bar-fill determinate" style={{width:`${running?prog.percent:0}%`}}></div>
              </div>
              <p className="progress-estimate">
                {running
                  ?`Estimated time: ${formatEstimatedTime(prog.percent)}. Scans up to ${MAX_SOURCE_FILES_PER_RUN} supported files.`
                  :`Supports Java, Python, and C++ (up to ${MAX_SOURCE_FILES_PER_RUN} files per run).`}
              </p>
              {running&&(
                <button type="button" className="cancel-prediction-button" onClick={stopScan} disabled={!jobId}>Cancel Prediction</button>
              )}
              <ol className="progress-steps">
                <li className={prog.percent>=5?"active":""}>Starting</li>
                <li className={prog.percent>=15?"active":""}>Cloning</li>
                <li className={prog.percent>=40?"active":""}>Metrics</li>
                <li className={prog.percent>=55?"active":""}>Git History</li>
                <li className={prog.percent>=72?"active":""}>Predicting</li>
                <li className={prog.percent>=86?"active":""}>SHAP</li>
              </ol>
            </div>
          </div>
        </div>
      </div>

      {guide&&(
        <div className="guide-modal-backdrop" role="presentation" onClick={()=>setGuide(null)}>
          <section className="guide-modal" role="dialog" aria-modal="true" aria-labelledby="guide-modal-title" onClick={e=>e.stopPropagation()}>
            <button type="button" className="guide-modal-close" aria-label="Close guide" onClick={()=>setGuide(null)}>x</button>
            {guide==="repo-url"?(
              <>
                <div className="guide-modal-header">
                  <span>GitHub Repository URL Guide</span>
                  <h2 id="guide-modal-title">Copy the repository HTTPS URL</h2>
                  <p>Use the repository URL from GitHub so the app can load branches, commits, and source files for prediction.</p>
                </div>
                <div className="guide-step-list">
                  <article className="guide-step-card">
                    <div className="guide-step-copy"><strong>Step 1</strong><p>Open the desire repository page on GitHub.</p></div>
                    <img src="/github-url-guide-1.png" alt="GitHub page with Code button"/>
                  </article>
                  <div className="guide-down-arrow" aria-hidden="true"></div>
                  <article className="guide-step-card">
                    <div className="guide-step-copy"><strong>Step 2</strong><p>Copy the root HTTPS OR click on the copy icon beside the repository URL after pressing "Code".</p></div>
                    <img src="/github-url-guide-2.png" alt="GitHub HTTPS clone URL copy area"/>
                  </article>
                </div>
              </>
            ):(
              <>
                <div className="guide-modal-header">
                  <span>GitHub PAT Guide</span>
                  <h2 id="guide-modal-title">Create a Personal Access Token</h2>
                  <p>Create a GitHub token so the app can request repository branches and commits without hitting public rate limits too quickly.</p>
                </div>
                <div className="guide-step-list">
                  <article className="guide-step-card"><div className="guide-step-copy"><strong>Step 1</strong><p>Open GitHub Profile settings.</p></div><img src="/pat-guide-1.png" alt="GitHub Developer settings page"/></article>
                  <div className="guide-down-arrow" aria-hidden="true"></div>
                  <article className="guide-step-card"><div className="guide-step-copy"><strong>Step 2</strong><p>Go to Developer settings.</p></div><img src="/pat-guide-2.png" alt="GitHub create Personal Access Token page"/></article>
                  <div className="guide-down-arrow" aria-hidden="true"></div>
                  <article className="guide-step-card"><div className="guide-step-copy"><strong>Step 3</strong><p>Create a new fine grained Personal Access Token (Public access only) and copy the generated token and paste it into the PAT field.</p></div><img src="/pat-guide-3.png" alt="GitHub generated Personal Access Token copy screen"/></article>
                </div>
              </>
            )}
          </section>
        </div>
      )}
      <RefDrawer isOpen={refOpen} title={refTitle} loading={loadingRefs} refs={refs} errorMessage={refErr} onClose={()=>setRefOpen(false)} onSelectRef={pickRef}/>
      <CommitDrawer isOpen={commitOpen} loading={loadingCommits} commits={commits} errorMessage={commitErr} currentPage={pg} pageSize={pgSize} hasNextPage={hasNext}
        onClose={()=>setCommitOpen(false)} onSelectCommit={c=>{setSha(c.sha);setCommitOpen(false);}}
        onNextPage={()=>loadCommitsPage(pg+1)} onPreviousPage={()=>{if(pg>1)loadCommitsPage(pg-1);}}/>
    </div>
  );
}
