/**
 * Sarthi Client-Side Edge Matching Engine
 * 
 * Implements Local Browser Personalization:
 * - Level 3 user portfolio holdings are stored ONLY in browser localStorage.
 * - The matcher does not transmit holdings. Free-text chat is sent to the server.
 * - The client receives the broadcasted daily event matrix and performs
 *   local ranking and relevance scoring in-browser.
 */

const DEFAULT_PORTFOLIO = [
  { ticker: "ITC", sector: "FMCG", allocation_pct: 20 },
  { ticker: "HDFCBANK", sector: "Banking", allocation_pct: 25 },
  { ticker: "TATAMOTORS", sector: "Automotive", allocation_pct: 15 },
  { ticker: "INFY", sector: "IT Services", allocation_pct: 20 },
  { ticker: "APOLLOTYRE", sector: "Auto Ancillary", allocation_pct: 10 },
  { ticker: "BAJFINANCE", sector: "NBFCs", allocation_pct: 10 }
];

const STORAGE_KEY_PORTFOLIO = "sarthi_local_portfolio_l3";
const STORAGE_KEY_PROFILE = "sarthi_local_user_profile";

class EdgeMatcher {
  constructor() {
    this.holdings = this.loadPortfolio();
    this.profile = this.loadProfile();
  }

  loadPortfolio() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_PORTFOLIO);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.warn("Could not read local storage, starting with no holdings.");
    }
    return [];
  }

  savePortfolio(holdings) {
    this.holdings = holdings;
    try {
      localStorage.setItem(STORAGE_KEY_PORTFOLIO, JSON.stringify(holdings));
    } catch (e) {
      console.error("Failed to persist local portfolio:", e);
    }
  }

  loadProfile() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_PROFILE);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.warn("Could not read profile, using default.");
    }
    const def = {
      display_name: "Prudent Investor",
      risk_band: "Balanced Compounding",
      avoided_sectors: []
    };
    this.saveProfile(def);
    return def;
  }

  saveProfile(profile) {
    this.profile = profile;
    try {
      localStorage.setItem(STORAGE_KEY_PROFILE, JSON.stringify(profile));
    } catch (e) {
      console.error("Failed to persist local profile:", e);
    }
  }

  addHolding(ticker, sector, allocation) {
    const cleanTicker = ticker.trim().toUpperCase();
    if (!/^[A-Z0-9&.-]{1,24}$/.test(cleanTicker)) throw new Error("Enter a valid ticker using letters, digits, &, . or -.");
    if (!Number.isFinite(allocation) || allocation <= 0 || allocation > 100) throw new Error("Weight must be greater than 0 and at most 100.");
    const total = this.holdings.filter(h => h.ticker !== cleanTicker).reduce((sum, h) => sum + h.allocation_pct, 0) + allocation;
    if (total > 100.000001) throw new Error("Total portfolio allocation cannot exceed 100%.");
    const existing = this.holdings.find(h => h.ticker === cleanTicker);
    if (existing) {
      existing.allocation_pct = allocation;
      existing.sector = sector;
    } else {
      this.holdings.push({
        ticker: cleanTicker,
        sector: sector,
        allocation_pct: allocation
      });
    }
    this.savePortfolio(this.holdings);
  }

  removeHolding(ticker) {
    this.holdings = this.holdings.filter(h => h.ticker !== ticker);
    this.savePortfolio(this.holdings);
  }

  matchAndPersonalize(dailyCards) {
    const portfolioTickers = new Set(this.holdings.map(h => h.ticker.toUpperCase()));
    const portfolioSectors = new Set(this.holdings.map(h => h.sector.toLowerCase()));
    const avoidedSectors = new Set((this.profile.avoided_sectors || []).map(s => s.toLowerCase()));

    const scoredCards = dailyCards.map(card => {
      let matchedTicker = null;
      let matchedSector = null;
      let isAvoided = false;

      // Check avoided sectors
      const sectors = card.sectors || [card.primary_sector];
      if (sectors.some(s => avoidedSectors.has(s.toLowerCase()))) {
        isAvoided = true;
      }

      // Check ticker match
      for (const t of card.impacted_tickers) {
        if (portfolioTickers.has(t.toUpperCase())) {
          matchedTicker = t.toUpperCase();
          break;
        }
      }

      // Check sector match
      matchedSector = sectors.find(s => portfolioSectors.has(s.toLowerCase())) || null;
      const matchedHoldings = this.holdings.filter(h =>
        card.impacted_tickers.some(t => t.toUpperCase() === h.ticker.toUpperCase()) ||
        sectors.some(s => s.toLowerCase() === h.sector.toLowerCase()));
      const exposure = matchedHoldings.reduce((sum, h) => sum + h.allocation_pct, 0);
      const relevance = matchedHoldings.length ?
        `${exposure.toFixed(1)}% of your entered allocation overlaps the listed tickers or sectors. This is exposure overlap, not an estimate of gain or loss.` :
        "No overlap with your entered holdings. Sector mapping is a heuristic.";

      // Compute local score
      // Ranking expresses exposure only, never investment confidence.
      let score = 0;
      if (matchedTicker) {
        score += 40 + (exposure * 0.5);
      } else if (matchedSector) {
        score += 20 + (exposure * 0.5);
      }

      return {
        ...card,
        is_matched: !!matchedTicker || !!matchedSector,
        matched_ticker: matchedTicker,
        matched_sector: matchedSector,
        matched_allocation_pct: exposure,
        relevance_explanation: relevance,
        is_avoided: isAvoided,
        local_score: score
      };
    });

    // Sort by local personalized relevance score descending
    scoredCards.sort((a, b) => b.local_score - a.local_score);

    // Morning Brief: Top 5 non-avoided cards
    const morningBrief = scoredCards.filter(c => !c.is_avoided && c.is_matched && c.passed_constraint_gate).slice(0, 5);
    const exploreFeed = scoredCards.filter(c => !morningBrief.includes(c));

    return {
      morningBrief,
      exploreFeed,
      totalHoldingsCount: this.holdings.length
    };
  }
}

window.edgeMatcher = new EdgeMatcher();
