// Chat helper: how is the live room pricing? Reads an ArtifactData copy of draft/state (or a
// Copy state paste saved to a file) and prints the learned Yahoo-vs-value weight, plus the likely
// price of any players named after the file.
// usage: node fantasy-draft/web/learn_room.js <state.json> [player ...]
const fs = require('fs'), path = require('path');
const DE = require(path.join(__dirname, 'engine.js'));
const DATA = JSON.parse(fs.readFileSync(path.join(__dirname, 'data.json'), 'utf8'));
const [file, ...names] = process.argv.slice(2);
let doc = JSON.parse(fs.readFileSync(file, 'utf8')); doc = doc.data || doc; const st = doc.state || doc;
const E = DE.create(DATA), L = DE.learnRoom(E, st), ctx = E.derive(st);
console.log(L.ready
  ? `room learned from ${L.n} sales: ${(L.w * 100).toFixed(0)}% Yahoo price / ${(100 - L.w * 100).toFixed(0)}% value; off by ~$${L.err_fit.toFixed(0)} a sale vs $${L.err_mid.toFixed(0)} for 50/50`
  : `not enough informative sales yet (${L.n}/${DE.LEARN.minN}); using 50/50 (raw fit ${(L.w_raw * 100).toFixed(0)}% Yahoo)`);
for (const n of names) {
  const [p, why] = E.resolveAvail(ctx, n);
  console.log(p ? `${p.name}: likely ~$${DE.expectedPrice(ctx, p, L.w)} (room $${DE.roomPrice(ctx, p).toFixed(0)}, market $${ctx.market.adj(p).toFixed(0)}, your MAX $${E.myPrice(ctx, p).max})` : why);
}
