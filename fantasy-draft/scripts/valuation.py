#!/usr/bin/env python3
"""Valuation core: z-scores -> VORP -> fair dollars -> keeper-inflated prices.

Pure stdlib by design: nothing to install minutes before a draft.

Key choices, and why:
  * Percentage categories are weighted by VOLUME. A 90% FT shooter on 2 attempts barely
    moves a team; a 60% shooter on 10 attempts is a real drag. We score
    attempts*(rate - pool_rate), i.e. makes above what a pool-average shooter yields on
    that volume, then z-score those impacts.
  * The z-score pool is refined iteratively. Including 234 players when only 132 get
    rostered drags the means down and inflates everyone's z-scores.
  * Availability is WAIVER-FILL by default: season = games*per_game + (82-games)*waiver_line,
    where waiver_line is the per-game production of the best unrostered players. With 2 IL
    slots and 88 acquisitions (6/wk), a missed game gets streamed, not lost, so value above
    replacement is games*(per_game - waiver_line). Durability is only worth something on top
    of above-waiver production. The older blend (blended_games = (1-a)*games + a*ref) is kept
    behind tuning.availability_model = "blend".
  * Inflation multiplies only the SURPLUS above $1, because no player can cost under $1.
"""
import csv, json, math, re, unicodedata, collections

COUNTING = ['pts', 'tpm', 'reb', 'ast', 'stl', 'blk', 'to']
PCT = {'fg_pct': 'fga', 'ft_pct': 'fta'}
INVERTED = {'to'}
ALL_CATS = ['fg_pct', 'ft_pct', 'tpm', 'pts', 'reb', 'ast', 'stl', 'blk', 'to']

