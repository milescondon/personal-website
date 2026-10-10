#!/usr/bin/env python3
"""Opponent model + category weights, used by draft_state.py.

The strongest signal in an auction is exact, not estimated: Yahoo reserves $1 per empty
slot, so a rival's ceiling is  max_bid = budget - (open_spots - 1).  Everything here is
built on that plus each team's category profile:

  * category weights  w_c = exp(-1/2 (delta_c / sigma_c)^2), delta_c = the team's z-sum in
    category c (a league-average team sums to ~0, because z is measured against the
    rostered pool). 1.0 when even, ->0 when far ahead (won) or far behind (punted). The
    weights are renormalized to mean 1 so they move RELATIVE value, not the price level.
  * personal value  = sum_c w_c * z_c, priced like the board: 1 + dpv*(v - repl), then
    live inflation on the surplus above $1.
"""
import math

CATS = ['fg_pct', 'ft_pct', 'tpm', 'pts', 'reb', 'ast', 'stl', 'blk', 'to']
SHORT = {'fg_pct': 'FG%', 'ft_pct': 'FT%', 'tpm': '3PM', 'pts': 'PTS', 'reb': 'REB',
         'ast': 'AST', 'stl': 'STL', 'blk': 'BLK', 'to': 'TO'}
REQUIRED = ['PG', 'SG', 'SF', 'PF', 'C']

def weights(roster, sigma, override=None):
    """-> (delta, raw w, normalized w). `override` pins categories (e.g. a confirmed punt)."""
    delta = {c: sum(p['z'][c] for p in roster if p.get('z')) for c in CATS}
    w = {c: math.exp(-0.5 * (delta[c] / sigma[c]) ** 2) for c in CATS}
    for c, v in (override or {}).items(): w[c] = v
    s = sum(w.values())
    wn = {c: w[c] * len(CATS) / s for c in CATS} if s > 1e-9 else {c: 1.0 for c in CATS}
    return delta, w, wn

def pval(p, wn):
    return sum(wn[c] * p['z'][c] for c in CATS)

class Pricer:
    """Prices players for one set of normalized weights. Replacement is the `rostered`-th
    best player under THOSE weights, so a punter's replacement level moves too."""
    def __init__(self, players, wn, rostered, dpv, k):
        self.wn, self.dpv, self.k = wn, dpv, k
        vals = sorted((pval(p, wn) for p in players), reverse=True)
        self.repl = vals[min(rostered, len(vals)) - 1]
    def fair(self, p):
        return 1.0 + self.dpv * max(pval(p, self.wn) - self.repl, 0.0)
    def adj(self, p):
        return 1.0 + (self.fair(p) - 1.0) * self.k

def positions(p):
    return set(p.get('pos') or [])

def unfilled(roster):
    have = set()
    for p in roster: have |= positions(p)
    return [x for x in REQUIRED if x not in have]

def acute_need(team, p):
    """True when the team must fill p's position soon: it has none there and its unfilled
    required positions nearly use up its open spots."""
    miss = unfilled(team['roster'])
    return bool(positions(p) & set(miss)) and team['open'] > 0 and len(miss) >= team['open'] - 1

def rival_rows(teams, me):
    return [t for tid, t in teams.items() if tid != me and t['open'] > 0]

def room_per_spot(teams, me=None):
    rs = [t for tid, t in teams.items() if tid != me and t['open'] > 0]
    b = sum(t['budget'] for t in rs); o = sum(t['open'] for t in rs)
    return b / o if o else 0.0

def threats(p, my_max, teams, me, pricers):
    """Rivals who can bid past my MAX, with their own valuation of p and liquidity."""
    avg = room_per_spot(teams, me)
    out = []
    for t in rival_rows(teams, me):
        if t['max_bid'] <= my_max: continue
        val = pricers[t['id']].adj(p)
        liquid = t['budget'] / t['open'] >= 1.15 * avg
        need = acute_need(t, p)
        out.append({'id': t['id'], 'max_bid': t['max_bid'], 'val': val, 'liquid': liquid,
                    'need': need, 'per_spot': t['budget'] / t['open']})
    return sorted(out, key=lambda r: -r['val'])

