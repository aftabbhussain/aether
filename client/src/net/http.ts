import axios from "axios";
import type {
  PredictionRequest,PredictionResponse,PredictionJobStatus,
  CommitListResponse,BranchListResponse,TagListResponse,
  ModelTransparencyResponse,PredictionHistoryListResponse,
  PredictionHistoryDetail,FeedbackRequest,FeedbackListResponse,FeedbackCreateResponse
} from "../models/api_types";

const BASE=import.meta.env.VITE_API_BASE_URL||"http://127.0.0.1:8000";

export const getApiErrorMessage=(err:unknown,fallback:string)=>{
  if(axios.isAxiosError(err)){
    if(!err.response){
      return "Network error. This may happen because the backend runs on Render's free plan and can sleep after about 15 minutes of inactivity. Please wait approximately 1 minute for the server to wake up, then try again.";
    }
    if(err.response?.status===404){
      return "The requested backend resource was not found. If this happened during prediction, the backend may have restarted while the job was running.";
    }
    const detail=err.response?.data?.detail;
    if(typeof detail==="string"&&detail.trim()){
      return detail;
    }
    if(Array.isArray(detail)&&detail.length>0){
      return detail.map(x=>x.msg||JSON.stringify(x)).join(" ");
    }
    if(err.message)return err.message;
  }
  if(err instanceof Error&&err.message)return err.message;
  return fallback;
};

export const predictDefects=async(req:PredictionRequest):Promise<PredictionResponse>=>{
  const r=await axios.post<PredictionResponse>(`${BASE}/predict`,req);
  return r.data;
};
export const startPredictionJob=async(req:PredictionRequest):Promise<PredictionJobStatus>=>{
  const r=await axios.post<PredictionJobStatus>(`${BASE}/prediction-jobs`,req);
  return r.data;
};
export const fetchPredictionJob=async(id:string):Promise<PredictionJobStatus>=>{
  const r=await axios.get<PredictionJobStatus>(`${BASE}/prediction-jobs/${id}`);
  return r.data;
};
export const cancelPredictionJob=async(id:string):Promise<PredictionJobStatus>=>{
  const r=await axios.post<PredictionJobStatus>(`${BASE}/prediction-jobs/${id}/cancel`);
  return r.data;
};
export const exportPredictionReport=async(resp:PredictionResponse):Promise<Blob>=>{
  const r=await axios.post(`${BASE}/export-report`,resp,{responseType:"blob"});
  return r.data;
};
export const fetchModelTransparency=async():Promise<ModelTransparencyResponse>=>{
  const r=await axios.get<ModelTransparencyResponse>(`${BASE}/model-transparency`);
  return r.data;
};
export const fetchFeedback=async():Promise<FeedbackListResponse>=>{
  const r=await axios.get<FeedbackListResponse>(`${BASE}/feedback`);
  return r.data;
};
export const submitFeedback=async(req:FeedbackRequest):Promise<FeedbackCreateResponse>=>{
  const r=await axios.post<FeedbackCreateResponse>(`${BASE}/feedback`,req);
  return r.data;
};
export const fetchPredictionHistory=async():Promise<PredictionHistoryListResponse>=>{
  const r=await axios.get<PredictionHistoryListResponse>(`${BASE}/prediction-history`);
  return r.data;
};
export const fetchPredictionHistoryDetail=async(id:string):Promise<PredictionHistoryDetail>=>{
  const r=await axios.get<PredictionHistoryDetail>(`${BASE}/prediction-history/${id}`);
  return r.data;
};
export const deletePredictionHistoryItem=async(id:string):Promise<void>=>{
  await axios.delete(`${BASE}/prediction-history/${id}`);
};
export const fetchBranches=async(repoUrl:string,usePat=false,tok=""):Promise<BranchListResponse>=>{
  const r=await axios.post<BranchListResponse>(`${BASE}/branches`,{repo_url:repoUrl,use_personal_access_token:usePat,github_token:tok||null});
  return r.data;
};
export const fetchTags=async(repoUrl:string,usePat=false,tok=""):Promise<TagListResponse>=>{
  const r=await axios.post<TagListResponse>(`${BASE}/tags`,{repo_url:repoUrl,use_personal_access_token:usePat,github_token:tok||null});
  return r.data;
};
export const fetchCommits=async(repoUrl:string,ref:string,max=20,skip=0,usePat=false,tok=""):Promise<CommitListResponse>=>{
  const r=await axios.post<CommitListResponse>(`${BASE}/commits`,{repo_url:repoUrl,git_ref:ref,max_commits:max,skip,use_personal_access_token:usePat,github_token:tok||null});
  return r.data;
};
