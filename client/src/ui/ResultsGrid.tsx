import type {PredictionResult} from "../models/api_types";
import type {ProbSortOrder} from "../views/ResultsView";
import sortIconUrl from "../../assets/24967-200.png";
import MetricChips from "./MetricChips";

interface Props {
  results:PredictionResult[];
  probabilitySortDirection:ProbSortOrder;
  onToggleProbabilitySort:()=>void;
  selectedResultKeys:Set<string>;
  getResultKey:(r:PredictionResult)=>string;
  onToggleResultSelection:(k:string)=>void;
  onToggleAllShown:()=>void;
  allShownSelected:boolean;
}

const checkTestFile=(r:PredictionResult)=>
  r.is_potential_test_file===true||r.is_potential_test_file===1||r.is_potential_test_file==="true"||r.is_potential_test_file==="1";

export default function ResultsGrid(p:Props){
  if(p.results.length===0){
    return <div className="form-card"><p>No supported Java, Python, or C++ files found for prediction.</p></div>;
  }
  const sortTxt=p.probabilitySortDirection==="desc"?"High to Low":"Low to High";
  return (
    <div className="table-card">
      <div className="table-scroll-box">
        <table className="prediction-table">
          <thead>
            <tr>
              <th className="col-select">
                <input type="checkbox" checked={p.allShownSelected} onChange={p.onToggleAllShown} title="Select all shown results"/>
              </th>
              <th className="col-no">No.</th>
              <th className="col-file">File Path</th>
              <th className="col-language">Language</th>
              <th className="col-prediction">Prediction</th>
              <th className="col-probability">
                <div className="probability-header">
                  <span>Risk Probability</span>
                  <small>Model confidence score</small>
                  <button className="sort-icon-button" onClick={p.onToggleProbabilitySort} title={`Sort probability: ${sortTxt}`}>
                    <img src={sortIconUrl} alt="Sort" className={p.probabilitySortDirection==="desc"?"sort-table-icon":"sort-table-icon rotate-up"}/>
                    <span>{sortTxt}</span>
                  </button>
                </div>
              </th>
              <th className="col-risk">Risk Level</th>
              <th className="col-recommendation">Recommendation</th>
              <th className="col-metrics"><span>Metric Values</span><small>Important SHAP factors</small></th>
              <th className="col-readable-explanation"><span>Explanation</span><small>Plain-language reason</small></th>
            </tr>
          </thead>
          <tbody>
            {p.results.map((it,idx)=>{
              const k=p.getResultKey(it);
              return (
                <tr key={k}>
                  <td className="col-select">
                    <input type="checkbox" checked={p.selectedResultKeys.has(k)} onChange={()=>p.onToggleResultSelection(k)} title={`Select ${it.file_path}`}/>
                  </td>
                  <td className="col-no">{idx+1}</td>
                  <td className="col-file file-path-cell">
                    <span>{it.file_path}</span>
                    {checkTestFile(it)&&(
                      <div className="test-file-badge">
                        <strong>Potential test file</strong>
                        <small>{it.test_file_reason||"Matched a common test-file naming pattern."}</small>
                      </div>
                    )}
                  </td>
                  <td className="col-language">{it.language||"Unknown"}</td>
                  <td className="col-prediction">
                    <span className={it.prediction_label==="Defective"?"badge danger":"badge success"}>{it.prediction_label}</span>
                  </td>
                  <td className="col-probability probability-cell">{(it.defect_risk_probability*100).toFixed(2)}%</td>
                  <td className="col-risk"><span className={`badge ${it.risk_level.toLowerCase()}`}>{it.risk_level}</span></td>
                  <td className="col-recommendation">{it.recommendation}</td>
                  <td className="col-metrics explanation-cell"><MetricChips explanation={it.top_contributing_metrics}/></td>
                  <td className="col-readable-explanation readable-explanation-cell">
                    <p>{it.readable_explanation||"The model detected code patterns that may affect defect risk."}</p>
                    {it.confidence_warning&&(
                      <div className="confidence-warning">
                        <strong>Confidence note</strong>
                        <span>{it.confidence_warning}</span>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
