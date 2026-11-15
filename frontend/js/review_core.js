/* Pure local portfolio/journal logic. No fetch, telemetry, or model calls. */
(function (root) {
  "use strict";
  const copy = value => JSON.parse(JSON.stringify(value));
  const JOURNAL_KEY = "sarthi_journal_v1";
  const SCENARIOS = {
    easing: {name:"Rates fall", assumption:"Hypothesis: policy rates fall. This is not a forecast.",
      questions:["Which funding and lending rates would actually reprice?", "Could deposit repricing offset changes in lending income?", "What company disclosure would confirm or contradict your assumption?"]},
    steady: {name:"Rates stay unchanged", assumption:"Hypothesis: policy rates stay unchanged. Transmission from earlier decisions may still be uncertain.",
      questions:["Which earlier policy assumptions are still untested?", "What evidence would justify changing your thesis without a new rate decision?", "Are you treating an unchanged rate as proof that company conditions are unchanged?"]},
    tightening: {name:"Rates rise", assumption:"Hypothesis: policy rates rise. This is not a forecast.",
      questions:["Which borrowing or refinancing assumptions would need checking?", "Could asset and liability repricing move differently?", "What evidence would change your view rather than simply increase your concern?"]}
  };
  function requireText(value, label, max=2000, required=true) {
    if (typeof value !== "string" || value.length > max || (required && !value.trim())) throw new Error(`${label} must be ${required ? "nonempty and " : ""}at most ${max} characters.`);
    return value.trim();
  }
  function validDate(value, label="Review date") {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(Date.parse(value+"T00:00:00Z")) || new Date(value+"T00:00:00Z").toISOString().slice(0,10) !== value) throw new Error(`${label} must be a valid date.`);
    return value;
  }
  function todayInIndia(instant=new Date()) {
    const parts = new Intl.DateTimeFormat("en", {timeZone:"Asia/Kolkata", year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date(instant));
    const part = name => parts.find(p => p.type===name).value;
    return `${part("year")}-${part("month")}-${part("day")}`;
  }
  function validateHoldings(rows) {
    if (!Array.isArray(rows) || rows.length > 300) throw new Error("Portfolio must contain at most 300 holdings.");
    const seen = new Set();
    const clean = rows.map(row => {
      const ticker = requireText(row.ticker,"Ticker",24).toUpperCase();
      if (!/^[A-Z0-9&.-]{1,24}$/.test(ticker) || seen.has(ticker)) throw new Error(`Invalid or duplicate ticker: ${ticker}`);
      seen.add(ticker);
      const sector = requireText(row.sector,"Sector",60);
      const allocation = row.allocation_pct;
      if (typeof allocation !== "number" || !Number.isFinite(allocation) || allocation <= 0 || allocation > 100) throw new Error(`Invalid allocation for ${ticker}.`);
      return {ticker,sector,allocation_pct:allocation};
    });
    if (clean.reduce((sum,h)=>sum+h.allocation_pct,0) > 100.000001) throw new Error("Total allocation exceeds 100%.");
    return clean;
  }
  function parseCSV(text) {
    if (typeof text !== "string" || text.length > 1_000_000) throw new Error("CSV must be smaller than one megabyte.");
    const rows=[]; let row=[], field="", quoted=false, closed=false;
    text=text.replace(/^\uFEFF/,"");
    for(let i=0;i<text.length;i++) {
      const c=text[i];
      if(quoted) {
        if(c==='"' && text[i+1]==='"') {field+='"';i++;}
        else if(c==='"') {quoted=false;closed=true;}
        else field+=c;
      } else if(c==='"') {
        if(field || closed) throw new Error("Malformed CSV quotation.");
        quoted=true;
      } else if(c===',' || c==='\n' || c==='\r') {
        row.push(field);field="";closed=false;
        if(c!==',') {if(row.some(v=>v.trim()))rows.push(row);row=[]; if(c==='\r' && text[i+1]==='\n')i++;}
      } else {
        if(closed && c.trim()) throw new Error("Unexpected text after CSV quotation.");
        if(!closed)field+=c;
      }
    }
    if(quoted) throw new Error("Unclosed CSV quotation.");
    row.push(field);if(row.some(v=>v.trim()))rows.push(row);
    const header=(rows.shift()||[]).map(v=>v.trim().toLowerCase());
    if(header.join(',')!=="ticker,sector,allocation_pct") throw new Error("CSV headers must be ticker,sector,allocation_pct in that order.");
    if(!rows.length) throw new Error("CSV contains no holdings.");
    return validateHoldings(rows.map((r,i)=>{
      if(r.length!==3 || !/^\d+(?:\.\d{1,4})?%?$/.test(r[2].trim()))throw new Error(`Invalid CSV values on data row ${i+1}.`);
      return {ticker:r[0],sector:r[1],allocation_pct:Number(r[2].trim().replace(/%$/,""))};
    }));
  }
  function portfolioSummary(holdings, sectorLimit=35) {
    const clean=validateHoldings(holdings);
    if(!Number.isFinite(sectorLimit) || sectorLimit<=0 || sectorLimit>100)throw new Error("Sector review threshold must be between 0 and 100.");
    const sectors=new Map();
    for(const h of clean) {const key=h.sector.toLowerCase();const s=sectors.get(key)||{name:h.sector,allocation:0};s.allocation+=h.allocation_pct;sectors.set(key,s);}
    const ordered=[...sectors.values()].sort((a,b)=>b.allocation-a.allocation);
    const allocated=clean.reduce((sum,h)=>sum+h.allocation_pct,0);
    return {holdingCount:clean.length,allocated,unassigned:Math.max(0,100-allocated),sectors:ordered,
      largestHolding:[...clean].sort((a,b)=>b.allocation_pct-a.allocation_pct)[0]||null,
      aboveThreshold:ordered.filter(s=>s.allocation>sectorLimit),sectorLimit};
  }
  function scenarioWorksheet(holdings, scenario) {
    if(!SCENARIOS[scenario])throw new Error("Unknown scenario.");
    const clean=validateHoldings(holdings);
    const mapped=new Set(["banking","nbfcs","real estate","automotive"]);
    return {...copy(SCENARIOS[scenario]), scenario, mapped:clean.filter(h=>mapped.has(h.sector.toLowerCase())),
      unmapped:clean.filter(h=>!mapped.has(h.sector.toLowerCase())),
      notice:"Qualitative worksheet. The four-sector mapping is a declared heuristic; unmapped holdings are not proven unaffected. No return, probability, or loss is estimated."};
  }
  function sourceSnapshot(card) {
    if(!card)return null;
    return {id:requireText(card.id,"Event ID",80),title:requireText(card.canonical_title,"Event title",1000),
      published_on:validDate(card.published_at.slice(0,10),"Event date"),
      source_url:requireText(card.source_url||"","Source URL",1200,false),
      text_sha256:requireText(card.source_text_sha256||"","Source hash",64,false),
      is_sample:!!card.is_sample,excerpt:requireText((card.evidence_excerpt||"").slice(0,6000),"Source excerpt",6000,false)};
  }
  function fields(value) {
    const ticker=requireText(value.ticker,"Ticker",24).toUpperCase();
    if(!/^[A-Z0-9&.-]{1,24}$/.test(ticker))throw new Error("Enter a valid ticker.");
    if(!["research","continue","revisit"].includes(value.decision))throw new Error("Choose a decision label.");
    return {ticker,thesis:requireText(value.thesis,"Thesis"),disconfirming:requireText(value.disconfirming,"Disconfirming evidence"),
      review_on:validDate(value.review_on),decision:value.decision,
      source:value.source ? sourceSnapshot({id:value.source.id,canonical_title:value.source.title,published_at:value.source.published_on,
        source_url:value.source.source_url,source_text_sha256:value.source.text_sha256,is_sample:value.source.is_sample,evidence_excerpt:value.source.excerpt}) : null};
  }
  class JournalStore {
    constructor(storage, {clock=()=>new Date().toISOString(), id=()=>crypto.randomUUID()}={}) {
      this.storage=storage;this.clock=clock;this.id=id;this.problem="";this.blocked=false;
      try {const raw=storage.getItem(JOURNAL_KEY);this.entries=raw?this.validate(JSON.parse(raw)):[];}
      catch(_) {this.entries=[];this.blocked=true;this.problem="Saved journal could not be read. Export the unreadable backup before replacing it; new saves are blocked.";}
    }
    validate(value) {
      if(!Array.isArray(value)||value.length>500)throw new Error("Journal must contain at most 500 entries.");
      const ids=new Set();
      return value.map(entry=>{
        const id=requireText(entry.id,"Entry ID",100);if(ids.has(id))throw new Error("Duplicate journal ID.");ids.add(id);
        if(!Array.isArray(entry.revisions)||!entry.revisions.length||entry.revisions.length>100 || !Array.isArray(entry.reviews)||entry.reviews.length>100)throw new Error("Invalid journal history.");
        const revisions=entry.revisions.map((r,i)=>{
          if(r.version!==i+1 || !Number.isFinite(Date.parse(r.saved_at)))throw new Error("Invalid revision order or date.");
          return {...fields(r),version:i+1,saved_at:r.saved_at};
        });
        const reviews=entry.reviews.map(r=>{
          if(!["unchanged","stronger","weaker","uncertain"].includes(r.outcome)||!Number.isFinite(Date.parse(r.saved_at)))throw new Error("Invalid review.");
          if(!Number.isInteger(r.revision_version)||r.revision_version<1||r.revision_version>revisions.length)throw new Error("Invalid review revision.");
          return {saved_at:r.saved_at,revision_version:r.revision_version,outcome:r.outcome,note:requireText(r.note,"Review note"),next_review_on:validDate(r.next_review_on)};
        });
        return {id,archived:entry.archived===true,revisions,reviews};
      });
    }
    commit(next) {
      if(this.blocked)throw new Error(this.problem);
      const valid=this.validate(next);
      try {this.storage.setItem(JOURNAL_KEY,JSON.stringify(valid));}
      catch(_) {throw new Error("Browser storage could not save the journal. Nothing was changed; export a backup and free storage.");}
      this.entries=valid;return this.list();
    }
    list(){return copy(this.entries);}
    create(input) {
      const revision={...fields(input),version:1,saved_at:this.clock()};
      const entry={id:this.id(),archived:false,revisions:[revision],reviews:[]};
      this.commit([entry,...this.entries]);return copy(entry);
    }
    update(id,input) {
      const next=this.list(),entry=next.find(e=>e.id===id);if(!entry)throw new Error("Journal entry not found.");
      entry.revisions.push({...fields(input),version:entry.revisions.length+1,saved_at:this.clock()});this.commit(next);
    }
    review(id,{outcome,note,next_review_on}) {
      const next=this.list(),entry=next.find(e=>e.id===id);if(!entry)throw new Error("Journal entry not found.");
      entry.reviews.push({saved_at:this.clock(),revision_version:entry.revisions.length,outcome,note,next_review_on});this.commit(next);
    }
    archive(id) {const next=this.list(),entry=next.find(e=>e.id===id);if(!entry)throw new Error("Journal entry not found.");entry.archived=!entry.archived;this.commit(next);}
    nextReviewOn(entry) {const latest=entry.revisions.at(-1),review=entry.reviews.at(-1);return review && review.revision_version===latest.version ? review.next_review_on : latest.review_on;}
    due(entry,today=todayInIndia()) {return !entry.archived && this.nextReviewOn(entry)<=today;}
    export(){return {format:"sarthi-journal-v1",exported_at:this.clock(),entries:this.list()};}
    import(value) {if(!value||value.format!=="sarthi-journal-v1")throw new Error("Unsupported journal backup.");return this.commit(value.entries);}
    restore(value) {
      if(!value||value.format!=="sarthi-journal-v1")throw new Error("Unsupported journal backup.");
      const valid=this.validate(value.entries);
      try {this.storage.setItem(JOURNAL_KEY,JSON.stringify(valid));}
      catch(_) {throw new Error("Browser storage could not restore the journal. Nothing was changed.");}
      this.entries=valid;this.blocked=false;this.problem="";return this.list();
    }
    rawBackup(){return this.storage.getItem(JOURNAL_KEY)||"[]";}
  }
  function reviewReport(holdings, entries, events, scenario, sectorLimit=35, instant=new Date().toISOString(), compareAll=false) {
    return {format:"sarthi-review-v1",generated_at:instant,scope:"Local reflection report, not a recommendation or prediction.",
      portfolio:portfolioSummary(holdings,sectorLimit),holdings:validateHoldings(holdings),
      scenario:scenarioWorksheet(holdings,scenario),
      scenario_comparison:(compareAll?["easing","steady","tightening"]:[scenario]).map(key=>scenarioWorksheet(holdings,key)),journal:copy(entries),
      evidence:events.filter(e=>!e.is_sample).map(sourceSnapshot)};
  }
  root.SarthiReview={validateHoldings,parseCSV,portfolioSummary,scenarioWorksheet,sourceSnapshot,todayInIndia,JournalStore,reviewReport,JOURNAL_KEY};
})(typeof window!=="undefined"?window:globalThis);
