#!/usr/bin/env python3
"""Parse the league's Draft_2026 Teams sheet -> keepers.csv + teams.csv.

The sheet is authoritative for keeper membership AND price: Yahoo's Protected-Keepers
page leaves Keeper Salary blank or stale for most rows, and disagrees on 6 players
(pre- vs post-deadline). Rows for departed teams are dropped.

Two gotchas this handles explicitly:
  * The sheet has two blank header cells, so csv.DictReader collapses columns.
    Access is positional.
  * Team names differ between the sheet and Yahoo ("O Captain" vs "O Captains",
    "Whyy" vs "Whyyy", "AND TAI 1" vs "AND TAI1"). Aliases are declared in
    league.json and an unmapped name is fatal, not a silent drop.
"""
import sys, csv, json, re, unicodedata, collections

TEAM, PLAYER, SOURCE, ORIG, ACQ, KEEP, YPROJ, YAVG, DISC, ISKEEP, _PAD, SUMLAB, SUMVAL = range(13)
NOT_KEEPABLE = 1000.0   # sheet sentinel for waiver adds that cannot be kept

def canon(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '', s)

def money(v):
    s = str(v or '').replace('$', '').replace(',', '').replace('"', '').strip()
    if s in ('', '-'): return None
    try: return float(s)
    except ValueError: return None

def main(src, league_json, kdst, tdst):
    cfg = json.load(open(league_json, encoding='utf-8'))
    amap, budget_of = {}, {}
    for t in cfg['teams_list']:
        budget_of[t['id']] = t['budget']
        amap[canon(t['id'])] = t['id']
        for a in t['aliases']: amap[canon(a)] = t['id']
    gone = {canon(t) for t in cfg.get('departed_teams', [])}
    spots = cfg['roster']['active_spots']

    rows = [r + [''] * (13 - len(r)) for r in csv.reader(open(src, encoding='utf-8-sig'))][1:]
    keepers, summary, dropped, unknown = [], {}, set(), set()
    for r in rows:
        team, name = r[TEAM].strip(), r[PLAYER].strip()
        tid = amap.get(canon(team))
        if team and tid and r[SUMLAB].strip():
            summary.setdefault(tid, {'owner': team})[r[SUMLAB].strip()] = money(r[SUMVAL])
        if not (team and name) or r[ISKEEP].strip() != '1':
            continue
        if tid is None:
            dropped.add(team)
            if canon(team) not in gone: unknown.add(team)
            continue
        acq, kc = money(r[ACQ]), money(r[KEEP])
        if kc is None or kc >= NOT_KEEPABLE:
            print(f"  WARN unusable keeper price, skipping {name} ({team}): acq={acq} keep={kc}")
            continue
        keepers.append({'player': name, 'owner': team, 'owner_canon': tid,
                        'source': r[SOURCE].strip(), 'acq_price': acq, 'keeper_cost': kc,
                        'escalator': (kc - acq) if (acq and acq < NOT_KEEPABLE) else None,
                        'yahoo_proj': money(r[YPROJ]), 'yahoo_avg': money(r[YAVG])})

    if unknown:
        sys.exit(f"FATAL unmapped team name(s) {sorted(unknown)} -- add an alias in league.json")

    with open(kdst, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['player','owner','owner_canon','source','acq_price',
                                          'keeper_cost','escalator','yahoo_proj','yahoo_avg'])
        w.writeheader(); w.writerows(keepers)

    trows = []
    for tid, bud in budget_of.items():
        mine = [k for k in keepers if k['owner_canon'] == tid]
        s = summary.get(tid, {})
        kcost = sum(k['keeper_cost'] for k in mine)
        trows.append({'owner': s.get('owner', tid), 'owner_canon': tid, 'budget': bud,
                      'keeper_cost': kcost, 'remaining_budget': bud - kcost,
                      'keepers': len(mine), 'remaining_spots': spots - len(mine),
                      'sheet_keeper_cost': s.get('Keeper cost'),
                      'sheet_remaining_balance': s.get('Remaining balance')})
    trows.sort(key=lambda t: -t['keeper_cost'])
    with open(tdst, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['owner','owner_canon','budget','keeper_cost',
            'remaining_budget','keepers','remaining_spots','sheet_keeper_cost','sheet_remaining_balance'])
        w.writeheader(); w.writerows(trows)

    if dropped: print(f"  dropped departed teams: {sorted(dropped)}")
    print(f"\nteams={len(trows)}  keepers={len(keepers)}")
    print(f"{'team':26s} {'bud':>4s} {'keep$':>6s} {'sheet':>6s} {'rem$':>5s} {'n':>2s} {'spots':>5s}  rec")
    bad = 0
    for t in trows:
        sk = t['sheet_keeper_cost']
        ok = sk is None or abs(sk - t['keeper_cost']) < 0.51
        bad += (not ok)
        print(f"{t['owner'][:26]:26s} {t['budget']:>4.0f} {t['keeper_cost']:>6.0f} "
              f"{('-' if sk is None else f'{sk:.0f}'):>6s} {t['remaining_budget']:>5.0f} "
              f"{t['keepers']:>2d} {t['remaining_spots']:>5d}  {'OK' if ok else 'MISMATCH'}")
    esc = collections.Counter(k['escalator'] for k in keepers if k['escalator'] is not None)
    print(f"\nescalator deltas: {dict(esc)}")
    print(f"reconciliation mismatches vs sheet totals: {bad}")
    tot_k = sum(k['keeper_cost'] for k in keepers)
    TB, NS = sum(budget_of.values()), cfg['teams'] * spots
    print(f"auction: ${TB - tot_k:.0f} for {NS - len(keepers)} spots "
          f"(${(TB - tot_k) / (NS - len(keepers)):.2f}/spot vs ${TB/NS:.2f} flat)")

if __name__ == '__main__':
    main(*sys.argv[1:5])