def canon(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return re.sub(r'[^a-z0-9]+', '', s)

def load_players(path):
    out = []
    for r in csv.DictReader(open(path, encoding='utf-8')):
        def f(k):
            try: return float(r[k])
            except (TypeError, ValueError): return 0.0
        p = {'name': r['name'].strip(), 'key': canon(r['name']), 'nba': r['nba'],
             'pos': [x for x in re.split(r'[,/]', r['pos'] or '') if x], 'inj': r.get('inj', ''),
             'games': f('games'), 'mpg': f('mpg'),
             'bbm_value': f('bbm_value'), 'bbm_rank': f('bbm_rank')}
        for c in COUNTING: p[c] = f(c)
        for pc, att in PCT.items(): p[pc], p[att] = f(pc), f(att)
        out.append(p)
    return out

def blended_games(p, ref, alpha):
    return (1 - alpha) * p['games'] + alpha * ref

def compute_totals(players, alpha, model='blend', waiver=None, fill_games=82.0):
    """Season totals per player. model='blend': counting stats x blended games.
    model='waiver_fill': own per-game for games played, `waiver` per-game line for the rest."""
    ref = sorted(p['games'] for p in players)[len(players) // 2]
    for p in players:
        if model == 'waiver_fill':
            g = p['games']; f = max(0.0, fill_games - g); w = waiver
        else:
            g = blended_games(p, ref, alpha); f = 0.0; w = None
        p['bg'] = g
        for c in COUNTING: p['t_' + c] = p[c] * g + (w[c] * f if f else 0.0)
        for pc, att in PCT.items():
            mk = 't_' + pc.replace('_pct', 'm')
            p['t_' + att] = p[att] * g + (w[att] * f if f else 0.0)          # total attempts
            p[mk] = p[pc] * p[att] * g + (w[pc] * w[att] * f if f else 0.0)  # total makes
    return ref

def waiver_line(players, rostered, depth=24):
    """Per-game line of the best UNROSTERED players: per-game ranks rostered+1..rostered+depth.
    This is what a streamed replacement produces on the nights a rostered player sits."""
    compute_totals(players, 1.0)            # alpha=1: everyone at the same games -> per-game rank
    refine_pool(players, rostered)
    for p in players: p['Vw'] = weighted_value(p, {})
    wire = sorted(players, key=lambda p: -p['Vw'])[rostered:rostered + depth]
    line = {c: sum(p[c] for p in wire) / len(wire) for c in COUNTING}
    for pc, att in PCT.items():
        a = sum(p[att] for p in wire) / len(wire)
        m = sum(p[pc] * p[att] for p in wire) / len(wire)
        line[att] = a; line[pc] = m / a if a else 0.0
    return line

def zscores(players, pool):
    """Z-scores for every player, with means/SDs taken from `pool` only."""
    stats = {}
    for c in COUNTING:
        xs = [p['t_' + c] for p in pool]
        mu = sum(xs) / len(xs)
        sd = math.sqrt(sum((x - mu) ** 2 for x in xs) / len(xs)) or 1e-9
        stats[c] = (mu, sd)
    # percentage categories: pool rate is total makes / total attempts (volume weighted)
    for pc, att in PCT.items():
        mk = 't_' + pc.replace('_pct', 'm')
        tot_m = sum(p[mk] for p in pool); tot_a = sum(p['t_' + att] for p in pool)
        rate = tot_m / tot_a if tot_a else 0.0
        # makes above what a pool-average shooter gets on the same attempts
        imps = [p[mk] - rate * p['t_' + att] for p in pool]
        mu = sum(imps) / len(imps)
        sd = math.sqrt(sum((x - mu) ** 2 for x in imps) / len(imps)) or 1e-9
        stats[pc] = (mu, sd, rate)

    for p in players:
        z = {}
        for c in COUNTING:
            mu, sd = stats[c]
            v = (p['t_' + c] - mu) / sd
            z[c] = -v if c in INVERTED else v
        for pc, att in PCT.items():
            mu, sd, rate = stats[pc]
            p['imp_' + pc] = p['t_' + pc.replace('_pct', 'm')] - rate * p['t_' + att]
            z[pc] = (p['imp_' + pc] - mu) / sd
        p['z'] = z
        p['V'] = sum(z.values())
    return stats

def refine_pool(players, size, rounds=6):
    """Iterate: score -> take top `size` -> rescore from that pool."""
    pool = players[:]
    for _ in range(rounds):
        stats = zscores(players, pool)
        ranked = sorted(players, key=lambda p: -p['V'])
        new = ranked[:size]
        if [p['key'] for p in new] == [p['key'] for p in pool]: break
        pool = new
    return pool, stats

def weighted_value(p, w):
    return sum(w.get(c, 1.0) * p['z'][c] for c in ALL_CATS)

def fair_dollars(players, rostered, total_budget, weights=None):
    """Fair values over the FULL pool and budget; they sum to the total budget."""
    w = weights or {c: 1.0 for c in ALL_CATS}
    for p in players: p['Vw'] = weighted_value(p, w)
    ranked = sorted(players, key=lambda p: -p['Vw'])
    repl = ranked[rostered - 1]['Vw']
    for p in players: p['vorp'] = p['Vw'] - repl
    pos = sum(p['vorp'] for p in ranked[:rostered] if p['vorp'] > 0) or 1e-9
    surplus = total_budget - rostered * 1.0
    for p in players:
        p['fair'] = 1.0 + surplus * max(p['vorp'], 0.0) / pos
    return ranked, repl

def keeper_inflation(auction_pool, auction_dollars):
    """Multiply only the surplus above $1 -- nobody can be bought for less than $1."""
    n = len(auction_pool)
    rem_val = sum(p['fair'] for p in auction_pool)
    denom = rem_val - n
    k = (auction_dollars - n) / denom if denom > 1e-9 else 1.0
    return k, rem_val

def sigma_match(players, pool_size, spots, trials=4000, seed=11):
    """Calibrate the H2H matchup SD empirically; the closed form sqrt(2*spots) is ~25% off."""
    import random
    rnd = random.Random(seed)
    pool = sorted(players, key=lambda p: -p['V'])[:pool_size]
    out = {}
    for c in ALL_CATS:
        zs = [p['z'][c] for p in pool]
        sums = [sum(rnd.sample(zs, spots)) for _ in range(trials)]
        m = sum(sums) / trials
        sd = math.sqrt(sum((s - m) ** 2 for s in sums) / trials)
        out[c] = math.sqrt(2) * sd
    return out

def cat_weight(delta, sig):
    """Marginal win-probability weight: the normal PDF, normalized to (0,1].
    Peaks when a category is even (production swings the most weeks), decays to 0 when
    far ahead (already won) or far behind (punted -- derived, not declared)."""
    return math.exp(-0.5 * (delta / sig) ** 2) if sig > 0 else 1.0


# ---- name resolution ------------------------------------------------------
# Sources disagree on spelling ("Alex Sarr" vs "Alexandre Sarr"), and during the draft
# names get typed fast and wrong. Resolution is staged, strictest first, and a miss is
# reported rather than silently dropped -- an unresolved keeper would otherwise stay in
# the available pool and get recommended.

def name_parts(name):
    """Name words, minus suffixes (Jr, III...) that canon() erases -- otherwise every
    'X Porter Jr.' indexes under an empty last name and 'porter' finds nobody."""
    words = re.split(r'\s+', re.sub(r'[^A-Za-z\s]', ' ', name).strip())
    return [w for w in words if canon(w)]

def build_index(players, aliases=None):
    idx = {'exact': {}, 'lastfirst': collections.defaultdict(list),
           'last': collections.defaultdict(list), 'players': players}
    for p in players:
        idx['exact'][p['key']] = p
        parts = name_parts(p['name'])
        if parts:
            last = canon(parts[-1]); first = canon(parts[0])
            idx['last'][last].append(p)
            if first: idx['lastfirst'][(last, first[0])].append(p)
    idx['aliases'] = {canon(k): canon(v) for k, v in (aliases or {}).items()
                      if not k.startswith('_')}
    return idx

def resolve_name(idx, raw):
    """-> (player|None, how). `how` is one of exact/alias/lastfirst/last/prefix/
    ambiguous:N/miss, so callers can log how confident the match was."""
    k = canon(raw)
    if k in idx['exact']: return idx['exact'][k], 'exact'
    a = idx['aliases'].get(k)
    if a and a in idx['exact']: return idx['exact'][a], 'alias'
    parts = name_parts(raw)
    if len(parts) >= 2:
        cand = idx['lastfirst'].get((canon(parts[-1]), canon(parts[0])[:1]), [])
        if len(cand) == 1: return cand[0], 'lastfirst'
        if len(cand) > 1: return None, f'ambiguous:{len(cand)}'
    if parts:
        cand = idx['last'].get(canon(parts[-1]), [])
        if len(cand) == 1: return cand[0], 'last'
        if len(cand) > 1: return None, f'ambiguous:{len(cand)}'
    cand = [p for key, p in idx['exact'].items() if key.startswith(k) or k.startswith(key)]
    if len(cand) == 1: return cand[0], 'prefix'
    if len(cand) > 1: return None, f'ambiguous:{len(cand)}'
    return None, 'miss'
