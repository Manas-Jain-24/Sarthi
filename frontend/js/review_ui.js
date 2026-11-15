/* Local review workspace. Only the public timeline is fetched. */
(function () {
  "use strict";
  const core=window.SarthiReview, e=value=>escapeHTML(value), $=id=>document.getElementById(id);
  const store=new core.JournalStore(localStorage);
  let events=[], timeline=null, editingSource=null, importBefore=null, importAfter=null;
  const status=message=>{$("workspace-status").textContent=message;};
  const run=fn=>{try{return fn();}catch(error){status(error.message);return null;}};
  const currentScenario=()=>$("scenario-choice").value;
  function href(url){try{const parsed=new URL(url);return parsed.protocol==="https:"?e(parsed.href):"";}catch(_){return "";}}
  function download(text,name,type="application/json") {
    const url=URL.createObjectURL(new Blob([text],{type}));
    const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function exportJSON(value,name){download(JSON.stringify(value,null,2),name);}
  function navigate(tab){$("tab-"+tab).click();}
  function showSnapshot(source) {
    if(!source)return "<p class='quiet'>No linked event.</p>";
    const current=events.find(c=>c.id===source.id);
    const changed=current && source.text_sha256 && current.source_text_sha256!==source.text_sha256;
    return `<p><span class="review-badge">${source.is_sample?"Synthetic sample":"Saved source snapshot"}</span>${e(source.published_on)}</p>
      <p>${e(source.title)}</p>${href(source.source_url)?`<a href="${href(source.source_url)}" target="_blank" rel="noopener noreferrer">Open saved source</a>`:""}
      ${changed?'<p class="review-flag">The loaded source revision differs from this saved snapshot. Recheck the evidence.</p>':""}
      <p class="quiet">Source hash: ${e(source.text_sha256||"Not supplied for this sample")}</p><blockquote>${e(source.excerpt)}</blockquote>`;
  }
  function fillEvents(selected="") {
    $("journal-event").innerHTML='<option value="">No linked event</option>'+events.map(c=>`<option value="${e(c.id)}">${c.is_sample?"Sample":"RBI"} · ${e(c.published_at.slice(0,10))} · ${e(c.canonical_title)}</option>`).join("");
    if(editingSource && !events.some(c=>c.id===editingSource.id)) {
      const option=document.createElement("option");option.value=editingSource.id;option.textContent="Saved snapshot · "+editingSource.title;$("journal-event").appendChild(option);
    }
    $("journal-event").value=selected;
  }
  function resetForm(){ if($("journal-editor")) $("journal-editor").open=false; $("journal-form").reset();$("journal-id").value="";editingSource=null;$("journal-date").value=core.todayInIndia();$("journal-form-title").textContent="New entry";fillEvents(); }
  function renderSummary() {
    const summary=core.portfolioSummary(window.edgeMatcher.holdings,Number($("sector-threshold").value));
    const entries=store.list(),due=entries.filter(entry=>store.due(entry)).sort((a,b)=>store.nextReviewOn(a).localeCompare(store.nextReviewOn(b)));
    $("review-metrics").innerHTML=[
      [summary.holdingCount,"Holdings"],[summary.allocated.toFixed(1)+"%","Allocated"],
      [summary.unassigned.toFixed(1)+"%","Unassigned"],[due.length,"Reviews due"]
    ].map(([value,label])=>`<article class="glass-panel review-metric"><strong>${e(value)}</strong><span>${e(label)}</span></article>`).join("");
    $("sector-breakdown").innerHTML=summary.sectors.length?summary.sectors.map(s=>`<div class="allocation-row"><div class="allocation-label"><span>${e(s.name)}</span><span>${e(s.allocation.toFixed(1))}%${s.allocation>summary.sectorLimit?" · above your threshold":""}</span></div><div class="allocation-track"><span class="allocation-fill" style="width:${s.allocation}%"></span></div></div>`).join(""):
      '<p>Add your holdings to see the allocation breakdown.</p>';
    $("review-queue").innerHTML=due.length?due.slice(0,5).map(entry=>`<p><button class="btn-secondary" data-edit-note="${e(entry.id)}">${e(entry.revisions.at(-1).ticker)} · review ${e(store.nextReviewOn(entry))}</button></p>`).join(""):
      `<p>${entries.length?"No reviews due.":"Your journal is empty."}</p>`;
    $("review-queue").querySelectorAll("[data-edit-note]").forEach(b=>b.addEventListener("click",()=>editNote(b.dataset.editNote)));
    const scenarios=$("compare-scenarios").checked?["easing","steady","tightening"]:[currentScenario()];
    $("scenario-worksheet").className=scenarios.length===3?"scenario-grid":"";
    $("scenario-worksheet").innerHTML=scenarios.map(key=>{
      const worksheet=core.scenarioWorksheet(window.edgeMatcher.holdings,key),exposure=worksheet.mapped.reduce((sum,h)=>sum+h.allocation_pct,0);
      return `<section class="scenario-card"><h3>${e(worksheet.name)}</h3><p>${e(worksheet.assumption)}</p>
        <p><strong>${exposure.toFixed(1)}%</strong> entered allocation overlaps the four mapped sectors. ${worksheet.unmapped.length} holding(s) are outside this mapping.</p>
        <ul>${worksheet.questions.map(q=>`<li>${e(q)}</li>`).join("")}</ul><p class="quiet">${e(worksheet.notice)}</p></section>`;
    }).join("");
    $("undo-portfolio-import").disabled=!importBefore || JSON.stringify(window.edgeMatcher.holdings)!==importAfter;
  }
  function editNote(id) {
    const entry=store.list().find(entry=>entry.id===id);if(!entry)return;
    navigate("journal");$("journal-editor").open=true;const latest=entry.revisions.at(-1);editingSource=latest.source;
    $("journal-id").value=id;$("journal-ticker").value=latest.ticker;$("journal-thesis").value=latest.thesis;
    $("journal-disconfirming").value=latest.disconfirming;$("journal-decision").value=latest.decision;$("journal-date").value=store.nextReviewOn(entry);
    $("journal-form-title").textContent=`Edit ${latest.ticker}`;fillEvents(latest.source?.id||"");$("journal-ticker").focus();
  }
  function renderJournal() {
    const filter=$("journal-filter").value;
    const entries=store.list().filter(entry=>filter==="all"||(filter==="archived"?entry.archived:filter==="due"?store.due(entry):!entry.archived));
    $("journal-entries").innerHTML=entries.length?entries.map(entry=>{
      const latest=entry.revisions.at(-1);
      return `<article class="glass-panel review-panel journal-card"><div class="section-heading"><h2>${e(latest.ticker)}</h2><span class="review-badge ${store.due(entry)?"due-badge":""}">${entry.archived?"Archived":store.due(entry)?"Review due":"Review scheduled"}</span></div>
        <p>${e(({research:"Research",continue:"Maintain thesis",revisit:"Revisit thesis"})[latest.decision])} · Review ${e(displayDate(store.nextReviewOn(entry)))} · v${latest.version}</p>
        <h3>Thesis</h3><blockquote>${e(latest.thesis)}</blockquote><h3>Review triggers</h3><blockquote>${e(latest.disconfirming)}</blockquote>
        <details><summary>Linked evidence snapshot</summary>${showSnapshot(latest.source)}</details>
        <div class="review-actions"><button class="btn-secondary" data-edit="${e(entry.id)}">Edit thesis</button><button class="btn-secondary" data-archive="${e(entry.id)}">${entry.archived?"Reopen":"Archive"}</button></div>
        <details><summary>Revision and review history (${entry.revisions.length+entry.reviews.length})</summary>
          ${entry.revisions.map(r=>`<section class="journal-revision"><strong>Version ${r.version} · ${e(r.saved_at)}</strong><p>Decision: ${e(r.decision)} · review ${e(r.review_on)}</p><blockquote>${e(r.thesis)}</blockquote><p>Disconfirming evidence:</p><blockquote>${e(r.disconfirming)}</blockquote>${showSnapshot(r.source)}</section>`).join("")}
          ${entry.reviews.map(r=>`<section class="journal-revision"><strong>Version ${r.revision_version} review · ${e(r.outcome)}</strong><p>${e(r.saved_at)} · next review ${e(r.next_review_on)}</p><blockquote>${e(r.note)}</blockquote></section>`).join("")}</details>
        ${entry.archived?"":`<details class="review-record"><summary>Record a review</summary><form data-review-id="${e(entry.id)}">
          <label>Thesis status<select name="outcome" class="chat-input"><option value="uncertain">Still uncertain</option><option value="unchanged">Unchanged</option><option value="stronger">Stronger</option><option value="weaker">Weaker</option></select></label>
          <label>Review note<textarea name="note" rows="3" maxlength="2000" class="chat-input" required></textarea></label>
          <label>Next review date<input name="next_review_on" type="date" class="chat-input" required></label><button class="btn-primary" type="submit">Save review</button></form></details>`}</article>`;
    }).join(""):'<p class="glass-panel review-panel">No entries yet.</p>';
    $("journal-entries").querySelectorAll("[data-edit]").forEach(b=>b.addEventListener("click",()=>editNote(b.dataset.edit)));
    $("journal-entries").querySelectorAll("[data-archive]").forEach(b=>b.addEventListener("click",()=>run(()=>{store.archive(b.dataset.archive);render();status("Entry updated.");})));
    $("journal-entries").querySelectorAll("[data-review-id]").forEach(form=>form.addEventListener("submit",event=>{
      event.preventDefault();run(()=>{store.review(form.dataset.reviewId,{outcome:form.elements.outcome.value,note:form.elements.note.value,next_review_on:form.elements.next_review_on.value});render();status("Review saved.");});
    }));
  }
  function renderTimeline() {
    if(!timeline)return;
    const {coverage}=timeline;
    $("timeline-coverage").textContent=`${coverage.count} archived observations, ${coverage.from||"—"} through ${coverage.through||"—"}. This is not a complete record of policy meetings.`;
    const observations=timeline.observations.filter(o=>o.repo_rate_pct!==null);
    if(observations.length) {
      const first=Date.parse(observations[0].published_on),last=Date.parse(observations.at(-1).published_on),min=Math.min(...observations.map(o=>o.repo_rate_pct))-.25,max=Math.max(...observations.map(o=>o.repo_rate_pct))+.25;
      const x=o=>55+(Date.parse(o.published_on)-first)/Math.max(1,last-first)*665,y=o=>175-(o.repo_rate_pct-min)/Math.max(.1,max-min)*140;
      $("policy-chart").innerHTML=`<svg viewBox="0 0 780 225" role="img" aria-label="Repo rate observations from ${e(coverage.from)} through ${e(coverage.through)}. A dated text list follows.">
        <line x1="55" y1="175" x2="735" y2="175" stroke="#dce4dc"/><text x="10" y="35" fill="#7d8b80" font-size="12">${max.toFixed(2)}%</text><text x="10" y="175" fill="#7d8b80" font-size="12">${min.toFixed(2)}%</text>
        ${observations.map(o=>`<circle cx="${x(o)}" cy="${y(o)}" r="5" fill="#557c61"><title>${e(o.published_on)}: ${o.repo_rate_pct}%</title></circle>`).join("")}
        <text x="55" y="210" fill="#7d8b80" font-size="12">${e(coverage.from)}</text><text x="640" y="210" fill="#7d8b80" font-size="12">${e(coverage.through)}</text></svg>`;
    }
    const query=$("timeline-search").value.toLowerCase(),filter=$("timeline-filter").value;
    const filtered=[...timeline.observations].reverse().filter(o=>(filter==="all"||o.decision_wording===filter)&&`${o.title} ${o.published_on}`.toLowerCase().includes(query));
    $("timeline-events").innerHTML=filtered.length?filtered.map(o=>`<article class="glass-panel review-panel timeline-item"><p class="date-label">${e(o.published_on)} · ${e(o.decision_wording)}</p><h2>${o.repo_rate_pct===null?"Rate not extracted":e(o.repo_rate_pct)+"% policy repo rate"}</h2>
      <p>${o.change_since_previous_archived_bps===null?"First observation in this archive.":`${o.change_since_previous_archived_bps>0?"+":""}${o.change_since_previous_archived_bps} basis points versus the previous archived observation, ${o.days_since_previous_archived} days earlier. This may span missing meetings.`}</p>
      <details><summary>Source passage [${e(o.paragraph_id)}]</summary><blockquote>${e(o.evidence_excerpt)}</blockquote></details>
      <div class="review-actions"><a class="btn-secondary" href="${href(o.source_url)}" target="_blank" rel="noopener noreferrer">RBI source</a><button class="btn-secondary" data-timeline-note="${e(o.id)}">Add to journal</button></div></article>`).join(""):'<p>No archived observations match these filters.</p>';
    $("timeline-events").querySelectorAll("[data-timeline-note]").forEach(b=>b.addEventListener("click",()=>{
      const o=timeline.observations.find(o=>o.id===b.dataset.timelineNote);
      noteFromEvent({id:o.id,canonical_title:o.title,published_at:o.published_on,source_url:o.source_url,source_text_sha256:o.source_text_sha256,is_sample:false,evidence_excerpt:o.evidence_excerpt});
    }));
  }
  function render(){run(()=>{renderSummary();renderJournal();});}
  function noteFromEvent(card){closeReasoningDrawer();navigate("journal");resetForm();$("journal-editor").open=true;editingSource=core.sourceSnapshot(card);fillEvents(card.id);$("journal-ticker").focus();status("Event linked to the new entry.");}
  function reportHTML(report) {
    const source=report.evidence;
    return `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Sarthi portfolio review</title><style>body{font:16px/1.6 system-ui;max-width:900px;margin:3rem auto;padding:0 1rem;color:#172033}table{border-collapse:collapse;width:100%}td,th{border:1px solid #cbd5e1;padding:.5rem;text-align:left}article{margin:2rem 0;break-inside:avoid}blockquote{white-space:pre-wrap;border-left:3px solid #0e7490;padding-left:1rem}small{color:#475569}@media print{body{margin:0}a{color:inherit}}</style>
      <h1>Sarthi · Portfolio review</h1><p>${e(report.generated_at)}</p><p>${e(report.scope)}</p><p>Private export. Keep this file wherever you keep personal financial notes. It contains no API key.</p>
      <h2>Entered holdings</h2><table><tr><th>Ticker</th><th>Sector</th><th>Allocation</th></tr>${report.holdings.map(h=>`<tr><td>${e(h.ticker)}</td><td>${e(h.sector)}</td><td>${h.allocation_pct}%</td></tr>`).join("")}</table><p>Unassigned: ${report.portfolio.unassigned.toFixed(1)}%. Sector review threshold: ${report.portfolio.sectorLimit}% (user preference).</p>
      <h2>Scenario worksheet</h2>${(report.scenario_comparison||[report.scenario]).map(s=>`<h3>${e(s.name)}</h3><p>${e(s.assumption)}</p><ul>${s.questions.map(q=>`<li>${e(q)}</li>`).join("")}</ul><p>${e(s.notice)}</p>`).join("")}
      <h2>Decision journal</h2>${report.journal.length?report.journal.map(entry=>`<article><h3>${e(entry.revisions.at(-1).ticker)}${entry.archived?" · archived":""}</h3>${entry.revisions.map(r=>`<h4>Version ${r.version} · ${e(r.saved_at)}</h4><p>Review: ${e(r.review_on)} · Decision: ${e(r.decision)}</p><blockquote>${e(r.thesis)}</blockquote><p>What would change my mind:</p><blockquote>${e(r.disconfirming)}</blockquote>${r.source?`<p>Linked source: ${e(r.source.title)} · ${e(r.source.published_on)}${r.source.is_sample?" · SYNTHETIC SAMPLE":""}</p><small>Hash: ${e(r.source.text_sha256)}</small><blockquote>${e(r.source.excerpt)}</blockquote>`:""}`).join("")}${entry.reviews.map(r=>`<h4>Review: ${e(r.outcome)}</h4><p>${e(r.saved_at)} · next ${e(r.next_review_on)}</p><blockquote>${e(r.note)}</blockquote>`).join("")}</article>`).join(""):"<p>No notes entered.</p>"}
      <h2>Loaded real-source evidence</h2><p>Publication dates are historical. Missing meetings are not filled.</p>${source.map(s=>`<article><h3>${e(s.published_on)} · ${e(s.title)}</h3><a href="${href(s.source_url)}">Original source</a><blockquote>${e(s.excerpt)}</blockquote><small>Source hash: ${e(s.text_sha256)}</small></article>`).join("")}</html>`;
  }
  function setupImports() {
    $("csv-template").addEventListener("click",()=>download('ticker,sector,allocation_pct\nHDFCBANK,Banking,25\nINFY,IT Services,20\n',"sarthi-holdings-template.csv","text/csv"));
    $("portfolio-csv").addEventListener("change",async event=>{
      const file=event.target.files[0];if(!file)return;
      try {
        if(file.size>1_000_000)throw new Error("CSV must be smaller than one megabyte.");
        const candidate=core.parseCSV(await file.text()),summary=core.portfolioSummary(candidate);
        $("csv-preview").hidden=false;$("csv-preview").innerHTML=`<p>Preview: ${candidate.length} holdings, ${summary.allocated.toFixed(1)}% entered allocation. Applying replaces the current holdings.</p><table class="portfolio-table"><tr><th>Ticker</th><th>Sector</th><th>Allocation</th></tr>${candidate.map(h=>`<tr><td>${e(h.ticker)}</td><td>${e(h.sector)}</td><td>${h.allocation_pct}%</td></tr>`).join("")}</table><button class="btn-primary" id="apply-csv">Replace holdings with this preview</button>`;
        $("apply-csv").addEventListener("click",()=>run(()=>{
          const before=window.edgeMatcher.holdings.map(h=>({...h}));window.edgeMatcher.savePortfolio(candidate);importBefore=before;importAfter=JSON.stringify(window.edgeMatcher.holdings);
          $("csv-preview").hidden=true;renderPortfolioTable();renderCards();render();status("CSV imported locally. Undo is available on this page until you edit holdings or reload.");
        }));
      }catch(error){$("csv-preview").hidden=true;status(error.message);}finally{event.target.value="";}
    });
    $("undo-portfolio-import").addEventListener("click",()=>run(()=>{
      if(!importBefore || JSON.stringify(window.edgeMatcher.holdings)!==importAfter)throw new Error("Holdings changed after import; automatic undo is unavailable.");
      window.edgeMatcher.savePortfolio(importBefore);importBefore=null;importAfter=null;renderPortfolioTable();renderCards();render();status("Previous holdings restored.");
    }));
    $("export-journal").addEventListener("click",()=>run(()=>{
      if(store.blocked)download(store.rawBackup(),"sarthi-journal-unreadable-backup.json");
      else exportJSON(store.export(),"sarthi-journal-backup.json");
      status("Journal backup downloaded locally. It contains your private notes.");
    }));
    $("import-journal").addEventListener("change",async event=>{
      const file=event.target.files[0];if(!file)return;
      try {
        if(file.size>5_000_000)throw new Error("Journal backup must be smaller than five megabytes.");
        const candidate=JSON.parse(await file.text());if(candidate.format!=="sarthi-journal-v1")throw new Error("Unsupported journal backup.");
        const valid=store.validate(candidate.entries);
        $("journal-restore-preview").hidden=false;$("journal-restore-preview").innerHTML=`<p>This backup contains ${valid.length} entries and will replace ${store.list().length} current entries. Download a current backup first.</p><button id="apply-journal-restore" class="btn-primary">Download current backup and restore this journal</button>`;
        $("apply-journal-restore").addEventListener("click",()=>run(()=>{
          if(store.blocked)download(store.rawBackup(),"sarthi-journal-unreadable-before-restore.json");
          else exportJSON(store.export(),"sarthi-journal-before-restore.json");
          store.restore(candidate);$("journal-restore-preview").hidden=true;resetForm();render();status("Journal restored locally. A copy of the previous data was downloaded.");
        }));
      }catch(error){$("journal-restore-preview").hidden=true;status(error.message);}finally{event.target.value="";}
    });
  }
  document.addEventListener("DOMContentLoaded",()=>{
    resetForm();setupImports();
    if(store.problem || window.edgeMatcher.portfolioWarning)status(store.problem || window.edgeMatcher.portfolioWarning);
    $("start-journal").addEventListener("click",()=>{navigate("journal");resetForm();$("journal-editor").open=true;$("journal-ticker").focus();});
    $("new-journal-entry").addEventListener("click",()=>$("start-journal").click());
    $("cancel-journal-edit").addEventListener("click",resetForm);
    $("journal-form").addEventListener("submit",event=>{event.preventDefault();run(()=>{
      const selected=$("journal-event").value,card=events.find(card=>card.id===selected);
      const input={ticker:$("journal-ticker").value,thesis:$("journal-thesis").value,disconfirming:$("journal-disconfirming").value,review_on:$("journal-date").value,decision:$("journal-decision").value,
        source:card?core.sourceSnapshot(card):(editingSource?.id===selected?editingSource:null)};
      if($("journal-id").value)store.update($("journal-id").value,input);else store.create(input);
      resetForm();render();status("Entry saved on this device.");
    });});
    ["sector-threshold","scenario-choice","compare-scenarios"].forEach(id=>$(id).addEventListener("change",()=>run(renderSummary)));
    $("journal-filter").addEventListener("change",renderJournal);
    $("timeline-search").addEventListener("input",renderTimeline);$("timeline-filter").addEventListener("change",renderTimeline);
    const currentReport=()=>core.reviewReport(window.edgeMatcher.holdings,store.list(),events,currentScenario(),Number($("sector-threshold").value),new Date().toISOString(),$("compare-scenarios").checked);
    $("export-review-json").addEventListener("click",()=>run(()=>exportJSON(currentReport(),"sarthi-review.json")));
    $("export-review-html").addEventListener("click",()=>run(()=>download(reportHTML(currentReport()),"sarthi-review.html","text/html")));
    render();
    fetch("/api/v1/rbi/timeline").then(response=>{if(!response.ok)throw new Error();return response.json();}).then(data=>{timeline=data;renderTimeline();}).catch(()=>{$("timeline-coverage").textContent="Timeline unavailable. Your local notes and holdings remain accessible.";});
  });
  window.workspaceUI={render,noteFromEvent,reportHTML,setEvents(cards){events=cards;const selected=$("journal-event").value;fillEvents(selected);render();}};
})();
