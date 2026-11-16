function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[c]));
}
function appendChatBubble(text, role) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble bubble-${role}`;
  bubble.style.whiteSpace = "pre-wrap";
  bubble.textContent = text;
  document.getElementById("chat-messages").appendChild(bubble);
}
/**
 * Sarthi Application Controller
 */

let currentEventCard = null;
let rawDailyCards = [];
let allPrecedents = [];
let auditTelemetry = null;
let dataMode = "rbi";
let loadSequence = 0;
let drawerReturnFocus = null;

document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("source-mode").addEventListener("change", loadPipelineData);
  document.getElementById("source-only").addEventListener("change", () => { renderCards(); if (currentEventCard && document.getElementById("reasoning-drawer").classList.contains("active")) openReasoningDrawer(currentEventCard.id); });
  document.getElementById("btn-refresh-rbi").addEventListener("click", refreshRBI);
  setupShell();
  setupTabs();
  setupPortfolioModal();
  setupAssistantChat();
  await loadPipelineData();
});

async function loadPipelineData() {
  const sequence = ++loadSequence;
  dataMode = document.getElementById("source-mode").value;
  try {
    const res = await fetch(dataMode === "rbi" ? "/api/v1/rbi/brief" : "/api/v1/pipeline/run");
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    const data = await res.json();
    if (sequence !== loadSequence) return;
    currentEventCard = null;
    closeReasoningDrawer();
    auditTelemetry = data.stats;
    rawDailyCards = [...data.morning_brief, ...data.explore_feed];

    document.getElementById("demo-notice").textContent = data.data_notice;
    document.getElementById("data-label").textContent = dataMode === "rbi" ? "RBI archive" : "Synthetic examples";
    const latest = rawDailyCards.map(c => c.published_at.slice(0,10)).sort().at(-1);
    document.getElementById("research-context").textContent = dataMode === "rbi" ? `Archived RBI announcements${latest ? ". Through " + displayDate(latest) : ""}.` : "Synthetic examples for demonstration.";
    document.getElementById("btn-refresh-rbi").disabled = dataMode !== "rbi";
    document.getElementById("source-only").disabled = dataMode !== "rbi";
    if (dataMode === "rbi") {
      const status = await fetch("/api/v1/rbi/status").then(r => r.json());
      if (sequence !== loadSequence) return;
      document.getElementById("provider-status").textContent = status.configured ? `Gemini: ${status.model}. Analysis runs on request.` : "Gemini key is not configured. Source documents are available.";
      renderResearchStatus(status);
    } else {
      document.getElementById("provider-status").textContent = "Fixed synthetic scenarios; no model requests.";
      document.getElementById("source-freshness").textContent = "";
      document.getElementById("research-history").replaceChildren();
    }
    window.workspaceUI?.setEvents(rawDailyCards);
    updateTelemetryBanner(data.stats);
    renderCards();
    loadPrecedents();
    renderPortfolioTable();
    renderAuditTelemetry(data);
  } catch (err) {
    console.error("Failed to load pipeline data:", err);
    document.getElementById("provider-status").textContent = "Public event feed unavailable. Your local journal and portfolio are still accessible.";
    document.getElementById("cards-container").innerHTML = `
      <div class="glass-panel" style="padding: 2rem; text-align: center; grid-column: 1 / -1;">
        <h3>Unable to reach Sarthi API</h3>
        <p style="color: var(--text-muted); margin-top: 0.5rem;">Please reload the page or try again shortly.</p>
      </div>
    `;
  }
}

function renderResearchStatus(status) {
  const freshness = status.freshness;
  const labels = {checked:"Official listing checked",never_checked:"Live sources have not been checked",checking:"Checking live sources",
    interrupted:"Previous check was interrupted",check_failed:"Latest check failed",partial:"Latest check was incomplete",
    unverified:"No resolution links found; freshness unverified",outdated:"Source check is over a day old",archive_error:"Live archive needs attention"};
  const label = labels[freshness.state] || "Source status unavailable";
  document.getElementById("source-freshness").textContent = `${label}${freshness.checked_at ? " · " + new Date(freshness.checked_at).toLocaleString() : ""}. Latest publication: ${freshness.latest_publication ? displayDate(freshness.latest_publication) : "unavailable"}.`;
  document.getElementById("research-context").textContent = `RBI announcements through ${displayDate(freshness.latest_publication)} · ${label.toLowerCase()}.`;
  const history = document.getElementById("research-history");
  history.replaceChildren();
  for (const run of freshness.history.slice(0,5)) {
    const item = document.createElement("p");
    const details = run.details;
    item.textContent = `${new Date(run.started_at).toLocaleString()} · ${run.status}. ${details.retrieved?.length || 0} retrieved; ${details.failures?.length || 0} failed${details.pending ? "; " + details.pending + " pending" : ""}.`;
    history.appendChild(item);
  }
  for (const attempt of status.analysis_history.slice(0,5)) {
    const item = document.createElement("p");
    item.textContent = `${attempt.document_id.replace("RBI_","RBI ")} · Gemini ${attempt.status}${attempt.error_code ? " (" + attempt.error_code.replaceAll("_"," ") + ")" : ""} · ${new Date(attempt.started_at).toLocaleString()}`;
    history.appendChild(item);
  }
  if (!history.childElementCount) history.textContent = "No live checks recorded on this device.";
  const note = document.createElement("p"); note.textContent = freshness.archive_error || freshness.notice; history.appendChild(note);
}

function updateTelemetryBanner(stats) {
  document.getElementById("stat-scanned").textContent = stats.scanned || 0;
  document.getElementById("stat-confirmed").textContent = stats.confirmed || 0;
  document.getElementById("stat-dropped").textContent = stats.dropped_at_confirm || 0;
  document.getElementById("stat-passed").textContent = stats.passed_constraint || 0;
}

function displayDate(value) {
  const date = new Date(value.slice(0,10) + "T12:00:00Z");
  return Number.isNaN(date.getTime()) ? value.slice(0,10) : new Intl.DateTimeFormat("en-IN", {day:"2-digit",month:"short",year:"numeric"}).format(date);
}
function renderCards() {
  const container = document.getElementById("cards-container");
  const view = document.querySelector(".tab-btn.active").dataset.tab;
  if (view !== "brief" && view !== "explore") return;
  const personal = window.edgeMatcher.matchAndPersonalize(rawDailyCards);
  const cards = view === "brief" ? personal.morningBrief : rawDailyCards;
  document.getElementById("research-all").classList.toggle("selected", view === "explore");
  if (!cards.length) {
    container.innerHTML = `<div class="empty-state"><h2>${view === "brief" ? "No matching announcements" : "No announcements available"}</h2><p>${view === "brief" ? "Add your holdings to see relevant research here." : "Check your source settings or try again later."}</p></div>`;
    return;
  }
  const baseline = document.getElementById("source-only").checked;
  container.innerHTML = cards.map(card => {
    const match = (card.baseline_text || "").match(/policy repo rate[^.;]{0,150}?(?:at|to)\s+(\d+(?:\.\d+)?)\s+per cent/i);
    const title = card.is_sample ? card.canonical_title : match ? `Policy repo rate: ${match[1]}%` : "Monetary policy decision";
    const text = (baseline && !card.is_sample ? card.baseline_text : card.summary_insight).replace(/\s+/g," ").trim();
    const preview = text.length > 190 ? text.slice(0,187) + "…" : text;
    const label = card.is_sample ? "Synthetic example" : card.analysis_status === "generated" ? "Analysis available" : card.analysis_status === "rejected" ? "Source · AI output rejected" : card.analysis_status === "failed" ? "Source · AI unavailable" : "Source document";
    return `<article class="research-row"><time class="research-date">${escapeHTML(displayDate(card.published_at))}</time><div><h2>${escapeHTML(title)}</h2><p>${escapeHTML(preview)}</p><p class="research-meta">${escapeHTML(label)}${card.matched_ticker ? " · " + escapeHTML(card.matched_ticker) : ""}</p></div><button class="btn-open-chain" data-event-id="${escapeHTML(card.id)}">Read ${card.analysis_status === "generated" && !baseline ? "analysis" : "source"} →</button></article>`;
  }).join("");
  container.querySelectorAll("[data-event-id]").forEach(button => button.addEventListener("click", () => openReasoningDrawer(button.dataset.eventId)));
}
function setupShell() {
  const dialog = document.getElementById("source-settings");
  document.querySelectorAll("[data-settings-open]").forEach(button => button.addEventListener("click", () => {
    document.querySelectorAll(".more-menu[open], .more-actions[open], .export-menu[open]").forEach(menu => menu.open = false);
    dialog.showModal();
  }));
  document.getElementById("close-source-settings").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", event => {if (event.target === dialog) {const r=dialog.getBoundingClientRect();if(event.clientX<r.left || event.clientX>r.right || event.clientY<r.top || event.clientY>r.bottom)dialog.close();}});
  document.addEventListener("click", event => {
    const selected = event.target.closest(".more-menu, .more-actions, .export-menu");
    document.querySelectorAll(".more-menu[open], .more-actions[open], .export-menu[open]").forEach(menu => {
      if(menu !== selected || event.target.closest(".menu-panel button, .menu-panel a")) menu.open=false;
    });
  });
  document.getElementById("research-all").addEventListener("click", () => document.getElementById("tab-explore-feed").click());
  const drawer = document.getElementById("reasoning-drawer");
  drawer.addEventListener("click", event => {if(event.target === drawer)closeReasoningDrawer();});
  document.addEventListener("keydown", event => {
    if (!drawer.classList.contains("active")) return;
    if (event.key === "Escape") {event.preventDefault();closeReasoningDrawer();}
    if (event.key === "Tab") {
      const controls = [...drawer.querySelectorAll("button:not([disabled]), a[href], input:not([disabled]), summary")].filter(node => node.getClientRects().length);
      const first = controls[0], last = controls.at(-1);
      if (event.shiftKey && document.activeElement === first) {event.preventDefault();last?.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault();first?.focus();}
    }
  });
}

function openReasoningDrawer(eventId) {
  const card = rawDailyCards.find(c => c.id === eventId);
  if (!card) return;
  if (!document.getElementById("reasoning-drawer").classList.contains("active")) drawerReturnFocus = document.activeElement;
  currentEventCard = card;
  const generate = document.getElementById("drawer-generate");
  generate.hidden = card.is_sample || card.analysis_status === "generated";
  generate.onclick = () => generateAnalysis(card.id, generate);
  document.getElementById("event-assistant").hidden = !card.is_sample;
  document.getElementById("journal-from-event").onclick = () => window.workspaceUI?.noteFromEvent(card);

  document.getElementById("evidence-excerpt").textContent = card.evidence_excerpt;
  document.getElementById("evidence-status").textContent = `${card.evidence_status}. ${card.impact_status}. ${card.gate_reason}`;
  const reference = document.getElementById("evidence-reference");
  reference.hidden = true;
  try {
    const url = new URL(card.source_url || card.reference_url);
    if (url.protocol === "https:") {
      reference.href = url.href; reference.hidden = false;
      reference.textContent = card.is_sample ? "Institution homepage — background only" : "Open original RBI resolution";
    }
  } catch (_) { /* No background link supplied. */ }
  document.getElementById("sample-date").textContent = `${card.is_sample ? "Sample date" : "Published"}: ${card.published_at.slice(0, 10)}. Archived dates do not indicate current news.`;
  document.getElementById("evidence-heading").textContent = card.is_sample ? "Synthetic sample input" : "Evidence from the archived RBI resolution";
  document.getElementById("source-excerpt-details").open = card.analysis_status !== "generated";
  renderEvidence(card);
  const sourceOnly = document.getElementById("source-only").checked && !card.is_sample;
  const chain = card.reasoning_chain;
  document.getElementById("drawer-title").textContent = card.canonical_title;
  document.getElementById("drawer-source").textContent = card.source_attribution;
  document.getElementById("drawer-impact-vector").textContent = sourceOnly ? "Source text only" : card.impact_vector;
  document.getElementById("drawer-rigour").textContent = sourceOnly ? "No AI interpretation shown" : card.impact_status;

  // Populate timeline steps
  document.getElementById("step-detected-text").textContent = chain.event_detected;
  document.getElementById("step-verify-text").textContent = chain.source_verification;
  document.getElementById("step-transmission-text").textContent = sourceOnly ? "Source-only comparison: no interpretation shown." : chain.transmission_chain;
  document.getElementById("step-why-text").textContent = sourceOnly ? card.baseline_text : chain.why_it_matters;
  document.getElementById("step-precedent-title").textContent = chain.historical_analogy_name;
  document.getElementById("step-similarity-text").textContent = chain.historical_similarity;
  document.getElementById("step-counter-text").textContent = sourceOnly ? "No AI counterargument shown in the source-only comparison." : chain.counter_analogy_differences;
  document.getElementById("step-caveat-text").textContent = sourceOnly ? "Source text alone does not establish stock returns." : chain.explicit_caveat;

  // Reset chat messages
  const chatBox = document.getElementById("chat-messages");
  chatBox.replaceChildren();
  document.getElementById("chat-user-input").disabled = !card.is_sample;
  document.getElementById("btn-send-chat").disabled = !card.is_sample;
  if (!card.is_sample) appendChatBubble("For real RBI documents, use the cited analysis and full source above. The fixed demo chatbot is disabled here.", "bot");
  else appendChatBubble("This demo assistant uses fixed responses from the selected scenario. Ask about its reasoning, analogy, or uncertainty. Messages are sent to the server; avoid entering private financial details.", "bot");

  document.getElementById("reasoning-drawer").classList.add("active");
  document.querySelector(".app-header").inert = true;
  document.querySelector(".app-container").inert = true;
  document.body.style.overflow = "hidden";
  document.getElementById("btn-close-drawer").focus();
}

function closeReasoningDrawer() {
  document.getElementById("reasoning-drawer").classList.remove("active");
  document.querySelector(".app-header").inert = false;
  document.querySelector(".app-container").inert = false;
  document.body.style.overflow = "";
  if (drawerReturnFocus?.isConnected) drawerReturnFocus.focus();
  drawerReturnFocus = null;
}

function setupAssistantChat() {
  const sendBtn = document.getElementById("btn-send-chat");
  const input = document.getElementById("chat-user-input");

  const sendQuery = async () => {
    const text = input.value.trim();
    if (!text || !currentEventCard) return;

    const chatBox = document.getElementById("chat-messages");
    appendChatBubble(text, "user");
    input.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
      const res = await fetch("/api/v1/chat/event-assistant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_id: currentEventCard.id,
          user_query: text
        })
      });
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    const data = await res.json();
      appendChatBubble(data.response, "bot");
      chatBox.scrollTop = chatBox.scrollHeight;
    } catch (e) {
      appendChatBubble("Unable to reach the assistant. Please try again.", "bot");
    }
  };

  sendBtn.addEventListener("click", sendQuery);
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendQuery();
  });
}

function setupTabs() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const target = tab.dataset.tab;
      document.querySelectorAll(".primary-nav .tab-btn").forEach(item => {
        const selected = item.dataset.tab === target || (target === "brief" && item.dataset.tab === "explore");
        item.classList.toggle("is-current", selected);
        if(selected)item.setAttribute("aria-current","page");else item.removeAttribute("aria-current");
      });
      document.querySelectorAll(".more-menu[open], .more-actions[open], .export-menu[open]").forEach(menu => menu.open = false);
      document.getElementById("research-toolbar").style.display = target === "brief" || target === "explore" ? "block" : "none";
      const names={review:"Overview",journal:"Journal",timeline:"Policy timeline",brief:"Research",explore:"Research",portfolio:"Holdings",precedents:"Reference library",audit:"Source checks"};
      document.title = names[target] + " · Sarthi";
      ["review", "journal", "timeline"].forEach(name => { document.getElementById(`${name}-section`).style.display = target === name ? "block" : "none"; });
      window.workspaceUI?.render();
      document.getElementById("cards-container").style.display = (target === "brief" || target === "explore") ? "flex" : "none";
      document.getElementById("precedents-section").style.display = (target === "precedents") ? "block" : "none";
      document.getElementById("portfolio-section").style.display = (target === "portfolio") ? "block" : "none";
      document.getElementById("audit-section").style.display = (target === "audit") ? "block" : "none";

      if (target === "brief" || target === "explore") {
        renderCards();
      }
    });
  });
}

async function loadPrecedents() {
  try {
    const res = await fetch("/api/v1/analogies");
    allPrecedents = await res.json();
    const container = document.getElementById("precedents-grid");
    container.innerHTML = allPrecedents.map(p => `
      <div class="precedent-card">
        <div class="precedent-code">${escapeHTML(p.id)} · ${escapeHTML(p.period)}</div>
        <h4 class="precedent-title">${escapeHTML(p.name)}</h4>
        <p class="quiet">${escapeHTML(p.macro_context)}</p>
        <details><summary>Read context</summary><div class="reference-mechanism">${escapeHTML(p.transmission_mechanism)}</div><p class="quiet">${escapeHTML(p.key_lessons)}</p></details>
      </div>
    `).join('');
  } catch (e) {
    console.error("Failed to load precedents:", e);
  }
}

function setupPortfolioModal() {
  document.getElementById("btn-demo-portfolio").addEventListener("click", () => {
    try { window.edgeMatcher.savePortfolio(DEFAULT_PORTFOLIO.map(h => ({...h}))); }
    catch(error) { document.getElementById("portfolio-message").textContent = error.message; return; }
    renderPortfolioTable(); renderCards();
    document.getElementById("portfolio-message").textContent = "Example portfolio loaded. These are fictional allocations for the walkthrough.";
  });
  document.getElementById("btn-clear-portfolio").addEventListener("click", () => {
    try { window.edgeMatcher.savePortfolio([]); }
    catch(error) { document.getElementById("portfolio-message").textContent = error.message; return; }
    renderPortfolioTable(); renderCards();
    document.getElementById("portfolio-message").textContent = "Holdings cleared from this browser.";
  });
  const addBtn = document.getElementById("btn-add-holding");
  if (addBtn) {
    addBtn.addEventListener("click", () => {
      const ticker = document.getElementById("input-ticker").value;
      const sector = document.getElementById("input-sector").value;
      const weight = parseFloat(document.getElementById("input-weight").value);
      if (ticker && weight > 0) {
        try { window.edgeMatcher.addHolding(ticker, sector, weight); }
        catch (error) { document.getElementById("portfolio-message").textContent = error.message; return; }
        document.getElementById("portfolio-message").textContent = "Holding saved in this browser.";
        renderPortfolioTable();
        renderCards();
        document.getElementById("input-ticker").value = "";
        document.getElementById("input-weight").value = "15";
      }
    });
  }
}

function renderPortfolioTable() {
  window.workspaceUI?.render();
  const tbody = document.getElementById("portfolio-tbody");
  if (!tbody) return;
  const holdings = window.edgeMatcher.holdings;
  tbody.innerHTML = holdings.map(h => `
    <tr>
      <td style="font-weight: 700; color: #60a5fa;">${escapeHTML(h.ticker)}</td>
      <td>${escapeHTML(h.sector)}</td>
      <td>${escapeHTML(h.allocation_pct)}%</td>
      <td>
        <button class="btn-danger" data-remove-ticker="${escapeHTML(h.ticker)}">Remove</button>
      </td>
    </tr>
  `).join('');
  tbody.querySelectorAll('[data-remove-ticker]').forEach(button => button.addEventListener('click', () => deleteHolding(button.dataset.removeTicker)));
}

function deleteHolding(ticker) {
  try { window.edgeMatcher.removeHolding(ticker); }
  catch(error) { document.getElementById("portfolio-message").textContent = error.message; return; }
  renderPortfolioTable();
  renderCards();
}

function renderAuditTelemetry(data) {
  const droppedList = document.getElementById("audit-dropped-list");
  if (!droppedList) return;
  droppedList.innerHTML = (data.dropped_events_audit || []).map(item => `
    <li style="margin-bottom: 0.75rem; background: rgba(255,255,255,0.03); padding: 0.85rem; border-radius: 6px; border-left: 3px solid #f43f5e;">
      <div style="font-weight: 600; color: #f8fafc; font-size: 0.9rem;">${escapeHTML(item.title)}</div>
      <div style="color: #fb7185; font-size: 0.82rem; margin-top: 0.25rem;">${escapeHTML(item.reason)}</div>
    </li>
  `).join('');
}

async function generateAnalysis(id, button) {
  button.disabled = true;
  button.textContent = "Preparing analysis…";
  const status = document.getElementById("provider-status");
  try {
    const response = await fetch(`/api/v1/rbi/analyze/${encodeURIComponent(id)}`, {method:"POST"});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Gemini analysis unavailable.");
    await loadPipelineData();
    openReasoningDrawer(id);
    status.textContent = result.analysis.abstain ? "Gemini abstained. See source evidence." : "Gemini analysis saved. Citations checked for text occurrence; interpretation requires review.";
  } catch (error) { status.textContent = error.message; }
  finally { document.getElementById("workspace-status").textContent = status.textContent; button.disabled = false; button.textContent = "Generate analysis"; }
}
async function refreshRBI() {
  const button = document.getElementById("btn-refresh-rbi");
  button.disabled = true;
  const status = document.getElementById("provider-status");
  status.textContent = "Checking RBI sources…";
  try {
    const response = await fetch("/api/v1/rbi/refresh", {method:"POST"});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Live refresh unavailable.");
    await loadPipelineData();
    status.textContent = `${result.status === "completed" ? "Check complete" : "Check incomplete"}: ${result.matching_items} matching resolutions; ${result.retrieved.length} retrieved; ${result.failures.length} failed; ${result.pending} pending.`;
  } catch (error) { status.textContent = error.message; }
  finally { document.getElementById("workspace-status").textContent = status.textContent; button.disabled = false; }
}
function renderEvidence(card) {
  const claims = document.getElementById("claim-evidence");
  claims.replaceChildren();
  if (!document.getElementById("source-only").checked) {
    for (const claim of card.cited_claims || []) {
      const item = document.createElement("article");
      const heading = document.createElement("h4");
      heading.textContent = claim.kind === "fact" ? "Source quote" : "Interpretation · requires review";
      item.appendChild(heading);
      const text = document.createElement("p"); text.textContent = claim.text; item.appendChild(text);
      if (claim.kind === "interpretation") {
        const supporting = document.createElement("details");
        const summary = document.createElement("summary"); summary.textContent = "Supporting passages"; supporting.appendChild(summary);
        for (const citation of claim.citations) {
          const quote = document.createElement("blockquote"); quote.textContent = `[${citation.paragraph_id}] ${citation.quote}`; supporting.appendChild(quote);
        }
        item.appendChild(supporting);
      }
      claims.appendChild(item);
    }
  }
  const source = document.getElementById("source-paragraphs");
  source.replaceChildren();
  for (const paragraph of card.evidence_paragraphs || []) {
    const p = document.createElement("p");
    p.textContent = `[${paragraph.id}] ${paragraph.text}`;
    source.appendChild(p);
  }
}
