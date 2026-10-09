#!/usr/bin/env node
/* Replay a Python-recorded draft (build_web.py parity) through engine.js and demand the
 * same numbers after every command. usage: node parity_test.js <fixture.json> [...more] */
'use strict';
const fs = require('fs'), path = require('path');
const DE = require('./engine.js');
const DATA = JSON.parse(fs.readFileSync(path.join(__dirname, 'data.json'), 'utf8'));
const E = DE.create(DATA);

function snapshot(ctx) {
  const me = ctx.me, pm = ctx.pricers[me];
  const top = DE.sortBy(ctx.avail, (p) => -pm.adj(p)).slice(0, 25);
  const mk = DE.sortBy(ctx.avail, (p) => -ctx.market.adj(p)).slice(0, 6);
  const nom = DE.nominations(ctx);
  const teams = {};
  for (const t of ctx.order) teams[t] = [ctx.teams[t].budget, ctx.teams[t].open, ctx.teams[t].max_bid];
  const unf = {}; for (const t of ctx.order) unf[t] = DE.unfilled(ctx.teams[t].roster);
  return {
    teams, k: ctx.k, k_raw: ctx.k_raw, n_open: ctx.n_open,
    top: top.map((p) => { const r = E.myPrice(ctx, p); return [p.name, r.max, r.target, r.mine, r.market]; }),
    alerts: DE.alerts(E, ctx), emitted: [...ctx.st.emitted].sort(), last_k: ctx.st.last_k,
    w: DE.CATS.map((c) => ctx.wts[me].w[c]),
    ceiling: DE.rivalCeiling(ctx, me),
    threats: mk.map((p) => DE.threats(ctx, p, E.myPrice(ctx, p).max).map((r) => [r.id, r.val, r.need, r.liquid])),
    nom: ['push', 'drain', 'hold', 'steal'].map((k) => nom[k].map((x) => x[1].name)),
    unfilled: unf,
  };
}

function close(a, b, p) {
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a));
  if (a === null || b === null || typeof a !== 'object') {
    if (a !== b) throw new Error(`${p}: python=${JSON.stringify(a)} js=${JSON.stringify(b)}`);
    return true;
  }
  if (Array.isArray(a) !== Array.isArray(b)) throw new Error(`${p}: shape differs`);
  const ka = Object.keys(a), kb = Object.keys(b);
  if (ka.length !== kb.length) throw new Error(`${p}: python has ${ka.length} entries, js ${kb.length}\n  py=${JSON.stringify(a).slice(0, 400)}\n  js=${JSON.stringify(b).slice(0, 400)}`);
  for (const k of ka) {
    if (!(k in b)) throw new Error(`${p}.${k} missing in js`);
    if (!close(a[k], b[k], `${p}.${k}`)) throw new Error(`${p}.${k}: python=${a[k]} js=${b[k]}`);
  }
  return true;
}

let failures = 0;
for (const f of process.argv.slice(2)) {
  const fx = JSON.parse(fs.readFileSync(f, 'utf8'));
  let st = E.freshState(), checked = 0;
  try {
    fx.commands.forEach((cmd, i) => {
      const r = DE.exec(E, st, cmd);
      st = r.state;
      const want = fx.snapshots[i], got = Object.assign(snapshot(E.derive(st)), { ok: r.ok });
      close(want, got, `step ${i} [${cmd}]`);
      checked++;
    });
    console.log(`PASS ${path.basename(f)}: ${checked} commands identical`);
  } catch (e) {
    failures++;
    console.log(`FAIL ${path.basename(f)} after ${checked} matching commands:\n  ${e.message}`);
  }
}
process.exit(failures ? 1 : 0);
