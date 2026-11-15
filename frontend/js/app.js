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

document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("source-mode").addEventListener("change", loadPipelineData);
  document.getElementById("source-only").addEventListener("change", () => { renderCards(); if (currentEventCard && document.getElementById("reasoning-drawer").classList.contains("active")) openReasoningDrawer(currentEventCard.id); });
  document.getElementById("btn-refresh-rbi").addEventListener("click", refreshRBI);
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
    document.getElementById("data-label").textContent = dataMode === "rbi" ? "REAL RBI ARCHIVE" : "SYNTHETIC DEMO";
    document.getElementById("btn-refresh-rbi").disabled = dataMode !== "rbi";
    document.getElementById("source-only").disabled = dataMode !== "rbi";
    if (dataMode === "rbi") {
      const status = await fetch("/api/v1/rbi/status").then(r => r.json());
      if (sequence !== loadSequence) return;
      document.getElementById("provider-status").textContent = status.configured ? `Gemini: ${status.model}. Analysis runs on request.` : "Gemini key is not configured. Source documents are available.";
    } else document.getElementById("provider-status").textContent = "Fixed synthetic scenarios; no model requests.";
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

function updateTelemetryBanner(stats) {
  document.getElementById("stat-scanned").textContent = stats.scanned || 0;
  document.getElementById("stat-confirmed").textContent = stats.confirmed || 0;
  document.getElementById("stat-dropped").textContent = stats.dropped_at_confirm || 0;
  document.getElementById("stat-passed").textContent = stats.passed_constraint || 0;
}

