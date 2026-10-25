/**
 * Sarthi Behavioral Onboarding Controller
 */

let currentStep = 1;
const totalSteps = 7;

const profileState = {
  name: "Prudent Investor",
  age_band: "30-45",
  income: "salaried",
  horizon: "long_term_5yr_plus",
  stated_risk: "moderate",
  scenario_response: "hold_patient",
  disclosure_level: 3,
  avoided_sectors: []
};

function selectChoice(element, category, value) {
  const parent = element.parentElement;
  Array.from(parent.children).forEach(child => child.classList.remove("selected"));
  element.classList.add("selected");

  if (category === "horizon") profileState.horizon = value;
  if (category === "scenario") profileState.scenario_response = value;
  if (category === "disclosure") profileState.disclosure_level = parseInt(value, 10);
}

async function changeStep(delta) {
  const newStep = currentStep + delta;
  if (newStep < 1) return;

  if (newStep > totalSteps) {
    // Finish onboarding
    completeOnboarding();
    return;
  }

  // Update State from current step
  if (currentStep === 1) {
    profileState.name = document.getElementById("user-name").value || "Prudent Investor";
    profileState.age_band = document.getElementById("user-age").value;
  } else if (currentStep === 6) {
    profileState.avoided_sectors = [];
    if (document.getElementById("avoid-tobacco").checked) profileState.avoided_sectors.push("FMCG", "Tobacco");
    if (document.getElementById("avoid-liquor").checked) profileState.avoided_sectors.push("Liquor", "Beverages");
    if (document.getElementById("avoid-gambling").checked) profileState.avoided_sectors.push("Gaming", "Casinos");
    if (document.getElementById("avoid-defense").checked) profileState.avoided_sectors.push("Defense");

    // Fetch calibrated profile from server
    await calibrateProfile();
  }

  // Hide old step, show new step
  document.getElementById(`step-${currentStep}`).style.display = "none";
  document.getElementById(`dot-${currentStep}`).classList.remove("active");
  if (delta > 0) document.getElementById(`dot-${currentStep}`).classList.add("completed");

  currentStep = newStep;
  document.getElementById(`step-${currentStep}`).style.display = "block";
  document.getElementById(`dot-${currentStep}`).classList.add("active");

  // Adjust button labels
  document.getElementById("btn-prev").style.visibility = (currentStep === 1) ? "hidden" : "visible";
  document.getElementById("btn-next").textContent = (currentStep === totalSteps) ? "Launch Dashboard →" : "Continue →";
}

async function calibrateProfile() {
  try {
    const res = await fetch("/api/v1/onboarding/calibrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        portfolio_size_inr: 1000000,
        scenario_response: profileState.scenario_response,
        stated_risk_tolerance: profileState.stated_risk,
        investment_horizon: profileState.horizon
      })
    });
    const data = await res.json();

    document.getElementById("summary-persona").textContent = data.calibrated_band;
    document.getElementById("summary-lambda").textContent = data.loss_aversion_lambda.toFixed(2);
    document.getElementById("summary-drawdown").textContent = `${data.max_tolerated_drawdown_pct}%`;

    const callout = document.getElementById("rationality-callout");
    if (data.has_rationality_gap) {
      callout.style.background = "rgba(244, 63, 94, 0.12)";
      callout.style.border = "1px solid rgba(244, 63, 94, 0.3)";
      callout.style.color = "#fda4af";
      callout.innerHTML = `<strong>⚠️ Rationality Gap Detected:</strong> ${data.gap_explanation}`;
    } else {
      callout.style.background = "rgba(16, 185, 129, 0.12)";
      callout.style.border = "1px solid rgba(16, 185, 129, 0.3)";
      callout.style.color = "#86efac";
      callout.innerHTML = `<strong>✅ Balanced Calibration:</strong> ${data.gap_explanation}`;
    }

    profileState.calibrated_band = data.calibrated_band;
    profileState.loss_aversion_lambda = data.loss_aversion_lambda;
  } catch (err) {
    console.error("Calibration failed:", err);
  }
}

function completeOnboarding() {
  window.edgeMatcher.saveProfile({
    display_name: profileState.name,
    age_band: profileState.age_band,
    risk_band: profileState.calibrated_band || "Balanced Compounding",
    avoided_sectors: profileState.avoided_sectors
  });
  window.location.href = "/";
}
