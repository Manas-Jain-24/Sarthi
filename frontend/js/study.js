let materials = [];
let trials = [];
let current = 0;
let trialStarted;
const responses = [];
const participant = crypto.randomUUID();
const random = () => crypto.getRandomValues(new Uint32Array(1))[0] / 4294967296;

function showTrial() {
  const item = trials[current];
  document.getElementById("trial-progress").textContent = `Announcement ${current + 1} of ${trials.length}`;
  document.getElementById("trial-title").textContent = item.title;
  document.getElementById("trial-text").textContent = item.condition === "source" ? item.baseline : item.briefing;
  document.getElementById("study-form").reset();
  trialStarted = performance.now();
}

document.addEventListener("DOMContentLoaded", async () => {
  const start = document.getElementById("study-start");
  const consent = document.getElementById("consent");
  try {
    const response = await fetch("/api/v1/rbi/study-material");
    if (!response.ok) throw new Error();
    const data = await response.json();
    materials = data.cases;
    document.getElementById("study-status").textContent = materials.length >= 2 ?
      `${materials.length} announcements are ready. Participation requires consent.` :
      "The researcher must generate accepted Gemini analyses for at least two RBI documents before the study can start.";
  } catch (_) { document.getElementById("study-status").textContent = "Study materials unavailable. Please return later."; }
  consent.addEventListener("change", () => { start.disabled = !consent.checked || materials.length < 2; });
  start.addEventListener("click", () => {
    if (!consent.checked || materials.length < 2) return;
    const shuffled = [...materials];
    for (let i = shuffled.length-1; i>0; i--) { const j=Math.floor(random()*(i+1)); [shuffled[i],shuffled[j]]=[shuffled[j],shuffled[i]]; }
    const offset = random() < 0.5 ? 0 : 1;
    trials = shuffled.map((m, i) => ({...m, condition: (i+offset)%2 ? "briefing" : "source"}));
    document.getElementById("consent-panel").hidden = true;
    document.getElementById("trial").hidden = false;
    showTrial();
  });
  document.getElementById("study-form").addEventListener("submit", event => {
    event.preventDefault();
    const item = trials[current];
    responses.push({document_id:item.document_id, source_text_sha256:item.source_text_sha256,
      condition:item.condition, order:current+1, model:item.model, prompt_version:item.prompt_version,
      repo_rate_pct:Number(document.getElementById("answer-rate").value),
      certainty:document.getElementById("answer-certainty").value,
      confidence:Number(document.getElementById("answer-confidence").value),
      elapsed_ms:Math.round(performance.now()-trialStarted)});
    current++;
    if (current < trials.length) showTrial();
    else { document.getElementById("trial").hidden=true; document.getElementById("study-end").hidden=false; }
  });
  document.getElementById("study-download").addEventListener("click", () => {
    const result = {protocol:"rbi-comprehension-v1", participant_id:participant, consent:true,
      completed_at:new Date().toISOString(), responses};
    const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:"application/json"}));
    const link=document.createElement("a"); link.href=url; link.download=`sarthi-study-${participant}.json`; link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
});