function renderCards() {
  const container = document.getElementById("cards-container");
  const activeTab = document.querySelector(".tab-btn.active").dataset.tab;
  
  const personalized = window.edgeMatcher.matchAndPersonalize(rawDailyCards);
  let cardsToShow = [];

  if (activeTab === "brief") {
    cardsToShow = personalized.morningBrief;
  } else if (activeTab === "explore") {
    cardsToShow = personalized.exploreFeed;
  }

  if (cardsToShow.length === 0) {
    container.innerHTML = `
      <div class="glass-panel" style="padding: 3rem; text-align: center; grid-column: 1 / -1;">
        <h3 style="color: var(--text-muted); font-family: var(--font-heading);">No cards in this feed</h3>
        <p style="color: var(--text-dim); margin-top: 0.5rem;">No relevant events in this view. Add holdings or load the example portfolio in My Portfolio, or browse Explore. Source-only cards contain no AI conclusion.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = cardsToShow.map(card => {
    const baselineView = document.getElementById("source-only").checked && !card.is_sample;
    const catClass = `cat-${escapeHTML(card.category)}`;
    let vecClass = "vec-monitor";
    if (card.impact_vector.includes("Tailwind")) vecClass = "vec-tailwind";
    else if (card.impact_vector.includes("Headwind")) vecClass = "vec-headwind";
    else if (card.impact_vector.includes("No Action")) vecClass = "vec-calm";

    const matchedBadge = card.matched_ticker ? `
      <span style="font-size: 0.72rem; color: #60a5fa; background: rgba(59, 130, 246, 0.15); padding: 0.2rem 0.5rem; border-radius: 9999px; font-weight: 600;">
        ⚡ Matched Holding (${escapeHTML(card.matched_ticker)})
      </span>
    ` : "";

    return `
      <div class="glass-panel event-card ${card.is_matched ? 'matched-holding' : ''}">
        <div class="card-top">
          <div class="badge-row">
            <span class="category-tag ${catClass}">${escapeHTML(card.category)}</span>
            <span class="tier-indicator">
              <span class="tier-dot-${card.highest_tier}">●</span> Tier ${card.highest_tier} · ${card.is_sample ? "Sample" : "RBI original"}
            </span>
          </div>

          ${matchedBadge}
          <p>${escapeHTML(card.relevance_explanation || "")}</p>

          <h3 class="card-title" style="margin-top: 0.5rem;">${escapeHTML(card.canonical_title)}</h3>

          <div class="card-tickers">
            ${card.impacted_tickers.map(t => `
              <span class="ticker-pill ${t === card.matched_ticker ? 'matched' : ''}">${escapeHTML(t)}</span>
            `).join('')}
          </div>

          <div class="verdict-box ${vecClass}">
            <div class="verdict-header">
              <span>${escapeHTML(baselineView ? "Source text only" : card.impact_vector)}</span>
              <span class="rigour-tag">${escapeHTML(baselineView ? "No interpretation in this comparison" : card.impact_status)}</span>
            </div>
          </div>

          <p class="card-summary">${escapeHTML(baselineView ? card.baseline_text : card.summary_insight)}</p>
          <p class="card-summary">${escapeHTML(card.evidence_status)} · ${card.is_sample ? "Sample date" : "Published"}: ${escapeHTML(card.published_at.slice(0, 10))}</p>
          ${card.analysis_model ? `<p class="card-summary">Recorded Gemini analysis: ${escapeHTML(card.analysis_model)}, ${escapeHTML(card.analysis_generated_at.slice(0, 10))}</p>` : ""}
        </div>

        <div class="card-action">
          ${!card.is_sample && card.analysis_status !== "generated" ? `<button class="btn-secondary" data-analyze-id="${escapeHTML(card.id)}">Generate Gemini analysis</button>` : ""}
          <button class="btn-open-chain" data-event-id="${escapeHTML(card.id)}">
            <span>🔍 View Auditable Reasoning Chain</span>
          </button>
        </div>
      </div>
    `;
  }).join('');
  container.querySelectorAll("[data-analyze-id]").forEach(button => button.addEventListener("click", () => generateAnalysis(button.dataset.analyzeId, button)));
  container.querySelectorAll("[data-event-id]").forEach(button => button.addEventListener("click", () => openReasoningDrawer(button.dataset.eventId)));
}

function openReasoningDrawer(eventId) {
  const card = rawDailyCards.find(c => c.id === eventId);
  if (!card) return;
  currentEventCard = card;
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
}

function closeReasoningDrawer() {
  document.getElementById("reasoning-drawer").classList.remove("active");
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
      ["review", "journal", "timeline"].forEach(name => { document.getElementById(`${name}-section`).style.display = target === name ? "block" : "none"; });
      window.workspaceUI?.render();
      document.getElementById("cards-container").style.display = (target === "brief" || target === "explore") ? "grid" : "none";
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
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">${escapeHTML(p.macro_context)}</p>
        <div style="background: rgba(0,0,0,0.25); padding: 0.75rem; border-radius: 6px; font-size: 0.82rem; margin-bottom: 0.5rem;">
          <strong style="color: #38bdf8;">Mechanism:</strong> ${escapeHTML(p.transmission_mechanism)}
        </div>
        <div style="font-size: 0.8rem; color: #a78bfa;">
          <strong>Key Lesson:</strong> ${escapeHTML(p.key_lessons)}
        </div>
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
  button.textContent = "Analyzing with Gemini…";
  const status = document.getElementById("provider-status");
  try {
    const response = await fetch(`/api/v1/rbi/analyze/${encodeURIComponent(id)}`, {method:"POST"});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Gemini analysis unavailable.");
    await loadPipelineData();
    status.textContent = result.analysis.abstain ? "Gemini abstained. See source evidence." : "Gemini analysis saved. Citations checked for text occurrence; interpretation requires review.";
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; button.textContent = "Generate Gemini analysis"; }
}
async function refreshRBI() {
  const button = document.getElementById("btn-refresh-rbi");
  button.disabled = true;
  const status = document.getElementById("provider-status");
  status.textContent = "Checking RBI feed…";
  try {
    const response = await fetch("/api/v1/rbi/refresh", {method:"POST"});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Live refresh unavailable.");
    await loadPipelineData();
    status.textContent = `Feed checked: ${result.matching_items} matching resolutions; ${result.retrieved.length} retrieved; ${result.failures.length} failed. Older resolutions may be absent from the rolling feed.`;
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
}
function renderEvidence(card) {
  const claims = document.getElementById("claim-evidence");
  claims.replaceChildren();
  if (!document.getElementById("source-only").checked) {
    for (const claim of card.cited_claims || []) {
      const item = document.createElement("article");
      const heading = document.createElement("h4");
      heading.textContent = claim.kind === "fact" ? "Fact (verbatim source quote)" : "AI interpretation (hypothesis)";
      item.appendChild(heading);
      const text = document.createElement("p"); text.textContent = claim.text; item.appendChild(text);
      for (const citation of claim.citations) {
        const quote = document.createElement("blockquote");
        quote.textContent = `[${citation.paragraph_id}] ${citation.quote}`;
        item.appendChild(quote);
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