def fold_risk(th, my_max):
    """A rival who can outbid me AND values him above my MAX (or must fill the position)
    AND has spare cash will likely take him past MAX: don't chase."""
    return [r for r in th if r['liquid'] and (r['val'] >= my_max + 2 or r['need'])]

def rival_ceiling(teams, me):
    rs = rival_rows(teams, me)
    if not rs: return 0, None
    top = max(rs, key=lambda t: t['max_bid'])
    return top['max_bid'], top['id']

def nominations(avail, teams, me, my_pricer, mkt, pricers, n=5):
    """Price-push: players I value below the market whom 2+ liquid rivals can afford --
    nominating them drains rival budgets at no cost to me.  Hold: my best bargains --
    don't nominate those while rivals are flush.  Steal: players I value above every
    rival's ceiling -- nominate now, nobody can stop you."""
    avg = room_per_spot(teams, me)
    ceil, _ = rival_ceiling(teams, me)
    my_max_bid = teams[me]['max_bid']
    push, drain, hold, steal = [], [], [], []
    for p in avail[:80]:
        m = mkt(p); mine = my_pricer.adj(p)
        if m < 6: continue
        able = [t for t in rival_rows(teams, me)
                if t['max_bid'] >= m and t['budget'] / t['open'] >= 0.9 * avg]
        wanting = [t for t in able if pricers[t['id']].adj(p) >= m - 1]
        if mine <= m - 2 and len(wanting) >= 2:
            push.append((len(wanting) * m + (m - mine) * 2, p, m, mine, [t['id'] for t in wanting]))
        elif mine <= m + 0.5 and m >= 15 and len(able) >= 3:
            # early-draft fallback: an expensive player you'd be fine losing at market
            drain.append((m, p, m, mine, [t['id'] for t in able]))
        if mine >= m + 1:
            hold.append((mine - m, p, m, mine))
        if mine > ceil + 1 and my_max_bid > ceil and mine >= 3:
            steal.append((mine, p, ceil))
    for xs in (push, drain, hold, steal): xs.sort(key=lambda x: -x[0])
    return push[:n], drain[:n], hold[:n], steal[:n]


# ---------------------------------------------------------------- room prices
# What the ROOM will likely pay, as opposed to what a player is worth to you. Managers
# anchor on the two numbers Yahoo's draft room shows -- average auction cost and projected
# $ -- so room_anchor is their mean (set at build time), scaled like inflation to the money
# actually left: room = 1 + (anchor - 1) * room_k. Players Yahoo doesn't price fall back
# to market value.

def room_k(avail, teams, n_open, k_max):
    numer = sum(t['budget'] for t in teams.values()) - n_open
    top = sorted((p for p in avail if p.get('room_anchor') is not None),
                 key=lambda p: -p['room_anchor'])[:n_open]
    denom = sum(max(p['room_anchor'] - 1.0, 0.0) for p in top)
    k = numer / denom if denom > 0.5 else (k_max if numer > 0 else 1.0)
    return max(0.0, min(k, k_max))

def room_price(p, rk, market):
    a = p.get('room_anchor')
    if a is None: return market.adj(p)
    return 1.0 + max(a - 1.0, 0.0) * rk

def room_nominations(avail, teams, me, my_pricer, room, n=5, min_gp=0):
    """Overpay: the room will pay well past your value -- nominate early so a rival burns
    the cash.  Late: the room undervalues him -- nominate when budgets are thin."""
    overpay, late = [], []
    for p in avail[:90]:
        r = room(p); mine = my_pricer.adj(p)
        able = [t for t in rival_rows(teams, me) if t['max_bid'] >= r]
        if r >= 10 and r - mine >= 5 and len(able) >= 2:
            overpay.append((r - mine, p, r, mine))
        if mine >= 8 and mine - r >= 5 and p['games'] >= min_gp:   # never wait on a player you won't buy
            late.append((mine - r, p, r, mine))
    overpay.sort(key=lambda x: -x[0]); late.sort(key=lambda x: -x[0])
    return overpay[:n], late[:n]
