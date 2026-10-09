#!/usr/bin/env python3
"""Build the draft-room web page and its parity fixtures.

  build_web.py data                 -> web/data.json (everything the page needs, from the board)
  build_web.py page                 -> web/dist/draft-room.html (app.html + engine.js + data inlined)
  build_web.py parity <seed> <out>  -> replay a simulated draft through the PYTHON engine and
                                       record every command plus a snapshot after each one;
                                       web/parity_test.js replays it through engine.js.
"""
import sys, os, json, random, io, contextlib, tempfile

WEB = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

def build_data():
    cfg = json.load(open(os.path.join(ROOT, 'league.json'), encoding='utf-8'))
    board = json.load(open(os.path.join(ROOT, 'build', 'value_board.json'), encoding='utf-8'))
    room = json.load(open(os.path.join(ROOT, cfg['keepers']['room_file']), encoding='utf-8'))
    aliases = json.load(open(os.path.join(ROOT, 'data', 'player_aliases.json'), encoding='utf-8'))
    bp = board['params']
    if bp.get('keeper_source') != cfg['keepers'].get('source_of_truth'):
        sys.exit('board was built from a different keeper source -- run build_board.py first')
    keep = ['name', 'nba', 'pos', 'games', 'fair', 'z', 'bbm_rank', 'kept_by', 'keeper_cost']
    return {
        'league': cfg['name'], 'draft_time': cfg['draft']['datetime'],
        'players': [{k: p[k] for k in keep} for p in board['players']],
        'aliases': aliases,
        'room': {'source_file': room.get('source_file'),
                 'teams': [{k: t[k] for k in ('id', 'yahoo_name', 'nomination_order', 'start',
                                               'salaries', 'remaining', 'keepers')} for t in room['teams']]},
        'me': cfg['me'], 'active_spots': cfg['roster']['active_spots'],
        'teams_list': [{'id': t['id'], 'aliases': t['aliases']} for t in cfg['teams_list']],
        'sigma': board['sigma_match'], 'rostered': bp['rostered'], 'dpv': bp['dollars_per_vorp'],
        'margin': bp['target_margin'], 'punt_threshold': cfg['tuning']['punt_weight_threshold'],
        'inflation_pre': bp['inflation_multiplier'], 'auction_dollars': bp['auction_dollars'],
        'auction_spots': bp['auction_spots'],
    }

def write_data():
    out = os.path.join(WEB, 'data.json')
    json.dump(build_data(), open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f"wrote {out} ({os.path.getsize(out) // 1024} KB)")

