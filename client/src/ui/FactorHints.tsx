const DESCS:Record<string,string>={
  "Method interaction complexity":"This means the file has many method calls or interactions. More interactions can make the file harder to understand and test.",
  "Number of conditional checks":"This means the file contains many if, else, switch, or comparison conditions. More conditions usually mean more decision paths.",
  "Static method usage":"This means the file uses many static method calls. High static usage may increase dependency or coupling between code parts.",
  "Class cohesion complexity":"This means the methods in the class may not be strongly related to each other. Low cohesion can make the class harder to maintain.",
  "Number of methods":"This means the file contains many methods. More methods may increase responsibility and maintenance difficulty.",
  "File size":"This means the file has many lines of code. Larger files are usually harder to review and maintain.",
  "Dependency between classes":"This means the file depends on many other classes. Higher dependency can increase the chance of side effects.",
  "Overall method complexity":"This means the file has more complex method logic, such as loops and condition branches.",
  "Number of return paths":"This means the file has many return statements. Many return paths can make logic flow harder to trace.",
  "Inheritance depth":"This means the class is deeper in the inheritance hierarchy. Deeper inheritance can make behavior harder to understand."
};

export default function FactorHints({explanation}:{explanation:string}){
  const parts=explanation.split(".").map(s=>s.trim()).filter(Boolean);
  return (
    <div className="explanation-list">
      {parts.map((s,i)=>{
        const kw=Object.keys(DESCS).find(k=>s.startsWith(k));
        if(!kw)return <div key={i} className="explanation-item">{s}.</div>;
        const rest=s.replace(kw,"").trim();
        return (
          <div key={i} className="explanation-item">
            <span className="tooltip-keyword">
              {kw}
              <span className="tooltip-box">{DESCS[kw]}</span>
            </span>
            <span> {rest}.</span>
          </div>
        );
      })}
    </div>
  );
}
