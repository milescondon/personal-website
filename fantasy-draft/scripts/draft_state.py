#!/usr/bin/env python3
"""Live auction state: log picks, track every budget, price players under the CURRENT room.

Pass the raw shorthand line straight through -- one call per action:

  draft_state.py jokic 71 t4        log a sale: <player> <price> <team>   (team: t# | prefix | me)
  draft_state.py giannis?           price him now: MAX / TARGET / who can outbid you
  draft_state.py undo               remove the last logged sale
  draft_state.py board [n]          best available under your weights (default 15)
  draft_state.py me                 your roster, cash, category profile, punts
  draft_state.py teams              every rival's budget, open spots, exact max bid
  draft_state.py nom                nomination ideas: push / drain / hold / steal
  draft_state.py status             summary + every live alert
  draft_state.py sync <page.html>   compare (pre-draft: reload) a saved Yahoo Draft Results page
  draft_state.py check am 52 theo 180 ...   compare budgets read off a screenshot (never overwrites)
  draft_state.py new <name> <price> <team>  log a player who isn't on the board (keeps budgets exact)
  draft_state.py adj <team> <+/-$>  budget-only correction
  draft_state.py punt ft | unpunt ft          pin / release a category weight
  draft_state.py log                every logged sale

Truth model: budgets are DERIVED from the Yahoo room's starting numbers minus every logged
price, so they are exact as long as every sale is logged. Screenshots and page saves are
cross-checks only -- they report differences and never silently overwrite state.
"""
import sys, os, re, json, math, difflib, datetime, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import valuation as V
import opponents as O

STATE_DIR = os.environ.get('DRAFT_STATE_DIR') or os.path.join(ROOT, 'state')   # override for tests
STATE = os.path.join(STATE_DIR, 'draft.json')
JOURNAL = os.path.join(STATE_DIR, 'journal.txt')
K_MAX = 3.0
CAT_TOK = {'fg': 'fg_pct', 'fg%': 'fg_pct', 'ft': 'ft_pct', 'ft%': 'ft_pct', '3': 'tpm', '3pm': 'tpm',
           '3pt': 'tpm', 'tpm': 'tpm', 'pts': 'pts', 'reb': 'reb', 'ast': 'ast', 'stl': 'stl',
           'st': 'stl', 'blk': 'blk', 'to': 'to'}

def die(msg):
    print(msg); sys.exit(1)

# ---------------------------------------------------------------- load / save
def load_json(p):
    return json.load(open(p, encoding='utf-8'))

def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(STATE), suffix='.tmp')
    with os.fdopen(fd, 'w', encoding='utf-8') as f: json.dump(st, f, indent=1, ensure_ascii=False)
    os.replace(tmp, STATE)

