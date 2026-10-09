#!/usr/bin/env python3
"""Parse a saved Yahoo "Draft Results" page -> data/yahoo_room.json.

Yahoo's room is what the draft actually ENFORCES: a team cannot bid past its Yahoo
budget, and a player Yahoo lists as kept cannot be nominated. So for the live draft the
room, not the league sheet, is the source of truth for keepers and starting budgets.
(Decided 2026-10-09 after this page disagreed with the sheet on 3 teams.)

Pre-draft the page has one table: Nomination Order | Team | Keepers | Starting Budget |
Salaries | Remaining Budget. Parsing is by header text, not position, and every row is
checked: start - salaries == remaining, and the keeper salaries sum to `Salaries`.
An unmapped team name is FATAL -- silent dropping already cost 5 teams' keepers once.

usage: yahoo_sync.py <saved.html> [league.json] [out.json]
"""
import sys, os, re, json, html.parser

def norm_team(s):
    return re.sub(r'\s+', ' ', (s or '').replace('’', "'")).strip().lower()

def money(s):
    m = re.search(r'-?\$?\s*(-?\d+)', s or '')
    return int(m.group(1)) if m else None

class Page(html.parser.HTMLParser):
    """Collects every table as rows of cells; a cell keeps its text, title attribute and
    any <dt>/<dd> keeper entries (name, salary, team-pos tail)."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.row, self.cell, self.kp, self.where = [], None, None, None, None
    def handle_starttag(self, t, a):
        a = dict(a)
        if t == 'table': self.tables.append([])
        elif t == 'tr' and self.tables: self.row = []; self.tables[-1].append(self.row)
        elif t in ('td', 'th') and self.row is not None:
            self.cell = {'text': '', 'title': a.get('title', ''), 'keepers': []}
            self.row.append(self.cell)
        elif self.cell is not None:
            if t == 'dt':
                self.kp = {'name': '', 'salary_title': None, 'tail': '', 'dd': ''}
                self.cell['keepers'].append(self.kp); self.where = 'dt'
            elif t == 'a' and self.where == 'dt': self.where = 'a'
            elif t == 'span' and self.kp is not None and 'Keeper Salary' in a.get('title', ''):
                self.kp['salary_title'] = money(a['title'])
            elif t == 'dd' and self.kp is not None: self.where = 'dd'
    def handle_endtag(self, t):
        if t in ('td', 'th'): self.cell = None; self.kp = None; self.where = None
        elif t == 'tr': self.row = None
        elif t == 'a' and self.where == 'a': self.where = 'dt'
        elif t in ('dd', 'dt'): self.where = None
    def handle_data(self, d):
        if self.cell is None: return
        self.cell['text'] += d
        if self.kp is not None:
            if self.where == 'a': self.kp['name'] += d
            elif self.where == 'dt': self.kp['tail'] += d
            elif self.where == 'dd': self.kp['dd'] += d

def parse(html_text, cfg):
    amap = {}
    for t in cfg['teams_list']:
        for n in [t['id']] + t['aliases']: amap[norm_team(n)] = t['id']
    p = Page(); p.feed(html_text)
    budget_tables = [t for t in p.tables if t and
                     {'Team', 'Remaining Budget'} <= {c['text'].strip() for c in t[0]}]
    if len(budget_tables) != 1:
        sys.exit(f"FATAL expected exactly one budget table, found {len(budget_tables)}")
    tab = budget_tables[0]
    hdr = [c['text'].strip() for c in tab[0]]
    col = {h: i for i, h in enumerate(hdr)}
    need = ['Team', 'Keepers', 'Starting Budget', 'Salaries', 'Remaining Budget']
    miss = [h for h in need if h not in col]
    if miss: sys.exit(f"FATAL budget table lacks columns {miss}; got {hdr}")
    nom_col = next((i for i, h in enumerate(hdr) if h.lower().startswith('nomination')), None)

    teams, unknown, errors = [], [], []
    for r in tab[1:]:
        if len(r) < len(hdr): continue
        name = (r[col['Team']]['title'] or r[col['Team']]['text']).strip()
        tid = amap.get(norm_team(name))
        if tid is None: unknown.append(name); continue
        start, sal, rem = (money(r[col[h]]['text']) for h in
                           ('Starting Budget', 'Salaries', 'Remaining Budget'))
        keepers = []
        for k in r[col['Keepers']]['keepers']:
            cost = money(k['dd']) if money(k['dd']) is not None else k['salary_title']
            m = re.search(r'\(([A-Z]{2,4})\s*-\s*([A-Z,]+)\)', k['tail'])
            keepers.append({'name': k['name'].strip(), 'cost': cost,
                            'nba': m.group(1) if m else '', 'pos': m.group(2).split(',') if m else []})
        nom = r[nom_col]['text'].strip() if nom_col is not None else ''
        teams.append({'id': tid, 'yahoo_name': name, 'nomination_order': nom,
                      'start': start, 'salaries': sal, 'remaining': rem, 'keepers': keepers})
        if None in (start, sal, rem): errors.append(f"{tid}: unparsed money cell")
        elif start - sal != rem: errors.append(f"{tid}: start {start} - salaries {sal} != remaining {rem}")
        ks = sum(k['cost'] or 0 for k in keepers)
        if sal is not None and ks != sal: errors.append(f"{tid}: keeper costs sum {ks} != salaries {sal}")
        if any(k['cost'] is None for k in keepers): errors.append(f"{tid}: keeper with no salary")
    if unknown:
        sys.exit(f"FATAL unmapped Yahoo team name(s) {unknown} -- add an alias in league.json")
    ids = [t['id'] for t in teams]
    if sorted(ids) != sorted(t['id'] for t in cfg['teams_list']):
        errors.append(f"team set mismatch: page has {sorted(ids)}")
    for t in teams:
        want = next(x['budget'] for x in cfg['teams_list'] if x['id'] == t['id'])
        if t['start'] != want: errors.append(f"{t['id']}: Yahoo start ${t['start']} != league.json ${want}")
    return teams, errors

def main(src, league_json='fantasy-draft/league.json', out='fantasy-draft/data/yahoo_room.json'):
    cfg = json.load(open(league_json, encoding='utf-8'))
    teams, errors = parse(open(src, encoding='utf-8', errors='replace').read(), cfg)
    spots = cfg['roster']['active_spots']
    room = {'source_file': os.path.basename(src), 'teams': teams,
            'totals': {'keepers': sum(len(t['keepers']) for t in teams),
                       'keeper_dollars': sum(t['salaries'] for t in teams),
                       'auction_dollars': sum(t['remaining'] for t in teams),
                       'auction_spots': sum(spots - len(t['keepers']) for t in teams)},
            'errors': errors}
    json.dump(room, open(out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f"{'team':13s} {'nom':>3s} {'start':>5s} {'kept$':>5s} {'left':>5s} {'open':>4s}  keepers")
    for t in sorted(teams, key=lambda t: -t['remaining']):
        ks = ', '.join(f"{k['name']} ${k['cost']}" for k in t['keepers'])
        print(f"{t['id']:13s} {t['nomination_order'] or '-':>3s} {t['start']:>5} {t['salaries']:>5} "
              f"{t['remaining']:>5} {spots - len(t['keepers']):>4}  {ks}")
    tt = room['totals']
    print(f"\n{tt['keepers']} keepers, ${tt['keeper_dollars']} | auction ${tt['auction_dollars']} "
          f"for {tt['auction_spots']} spots")
    if errors:
        print("\n!! CHECKS FAILED -- do not trust this sync:")
        for e in errors: print("   ", e)
        sys.exit(2)
    print("checks: all rows reconcile (start - salaries = remaining; keeper costs = salaries)")
    print(f"wrote {out}")

if __name__ == '__main__':
    main(*sys.argv[1:4])
