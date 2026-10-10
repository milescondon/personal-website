/* Draft engine: a line-for-line port of scripts/draft_state.py + opponents.py + the name
 * resolution in valuation.py. Pure functions over (DATA, state); no DOM. Runs in the
 * browser (window.DraftEngine) and in Node (require) so web/parity_test.js can replay the
 * same sales through both engines and demand identical numbers.
 *
 * Python semantics copied on purpose: round() is round-half-even, '{:.Nf}' formatting is
 * half-even on exact ties, sorted() is stable, dict order is insertion order.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DraftEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const CATS = ['fg_pct', 'ft_pct', 'tpm', 'pts', 'reb', 'ast', 'stl', 'blk', 'to'];
  const SHORT = { fg_pct: 'FG%', ft_pct: 'FT%', tpm: '3PM', pts: 'PTS', reb: 'REB',
                  ast: 'AST', stl: 'STL', blk: 'BLK', to: 'TO' };
  const REQUIRED = ['PG', 'SG', 'SF', 'PF', 'C'];
  const K_MAX = 3.0;
  const CAT_TOK = { fg: 'fg_pct', 'fg%': 'fg_pct', ft: 'ft_pct', 'ft%': 'ft_pct', '3': 'tpm',
                    '3pm': 'tpm', '3pt': 'tpm', tpm: 'tpm', pts: 'pts', reb: 'reb', ast: 'ast',
                    stl: 'stl', st: 'stl', blk: 'blk', to: 'to' };

  class CmdError extends Error {}
  const die = (msg) => { throw new CmdError(msg); };

  // ------------------------------------------------------------ python-compatible numerics
  function pyRound(x) {                       // round-half-even, like Python 3 round()
    const f = Math.floor(x), diff = x - f;
    if (diff > 0.5) return f + 1;
    if (diff < 0.5) return f;
    return f % 2 === 0 ? f : f + 1;
  }
  function pyFixed(x, d) {                    // '{:.df}'.format(x)
    const m = Math.pow(2, d + 1), q = x * m;  // exact: scaling by a power of two
    if (Number.isInteger(q) && Math.abs(q) % 2 === 1) {      // exact decimal tie
      const s = Math.pow(5, d) * q;           // = 2 * x * 10^d, odd
      let lo = (s - 1) / 2, hi = (s + 1) / 2;
      const n = (Math.abs(lo) % 2 === 0) ? lo : hi;
      const v = n / Math.pow(10, d);
      return (v === 0 && x < 0 ? '-' : '') + v.toFixed(d);
    }
    const r = x.toFixed(d);
    return r;
  }
  const sgn = (x, d) => ((x < 0 || Object.is(x, -0)) ? '-' : '+') + pyFixed(Math.abs(x), d);
  const money = (x) => '$' + pyFixed(x, 0);
  const fsum = (arr) => arr.reduce((a, b) => a + b, 0);       // left-to-right like sum()
  const sortBy = (arr, key) => arr.map((v, i) => [key(v), i, v])
    .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1] - b[1])).map((t) => t[2]);
  const floorDiv = (a, b) => Math.floor(a / b);

  // ------------------------------------------------------------ names (valuation.py)
  function canon(s) {
    s = (s || '').normalize('NFKD').replace(/[^\x00-\x7F]/g, '').toLowerCase();
    s = s.replace(/\b(jr|sr|ii|iii|iv)\b/g, '');
    return s.replace(/[^a-z0-9]+/g, '');
  }
  function nameParts(name) {
    const words = (name || '').replace(/[^A-Za-z\s]/g, ' ').trim().split(/\s+/);
    return words.filter((w) => canon(w));
  }
  function buildIndex(players, aliases) {
    const idx = { exact: new Map(), lastfirst: new Map(), last: new Map(), aliases: new Map() };
    for (const p of players) {
      idx.exact.set(p.key, p);
      const parts = nameParts(p.name);
      if (parts.length) {
        const last = canon(parts[parts.length - 1]), first = canon(parts[0]);
        if (!idx.last.has(last)) idx.last.set(last, []);
        idx.last.get(last).push(p);
        if (first) {
          const k = last + '|' + first[0];
          if (!idx.lastfirst.has(k)) idx.lastfirst.set(k, []);
          idx.lastfirst.get(k).push(p);
        }
      }
    }
    for (const [k, v] of Object.entries(aliases || {})) if (!k.startsWith('_')) idx.aliases.set(canon(k), canon(v));
    return idx;
  }
  function resolveName(idx, raw) {
    const k = canon(raw);
    if (idx.exact.has(k)) return [idx.exact.get(k), 'exact'];
    const a = idx.aliases.get(k);
    if (a && idx.exact.has(a)) return [idx.exact.get(a), 'alias'];
    const parts = nameParts(raw);
    if (parts.length >= 2) {
      const cand = idx.lastfirst.get(canon(parts[parts.length - 1]) + '|' + canon(parts[0]).slice(0, 1)) || [];
      if (cand.length === 1) return [cand[0], 'lastfirst'];
      if (cand.length > 1) return [null, 'ambiguous:' + cand.length];
    }
    if (parts.length) {
      const cand = idx.last.get(canon(parts[parts.length - 1])) || [];
      if (cand.length === 1) return [cand[0], 'last'];
      if (cand.length > 1) return [null, 'ambiguous:' + cand.length];
    }
    const cand = [];
    for (const [key, p] of idx.exact) if (key.startsWith(k) || k.startsWith(key)) cand.push(p);
    if (cand.length === 1) return [cand[0], 'prefix'];
    if (cand.length > 1) return [null, 'ambiguous:' + cand.length];
    return [null, 'miss'];
  }

  // ------------------------------------------------------------ opponents.py
  function weights(roster, sigma, override) {
    const d = {}, w = {};
    for (const c of CATS) d[c] = fsum(roster.filter((p) => p.z).map((p) => p.z[c]));
    for (const c of CATS) w[c] = Math.exp(-0.5 * Math.pow(d[c] / sigma[c], 2));
    for (const [c, v] of Object.entries(override || {})) w[c] = v;
    const s = fsum(CATS.map((c) => w[c]));
    const wn = {};
    for (const c of CATS) wn[c] = s > 1e-9 ? w[c] * CATS.length / s : 1.0;
    return { d, w, wn };
  }
  const pval = (p, wn) => fsum(CATS.map((c) => wn[c] * p.z[c]));
  class Pricer {
    constructor(players, wn, rostered, dpv, k) {
      this.wn = wn; this.dpv = dpv; this.k = k;
      const vals = players.map((p) => pval(p, wn)).sort((a, b) => b - a);
      this.repl = vals[Math.min(rostered, vals.length) - 1];
      this.cache = new Map();
    }
    fair(p) { return 1.0 + this.dpv * Math.max(pval(p, this.wn) - this.repl, 0.0); }
    adj(p) {
      let v = this.cache.get(p.key);
      if (v === undefined) { v = 1.0 + (this.fair(p) - 1.0) * this.k; this.cache.set(p.key, v); }
      return v;
    }
  }
  const positions = (p) => new Set(p.pos || []);
  function unfilled(roster) {
    const have = new Set();
    for (const p of roster) for (const x of positions(p)) have.add(x);
    return REQUIRED.filter((x) => !have.has(x));
  }
  function acuteNeed(team, p) {
    const miss = unfilled(team.roster);
    const ps = positions(p);
    return miss.some((m) => ps.has(m)) && team.open > 0 && miss.length >= team.open - 1;
  }
  const rivalRows = (ctx, me) => ctx.order.filter((t) => t !== me && ctx.teams[t].open > 0).map((t) => ctx.teams[t]);
  function roomPerSpot(ctx, me) {
    const rs = ctx.order.filter((t) => t !== me && ctx.teams[t].open > 0).map((t) => ctx.teams[t]);
    const b = fsum(rs.map((t) => t.budget)), o = fsum(rs.map((t) => t.open));
    return o ? b / o : 0.0;
  }
  function threats(ctx, p, myMax) {
    const avg = roomPerSpot(ctx, ctx.me), out = [];
    for (const t of rivalRows(ctx, ctx.me)) {
      if (t.max_bid <= myMax) continue;
      const val = ctx.pricers[t.id].adj(p);
      out.push({ id: t.id, max_bid: t.max_bid, val, liquid: t.budget / t.open >= 1.15 * avg,
                 need: acuteNeed(t, p), per_spot: t.budget / t.open });
    }
    return sortBy(out, (r) => -r.val);
  }
  const foldRisk = (th, myMax) => th.filter((r) => r.liquid && (r.val >= myMax + 2 || r.need));
  function rivalCeiling(ctx, me) {
    const rs = rivalRows(ctx, me);
    if (!rs.length) return [0, null];
    let top = rs[0];
    for (const t of rs) if (t.max_bid > top.max_bid) top = t;
    return [top.max_bid, top.id];
  }
  function nominations(ctx, n = 5) {
    const me = ctx.me, avail = sortBy(ctx.avail, (p) => -ctx.market.adj(p));
    const avg = roomPerSpot(ctx, me);
    const [ceil] = rivalCeiling(ctx, me);
    const myMaxBid = ctx.teams[me].max_bid, mine_ = ctx.pricers[me];
    const push = [], drain = [], hold = [], steal = [];
    for (const p of avail.slice(0, 80)) {
      const m = ctx.market.adj(p), mine = mine_.adj(p);
      if (m < 6) continue;
      const able = rivalRows(ctx, me).filter((t) => t.max_bid >= m && t.budget / t.open >= 0.9 * avg);
      const wanting = able.filter((t) => ctx.pricers[t.id].adj(p) >= m - 1);
      if (mine <= m - 2 && wanting.length >= 2)
        push.push([wanting.length * m + (m - mine) * 2, p, m, mine, wanting.map((t) => t.id)]);
      else if (mine <= m + 0.5 && m >= 15 && able.length >= 3)
        drain.push([m, p, m, mine, able.map((t) => t.id)]);
      if (mine >= m + 1) hold.push([mine - m, p, m, mine]);
      if (mine > ceil + 1 && myMaxBid > ceil && mine >= 3) steal.push([mine, p, ceil]);
    }
    const srt = (xs) => sortBy(xs, (x) => -x[0]).slice(0, n);
    return { push: srt(push), drain: srt(drain), hold: srt(hold), steal: srt(steal) };
  }

  // ------------------------------------------------------------ room prices (opponents.py)
  function roomK(ctx) {
    const numer = fsum(ctx.order.map((t) => ctx.teams[t].budget)) - ctx.n_open;
    const top = sortBy(ctx.avail.filter((p) => p.room_anchor !== null && p.room_anchor !== undefined),
                       (p) => -p.room_anchor).slice(0, Math.max(ctx.n_open, 0));
    const denom = fsum(top.map((p) => Math.max(p.room_anchor - 1.0, 0.0)));
    const k = denom > 0.5 ? numer / denom : (numer > 0 ? K_MAX : 1.0);
    return Math.max(0.0, Math.min(k, K_MAX));
  }
  function roomPrice(ctx, p) {
    const a = p.room_anchor;
    if (a === null || a === undefined) return ctx.market.adj(p);
    return 1.0 + Math.max(a - 1.0, 0.0) * ctx.room_k;
  }
  function roomNominations(ctx, n = 5, minGp = 0) {
    const me = ctx.me, pm = ctx.pricers[me], overpay = [], late = [];
    const avail = sortBy(ctx.avail, (p) => -ctx.market.adj(p));
    for (const p of avail.slice(0, 90)) {
      const r = roomPrice(ctx, p), mine = pm.adj(p);
      const able = rivalRows(ctx, me).filter((t) => t.max_bid >= r);
      if (r >= 10 && r - mine >= 5 && able.length >= 2) overpay.push([r - mine, p, r, mine]);
      if (mine >= 8 && mine - r >= 5 && p.games >= minGp) late.push([mine - r, p, r, mine]);   // never wait on a player you won't buy
    }
    return { overpay: sortBy(overpay, (x) => -x[0]).slice(0, n), late: sortBy(late, (x) => -x[0]).slice(0, n) };
  }

  // Spend plan (page only): the set of available players that maximizes your value at the
  // prices you should expect to pay, within your cash and open spots. Expected price is the
  // midpoint of the room price (Yahoo anchors) and market value, because the room holds both
  // anchor-followers and value-modelers. Slots left empty are filled with $1 players worth ~$1.
  // Position groups for the plan: guard (PG/SG), forward (SF/PF), center. Starting slots are
  // PG,SG,G / SF,PF,F / C / Util, so a roster needs 3 guards, 3 forwards and 1 C, and more than
  // 3 centers is dead weight. $1 fillers can be any position, so they can cover a shortfall.
  const PLAN_RULES = { gMin: 3, fMin: 3, cMin: 1, cMax: 3 };
  function posGroup(pos) {
    const ps = pos || [];
    if (ps.includes('PG') || ps.includes('SG')) return 'g';
    if (ps.includes('SF') || ps.includes('PF')) return 'f';
    if (ps.includes('C')) return 'c';
    return 'x';
  }
  function spendPlan(E, ctx, nCand = 50) {
    const me = ctx.teams[ctx.me], slots = me.open, B = me.budget;
    if (slots <= 0 || B < slots) return null;
    const pm = ctx.pricers[ctx.me];
    const have = { g: 0, f: 0, c: 0 };
    for (const p of me.roster) { const g = posGroup(p.pos); if (g in have) have[g]++; }
    const cand = sortBy(ctx.avail, (p) => -pm.adj(p)).slice(0, nCand).map((p) => ({
      p, grp: posGroup(p.pos), val: pm.adj(p),
      cost: Math.max(1, pyRound((roomPrice(ctx, p) + ctx.market.adj(p)) / 2)) }))
      .filter((c) => c.val > 1 && c.p.games >= (E.DATA.min_gp || 0));   // durable players only (Miles's rule)
    return planKnapsack(cand, slots, B, have);
  }
  // Pick at most S of `cand` ({val, cost, grp}) maximizing total val + $1 per unfilled slot,
  // keeping $1 for every filler, never holding more than cMax centers, and leaving enough
  // fillers to cover any guard/forward/center shortfall.
  function planKnapsack(cand, S, B, have, rules) {
    have = have || { g: 0, f: 0, c: 0 }; rules = rules || PLAN_RULES;
    const G = rules.gMin, F = rules.fMin, CM = rules.cMax, W = B + 1, NEG = -1e18;
    const c0 = have.c;
    const g0 = Math.min(G, have.g), f0 = Math.min(F, have.f);
    const CN = Math.max(CM, c0) + 1;                       // center counts 0..max(cMax, have)
    const stride = [(G + 1) * (F + 1) * CN * W, (F + 1) * CN * W, CN * W, W];
    const at = (j, g, f, c, b) => j * stride[0] + g * stride[1] + f * stride[2] + c * stride[3] + b;
    const dp = new Float64Array((S + 1) * stride[0]).fill(NEG);
    dp[at(0, g0, f0, c0, 0)] = 0;
    const take = [];                                       // per item: 0 no, 1 counter +1, 2 counter at cap
    for (const it of cand) {
      const t = new Uint8Array(dp.length);
      for (let j = S; j >= 1; j--) {
        for (let g = 0; g <= G; g++) for (let f = 0; f <= F; f++) for (let c = 0; c < CN; c++) {
          // where did this state come from if `it` is the j-th buy?
          let pg = g, pf = f, pc = c, mode = 1;
          if (it.grp === 'g') { if (g === G) { mode = 2; } else { pg = g - 1; } }
          else if (it.grp === 'f') { if (f === F) { mode = 2; } else { pf = f - 1; } }
          else if (it.grp === 'c') { if (c > CM) continue; pc = c - 1; }
          if (pg < 0 || pf < 0 || pc < 0) continue;
          const base = at(j, g, f, c, 0), prev = at(j - 1, pg, pf, pc, 0);
          for (let b = B; b >= it.cost; b--) {
            const pv = dp[prev + b - it.cost];
            if (pv <= NEG / 2) continue;
            const v = pv + it.val;
            if (v > dp[base + b] + 1e-9) { dp[base + b] = v; t[base + b] = mode; }
          }
          // a capped guard/forward state can also come from one below the cap
          if (mode === 2) {
            const prev2 = it.grp === 'g' ? at(j - 1, g - 1, f, c, 0) : at(j - 1, g, f - 1, c, 0);
            if ((it.grp === 'g' ? g - 1 : f - 1) >= 0) for (let b = B; b >= it.cost; b--) {
              const pv = dp[prev2 + b - it.cost];
              if (pv <= NEG / 2) continue;
              const v = pv + it.val;
              if (v > dp[base + b] + 1e-9) { dp[base + b] = v; t[base + b] = 1; }
            }
          }
        }
      }
      take.push(t);
    }
    let best = null;
    for (let j = 0; j <= S; j++) {
      const fill = S - j, cap = B - fill;
      for (let g = 0; g <= G; g++) for (let f = 0; f <= F; f++) for (let c = 0; c < CN; c++) {
        const short = (G - g) + (F - f) + Math.max(0, rules.cMin - c);
        if (short > fill) continue;
        for (let b = 0; b <= cap; b++) {
          const v = dp[at(j, g, f, c, b)];
          if (v <= NEG / 2) continue;
          const total = v + fill;
          if (!best || total > best.total + 1e-9) best = { total, j, g, f, c, b };
        }
      }
    }
    if (!best) return null;
    const picks = []; let { j, g, f, c, b } = best;
    for (let i = cand.length - 1; i >= 0 && j > 0; i--) {
      const m = take[i][at(j, g, f, c, b)];
      if (!m) continue;
      const it = cand[i];
      picks.push(it); b -= it.cost; j--;
      if (m === 1) { if (it.grp === 'g') g--; else if (it.grp === 'f') f--; }
      if (it.grp === 'c') c--;
    }
    picks.reverse();
    const spend = fsum(picks.map((x) => x.cost));
    return { picks, spend, fillers: S - picks.length, left: B - spend, value: best.total };
  }

  // ------------------------------------------------------------ state + derive (draft_state.py)
  function create(DATA) {
    const players = DATA.players.map((p, i) => Object.assign({}, p, { key: canon(p.name), rank: i + 1 }));
    const byKey = new Map(players.map((p) => [p.key, p]));
    const idxAll = buildIndex(players, DATA.aliases);
    const order = DATA.room.teams.map((t) => t.id);
    const spots = DATA.active_spots;

    function freshState() {
      const nom = {};
      for (const t of DATA.room.teams) {
        const s = String(t.nomination_order == null ? '' : t.nomination_order).trim();
        if (/^\d+$/.test(s)) nom[parseInt(s, 10)] = t.id;
      }
      const keys = Object.keys(nom).map(Number).sort((a, b) => a - b);
      const teams = {};
      for (const t of DATA.room.teams)
        teams[t.id] = { start: t.remaining, open0: spots - t.keepers.length, keepers: t.keepers };
      return { version: 1, me: DATA.me, room_source: DATA.room.source_file, teams,
               nom_order: keys.length === DATA.room.teams.length ? keys.map((k) => nom[k]) : [],
               picks: [], weights_override: {}, emitted: [], last_k: null };
    }

    function derive(st) {
      const ctx = { st, me: st.me, order, players, byKey, drafted: new Map(), teams: {} };
      for (const tid of order) {
        const t = st.teams[tid], roster = [];
        for (const k of t.keepers) {
          let [p] = resolveName(idxAll, k.name);
          p = p ? byKey.get(canon(p.name)) : null;
          const e = (p && p.kept_by === tid) ? Object.assign({}, p) : { name: k.name, z: null };
          if (k.pos && k.pos.length) e.pos = k.pos;
          e.price = k.cost; e.kept = true;
          roster.push(e);
        }
        ctx.teams[tid] = { id: tid, budget: t.start, open: t.open0, roster };
      }
      for (const e of st.picks) {
        const t = ctx.teams[e.team];
        if (e.type === 'adj') { t.budget += e.delta; t.open += (e.open_delta || 0); continue; }
        t.budget -= e.price; t.open -= 1;
        const p = e.key ? byKey.get(e.key) : null;
        const row = p ? Object.assign({}, p) : { name: e.player, z: null, pos: [] };
        row.price = e.price; t.roster.push(row);
        if (p) ctx.drafted.set(p.key, e);
      }
      for (const tid of order) {
        const t = ctx.teams[tid];
        t.max_bid = t.open > 0 ? t.budget - (t.open - 1) : 0;
      }
      ctx.avail = players.filter((p) => !p.kept_by && !ctx.drafted.has(p.key));
      const nOpen = fsum(order.map((t) => ctx.teams[t].open));
      const top = sortBy(ctx.avail, (p) => -p.fair).slice(0, Math.max(nOpen, 0));
      const denom = fsum(top.map((p) => p.fair)) - nOpen;
      const numer = fsum(order.map((t) => ctx.teams[t].budget)) - nOpen;
      ctx.n_open = nOpen;
      ctx.k_raw = denom > 0.5 ? numer / denom : (numer > 0 ? K_MAX : 1.0);
      ctx.k = Math.max(0.0, Math.min(ctx.k_raw, K_MAX));
      ctx.pricers = {}; ctx.wts = {};
      for (const tid of order) {
        const ov = tid === ctx.me ? st.weights_override : null;
        const w = weights(ctx.teams[tid].roster, DATA.sigma, ov);
        ctx.wts[tid] = w;
        ctx.pricers[tid] = new Pricer(players, w.wn, DATA.rostered, DATA.dpv, ctx.k);
      }
      const ones = {}; for (const c of CATS) ones[c] = 1.0;
      ctx.market = new Pricer(players, ones, DATA.rostered, DATA.dpv, ctx.k);
      ctx.room_k = roomK(ctx);
      return ctx;
    }

    function resolveAvail(ctx, raw) {
      const idx = buildIndex(ctx.avail, DATA.aliases);
      const [p, how] = resolveName(idx, raw);
      if (p) return [p, how];
      let [q] = resolveName(idxAll, raw);
      if (q) {
        q = byKey.get(canon(q.name));
        if (q.kept_by) return [null, `${q.name} is KEPT by ${q.kept_by} (${money(q.keeper_cost)})`];
        const e = ctx.drafted.get(q.key);
        if (e) return [null, `${q.name} already sold to ${e.team} for $${e.price} (#${e.n})`];
      }
      if (how.startsWith('ambiguous')) {
        const rp = nameParts(raw), k = rp.length ? canon(rp[rp.length - 1]) : '';
        const c = ctx.avail.filter((p) => ((nameParts(p.name).slice(-1)[0] || '').toLowerCase() === k)
                                       || canon(p.name).startsWith(canon(raw))).map((p) => p.name);
        return [null, `ambiguous '${raw}': ${c.slice(0, 6).join(', ')} -- add a first initial`];
      }
      const sug = suggest(ctx, raw);
      return [null, `no board player matches '${raw}'` + (sug.length ? ` -- did you mean: ${sug.join(', ')}?`
        : " -- if he's real but unprojected, log with: new <name> <price> <team>")];
    }
    function suggest(ctx, raw, n = 4) {      // bigram similarity; stands in for difflib
      const big = (s) => { const out = []; for (let i = 0; i < s.length - 1; i++) out.push(s.slice(i, i + 2)); return out; };
      const a = big(canon(raw));
      if (!a.length) return [];
      const scored = ctx.avail.map((p) => {
        const b = big(p.key); let hit = 0; const pool = b.slice();
        for (const g of a) { const j = pool.indexOf(g); if (j >= 0) { hit++; pool.splice(j, 1); } }
        return [2 * hit / (a.length + b.length), p.name];
      }).filter((x) => x[0] >= 0.5);
      return sortBy(scored, (x) => -x[0]).slice(0, n).map((x) => x[1]);
    }
    function resolveTeam(ctx, tok) {
      const t = tok.toLowerCase().trim().replace(/!+$/, '');
      if (['me', 'mine', 'my', 'i', 'us'].includes(t)) return ctx.me;
      const m = /^t(\d{1,2})$/.exec(t);
      if (m) {
        const ord = ctx.st.nom_order || [], i = parseInt(m[1], 10);
        if (!ord.length) die("t# needs the nomination order -- sync a page saved after it's set, or use a name prefix (am, theo, hr, me...)");
        if (!(i >= 1 && i <= ord.length)) die(`t${i} out of range 1-${ord.length}`);
        return ord[i - 1];
      }
      const c = canon(t), cands = new Set();
      for (const x of DATA.teams_list) {
        for (const nm of [x.id].concat(x.aliases)) {
          const cn = canon(nm);
          if (cn === c) return x.id;
          if (cn.startsWith(c)) cands.add(x.id);
        }
      }
      if (cands.size === 1) return [...cands][0];
      if (!cands.size) die(`unknown team '${tok}'. ids: ${order.join(', ')}`);
      die(`team '${tok}' is ambiguous: ${[...cands].join(', ')}`);
    }
    function myPrice(ctx, p) {
      const me = ctx.teams[ctx.me], mine = ctx.pricers[ctx.me].adj(p), cap = me.max_bid;
      const mx = Math.max(1, Math.min(pyRound(mine), cap));
      const tgt = Math.max(1, pyRound(mx * (1 - DATA.margin)));
      return { max: mx, target: tgt, mine, market: ctx.market.adj(p), capped: mine > cap };
    }
    return { DATA, players, byKey, order, freshState, derive, resolveAvail, resolveTeam, myPrice,
             suggest, idxAll };
  }

  // ------------------------------------------------------------ output helpers
  function tierOf(adj) {
    for (const [lo, name] of [[55, 'T1'], [38, 'T2'], [26, 'T3'], [16, 'T4'], [9, 'T5'], [4, 'T6'], [2, 'T7']])
      if (adj >= lo) return name;
    return 'T8';
  }
  function catSplit(p, top = 3) {
    if (!p.z) return { good: [], bad: [] };
    const zs = CATS.map((c) => [p.z[c], SHORT[c]]).sort((a, b) => (b[0] - a[0]) || (a[1] < b[1] ? 1 : a[1] > b[1] ? -1 : 0));
    const good = zs.slice(0, top).filter(([v]) => v > 0.25).map(([v, n]) => [n, v]);
    const bad = zs.slice(-top).reverse().filter(([v]) => v < -0.25).map(([v, n]) => [n, v]);
    return { good, bad };
  }

  // ------------------------------------------------------------ alerts (draft_state.alerts)
  function alerts(E, ctx) {
    const out = [], me = ctx.teams[ctx.me], st = ctx.st;
    const n = st.picks.filter((e) => e.type === 'pick').length;
    const lk = st.last_k;
    if (lk !== null && lk !== undefined && Math.abs(ctx.k - lk) >= 0.08 && ctx.k_raw <= K_MAX)
      out.push([`k:${pyFixed(ctx.k, 2)}`, `INFLATION ${pyFixed(lk, 2)} -> ${pyFixed(ctx.k, 2)}: room prices `
        + `${ctx.k > lk ? 'UP' : 'DOWN'} ~${pyFixed(Math.abs(ctx.k / lk - 1) * 100, 0)}% on the surplus`]);
    if (ctx.k_raw > K_MAX)
      out.push([`glut:${floorDiv(n, 10)}`, `CASH GLUT: $${fsum(ctx.order.map((t) => ctx.teams[t].budget))} left `
        + `chasing little value (raw inflation ${pyFixed(ctx.k_raw, 1)}, capped ${K_MAX.toFixed(1)}). Prices now set `
        + 'by who still has cash -- check `teams` ceilings, not MAX']);
    const mk = new Map(ctx.avail.slice(0, 150).map((p) => [p.key, ctx.market.adj(p)]));
    for (const tier of ['T1', 'T2', 'T3', 'T4']) {
      const left = ctx.avail.slice(0, 150).filter((p) => tierOf(mk.get(p.key)) === tier);
      if (left.length >= 1 && left.length <= 2)
        out.push([`cliff:${tier}:${left.length}`, `TIER CLIFF ${tier}: only ${left.length} left -- `
          + left.map((p) => `${p.name} ${money(mk.get(p.key))}`).join(', ')]);
    }
    const last = st.picks.filter((e) => e.type === 'pick').map((e) => (e.key ? E.byKey.get(e.key) : undefined)).slice(-6);
    const pc = new Map();
    for (const p of last) for (const x of ((p || {}).pos || [])) pc.set(x, (pc.get(x) || 0) + 1);
    for (const [pos, c] of pc) {
      if (c >= 3) {
        const left = ctx.avail.filter((p) => p.pos.includes(pos) && (mk.get(p.key) || 0) >= 10);
        out.push([`run:${pos}:${floorDiv(n, 5)}`, `${pos} RUN: ${c} of the last ${last.length} sales. `
          + `${left.length} ${pos}s worth $10+ left`]);
      }
    }
    if (unfilled(me.roster).includes('C') && me.open > 0) {
      const cs = ctx.avail.filter((p) => p.pos.includes('C') && (mk.get(p.key) || 0) >= 8);
      if (cs.length <= 4)
        out.push([`c:${cs.length}`, `C SCARCITY: you have no C and only ${cs.length} Cs worth $8+ remain`]);
    }
    const { d, w } = ctx.wts[ctx.me], thr = E.DATA.punt_threshold;
    for (const c of CATS) {
      if (w[c] < thr && !(c in st.weights_override)) {
        const side = d[c] < 0 ? 'far BEHIND -- punt forming' : 'far AHEAD -- already won';
        out.push([`w:${c}:${d[c] < 0 ? 'lo' : 'hi'}`, `${SHORT[c]} weight ${pyFixed(w[c], 2)}: you're ${side} `
          + `(z ${sgn(d[c], 1)}). Board already discounts it; \`punt ${c.split('_')[0]}\` to pin it`]);
      }
    }
    if (me.open > 0) {
      const avg = roomPerSpot(ctx, ctx.me), mine = me.budget / me.open;
      if (avg > 0 && mine >= 1.4 * avg)
        out.push([`pace:hi:${floorDiv(n, 8)}`, `CASH-HEAVY: $${pyFixed(mine, 1)}/spot vs room $${pyFixed(avg, 1)}. `
          + 'Money is worth nothing after the draft -- buy at MAX, not TARGET']);
      else if (avg > 0 && mine <= 0.65 * avg)
        out.push([`pace:lo:${floorDiv(n, 8)}`, `CASH-LIGHT: $${pyFixed(mine, 1)}/spot vs room $${pyFixed(avg, 1)} -- TARGET prices only`]);
      const pm = ctx.pricers[ctx.me];
      const best = sortBy(ctx.avail, (p) => -pm.adj(p)).slice(0, me.open);
      const absorb = fsum(best.map((p) => pm.adj(p) - 1)), spare = me.budget - me.open;
      if (spare > absorb + 5)
        out.push([`strand:${floorDiv(n, 5)}`, `STRANDED CASH: $${spare} spare but the best ${me.open} `
          + `left are worth only ${money(absorb)} above $1 -- overpay for the best ones now`]);
    }
    const [ceil, who] = rivalCeiling(ctx, ctx.me);
    if (me.open > 0 && who && me.max_bid > ceil) {
      const pm = ctx.pricers[ctx.me];
      const above = ctx.avail.filter((p) => pm.adj(p) > ceil + 1);
      if (above.length)
        out.push([`dom:${ceil}`, `NO RIVAL CAN BID PAST $${ceil} (${who}). You can take `
          + above.slice(0, 3).map((p) => p.name).join(', ') + ` at $${ceil + 1}`]);
    }
    return out;
  }

  // ------------------------------------------------------------ commands
  // exec() returns {ok, kind, lines, state, player?, newAlerts?}. state is a NEW object when
  // the command changed it; the caller persists it.
  function exec(E, st, rawLine, now) {
    let line = (rawLine || '').trim();
    const res = { ok: true, kind: 'info', lines: [], state: st, changed: false };
    try {
      if (!line) return res;
      const force = line.endsWith('!');
      line = line.replace(/!+$/, '').trim();
      const toks = line.split(/\s+/), head = toks[0].toLowerCase();
      if (line.endsWith('?') || head === '?' || head === 'price') {
        let q = line.replace(/\?+$/, '').trim();
        if (head === '?' || head === 'price') q = q.slice(head.length).trim();
        const ctx = E.derive(st);
        const [p, why] = E.resolveAvail(ctx, q);
        if (!p) die(why);
        res.kind = 'price'; res.player = p; res.lines.push(p.name);
        return res;
      }
      const ns = JSON.parse(JSON.stringify(st));
      const ctx0 = E.derive(ns);
      if (head === 'undo') {
        if (!ns.picks.length) die('nothing to undo');
        const e = ns.picks.pop();
        res.kind = 'undo'; res.undone = e;
        res.lines.push(e.type === 'pick' ? `undid #${e.n} ${e.player} $${e.price} -> ${e.team}`
                                         : `undid adj ${e.team} ${e.delta > 0 ? '+' : ''}${e.delta}`);
      } else if (head === 'check') {
        const t = toks.slice(1);
        if (t.length % 2) die('usage: check <team> <budget> [<team> <budget> ...]');
        let bad = 0;
        for (let i = 0; i < t.length; i += 2) {
          const tid = E.resolveTeam(ctx0, t[i]), seen = parseInt(t[i + 1].replace(/^\$/, ''), 10);
          const mine = ctx0.teams[tid].budget;
          if (seen !== mine) { bad++; res.lines.push(`MISMATCH ${tid}: screen $${seen}, tracked $${mine} (diff ${seen - mine > 0 ? '+' : ''}${seen - mine})`); }
        }
        res.lines.push(`checked ${t.length / 2} team(s): ${bad} mismatch(es)` + (bad ? '' : ' -- state agrees'));
        res.kind = 'check'; return res;
      } else if (head === 'adj') {
        const t = toks.slice(1);
        if (t.length !== 2) die('usage: adj <team> <+/-dollars>');
        const tid = E.resolveTeam(ctx0, t[0]), dlt = parseInt(t[1].replace(/^\$/, ''), 10);
        if (!Number.isFinite(dlt)) die(`'${t[1]}' is not a whole number`);
        ns.picks.push({ type: 'adj', team: tid, delta: dlt });
        res.kind = 'adj'; res.lines.push(`${tid} budget adjusted ${dlt > 0 ? '+' : ''}${dlt}`);
      } else if (head === 'punt' || head === 'unpunt') {
        for (const tk of toks.slice(1)) {
          const c = CAT_TOK[tk.toLowerCase()];
          if (!c) die(`unknown category '${tk}' (fg ft 3pm pts reb ast stl blk to)`);
          if (head === 'punt') ns.weights_override[c] = 0.0; else delete ns.weights_override[c];
        }
        res.kind = 'punt';
        const pins = Object.keys(ns.weights_override);
        res.lines.push('pinned weights: ' + (pins.length ? pins.map((c) => `${SHORT[c]}=0`).join(', ') : 'none'));
      } else if (head === 'order') {
        const ids = toks.slice(1).map((t) => E.resolveTeam(ctx0, t));
        if (ids.length !== E.order.length || new Set(ids).size !== ids.length)
          die(`order needs all ${E.order.length} teams once each, in nomination order`);
        ns.nom_order = ids; res.kind = 'order';
        res.lines.push('nomination order: ' + ids.map((x, i) => `t${i + 1}=${x}`).join(' '));
      } else if (['board', 'me', 'teams', 'nom', 'status', 'alerts', 'log'].includes(head)) {
        res.kind = head === 'alerts' ? 'status' : head; return res;
      } else {
        const isNew = head === 'new';
        const pt = isNew ? toks.slice(1) : toks;
        if (pt.length < 3) die('usage: <player> <price> <team>   (or: <player>? to price him)');
        const team = E.resolveTeam(ctx0, pt[pt.length - 1]);
        const ptok = pt[pt.length - 2].replace(/^\$/, '');
        if (!/^[+-]?\d+$/.test(ptok)) die(`price '${pt[pt.length - 2]}' is not a whole number`);
        const price = parseInt(ptok, 10), raw = pt.slice(0, -2).join(' ');
        const t = ctx0.teams[team];
        if (t.open <= 0 && !force) die(`${team} has no open spots -- wrong team? (add ! to force)`);
        if (price < 1) die('price must be >= $1');
        if (price > t.max_bid && !force)
          die(`${team} can bid at most $${t.max_bid} ($${t.budget} left, ${t.open} open) -- typo? (add ! to force)`);
        let entry;
        if (isNew) entry = { player: raw, key: null, how: 'new' };
        else {
          let [p, how] = E.resolveAvail(ctx0, raw);
          if (!p) {
            if (force && how.includes('KEPT')) {
              const [q] = resolveName(E.idxAll, raw); p = E.byKey.get(canon(q.name)); how = 'forced-over-keeper';
            } else die(how);
          }
          entry = { player: p.name, key: p.key, how };
        }
        const n = ns.picks.filter((e) => e.type === 'pick').length + 1;
        Object.assign(entry, { type: 'pick', n, price, team, t: now || new Date().toISOString().slice(0, 19) });
        if (entry.how === 'forced-over-keeper')
          for (const tm of Object.values(ns.teams)) tm.keepers = tm.keepers.filter((k) => canon(k.name) !== entry.key);
        ns.picks.push(entry);
        const ctx = E.derive(ns);
        // emit_new: alerts not seen before, then remember them
        const seen = new Set(ns.emitted), fresh = alerts(E, ctx).filter(([k]) => !seen.has(k));
        ns.emitted = [...new Set([...ns.emitted, ...fresh.map(([k]) => k)])];
        if (ns.last_k === null || ns.last_k === undefined || fresh.some(([k]) => k.startsWith('k:'))) ns.last_k = ctx.k;
        const tm = ctx.teams[team], p = entry.key ? E.byKey.get(entry.key) : null;
        let verdict = '';
        if (p) { const m = ctx.market.adj(p); verdict = ` (market ${money(m)}, ${price >= m ? '+' : '-'}${money(Math.abs(price - m))})`; }
        res.kind = 'pick'; res.entry = entry; res.player = p; res.oldK = ctx0.k; res.newK = ctx.k;
        res.lines.push(`#${n} ${entry.player} $${price} -> ${team}${verdict}`
          + (['exact', 'new'].includes(entry.how) ? '' : ` [matched via ${entry.how}]`));
        res.lines.push(`${team}: $${tm.budget} left, ${tm.open} open, max bid $${tm.max_bid}`);
        if (tm.budget < tm.open || tm.open < 0)
          res.lines.push(`TRACKING ERROR: Yahoo makes this impossible (${team} now $${tm.budget} for ${tm.open} open). A sale is missing or mistyped -- check the log`);
        res.newAlerts = fresh;
      }
      res.state = ns; res.changed = true;
      return res;
    } catch (err) {
      if (err instanceof CmdError) return { ok: false, kind: 'error', lines: [err.message], state: st, changed: false };
      throw err;
    }
  }

  return { create, exec, alerts, nominations, roomPrice, roomNominations, spendPlan, planKnapsack, threats, foldRisk, rivalCeiling, roomPerSpot, unfilled,
           weights, tierOf, catSplit, canon, nameParts, pyRound, pyFixed, sgn, money,
           CATS, SHORT, K_MAX, sortBy };
});
