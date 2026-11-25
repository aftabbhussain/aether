import {BrowserRouter,Routes,Route} from "react-router-dom";
import TopBar from "./ui/TopBar";
import LandingView from "./views/LandingView";
import ScanInputView from "./views/ScanInputView";
import ResultsView from "./views/ResultsView";
import GuideView from "./views/GuideView";
import HistoryView from "./views/HistoryView";
import FeedbackView from "./views/FeedbackView";

export default function App(){
  return (
    <BrowserRouter>
      <TopBar/>
      <Routes>
        <Route path="/" element={<LandingView/>}/>
        <Route path="/repository-input" element={<ScanInputView/>}/>
        <Route path="/prediction-result" element={<ResultsView/>}/>
        <Route path="/how-it-works" element={<GuideView/>}/>
        <Route path="/prediction-history" element={<HistoryView/>}/>
        <Route path="/feedback" element={<FeedbackView/>}/>
      </Routes>
    </BrowserRouter>
  );
}
