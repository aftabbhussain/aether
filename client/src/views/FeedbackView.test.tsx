import {render,screen,waitFor} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {beforeEach,describe,expect,it,vi} from "vitest";
import FeedbackView from "./FeedbackView";
import {fetchFeedback,submitFeedback} from "../net/http";

vi.mock("../net/http",()=>({
  fetchFeedback:vi.fn(),
  submitFeedback:vi.fn(),
  getApiErrorMessage:vi.fn((_e:unknown,fb:string)=>fb)
}));

const mFetch=vi.mocked(fetchFeedback);
const mSubmit=vi.mocked(submitFeedback);

describe("FeedbackView",()=>{
  beforeEach(()=>{vi.clearAllMocks();mFetch.mockResolvedValue({feedback:[]});});

  it("renders public feedback from backend",async()=>{
    mFetch.mockResolvedValue({feedback:[{id:"fb-1",name:"Student Tester",role:"Student",rating:5,message:"The prediction dashboard is easy to understand.",submitted_at:"2026-06-16T08:00:00.000Z"}]});
    render(<FeedbackView/>);
    expect(await screen.findByText("The prediction dashboard is easy to understand.")).toBeInTheDocument();
    expect(screen.getByText("Student Tester")).toBeInTheDocument();
    expect(screen.getByText("5/5")).toBeInTheDocument();
  });

  it("blocks empty feedback",async()=>{
    const u=userEvent.setup();
    render(<FeedbackView/>);
    await waitFor(()=>expect(mFetch).toHaveBeenCalled());
    await u.click(screen.getByRole("button",{name:"Submit Feedback"}));
    expect(screen.getByText("Please write your feedback before submitting.")).toBeInTheDocument();
    expect(mSubmit).not.toHaveBeenCalled();
  });

  it("prepends submitted feedback",async()=>{
    const u=userEvent.setup();
    mSubmit.mockResolvedValue({feedback:{id:"fb-2",name:"Developer Tester",role:"Developer",rating:4,message:"The repository input guide is helpful.",submitted_at:"2026-06-16T09:00:00.000Z"}});
    render(<FeedbackView/>);
    await waitFor(()=>expect(mFetch).toHaveBeenCalled());
    await u.type(screen.getByLabelText("Name"),"Developer Tester");
    await u.type(screen.getByLabelText("Feedback"),"The repository input guide is helpful.");
    await u.click(screen.getByRole("button",{name:"Submit Feedback"}));
    expect(await screen.findByText("Thank you. Your feedback is now visible on this page.")).toBeInTheDocument();
    expect(screen.getByText("The repository input guide is helpful.")).toBeInTheDocument();
  });
});
