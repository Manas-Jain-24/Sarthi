/**
 * Sarthi Client-Side Edge Matching Engine
 * 
 * Implements Zero-Knowledge Personalization:
 * - Level 3 user portfolio holdings are stored ONLY in browser localStorage.
 * - Sensitive financial assets are NEVER transmitted to the server.
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
      console.warn("Could not read local storage, using default portfolio.");
    }
    this.savePortfolio(DEFAULT_PORTFOLIO);
    return DEFAULT_PORTFOLIO;
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
      if (avoidedSectors.has(card.primary_sector.toLowerCase())) {
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
      if (portfolioSectors.has(card.primary_sector.toLowerCase())) {
        matchedSector = card.primary_sector;
      }

      // Compute local score
      let score = card.evidence_rigour_score * 0.4;
      if (matchedTicker) {
        const holding = this.holdings.find(h => h.ticker === matchedTicker);
        const weight = holding ? holding.allocation_pct : 10;
        score += 40 + (weight * 0.5);
      } else if (matchedSector) {
        score += 20;
      }

      return {
        ...card,
        is_matched: !!matchedTicker || !!matchedSector,
        matched_ticker: matchedTicker,
        matched_sector: matchedSector,
        is_avoided: isAvoided,
        local_score: score
      };
    });

    // Sort by local personalized relevance score descending
    scoredCards.sort((a, b) => b.local_score - a.local_score);

    // Morning Brief: Top 5 non-avoided cards
    const morningBrief = scoredCards.filter(c => !c.is_avoided).slice(0, 5);
    const exploreFeed = scoredCards.filter(c => !morningBrief.includes(c));

    return {
      morningBrief,
      exploreFeed,
      totalHoldingsCount: this.holdings.length
    };
  }
}

window.edgeMatcher = new EdgeMatcher();
