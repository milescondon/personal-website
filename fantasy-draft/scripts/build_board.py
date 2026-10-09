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
    alpha = cfg['tuning']['availability_blend']
    margin = cfg['tuning']['target_margin']

    players = V.load_players(f'{root}/data/projections.csv')
    ref = V.compute_totals(players, alpha)
    pool, stats = V.refine_pool(players, rostered)
    ranked, repl = V.fair_dollars(players, rostered, TB)

    # ---- keepers ------------------------------------------------------------
    keepers = list(csv.DictReader(open(f'{root}/data/keepers.csv', encoding='utf-8')))
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
                 'availability_blend': alpha, 'target_margin': margin},
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
                   'keeper_cost': p['keeper_cost']}
                  for p in ranked],
    }
    os.makedirs(f'{root}/build', exist_ok=True)
    json.dump(out, open(f'{root}/build/value_board.json','w',encoding='utf-8'),
              indent=1, ensure_ascii=False)

    # ---- report -------------------------------------------------------------
    print(f"league {cfg['name']}: {nteams} teams x {spots} spots = {rostered} rostered")
    print(f"budget ${TB:.0f} | keepers {len(keepers)} costing ${keeper_dollars:.0f}")
    print(f"auction ${auction_dollars:.0f} for {auction_spots} spots (${auction_dollars/auction_spots:.2f}/spot)")
    print(f"fair value of the {auction_spots}-player auction pool: ${rem_val:.0f}")
    print(f"\n>>> INFLATION MULTIPLIER = {k_infl:.3f}  "
          f"({'inflation' if k_infl>1 else 'DEFLATION'}: a $40 fair player costs "
          f"${1+(40-1)*k_infl:.0f})")
    if not (0.8 <= k_infl <= 1.6):
        print("    !! outside the plausible 0.8-1.6 band -- check the keeper list")
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
