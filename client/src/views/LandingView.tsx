import {Link} from "react-router-dom";

const TAGS=["JAVA","PYTHON","C++","XGB","SHAP","GIT"];

export default function LandingView(){
  return (
    <div className="page landing-shell">
      <section className="split-hero">
        <div className="split-hero-left">
          <h1>
            Predict code risk directly from your{" "}
            <em className="accent-italic">GitHub commits!</em>
          </h1>
          <div className="split-subkicker">Static + Git Process Analysis</div>
          <p className="split-lead">
            Aether scans Java, Python, and C++ files in any selected commit,
            combining code complexity with Git history to surface high-risk files
            before release.
          </p>
          <div className="split-cta-row">
            <Link to="/repository-input" className="hero-black-cta">
              <span className="cta-icon">⌘</span>
              <span>Start Prediction</span>
            </Link>
            <Link to="/how-it-works" className="secondary-home-link">
              How It Works
            </Link>
          </div>
          <div className="idle-telemetry-card">
            <div className="idle-telemetry-top">
              <span className="idle-pill">Engine Ready</span>
              <strong className="idle-pct">0<sub>%</sub></strong>
            </div>
            <div className="idle-track"><span/></div>
            <div className="idle-telemetry-foot">
              <span>Select a repository commit to scan</span>
              <b>Ready</b>
            </div>
          </div>
        </div>

        <div className="split-hero-right">
          <div className="console-card">
            <div className="console-top-grid">
              <div className="console-box">
                <span className="console-label">NEW ANALYSIS</span>
                <Link to="/repository-input" className="console-white-btn">
                  Scan Repository
                </Link>
              </div>
              <div className="console-box">
                <span className="console-label">SAVED RUNS</span>
                <div className="console-inline-row">
                  <span className="console-fake-input">PAST SCANS</span>
                  <Link to="/prediction-history" className="console-red-btn">
                    Open
                  </Link>
                </div>
              </div>
            </div>

            <div className="console-box console-mid-box">
              <span className="console-label">ACTIVE PIPELINE CAPABILITIES :</span>
              <div className="console-tile-row">
                <div className="console-tiles">
                  {TAGS.map(t=><span key={t} className="console-tile">{t}</span>)}
                </div>
                <div className="console-qr-badge">
                  <span>19</span>
                  <small>SIGNALS</small>
                </div>
              </div>
              <div className="console-chip-actions">
                <Link to="/how-it-works" className="console-mini-pill">Model Metrics</Link>
                <Link to="/prediction-history" className="console-mini-pill">Scan History</Link>
                <Link to="/feedback" className="console-mini-pill">Feedback</Link>
              </div>
            </div>

            <div className="console-status-strip">
              <span>SHAP TreeExplainer + XGBoost</span>
              <b>Standby</b>
            </div>

            <div className="console-footer-metrics">
              <div>
                <span>ML ENGINE</span>
                <b className="txt-green">Online</b>
              </div>
              <div>
                <span>CLASSIFIER</span>
                <b>XGBoost</b>
              </div>
              <div>
                <span>THRESHOLD</span>
                <b>34.0%</b>
              </div>
              <div>
                <span>THROUGHPUT</span>
                <b className="txt-cyan">500 Files</b>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="card-grid home-card-grid">
        <div className="card home-step-card">
          <span>1</span><h3>Choose Repository</h3>
          <p>Enter a GitHub repository URL, select a branch or tag, then pick a commit to inspect.</p>
        </div>
        <div className="card home-step-card">
          <span>2</span><h3>Extract Metrics</h3>
          <p>Measures file size, complexity, conditional checks, method structure, and commit churn.</p>
        </div>
        <div className="card home-step-card">
          <span>3</span><h3>Review Risk</h3>
          <p>Ranks files by defect probability and explains which metric values drove the score.</p>
        </div>
      </section>
    </div>
  );
}