def write_page():
    data = json.dumps(build_data(), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    engine = open(os.path.join(WEB, 'engine.js'), encoding='utf-8').read()
    tpl = open(os.path.join(WEB, 'app.html'), encoding='utf-8').read()
    for ph in ('/*__DATA__*/', '/*__ENGINE__*/'):
        if tpl.count(ph) != 1: sys.exit(f'template must contain {ph} exactly once')
    page = tpl.replace('/*__ENGINE__*/', engine).replace('/*__DATA__*/', 'window.DRAFT_DATA = ' + data + ';')
    os.makedirs(os.path.join(WEB, 'dist'), exist_ok=True)
    out = os.path.join(WEB, 'dist', 'draft-room.html')
    open(out, 'w', encoding='utf-8').write(page)
    print(f"wrote {out} ({len(page.encode()) // 1024} KB)")

# ------------------------------------------------------------------ parity
def snapshot(D, O, ctx):
    me = ctx.me
    pm = ctx.pricers[me]
    top = sorted(ctx.avail, key=lambda p: -pm.adj(p))[:25]
    mk = sorted(ctx.avail, key=lambda p: -ctx.market.adj(p))[:6]
    push, drain, hold, steal = O.nominations(sorted(ctx.avail, key=lambda p: -ctx.market.adj(p)),
                                             ctx.teams, me, pm, ctx.market.adj, ctx.pricers)
    out = {'teams': {t: [x['budget'], x['open'], x['max_bid']] for t, x in ctx.teams.items()},
           'k': ctx.k, 'k_raw': ctx.k_raw, 'n_open': ctx.n_open,
           'top': [[p['name']] + list(D.Ctx.my_price(ctx, p)[:2]) +
                   [ctx.pricers[me].adj(p), ctx.market.adj(p)] for p in top],
           'alerts': [list(a) for a in D.alerts(ctx)],
           'emitted': sorted(ctx.st['emitted']), 'last_k': ctx.st['last_k'],
           'w': [ctx.wts[me][1][c] for c in O.CATS],
           'ceiling': list(O.rival_ceiling(ctx.teams, me)),
           'threats': [[(r['id'], r['val'], r['need'], r['liquid'])
                        for r in O.threats(p, D.Ctx.my_price(ctx, p)[0], ctx.teams, me, ctx.pricers)]
                       for p in mk],
           'nom': [[x[1]['name'] for x in xs] for xs in (push, drain, hold, steal)],
           'unfilled': {t: O.unfilled(x['roster']) for t, x in ctx.teams.items()}}
    return out

def parity(seed, out_path):
    os.environ['DRAFT_STATE_DIR'] = tempfile.mkdtemp()
    import draft_state as D, opponents as O, valuation as V
    rnd = random.Random(seed)
    def run(line):
        buf = io.StringIO(); ok = True
        try:
            with contextlib.redirect_stdout(buf): D.main(line.split())
        except SystemExit as e:
            ok = not e.code
        return ok, buf.getvalue()
    run('init --force')
    cmds, snaps = [], []
    def step(line):
        ok, txt = run(line)
        cmds.append(line); snaps.append(dict(snapshot(D, O, D.Ctx()), ok=ok))
        return ok, txt
    step('board')
    for i in range(400):
        ctx = D.Ctx()
        open_teams = [t for t in ctx.teams.values() if t['open'] > 0]
        if not open_teams: break
        r = rnd.random()
        pool = sorted(ctx.avail, key=lambda p: -ctx.market.adj(p))[:14]
        p = rnd.choice(pool)
        parts = V.name_parts(p['name'])
        form = rnd.random()
        name = p['name'] if form < 0.5 else (parts[-1] if form < 0.8 else parts[0][0] + ' ' + parts[-1]).lower()
        if r < 0.06 and ctx.st['picks']: step('undo'); continue
        if r < 0.09: step(name + '?'); continue
        if r < 0.11: step(rnd.choice(['murray 5 me', 'jokic 3 am', 'maxey 999 why', 'zzzz 2 hr', 'durant 4 t3',
                                      'porter 9 theo'])); continue
        if r < 0.12: step(rnd.choice(['punt ft', 'punt to', 'unpunt ft', 'unpunt to'])); continue
        if r < 0.13: step(f"adj {rnd.choice(list(ctx.teams))} {rnd.choice([-3, 2, 5])}"); continue
        m = ctx.market.adj(p)
        t = rnd.choice(open_teams)
        mx = D.Ctx.my_price(ctx, p)[0]
        price = max(1, min(round(m * rnd.uniform(0.75, 1.3)), t['max_bid']))
        if ctx.teams[ctx.me]['open'] > 0 and price <= mx and rnd.random() < 0.3:
            t = ctx.teams[ctx.me]; price = max(1, min(price, t['max_bid']))
        tok = 'me' if t['id'] == ctx.me and rnd.random() < 0.5 else t['id']
        step(f"{name} {price} {tok}")
    json.dump({'seed': seed, 'commands': cmds, 'snapshots': snaps}, open(out_path, 'w'), indent=0)
    picks = [e for e in D.Ctx().st['picks'] if e['type'] == 'pick']
    print(f"seed {seed}: {len(cmds)} commands, {len(picks)} sales, "
          f"{sum(1 for s in snaps if not s['ok'])} rejected -> {out_path}")

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'page'
    if cmd == 'data': write_data()
    elif cmd == 'page': write_page()
    elif cmd == 'parity': parity(int(sys.argv[2]), sys.argv[3])
    else: sys.exit(__doc__)
