// Run the actual matcher with browser storage mocked; no DOM or network needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const storage = new Map();
const context = vm.createContext({window: {}, console, localStorage: {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value)
}});
vm.runInContext(fs.readFileSync('frontend/js/review_core.js', 'utf8'), context);
vm.runInContext(fs.readFileSync('frontend/js/edge_matcher.js', 'utf8'), context);
const matcher = context.window.edgeMatcher;
const card = (id, extra = {}) => ({id, primary_sector: 'FMCG', sectors: ['FMCG', 'Tobacco'], impacted_tickers: ['ITC'], passed_constraint_gate: true, ...extra});
assert.equal(matcher.holdings.length, 0, 'New users must not receive invented holdings');
assert.equal(matcher.matchAndPersonalize([card('empty')]).morningBrief.length, 0);
matcher.addHolding('itc', 'FMCG', 50);
assert.throws(() => matcher.addHolding('<script>', 'FMCG', 10));
assert.throws(() => matcher.addHolding('INFY', 'IT', Infinity));
assert.throws(() => matcher.addHolding('INFY', 'IT', 60));
const result = matcher.matchAndPersonalize([
  card('matched'), card('failed', {passed_constraint_gate: false}),
  card('unrelated', {sectors: ['Technology'], primary_sector: 'Technology', impacted_tickers: ['INFY']})
]);
assert.deepEqual(Array.from(result.morningBrief, c => c.id), ['matched']);
assert.equal(result.exploreFeed.length, 2);
assert.equal(result.morningBrief[0].matched_allocation_pct, 50, 'A holding matching ticker and sector must count once');
assert.match(result.morningBrief[0].relevance_explanation, /50.0%/);
matcher.saveProfile({avoided_sectors: ['Tobacco']});
assert.equal(matcher.matchAndPersonalize([card('avoided')]).morningBrief.length, 0, 'Check every affected sector');
matcher.saveProfile({avoided_sectors: []});
matcher.savePortfolio([{ticker: 'OTHER', sector: 'Tobacco', allocation_pct: 10}]);
assert.equal(matcher.matchAndPersonalize([card('secondary-sector')]).morningBrief.length, 1);
assert.equal(storage.has('sarthi_local_portfolio_l3'), true);
// Verify user/API strings are escaped and chat bubbles receive literal text.
const elements = [];
context.document = {
  addEventListener() {},
  createElement() { return {style: {}}; },
  getElementById() { return {appendChild: element => elements.push(element)}; }
};
vm.runInContext(fs.readFileSync('frontend/js/app.js', 'utf8'), context);
assert.equal(vm.runInContext('escapeHTML("<img src=x onerror=alert(1)>")', context), '&lt;img src=x onerror=alert(1)&gt;');
vm.runInContext('appendChatBubble("<script>alert(1)</script>", "user")', context);
assert.equal(elements[0].textContent, '<script>alert(1)</script>');
assert.equal(elements[0].innerHTML, undefined);
console.log('PASS: local matching, exclusions, failed gates, allocation validation, escaping and literal chat');
