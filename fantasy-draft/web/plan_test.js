/* Spend-plan optimizer vs brute force on random small cases, with the position rules.
 * usage: node fantasy-draft/web/plan_test.js */
const DE = require(process.argv[2] || require('path').join(__dirname, 'engine.js'));
let seed = 11; const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
const R = { gMin: 3, fMin: 3, cMin: 1, cMax: 3 };
let fails = 0, trials = 0, infeasible = 0;
for (let t = 0; t < 600; t++) {
  const n = 3 + Math.floor(rnd() * 9), S = 1 + Math.floor(rnd() * 6), B = S + Math.floor(rnd() * 70);
  const grps = ['g', 'f', 'c'];
  const cand = Array.from({ length: n }, () => ({ val: 1 + rnd() * 40, cost: 1 + Math.floor(rnd() * 30), grp: grps[Math.floor(rnd() * 3)] }));
  const have = { g: Math.floor(rnd() * 4), f: Math.floor(rnd() * 4), c: Math.floor(rnd() * 3) };
  let best = -1;
  for (let m = 0; m < (1 << n); m++) {
    const sel = cand.filter((_, i) => m & (1 << i)); if (sel.length > S) continue;
    const cost = sel.reduce((a, c) => a + c.cost, 0), fill = S - sel.length; if (cost > B - fill) continue;
    const cnt = { g: have.g, f: have.f, c: have.c }; sel.forEach((c) => cnt[c.grp]++);
    if (sel.some((c) => c.grp === 'c') && cnt.c > R.cMax) continue;
    const short = Math.max(0, R.gMin - cnt.g) + Math.max(0, R.fMin - cnt.f) + Math.max(0, R.cMin - cnt.c);
    if (short > fill) continue;
    best = Math.max(best, sel.reduce((a, c) => a + c.val, 0) + fill);
  }
  const r = DE.planKnapsack(cand, S, B, have, R); trials++;
  if (best < 0) { infeasible++; if (r !== null) { fails++; console.log('FAIL: expected infeasible', JSON.stringify({ S, B, have, r: r.value })); } continue; }
  let ok = r && Math.abs(r.value - best) < 1e-6 && r.picks.length <= S && r.spend <= B - r.fillers
    && Math.abs(r.picks.reduce((a, c) => a + c.val, 0) + r.fillers - r.value) < 1e-6;
  if (ok) {   // the returned picks must satisfy the rules themselves
    const cnt = { g: have.g, f: have.f, c: have.c }; r.picks.forEach((c) => cnt[c.grp]++);
    const short = Math.max(0, R.gMin - cnt.g) + Math.max(0, R.fMin - cnt.f) + Math.max(0, R.cMin - cnt.c);
    ok = short <= r.fillers && (!r.picks.some((c) => c.grp === 'c') || cnt.c <= R.cMax);
  }
  if (!ok) { fails++; if (fails < 4) console.log('FAIL', JSON.stringify({ S, B, have, best, got: r && r.value, picks: r && r.picks })); }
}
console.log(`spend-plan optimizer: ${trials - fails}/${trials} random cases match brute force (${infeasible} infeasible cases correctly null)`);
process.exit(fails ? 1 : 0);
