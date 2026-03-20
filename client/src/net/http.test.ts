import {describe,expect,it} from "vitest";
import {getApiErrorMessage} from "./http";

describe("getApiErrorMessage",()=>{
  it("handles network errors",()=>{
    const m=getApiErrorMessage({isAxiosError:true},"Fallback");
    expect(m).toContain("Network error");
    expect(m).toContain("Render's free plan");
    expect(m).toContain("approximately 1 minute");
  });
  it("handles 404 responses",()=>{
    const m=getApiErrorMessage({isAxiosError:true,response:{status:404,data:{}}},"Fallback");
    expect(m).toContain("backend resource was not found");
    expect(m).toContain("backend may have restarted");
  });
  it("returns backend detail message",()=>{
    const m=getApiErrorMessage({isAxiosError:true,response:{status:403,data:{detail:"GitHub authentication failed. Personal Access Token is invalid or out of access."}}},"Fallback");
    expect(m).toContain("GitHub authentication failed");
    expect(m).toContain("Personal Access Token");
  });
});