def journal(line):
    os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
    with open(JOURNAL, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {line}\n")

def fresh_state(cfg, room):
    spots = cfg['roster']['active_spots']
    nom = {}
    for t in room['teams']:
        if str(t.get('nomination_order', '')).strip().isdigit(): nom[int(t['nomination_order'])] = t['id']
    return {'version': 1, 'me': cfg['me'], 'room_source': room.get('source_file'),
            'teams': {t['id']: {'start': t['remaining'], 'open0': spots - len(t['keepers']),
                                'keepers': t['keepers']} for t in room['teams']},
            'nom_order': [nom[k] for k in sorted(nom)] if len(nom) == len(room['teams']) else [],
            'picks': [], 'weights_override': {}, 'emitted': [], 'last_k': None}

class Ctx:
    def __init__(self):
        self.cfg = load_json(os.path.join(ROOT, 'league.json'))
        self.board = load_json(os.path.join(ROOT, 'build', 'value_board.json'))
        self.room = load_json(os.path.join(ROOT, self.cfg['keepers']['room_file']))
        if os.path.exists(STATE): self.st = load_json(STATE)
        else:
            self.st = fresh_state(self.cfg, self.room); save_state(self.st)
        bp = self.board['params']
        if bp.get('keeper_source') != self.cfg['keepers'].get('source_of_truth'):
            die("board was built from a different keeper source -- run build_board.py first")
        self.me = self.st['me']
        self.rostered = bp['rostered']; self.dpv = bp['dollars_per_vorp']
        self.margin = bp['target_margin']; self.sigma = self.board['sigma_match']
        self.players = self.board['players']
        for i, p in enumerate(self.players):
            p['key'] = V.canon(p['name']); p['rank'] = i + 1
        self.by_key = {p['key']: p for p in self.players}
        self.aliases = load_json(os.path.join(ROOT, 'data', 'player_aliases.json'))
        self.names = {t['id']: t['aliases'][0] for t in self.cfg['teams_list']}
        self.derive()

    def derive(self):
        st = self.st
        self.drafted = {}
        teams = {}
        for tid, t in st['teams'].items():
            roster = []
            for k in t['keepers']:
                # only trust the match the board itself made for this team's keeper
                p, _ = V.resolve_name(self.idx_all(), k['name'])
                p = self.by_key.get(V.canon(p['name'])) if p else None
                e = dict(p) if p and p['kept_by'] == tid else {'name': k['name'], 'z': None}
                if k.get('pos'): e['pos'] = k['pos']        # Yahoo multi-position beats BBM's single
                e['price'] = k['cost']; e['kept'] = True
                roster.append(e)
            teams[tid] = {'id': tid, 'budget': t['start'], 'open': t['open0'], 'roster': roster}
        for e in st['picks']:
            t = teams[e['team']]
            if e['type'] == 'adj':
                t['budget'] += e['delta']; t['open'] += e.get('open_delta', 0); continue
            t['budget'] -= e['price']; t['open'] -= 1
            p = self.by_key.get(e.get('key'))
            row = dict(p) if p else {'name': e['player'], 'z': None, 'pos': []}
            row['price'] = e['price']; t['roster'].append(row)
            if p: self.drafted[p['key']] = e
        for t in teams.values():
            t['max_bid'] = t['budget'] - (t['open'] - 1) if t['open'] > 0 else 0
        self.teams = teams
        self.avail = [p for p in self.players if not p['kept_by'] and p['key'] not in self.drafted]
        # live inflation: remaining money above $1/slot over remaining value above $1/slot
        n_open = sum(t['open'] for t in teams.values())
        top = sorted(self.avail, key=lambda p: -p['fair'])[:n_open]
        denom = sum(p['fair'] for p in top) - n_open
        numer = sum(t['budget'] for t in teams.values()) - n_open
        self.n_open = n_open
        # Late in a draft money can dwarf the value left and the ratio explodes (a $5 player
        # "worth" $24). Past K_MAX prices are set by who still has cash, not by value, so
        # cap it and say so (the CASH GLUT alert) rather than print absurd MAXes.
        self.k_raw = numer / denom if denom > 0.5 else (K_MAX if numer > 0 else 1.0)
        self.k = max(0.0, min(self.k_raw, K_MAX))
        # category weights and pricers for every team
        self.pricers, self.wts = {}, {}
        for tid, t in teams.items():
            ov = st['weights_override'] if tid == self.me else None
            d, w, wn = O.weights(t['roster'], self.sigma, ov)
            self.wts[tid] = (d, w, wn)
            self.pricers[tid] = O.Pricer(self.players, wn, self.rostered, self.dpv, self.k)
        self.market = O.Pricer(self.players, {c: 1.0 for c in O.CATS}, self.rostered, self.dpv, self.k)

    _idx_all = None
    def idx_all(self):
        if self._idx_all is None:
            ps = [dict(p, key=V.canon(p['name'])) for p in self.board['players']]
            self._idx_all = V.build_index(ps, self.aliases)
        return self._idx_all

    def resolve_avail(self, raw):
        idx = V.build_index(self.avail, self.aliases)
        p, how = V.resolve_name(idx, raw)
        if p: return p, how
        q, how2 = V.resolve_name(self.idx_all(), raw)
        if q:
            q = self.by_key[V.canon(q['name'])]
            if q['kept_by']: return None, f"{q['name']} is KEPT by {q['kept_by']} (${q['keeper_cost']:.0f})"
            e = self.drafted.get(q['key'])
            if e: return None, f"{q['name']} already sold to {e['team']} for ${e['price']} (#{e['n']})"
        if how.startswith('ambiguous'):
            rp = V.name_parts(raw); k = V.canon(rp[-1]) if rp else ''
            c = [p['name'] for p in self.avail if (V.name_parts(p['name']) or [''])[-1].lower() == k
                 or V.canon(p['name']).startswith(V.canon(raw))]
            return None, f"ambiguous '{raw}': {', '.join(c[:6])} -- add a first initial"
        close = difflib.get_close_matches(V.canon(raw), [p['key'] for p in self.avail], n=4, cutoff=0.6)
        sug = ', '.join(self.by_key[k]['name'] for k in close)
        return None, f"no board player matches '{raw}'" + (f" -- did you mean: {sug}?" if sug else
               " -- if he's real but unprojected, log with: new <name> <price> <team>")

    def resolve_team(self, tok):
        t = tok.lower().strip().rstrip('!')
        if t in ('me', 'mine', 'my', 'i', 'us'): return self.me
        m = re.fullmatch(r't(\d{1,2})', t)
        if m:
            order = self.st.get('nom_order') or []
            i = int(m.group(1))
            if not order: die("t# needs the nomination order -- sync a page saved after it's set, "
                              "or use a name prefix (am, theo, hr, me...)")
            if not 1 <= i <= len(order): die(f"t{i} out of range 1-{len(order)}")
            return order[i - 1]
        c = V.canon(t)
        cands = {}
        for x in self.cfg['teams_list']:
            for n in [x['id']] + x['aliases']:
                cn = V.canon(n)
                if cn == c: return x['id']
                if cn.startswith(c): cands[x['id']] = 1
        if len(cands) == 1: return next(iter(cands))
        if not cands: die(f"unknown team '{tok}'. ids: {', '.join(self.st['teams'])}")
        die(f"team '{tok}' is ambiguous: {', '.join(cands)}")

    # ---- pricing
    def my_price(self, p):
        me = self.teams[self.me]
        mine = self.pricers[self.me].adj(p)
        cap = me['max_bid']
        mx = max(1, min(round(mine), cap))
        tgt = max(1, round(mx * (1 - self.margin)))
        return mx, tgt, mine, self.market.adj(p), mine > cap

# ---------------------------------------------------------------- output helpers
def money(x): return f"${x:.0f}"

def cat_line(p, top=3):
    if not p.get('z'): return ''
    zs = sorted(((p['z'][c], O.SHORT[c]) for c in O.CATS), reverse=True)
    good = ' '.join(f"{n} {v:+.1f}" for v, n in zs[:top] if v > 0.25)
    bad = ' '.join(f"{n} {v:+.1f}" for v, n in reversed(zs[-top:]) if v < -0.25)
    return f"helps: {good or '-'} | hurts: {bad or '-'}"

def tier_of(adj):
    for lo, name in [(55, 'T1'), (38, 'T2'), (26, 'T3'), (16, 'T4'), (9, 'T5'), (4, 'T6'), (2, 'T7')]:
        if adj >= lo: return name
    return 'T8'

# ---------------------------------------------------------------- alerts
def alerts(ctx):
    """-> list of (key, message). Keys let `pick` print each alert once."""
    out = []
    me = ctx.teams[ctx.me]; st = ctx.st
    n = len([e for e in st['picks'] if e['type'] == 'pick'])
    # live-inflation swing
    lk = st.get('last_k')
    if lk is not None and abs(ctx.k - lk) >= 0.08 and ctx.k_raw <= K_MAX:
        out.append((f"k:{ctx.k:.2f}", f"INFLATION {lk:.2f} -> {ctx.k:.2f}: room prices "
                    f"{'UP' if ctx.k > lk else 'DOWN'} ~{abs(ctx.k / lk - 1) * 100:.0f}% on the surplus"))
    if ctx.k_raw > K_MAX:
        out.append((f"glut:{n // 10}", f"CASH GLUT: ${sum(t['budget'] for t in ctx.teams.values())} left "
                    f"chasing little value (raw inflation {ctx.k_raw:.1f}, capped {K_MAX}). Prices now set "
                    f"by who still has cash -- check `teams` ceilings, not MAX"))
    # tier cliffs (market tiers T1-T4)
    mk = {p['key']: ctx.market.adj(p) for p in ctx.avail[:150]}
    for tier in ('T1', 'T2', 'T3', 'T4'):
        left = [p for p in ctx.avail[:150] if tier_of(mk[p['key']]) == tier]
        if 1 <= len(left) <= 2:
            out.append((f"cliff:{tier}:{len(left)}", f"TIER CLIFF {tier}: only {len(left)} left -- "
                        + ', '.join(f"{p['name']} {money(mk[p['key']])}" for p in left)))
    # positional run (last 6 sales)
    last = [ctx.by_key.get(e.get('key')) for e in st['picks'] if e['type'] == 'pick'][-6:]
    pc = {}
    for p in last:
        for x in (p or {}).get('pos', []): pc[x] = pc.get(x, 0) + 1
    for pos, c in pc.items():
        if c >= 3:
            left = [p for p in ctx.avail if pos in p['pos'] and mk.get(p['key'], 0) >= 10]
            out.append((f"run:{pos}:{n // 5}", f"{pos} RUN: {c} of the last {len(last)} sales. "
                        f"{len(left)} {pos}s worth $10+ left"))
    # positional scarcity for me: C is the one real constraint (1 C slot)
    if 'C' in O.unfilled(me['roster']) and me['open'] > 0:
        cs = [p for p in ctx.avail if 'C' in p['pos'] and mk.get(p['key'], 0) >= 8]
        if len(cs) <= 4:
            out.append((f"c:{len(cs)}", f"C SCARCITY: you have no C and only {len(cs)} Cs worth $8+ remain"))
    # punts forming
    d, w, wn = ctx.wts[ctx.me]
    thr = ctx.cfg['tuning']['punt_weight_threshold']
    for c in O.CATS:
        if w[c] < thr and c not in st['weights_override']:
            side = 'far BEHIND -- punt forming' if d[c] < 0 else 'far AHEAD -- already won'
            out.append((f"w:{c}:{'lo' if d[c] < 0 else 'hi'}", f"{O.SHORT[c]} weight {w[c]:.2f}: you're {side} "
                        f"(z {d[c]:+.1f}). Board already discounts it; `punt {c.split('_')[0]}` to pin it"))
    # budget pace
    if me['open'] > 0:
        avg = O.room_per_spot(ctx.teams, ctx.me)
        mine = me['budget'] / me['open']
        if avg > 0 and mine >= 1.4 * avg:
            out.append((f"pace:hi:{n // 8}", f"CASH-HEAVY: ${mine:.1f}/spot vs room ${avg:.1f}. "
                        f"Money is worth nothing after the draft -- buy at MAX, not TARGET"))
        elif avg > 0 and mine <= 0.65 * avg:
            out.append((f"pace:lo:{n // 8}", f"CASH-LIGHT: ${mine:.1f}/spot vs room ${avg:.1f} -- TARGET prices only"))
        # stranded cash: even the best `open` players can't absorb your surplus
        best = sorted(ctx.avail, key=lambda p: -ctx.pricers[ctx.me].adj(p))[:me['open']]
        absorb = sum(ctx.pricers[ctx.me].adj(p) - 1 for p in best)
        spare = me['budget'] - me['open']
        if spare > absorb + 5:
            out.append((f"strand:{n // 5}", f"STRANDED CASH: ${spare:.0f} spare but the best {me['open']} "
                        f"left are worth only ${absorb:.0f} above $1 -- overpay for the best ones now"))
    # nobody can outbid you
    # nobody can outbid you -- only worth saying once someone you want is worth more than that
    ceil, who = O.rival_ceiling(ctx.teams, ctx.me)
    if me['open'] > 0 and who and me['max_bid'] > ceil:
        mine = ctx.pricers[ctx.me]
        above = [p for p in ctx.avail if mine.adj(p) > ceil + 1]
        if above:
            out.append((f"dom:{ceil}", f"NO RIVAL CAN BID PAST ${ceil} ({who}). You can take "
                        + ', '.join(p['name'] for p in above[:3]) + f" at ${ceil + 1}"))
    return out

def emit_new(ctx):
    seen = set(ctx.st['emitted'])
    new = [(k, m) for k, m in alerts(ctx) if k not in seen]
    for k, m in new: print(f"  ! {m}")
    ctx.st['emitted'] = list(seen | {k for k, _ in new})
    if ctx.st.get('last_k') is None or any(k.startswith('k:') for k, _ in new):
        ctx.st['last_k'] = ctx.k

# ---------------------------------------------------------------- commands
def cmd_price(ctx, raw):
    p, why = ctx.resolve_avail(raw)
    if not p: die(why)
    mx, tgt, mine, mkt, capped = ctx.my_price(p)
    me = ctx.teams[ctx.me]
    print(f"{p['name']}  {'/'.join(p['pos'])} {p['nba']}  {p['games']:.0f}gp  {tier_of(mkt)}  (BBM #{p['bbm_rank']:.0f})")
    note = ' (capped by $1/slot reserve)' if capped else ''
    diff = f" -- fits your cats +${mine - mkt:.0f}" if mine - mkt >= 2 else (
           f" -- your cats need him less, -${mkt - mine:.0f}" if mkt - mine >= 2 else '')
    print(f"MAX {money(mx)}  TARGET {money(tgt)}{note}   market {money(mkt)}{diff}")
    print(cat_line(p))
    ceil, who = O.rival_ceiling(ctx.teams, ctx.me)
    th = O.threats(p, mx, ctx.teams, ctx.me, ctx.pricers)
    print(f"you: {money(me['budget'])} / {me['open']} open, max bid {money(me['max_bid'])}"
          f"  | rival ceiling {money(ceil)} {who or ''}")
    if not th:
        print(f"SAFE: no rival can bid past ${mx} -- you win at MAX or less")
    else:
        fr = O.fold_risk(th, mx)
        if fr:
            print("FOLD RISK: " + '; '.join(f"{r['id']} values him {money(r['val'])}"
                  f"{' + NEEDS ' + '/'.join(p['pos']) if r['need'] else ''}, ${r['per_spot']:.0f}/spot"
                  for r in fr[:3]) + " -- likely goes past your MAX; don't chase")
        else:
            keen = [r for r in th if r['val'] >= mx + 2]
            print(f"{len(th)} rival(s) can go past ${mx}; "
                  + ('keen but cash-short: ' + ', '.join(f"{r['id']} {money(r['val'])} "
                     f"(${r['per_spot']:.0f}/spot)" for r in keen[:3]) if keen else
                     'none values him above your MAX'))

def cmd_pick(ctx, toks, force=False, new=False):
    if len(toks) < 3: die("usage: <player> <price> <team>")
    team = ctx.resolve_team(toks[-1])
    try: price = int(toks[-2].lstrip('$'))
    except ValueError: die(f"price '{toks[-2]}' is not a whole number")
    raw = ' '.join(toks[:-2])
    t = ctx.teams[team]
    if t['open'] <= 0 and not force: die(f"{team} has no open spots -- wrong team? (add ! to force)")
    if price < 1: die("price must be >= $1")
    if price > t['max_bid'] and not force:
        die(f"{team} can bid at most ${t['max_bid']} (${t['budget']} left, {t['open']} open) -- typo? (add ! to force)")
    if new:
        entry = {'player': raw, 'key': None, 'how': 'new'}
    else:
        p, how = ctx.resolve_avail(raw)
        if not p:
            if force and ('KEPT' in how):
                q, _ = V.resolve_name(ctx.idx_all(), raw); p = ctx.by_key[V.canon(q['name'])]
                p['kept_by'] = None; how = 'forced-over-keeper'
            else: die(how)
        entry = {'player': p['name'], 'key': p['key'], 'how': how}
    n = len([e for e in ctx.st['picks'] if e['type'] == 'pick']) + 1
    entry.update({'type': 'pick', 'n': n, 'price': price, 'team': team,
                  't': datetime.datetime.now().isoformat(timespec='seconds')})
    if entry['how'] == 'forced-over-keeper':
        for tm in ctx.st['teams'].values():
            tm['keepers'] = [k for k in tm['keepers'] if V.canon(k['name']) != entry['key']]
    ctx.st['picks'].append(entry); journal(f"PICK {json.dumps(entry, ensure_ascii=False)}")
    old_k = ctx.k
    ctx.derive()
    t = ctx.teams[team]
    p = ctx.by_key.get(entry['key'])
    verdict = ''
    if p:
        mkt = ctx.market.adj(p)
        verdict = f" (market {money(mkt)}, {'+' if price >= mkt else '-'}${abs(price - mkt):.0f})"
    flag = '' if entry['how'] in ('exact', 'new') else f" [matched via {entry['how']}]"
    print(f"#{n} {entry['player']} ${price} -> {team}{verdict}{flag}")
    print(f"   {team}: ${t['budget']} left, {t['open']} open, max bid ${t['max_bid']}"
          f" | inflation {old_k:.3f} -> {ctx.k:.3f}")
    if t['budget'] < t['open'] or t['open'] < 0:
        print(f"  !! TRACKING ERROR: Yahoo makes this impossible ({team} now ${t['budget']} for "
              f"{t['open']} open). A sale is missing or mistyped -- `log`, then `check` against the room")
    emit_new(ctx); save_state(ctx.st)

def cmd_undo(ctx):
    if not ctx.st['picks']: die("nothing to undo")
    e = ctx.st['picks'].pop(); journal(f"UNDO {json.dumps(e, ensure_ascii=False)}")
    save_state(ctx.st); ctx.derive()
    if e['type'] == 'pick': print(f"undid #{e['n']} {e['player']} ${e['price']} -> {e['team']}")
    else: print(f"undid adj {e['team']} {e['delta']:+d}")
    t = ctx.teams[e['team']]
    print(f"   {e['team']}: ${t['budget']} left, {t['open']} open | inflation {ctx.k:.3f}")

def cmd_board(ctx, n=15):
    me = ctx.pricers[ctx.me]
    rows = sorted(ctx.avail, key=lambda p: -me.adj(p))[:n]
    print(f"inflation {ctx.k:.3f} | {ctx.n_open} spots open | you {money(ctx.teams[ctx.me]['budget'])}"
          f" / {ctx.teams[ctx.me]['open']} open")
    print(f"{'player':24s} {'pos':4s} {'MAX':>4s} {'TGT':>4s} {'mkt':>4s} {'gp':>3s}")
    for p in rows:
        mx, tgt, mine, mkt, _ = ctx.my_price(p)
        print(f"{p['name'][:24]:24s} {'/'.join(p['pos'])[:4]:4s} {mx:>4d} {tgt:>4d} {mkt:>4.0f} {p['games']:>3.0f}")

def cmd_me(ctx):
    me = ctx.teams[ctx.me]
    avg = O.room_per_spot(ctx.teams, ctx.me)
    print(f"{ctx.names.get(ctx.me, ctx.me)} ({ctx.me}): {money(me['budget'])} left, {me['open']} open, "
          f"max bid {money(me['max_bid'])}, ${me['budget'] / max(me['open'], 1):.1f}/spot (rivals ${avg:.1f})")
    for p in me['roster']:
        tag = 'K' if p.get('kept') else ' '
        print(f"  {tag} {p['name'][:24]:24s} {'/'.join(p.get('pos') or [])[:8]:8s} ${p['price']:.0f}")
    d, w, wn = ctx.wts[ctx.me]
    print("cat    z-sum  weight")
    for c in O.CATS:
        pin = ' (pinned)' if c in ctx.st['weights_override'] else ''
        print(f"  {O.SHORT[c]:4s} {d[c]:+6.1f}  {w[c]:.2f}{pin}")
    thr = ctx.cfg['tuning']['punt_weight_threshold']
    lo = [O.SHORT[c] for c in O.CATS if w[c] < thr and d[c] < 0]
    print(f"punting: {', '.join(lo) if lo else 'nothing yet (all weights >= %.1f or ahead)' % thr}")
    miss = O.unfilled(me['roster'])
    print(f"positions unfilled: {', '.join(miss) or 'none'}")

def cmd_teams(ctx):
    avg = O.room_per_spot(ctx.teams)
    print(f"{'team':13s} {'left':>5s} {'open':>4s} {'max':>4s} {'$/spot':>6s}  unfilled   room avg ${avg:.1f}/spot")
    order = ctx.st.get('nom_order') or []
    for t in sorted(ctx.teams.values(), key=lambda t: -t['max_bid']):
        tn = f"t{order.index(t['id']) + 1}" if t['id'] in order else ''
        mark = ' <- you' if t['id'] == ctx.me else ''
        ps = t['budget'] / t['open'] if t['open'] else 0
        print(f"{t['id']:13s} {t['budget']:>5d} {t['open']:>4d} {t['max_bid']:>4d} {ps:>6.1f}  "
              f"{','.join(O.unfilled(t['roster'])) or '-':10s} {tn}{mark}")

def cmd_nom(ctx):
    push, drain, hold, steal = O.nominations(
        sorted(ctx.avail, key=lambda p: -ctx.market.adj(p)), ctx.teams, ctx.me,
        ctx.pricers[ctx.me], ctx.market.adj, ctx.pricers)
    if steal:
        print("STEAL (no rival can outbid you -- nominate and take him):")
        for _, p, ceil in steal[:3]: print(f"  {p['name']} -- rivals capped at ${ceil}")
    if push:
        print("PUSH (you value him below market, 2+ rivals want him -- drains their cash):")
        for _, p, m, mine, who in push[:3]:
            print(f"  {p['name']}  market {money(m)} vs you {money(mine)}  wanted by {', '.join(who[:4])}")
    if drain and not push:
        print("DRAIN (pricey, you're fine losing him at market):")
        for _, p, m, mine, who in drain[:3]:
            print(f"  {p['name']}  market {money(m)}  {len(who)} rivals can afford")
    if hold:
        print("HOLD (your bargains -- don't nominate while rivals are flush):")
        for _, p, m, mine in hold[:3]: print(f"  {p['name']}  you {money(mine)} vs market {money(m)}")
    if not (steal or push or drain or hold): print("no strong nomination signal -- nominate a $1-3 player you'd take")

def cmd_status(ctx):
    n = len([e for e in ctx.st['picks'] if e['type'] == 'pick'])
    me = ctx.teams[ctx.me]
    print(f"{n} sold, {ctx.n_open} spots open, inflation {ctx.k:.3f} | you {money(me['budget'])}/"
          f"{me['open']} open, max bid {money(me['max_bid'])}")
    al = alerts(ctx)
    for _, m in al: print(f"  ! {m}")
    if not al: print("  no alerts")

def cmd_log(ctx):
    for e in ctx.st['picks']:
        if e['type'] == 'pick': print(f"#{e['n']:<3d} {e['player'][:24]:24s} ${e['price']:<3d} {e['team']}")
        else: print(f"adj  {e['team']} {e['delta']:+d}")

def cmd_check(ctx, toks):
    if len(toks) % 2: die("usage: check <team> <budget> [<team> <budget> ...]")
    bad = 0
    for i in range(0, len(toks), 2):
        tid = ctx.resolve_team(toks[i]); seen = int(toks[i + 1].lstrip('$'))
        mine = ctx.teams[tid]['budget']
        if seen != mine:
            bad += 1
            print(f"MISMATCH {tid}: screen ${seen}, tracked ${mine} (diff {seen - mine:+d}) -- "
                  f"find the missed/mistyped sale; `log` lists them")
    print(f"checked {len(toks) // 2} team(s): {bad} mismatch(es)" + ('' if bad else ' -- state agrees'))

def cmd_adj(ctx, toks):
    if len(toks) != 2: die("usage: adj <team> <+/-dollars>")
    tid = ctx.resolve_team(toks[0]); d = int(toks[1].lstrip('$'))
    e = {'type': 'adj', 'team': tid, 'delta': d}
    ctx.st['picks'].append(e); journal(f"ADJ {json.dumps(e)}"); save_state(ctx.st); ctx.derive()
    print(f"{tid} budget adjusted {d:+d} -> ${ctx.teams[tid]['budget']}")

def cmd_punt(ctx, toks, on=True):
    for tk in toks:
        c = CAT_TOK.get(tk.lower())
        if not c: die(f"unknown category '{tk}' (fg ft 3pm pts reb ast stl blk to)")
        if on: ctx.st['weights_override'][c] = 0.0
        else: ctx.st['weights_override'].pop(c, None)
    save_state(ctx.st); ctx.derive()
    print("pinned weights: " + (', '.join(f"{O.SHORT[c]}=0" for c in ctx.st['weights_override']) or 'none'))

def cmd_sync(ctx, path):
    import yahoo_sync as Y
    try:
        teams, errors = Y.parse(open(path, encoding='utf-8', errors='replace').read(), ctx.cfg)
    except SystemExit as e:
        die(f"sync failed: {e}")
    picks = [e for e in ctx.st['picks'] if e['type'] == 'pick']
    order = {int(t['nomination_order']): t['id'] for t in teams
             if str(t['nomination_order']).strip().isdigit()}
    if len(order) == len(teams):
        ctx.st['nom_order'] = [order[k] for k in sorted(order)]
        print("nomination order: " + ' '.join(f"t{i + 1}={x}" for i, x in enumerate(ctx.st['nom_order'])))
    if not picks:
        old = {t['id']: (t['remaining'], sorted(k['name'] for k in t['keepers'])) for t in ctx.room['teams']}
        new = {t['id']: (t['remaining'], sorted(k['name'] for k in t['keepers'])) for t in teams}
        if errors: die("page failed its checks, nothing changed:\n  " + '\n  '.join(errors))
        if old != new:
            print("pre-draft: keepers/budgets CHANGED on Yahoo:")
            for tid in new:
                if old.get(tid) != new[tid]: print(f"  {tid}: {old.get(tid)} -> {new[tid]}")
            print("run:  python3 -I fantasy-draft/scripts/yahoo_sync.py <page> && "
                  "python3 -I fantasy-draft/scripts/build_board.py fantasy-draft && "
                  "python3 -I fantasy-draft/scripts/draft_state.py init --force")
        else:
            print("pre-draft: Yahoo keepers and budgets match the board -- nothing to rebuild")
        save_state(ctx.st); return
    bad = 0
    for t in teams:
        if t['remaining'] is None: continue
        mine = ctx.teams[t['id']]['budget']
        if t['remaining'] != mine:
            bad += 1; print(f"MISMATCH {t['id']}: Yahoo ${t['remaining']}, tracked ${mine} ({t['remaining'] - mine:+d})")
    print(f"mid-draft sync: {bad} budget mismatch(es) over {len(teams)} teams" + ('' if bad else ' -- state agrees'))
    save_state(ctx.st)

def main(argv):
    line = ' '.join(argv).strip()
    if not line or line in ('help', '-h', '--help'): print(__doc__); return
    if line.startswith('init'):
        if os.path.exists(STATE) and '--force' not in line:
            die("state exists; `init --force` discards every logged sale (journal.txt keeps a record)")
        cfg = load_json(os.path.join(ROOT, 'league.json'))
        room = load_json(os.path.join(ROOT, cfg['keepers']['room_file']))
        if os.path.exists(STATE): journal("INIT --force (previous state discarded)")
        save_state(fresh_state(cfg, room)); print("fresh draft state from the Yahoo room")
        Ctx(); return
    ctx = Ctx()
    force = line.endswith('!')
    line = line.rstrip('!').strip()
    toks = line.split()
    head = toks[0].lower()
    if line.endswith('?') or head in ('?', 'price'):
        q = line.rstrip('?').strip()
        q = q[len(head):].strip() if head in ('?', 'price') else q
        return cmd_price(ctx, q)
    if head == 'undo': return cmd_undo(ctx)
    if head == 'board': return cmd_board(ctx, int(toks[1]) if len(toks) > 1 else 15)
    if head == 'me': return cmd_me(ctx)
    if head == 'teams': return cmd_teams(ctx)
    if head == 'nom': return cmd_nom(ctx)
    if head in ('status', 'alerts'): return cmd_status(ctx)
    if head == 'log': return cmd_log(ctx)
    if head == 'sync':
        if len(toks) < 2: die("usage: sync <saved Yahoo Draft Results .html>")
        return cmd_sync(ctx, ' '.join(toks[1:]))
    if head == 'check': return cmd_check(ctx, toks[1:])
    if head == 'adj': return cmd_adj(ctx, toks[1:])
    if head == 'punt': return cmd_punt(ctx, toks[1:], True)
    if head == 'unpunt': return cmd_punt(ctx, toks[1:], False)
    if head == 'new': return cmd_pick(ctx, toks[1:], force, new=True)
    return cmd_pick(ctx, toks, force)

if __name__ == '__main__':
    main(sys.argv[1:])
