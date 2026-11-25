import {describe,expect,it} from "vitest";
import type {PredictionResponse,PredictionResult} from "../models/api_types";
import {buildPdfReportHtml,filterPredictionResults} from "./ResultsView";

const rows:PredictionResult[]=[
  {file_path:"src/main.py",language:"Python",prediction_label:"Defective",defect_risk_probability:0.82,risk_level:"High",recommendation:"Review immediately before release",top_contributing_metrics:"conditional checks"},
  {file_path:"src/helper.py",language:"Python",prediction_label:"Non-defective",defect_risk_probability:0.31,risk_level:"Low",recommendation:"Low priority",top_contributing_metrics:"file size"},
  {file_path:"src/Worker.java",language:"Java",prediction_label:"Defective",defect_risk_probability:0.64,risk_level:"Medium",recommendation:"Review during normal testing",top_contributing_metrics:"method count"}
];

describe("ResultsView helpers",()=>{
  it("filters rows by path and risk tier",()=>{
    const f1=filterPredictionResults(rows,{fileSearch:"main",languageFilter:"All",riskFilter:"High",predictionFilter:"All",minProbability:"",maxProbability:""});
    expect(f1).toHaveLength(1);
    expect(f1[0].file_path).toBe("src/main.py");
    const f2=filterPredictionResults(rows,{fileSearch:"",languageFilter:"All",riskFilter:"All",predictionFilter:"All",minProbability:"",maxProbability:""});
    expect(f2).toHaveLength(3);
  });

  it("builds PDF HTML for selected rows only",()=>{
    const resp:PredictionResponse={repo_url:"https://github.com/sclorg/s2i-python-container.git",commit_sha:"1234567890abcdef1234567890abcdef12345678",prediction_threshold:0.5,total_files_scanned:1,results:[rows[0]]};
    const html=buildPdfReportHtml(resp,[rows[0]]);
    expect(html).toContain("src/main.py");
    expect(html).not.toContain("src/helper.py");
    expect(html).toContain("Exported Files</span><strong>1");
  });
});
