SIGNAL_MAP=[
  ("method interaction complexity","method interaction complexity"),
  ("number of conditional checks","conditional checks"),
  ("static method usage","static method usage"),
  ("class cohesion complexity","class cohesion complexity"),
  ("number of methods","number of methods"),
  ("file size","file size"),
  ("dependency between classes","class dependency level"),
  ("overall method complexity","method complexity"),
  ("number of return paths","return paths"),
  ("inheritance depth","inheritance depth"),
  ("historical file change frequency","file change history"),
  ("previous bug-fix activity","previous bug-fix history"),
  ("recent file change activity","recent file changes"),
  ("time since the file was last changed","time since last change"),
  ("lines added in the previous file change","lines added in the previous change"),
  ("lines deleted in the previous file change","lines deleted in the previous change"),
  ("code churn in the previous file change","previous change churn"),
  ("files changed together in the previous commit","files changed together"),
  ("selected commit author's prior changes","author's previous changes to this file")
]

class TextSummaryBuilder:
  def make_summary(self,raw_exp:str,risk:str,prob:float)->str:
    low=raw_exp.lower()
    reasons=[label for needle,label in SIGNAL_MAP if needle in low]
    if not reasons:
      reasons=["several metric patterns"]
    reason_str=self._join_reasons(reasons)
    pct=round(prob*100,2)
    if risk=="High":
      return f"The model gives this file a high defect risk score ({pct}%). The strongest signals are {reason_str}. This does not prove the file contains a bug, but it means the file looks similar to higher-risk examples seen during training. Review it before lower-risk files."
    if risk=="Medium":
      return f"The model gives this file a medium defect risk score ({pct}%). The main signals are {reason_str}. The result is not an urgent warning, but these areas are worth checking if the file is part of the current change."
    return f"The model gives this file a low defect risk score ({pct}%). It still considered signals such as {reason_str}, but they did not strongly push the prediction toward higher risk. Review is optional unless this file is important to the current change."

  def _join_reasons(self,items:list)->str:
    if len(items)==1:
      return items[0]
    if len(items)==2:
      return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1])+f", and {items[-1]}"
