#!/usr/bin/env python3
"""Build the auction value board: value_board.json + cheat_sheet.md."""
import sys, os, csv, json, math, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import valuation as V

def tier_of(adj):
    for lo, name in [(55,'T1 elite'),(38,'T2 star'),(26,'T3 core'),(16,'T4 starter'),
                     (9,'T5 value'),(4,'T6 depth'),(2,'T7 flier')]:
        if adj >= lo: return name
    return 'T8 $1'

def main(root):
    cfg = json.load(open(f'{root}/league.json', encoding='utf-8'))
    spots = cfg['roster']['active_spots']; nteams = cfg['teams']
    rostered = nteams * spots
    budget_of = {t['id']: t['budget'] for t in cfg['teams_list']}
    TB = sum(budget_of.values())
    tun = cfg['tuning']
    alpha = tun['availability_blend']
    model = tun.get('availability_model', 'blend')
    margin = tun['target_margin']

    season = (tun['season_start'], tun['season_end']) if tun.get('season_start') else None
    players = V.load_players(f'{root}/data/projections.csv', season)
    wline = None
    if model == 'waiver_fill':
        wline = V.waiver_line(players, rostered, tun.get('waiver_depth', 24))
    ref = V.compute_totals(players, alpha, model, wline, tun.get('waiver_fill_games', 82))
    pool, stats = V.refine_pool(players, rostered)
    ranked, repl = V.fair_dollars(players, rostered, TB)

    # ---- keepers ------------------------------------------------------------
    # Yahoo's room is the default truth: it enforces budgets and blocks nominating keepers.
    ksrc = cfg['keepers'].get('source_of_truth', 'league_sheet')
    if ksrc == 'yahoo_room':
        room = json.load(open(f"{root}/{cfg['keepers']['room_file']}", encoding='utf-8'))
        if room.get('errors'): sys.exit(f"FATAL yahoo_room.json failed its checks: {room['errors']}")
        for t in room['teams']:
            if t['start'] != budget_of[t['id']]:
                sys.exit(f"FATAL {t['id']}: Yahoo start ${t['start']} != league.json ${budget_of[t['id']]}")
        keepers = [{'player': k['name'], 'owner': t['id'], 'owner_canon': t['id'],
                    'keeper_cost': k['cost']} for t in room['teams'] for k in t['keepers']]
        team_salaries = {t['id']: t['salaries'] for t in room['teams']}
    else:
        keepers = list(csv.DictReader(open(f'{root}/data/keepers.csv', encoding='utf-8')))
        team_salaries = {r['owner_canon']: float(r['sheet_keeper_cost'] or 0) for r in
                         csv.DictReader(open(f'{root}/data/teams.csv', encoding='utf-8'))}
    aliases = json.load(open(f'{root}/data/player_aliases.json', encoding='utf-8'))
    idx = V.build_index(players, aliases)
    kept, unmatched, fuzzy = {}, [], []
    for k in keepers:
        cost = float(k['keeper_cost'])
        p, how = V.resolve_name(idx, k['player'])
        if p is not None:
            kept[p['key']] = {'owner': k['owner_canon'], 'cost': cost}
            if how != 'exact': fuzzy.append((k['player'], p['name'], how))
        else:
            unmatched.append((k['player'], k['owner'], cost, how))
    keeper_dollars = sum(float(k['keeper_cost']) for k in keepers)
    kc_by_team = collections.Counter()
    for k in keepers: kc_by_team[k['owner_canon']] += float(k['keeper_cost'])
    recon_bad = [t for t in budget_of if abs(kc_by_team[t] - float(team_salaries.get(t, 0))) > 0.5]
    auction_dollars = TB - keeper_dollars
    auction_spots = rostered - len(keepers)

    avail = [p for p in ranked if p['key'] not in kept]
    auction_pool = avail[:auction_spots]
    k_infl, rem_val = V.keeper_inflation(auction_pool, auction_dollars)

    for p in players:
        p['adj'] = 1.0 + (p['fair'] - 1.0) * k_infl
        p['target'] = p['adj'] * (1 - margin)
        p['kept_by'] = kept.get(p['key'], {}).get('owner')
        p['keeper_cost'] = kept.get(p['key'], {}).get('cost')

    sig = V.sigma_match(players, rostered, spots)

    # ---- room anchors: what the room is likely to pay -----------------------
    # Yahoo's average auction cost and Yahoo's projected $ are the two numbers managers see
    # in Yahoo's draft room. room_anchor = their mean; draft_state scales it to the live money.
    # Missing players get None and are priced at market instead.
    ypath = f'{root}/data/yahoo_prices.csv'
    yp_by = {}
    if os.path.exists(ypath):
        for r in csv.DictReader(open(ypath, encoding='utf-8')):
            yp_by[V.canon(r['name'])] = (float(r['yahoo_avg']), float(r['yahoo_proj']))
    for p in players:
        a = yp_by.get(p['key']) or yp_by.get(idx['aliases'].get(p['key'], ''))
        p['yahoo_avg'], p['yahoo_proj'] = (a if a else (None, None))
        p['room_anchor'] = (a[0] + a[1]) / 2 if a else None

    # ---- surplus on keepers: who got a bargain -----------------------------
    ksurp = sorted(({'name': p['name'], 'owner': p['kept_by'], 'cost': p['keeper_cost'],
                     'fair': p['fair'], 'adj': p['adj'], 'surplus': p['adj'] - p['keeper_cost']}
                    for p in players if p['kept_by']), key=lambda x: -x['surplus'])

    out = {
      'league': cfg['name'], 'generated_for_draft': cfg['draft']['datetime'],
      'params': {'teams': nteams, 'active_spots': spots, 'rostered': rostered,
                 'total_budget': TB, 'keeper_dollars': keeper_dollars,
                 'auction_dollars': auction_dollars, 'auction_spots': auction_spots,
                 'inflation_multiplier': round(k_infl, 4),
                 'replacement_V': round(repl, 4), 'ref_games': ref,
                 'dollars_per_vorp': (TB - rostered) / (sum(max(p['vorp'], 0) for p in ranked[:rostered]) or 1e-9),
                 'availability_model': model, 'availability_blend': alpha,
                 'waiver_line': wline, 'keeper_source': ksrc, 'me': cfg.get('me'),
                 'target_margin': margin},
      'sigma_match': {c: round(s, 3) for c, s in sig.items()},
      'unmatched_keepers': [{'player': n, 'owner': o, 'cost': c, 'why': h}
                            for n, o, c, h in unmatched],
      'fuzzy_matched_keepers': [{'input': a, 'matched': b, 'how': h} for a, b, h in fuzzy],
      'keeper_surplus': [{**x, 'cost': x['cost'], 'fair': round(x['fair'],1),
                          'adj': round(x['adj'],1), 'surplus': round(x['surplus'],1)} for x in ksurp],
      'players': [{'name': p['name'], 'nba': p['nba'], 'pos': p['pos'], 'inj': p['inj'],
                   'games': p['games'], 'mpg': round(p['mpg'],1),
                   'V': round(p['Vw'],3), 'vorp': round(p['vorp'],3),
                   'fair': round(p['fair'],1), 'adj': round(p['adj'],1),
                   'target': round(p['target'],1), 'tier': tier_of(p['adj']),
                   'z': {c: round(v,3) for c, v in p['z'].items()},
                   'bbm_rank': p['bbm_rank'], 'kept_by': p['kept_by'],
                   'keeper_cost': p['keeper_cost'], 'yahoo_avg': p['yahoo_avg'],
                   'yahoo_proj': p['yahoo_proj'], 'room_anchor': p['room_anchor']}
                  for p in ranked],
    }
    os.makedirs(f'{root}/build', exist_ok=True)
    json.dump(out, open(f'{root}/build/value_board.json','w',encoding='utf-8'),
              indent=1, ensure_ascii=False)

    # ---- report -------------------------------------------------------------
    print(f"league {cfg['name']}: {nteams} teams x {spots} spots = {rostered} rostered")
    print(f"availability model: {model}" + (f" (waiver line {wline['pts']:.1f}p {wline['tpm']:.1f}3 "
          f"{wline['reb']:.1f}r {wline['ast']:.1f}a)" if wline else f" alpha={alpha}"))
    print(f"keeper source: {ksrc}")
    print(f"budget ${TB:.0f} | keepers {len(keepers)} costing ${keeper_dollars:.0f}")
    print(f"auction ${auction_dollars:.0f} for {auction_spots} spots (${auction_dollars/auction_spots:.2f}/spot)")
    print(f"fair value of the {auction_spots}-player auction pool: ${rem_val:.0f}")
    print(f"\n>>> INFLATION MULTIPLIER = {k_infl:.3f}  "
          f"({'inflation' if k_infl>1 else 'DEFLATION'}: a $40 fair player costs "
          f"${1+(40-1)*k_infl:.0f})")
    # the verification checks -- each must say PASS
    fair_sum = sum(p['fair'] for p in ranked[:rostered])
    max_sum = sum(1 + (p['fair'] - 1) * k_infl for p in auction_pool)
    checks = [('fair values over top %d sum to budget $%.0f' % (rostered, TB), abs(fair_sum - TB) < 0.01),
              ('MAX over the %d-player auction pool sums to $%.0f' % (auction_spots, auction_dollars),
               abs(max_sum - auction_dollars) < 0.01),
              ('keeper costs reconcile per team (%d mismatches)' % len(recon_bad), not recon_bad),
              ('inflation %.3f inside 0.8-1.6' % k_infl, 0.8 <= k_infl <= 1.6)]
    print()
    for name, ok in checks: print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not all(ok for _, ok in checks): print("  !! a check FAILED -- do not trust this board")
    if fuzzy:
        print(f"\nkeepers matched non-exactly ({len(fuzzy)}) -- verify these:")
        for a,b,h in fuzzy: print(f"    {a:26s} -> {b:26s} via {h}")
    if unmatched:
        print(f"\nkeepers with no projection row ({len(unmatched)}) -- cost counted, no value,")
        print( "    and EXCLUDED from the biddable board so they are never recommended:")
        for n,o,c,h in unmatched: print(f"    {n:26s} {o:16s} ${c:.0f}  ({h})")

    # BBM cross-check: rank correlation
    pairs=[(i+1,p['bbm_rank']) for i,p in enumerate(ranked) if p['bbm_rank']>0][:132]
    n=len(pairs); d2=sum((a-b)**2 for a,b in pairs)
    rho=1-6*d2/(n*(n*n-1))
    print(f"\nsanity: Spearman rho vs BBM's own ranking (top {n}) = {rho:.3f}")
    print(f"sigma_match range: {min(sig.values()):.2f}-{max(sig.values()):.2f} "
          f"(closed form sqrt(2*{spots}) = {math.sqrt(2*spots):.2f})")

    dis=sorted(((abs(i+1-p['bbm_rank']), i+1, p) for i,p in enumerate(ranked[:132])
                if p['bbm_rank']>0), reverse=True)[:6]
    print("biggest rank disagreements vs BBM (bug sniff):")
    for d,mine,p in dis:
        print(f"    {p['name'][:24]:24s} me #{mine:<4d} bbm #{p['bbm_rank']:<5.0f} "
              f"GP={p['games']:.0f} mpg={p['mpg']:.1f}")

    if yp_by:
        have = sum(1 for p in avail[:auction_spots] if p['room_anchor'] is not None)
        print(f"room anchors: {len(yp_by)} Yahoo prices, {have}/{auction_spots} of the auction pool covered")
    print(f"\nbiggest keeper bargains (adjusted value minus keeper cost):")
    for x in ksurp[:8]:
        print(f"    {x['name'][:24]:24s} {x['owner'][:12]:12s} cost ${x['cost']:>3.0f}  "
              f"worth ${x['adj']:>5.1f}  surplus ${x['surplus']:>+6.1f}")

    # ---- cheat sheet --------------------------------------------------------
    lines=[f"# {cfg['name']} auction cheat sheet",
      f"", f"Draft {cfg['draft']['datetime']} | {nteams} teams x {spots} spots | ${TB:.0f} total",
      f"Auction: **${auction_dollars:.0f}** for **{auction_spots}** spots. "
      f"Inflation multiplier **{k_infl:.3f}**.",
      f"", f"MAX = walk-away price. TARGET = {int(margin*100)}% under MAX, where he's a real win.",
      f"Always leave $1 per unfilled slot.", f"",
      f"| # | Player | Pos | Tier | MAX | TARGET | GP | V |", f"|--:|---|---|---|--:|--:|--:|--:|"]
    unres = {V.canon(n) for n, _o, _c, _h in unmatched}
    rank=0
    for p in ranked:
        if p['kept_by'] or p['adj'] < 1.5 or p['key'] in unres: continue
        rank+=1
        lines.append(f"| {rank} | {p['name']} | {'/'.join(p['pos'])} | {tier_of(p['adj'])} | "
                     f"${p['adj']:.0f} | ${p['target']:.0f} | {p['games']:.0f} | {p['Vw']:.1f} |")
        if rank>=120: break
    lines += ["", "## Kept (off the board)", "",
              "| Player | Owner | Cost | Worth | Surplus |", "|---|---|--:|--:|--:|"]
    for x in ksurp:
        lines.append(f"| {x['name']} | {x['owner']} | ${x['cost']:.0f} | ${x['adj']:.1f} | ${x['surplus']:+.1f} |")
    open(f'{root}/build/cheat_sheet.md','w',encoding='utf-8').write("\n".join(lines)+"\n")
    print(f"\nwrote build/value_board.json and build/cheat_sheet.md ({rank} biddable players)")

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv)>1 else 'fantasy-draft')
