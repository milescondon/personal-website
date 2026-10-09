#!/usr/bin/env python3
"""Normalize a Basketball Monster PlayerRankings.xls export into projections.csv.

BBM gives per-game rates plus projected games (g), and crucially fga/g and fta/g,
which are required to weight FG%/FT% by volume. It also ships its own per-category
value scores (pV..toV); we keep them as an independent cross-check on our z-scores.
"""
import sys, csv, xlrd

COLS = {  # our name -> BBM header
    'name':'Name','nba':'Team','pos':'Pos','inj':'Inj','games':'g','mpg':'m/g',
    'pts':'p/g','tpm':'3/g','reb':'r/g','ast':'a/g','stl':'s/g','blk':'b/g',
    'fg_pct':'fg%','fga':'fga/g','ft_pct':'ft%','fta':'fta/g','to':'to/g',
    'bbm_value':'Value','bbm_rank':'Rank',
}
VCOLS = {'pV':'pts','3V':'tpm','rV':'reb','aV':'ast','sV':'stl','bV':'blk',
         'fg%V':'fg_pct','ft%V':'ft_pct','toV':'to'}

def main(src, dst):
    sh = xlrd.open_workbook(src).sheet_by_index(0)
    hdr = [str(c.value).strip() for c in sh.row(0)]
    idx = {h: i for i, h in enumerate(hdr)}
    for want in COLS.values():
        if want not in idx: sys.exit(f"missing BBM column: {want!r} (have {hdr})")

    fields = list(COLS) + ['bbm_'+v for v in VCOLS.values()]
    rows = []
    for r in range(1, sh.nrows):
        row = sh.row(r)
        name = str(row[idx['Name']].value).strip()
        if not name: continue
        rec = {}
        for k, h in COLS.items():
            v = row[idx[h]].value
            rec[k] = str(v).strip() if isinstance(v, str) else v
        for vc, cat in VCOLS.items():
            rec['bbm_'+cat] = row[idx[vc]].value if vc in idx else ''
        rows.append(rec)

    with open(dst, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} players -> {dst}")
    g = [r['games'] for r in rows if isinstance(r['games'], float)]
    print(f"projected games: min={min(g):.0f} median={sorted(g)[len(g)//2]:.0f} max={max(g):.0f}")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
