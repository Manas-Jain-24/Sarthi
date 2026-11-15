const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const context=vm.createContext({window:{},console,URL});
vm.runInContext(fs.readFileSync('frontend/js/review_core.js','utf8'),context);
const core=context.window.SarthiReview;
const plain=value=>JSON.parse(JSON.stringify(value));
let passed=0;
function test(name,fn){fn();passed++;console.log('PASS:',name);}
function storage(initial){const data=new Map(initial||[]);return {getItem:key=>data.get(key)||null,setItem:(key,value)=>data.set(key,value),data};}
const holding=[{ticker:'HDFCBANK',sector:'Banking',allocation_pct:25},{ticker:'INFY',sector:'IT Services',allocation_pct:20}];
const input={ticker:'HDFCBANK',thesis:'My initial investment thesis.',disconfirming:'Evidence that would contradict it.',review_on:'2026-11-15',decision:'research',source:null};
const snapshot={id:'RBI_TEST',canonical_title:'A policy event',published_at:'2025-12-05',source_url:'https://www.rbi.org.in/',source_text_sha256:'a'.repeat(64),is_sample:false,evidence_excerpt:'An exact saved source excerpt.'};
let id=0;
function journal(s=storage()){return new core.JournalStore(s,{clock:()=> '2026-11-15T00:00:00Z',id:()=>`test-${++id}`});}
test('CSV BOM, CRLF, quoted comma and percentage parsing',()=>{
 const result=core.parseCSV('\uFEFFticker,sector,allocation_pct\r\nHDFCBANK,"Banking, private",25%\r\nINFY,IT Services,20\r\n');
 assert.equal(result[0].sector,'Banking, private');assert.equal(result[1].allocation_pct,20);
});
test('Duplicate tickers and excessive totals are rejected',()=>{
 assert.throws(()=>core.parseCSV('ticker,sector,allocation_pct\nITC,FMCG,20\nitc,FMCG,30'));
 assert.throws(()=>core.parseCSV('ticker,sector,allocation_pct\nITC,FMCG,60\nINFY,IT,60'));
});
test('Malformed, formula, empty, and nonfinite CSV input is rejected',()=>{
 for(const raw of ['ticker,sector,allocation_pct\n"ITC,FMCG,20','ticker,sector,allocation_pct\nITC,FMCG,Infinity','ticker,sector,allocation_pct\n=CMD,FMCG,20','ticker,sector,allocation_pct\nITC,FMCG,20,extra','ticker,sector,allocation_pct','wrong,headers\nITC,FMCG'])assert.throws(()=>core.parseCSV(raw));
});
test('Invalid weights and repeated holdings fail validation',()=>{
 for(const n of [NaN,Infinity,-1,0,101,'25'])assert.throws(()=>core.validateHoldings([{ticker:'ITC',sector:'FMCG',allocation_pct:n}]));
});
test('Sector concentration merges casing, leaves allocation unassigned',()=>{
 const result=core.portfolioSummary([...holding,{ticker:'SBIN',sector:'banking',allocation_pct:15}],35);
 assert.equal(result.allocated,60);assert.equal(result.unassigned,40);assert.equal(result.sectors[0].allocation,40);assert.equal(result.aboveThreshold.length,1);
});
test('Empty portfolio is not treated as cash or invested exposure',()=>{
 const s=core.portfolioSummary([]);assert.equal(s.unassigned,100);assert.equal(s.largestHolding,null);assert.equal(s.aboveThreshold.length,0);
});
test('Scenario mapping distinguishes unmapped holdings without returns',()=>{
 const s=core.scenarioWorksheet(holding,'tightening');assert.equal(s.mapped.length,1);assert.equal(s.unmapped.length,1);assert.match(s.notice,/No return/);assert.throws(()=>core.scenarioWorksheet(holding,'made-up'));
});
test('Review dates use India day boundary',()=>{
 assert.equal(core.todayInIndia('2026-11-14T18:29:59Z'),'2026-11-14');assert.equal(core.todayInIndia('2026-11-14T18:30:00Z'),'2026-11-15');
});
test('Journal persists and reloads without server calls',()=>{
 const s=storage(),j=journal(s);j.create(input);assert.equal(journal(s).list()[0].revisions[0].thesis,input.thesis);
});
test('Edits append revisions and do not rewrite earlier reasoning',()=>{
 const j=journal(),entry=j.create(input);j.update(entry.id,{...input,thesis:'An updated investment thesis.'});assert.equal(j.list()[0].revisions.length,2);assert.equal(j.list()[0].revisions[0].thesis,input.thesis);
 const leaked=j.list();leaked[0].revisions[0].thesis='mutated';assert.equal(j.list()[0].revisions[0].thesis,input.thesis);
});
test('Evidence snapshots survive changes to loaded events',()=>{
 const card={...snapshot},source=core.sourceSnapshot(card),j=journal();j.create({...input,source});card.evidence_excerpt='changed';assert.equal(j.list()[0].revisions[0].source.excerpt,snapshot.evidence_excerpt);
});
test('Review log changes next due date and preserves thesis',()=>{
 const j=journal(),entry=j.create(input);assert.equal(j.due(entry,'2026-11-15'),true);
 j.review(entry.id,{outcome:'uncertain',note:'I need more evidence before changing my view.',next_review_on:'2026-12-01'});
 assert.equal(j.due(j.list()[0],'2026-11-15'),false);assert.equal(j.list()[0].revisions.length,1);
 j.update(entry.id,{...input,review_on:'2026-11-16'});assert.equal(j.nextReviewOn(j.list()[0]),'2026-11-16');
});
test('Archive is reversible and suppresses review prompts',()=>{
 const j=journal(),entry=j.create(input);j.archive(entry.id);assert.equal(j.due(j.list()[0]),false);j.archive(entry.id);assert.equal(j.due(j.list()[0],'2026-11-15'),true);
});
test('Invalid dates and incomplete notes are not persisted',()=>{
 const s=storage(),j=journal(s);assert.throws(()=>j.create({...input,review_on:'2026-02-31'}));assert.throws(()=>j.create({...input,thesis:''}));assert.equal(s.data.size,0);
});
test('Quota failure is atomic and visible',()=>{
 const s=storage(),j=journal(s);j.create(input);s.setItem=()=>{throw new Error('quota');};assert.throws(()=>j.update(j.list()[0].id,{...input,thesis:'A replacement thesis.'}),/Nothing was changed/);assert.equal(j.list()[0].revisions.length,1);
});
test('Unreadable saved journal stays intact until explicit restore',()=>{
 const s=storage([[core.JOURNAL_KEY,'not-json']]),j=journal(s);assert.equal(j.blocked,true);assert.throws(()=>j.create(input));assert.equal(j.rawBackup(),'not-json');j.restore({format:'sarthi-journal-v1',entries:[]});j.create(input);assert.equal(j.list().length,1);
});
test('Malformed and duplicate backup entries cannot overwrite good data',()=>{
 const j=journal(),entry=j.create(input);assert.throws(()=>j.import({format:'wrong',entries:[]}));assert.throws(()=>j.restore({format:'sarthi-journal-v1',entries:[entry,entry]}));assert.equal(j.list().length,1);
});
test('Backup round trip preserves all revisions and reviews',()=>{
 const j=journal(),entry=j.create(input);j.update(entry.id,{...input,thesis:'A second version of my thesis.'});j.review(entry.id,{outcome:'stronger',note:'Supporting evidence was published.',next_review_on:'2026-12-01'});
 const other=journal();other.import(j.export());assert.deepEqual(plain(other.list()),plain(j.list()));
});
test('Review report contains local notes and public evidence without model credentials',()=>{
 const j=journal();j.create(input);const report=core.reviewReport(holding,j.list(),[snapshot],'steady',35,'2026-11-15T00:00:00Z');assert.equal(report.journal.length,1);assert.equal(report.holdings.length,2);assert.equal(report.evidence.length,1);assert.equal(JSON.stringify(report).includes('API_KEY'),false);
});
test('Comparison exports preserve all three explicitly selected scenarios',()=>{
 const report=core.reviewReport(holding,[],[snapshot],'steady',35,'2026-11-15T00:00:00Z',true);
 assert.equal(report.scenario_comparison.length,3);assert.deepEqual(plain(report.scenario_comparison.map(s=>s.scenario)),['easing','steady','tightening']);
});
test('Portfolio storage failure leaves previous in-memory holdings unchanged',()=>{
 const s=storage();context.localStorage=s;vm.runInContext(fs.readFileSync('frontend/js/edge_matcher.js','utf8'),context);const matcher=context.window.edgeMatcher;matcher.savePortfolio(holding);s.setItem=()=>{throw new Error('quota');};assert.throws(()=>matcher.addHolding('ITC','FMCG',10));assert.equal(matcher.holdings.length,2);assert.throws(()=>matcher.removeHolding('HDFCBANK'));assert.equal(matcher.holdings.length,2);
});
test('Printable review escapes note markup and strips unsafe links',()=>{
 const s=storage();context.localStorage=s;context.document={addEventListener(){}};context.escapeHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 vm.runInContext(fs.readFileSync('frontend/js/review_ui.js','utf8'),context);
 const j=journal();j.create({...input,thesis:'<script>steal()</script>'});const report=core.reviewReport(holding,j.list(),[{...snapshot,source_url:'javascript:alert(1)'}],'steady');const html=context.window.workspaceUI.reportHTML(report);assert.equal(html.includes('<script>'),false);assert.equal(html.includes('href="javascript:'),false);assert.match(html,/&lt;script&gt;/);
});
console.log(`${passed} review-workspace checks passed.`);
