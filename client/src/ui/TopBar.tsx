import {Link,useLocation} from "react-router-dom";

export default function TopBar(){
  const loc=useLocation();
  const active=(p:string)=>loc.pathname===p?"nav-link is-active":"nav-link";
  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <div className="navbar-title">Aether</div>
      </Link>
      <div className="navbar-links">
        <Link to="/" className={active("/")}>Home</Link>
        <Link to="/repository-input" className={active("/repository-input")}>Scan</Link>
        <Link to="/prediction-history" className={active("/prediction-history")}>History</Link>
        <Link to="/how-it-works" className={active("/how-it-works")}>How It Works</Link>
        <Link to="/feedback" className={active("/feedback")}>Feedback</Link>
      </div>
      <div className="navbar-right">
        <Link to="/repository-input" className="nav-status-pill">
          <span className="nav-status-dot"/>
          <span>STANDBY</span>
        </Link>
        <Link to="/how-it-works" className="nav-icon-btn" title="Model Evaluation">✦</Link>
      </div>
    </nav>
  );
}
