export const MAX_SOURCE_FILES_PER_RUN=500;
const EST_SECS=300;
export const formatEstimatedTime=(pct:number)=>{
  if(pct>=100)return "less than 1 minute";
  const rem=Math.max(0,100-pct);
  const secs=Math.max(30,Math.ceil((rem/100)*EST_SECS));
  const mins=Math.max(1,Math.ceil(secs/60));
  return `${mins} minute${mins===1?"":"s"}`;
};
