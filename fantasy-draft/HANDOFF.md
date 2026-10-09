# Session handoff — OG Keepers auction draft agent

**Draft: Fri Oct 9 2026, 9:30pm CDT.** Nomination 30s, bid 20s.
This file is the durable record; the plan file under `/root/.claude/plans/` is stale and does
**not** survive container recycling. Branch: `claude/fantasy-basketball-draft-agent-dnfgr9`.

---

## 0. START HERE (state at handoff, ~6:45pm CDT)

**Miles drafts in the Draft Room web page** (private claude.ai artifact, `db` capability):
https://claude.ai/artifact/5uQ4uJacVXoj694L1XTVru. It is **published at version 1**, which does
NOT yet have room prices or the spend plan. Chat is the backup and the place for judgment
questions. Miles's team is `dynasty`.

**Done and committed since version 1 (all tests below pass on the committed code):**
- **Room prices** (what the room will likely pay, vs what a player is worth to Miles). Source:
  Yahoo average auction cost + Yahoo projected $, taken from chaqing's public draft tool (§6).
  Both engines; included in the Python↔JS parity test.
- **Spend plan** (page only): the value-maximizing set of available players Miles can afford at
  expected prices, with position rules (≤3 C; enough G/F/C for the starting slots; $1 fillers
  can cover a shortfall). `web/plan_test.js` checks it against brute force: 600/600.
- Page UI: Room box on the price card plus ROOM OVERPAYS / ROOM UNDERVALUES lines; Room column on
  the board; "Nominate early: room overpays" / "Nominate late: room undervalues" lists; the spend
  plan under Your team, with a fallback message when no plan fits.
- `web/dist/draft-room.html` is rebuilt and matches the current sources exactly.

**Next steps, in order:**
1. **Browser smoke test** of `web/dist/draft-room.html`. This has NOT been run since the
   position-aware plan and the no-plan fallback went in. See "Smoke test" in §4b. Check: no
   console errors, no horizontal overflow at 400px, the price card shows Room, and the plan updates
   after `maxey 76 me`.
2. **Republish** to the SAME URL. A new session must first `Artifact` `action:"read"` that URL
   (a publish to an artifact the session hasn't read is refused), then publish with
   `file_path: fantasy-draft/web/dist/draft-room.html` and `url:` the artifact URL. **Omit
   `capabilities`** (keeps `db`) and **omit `icon`**. The db log survives republishes.
3. Optional: add a line on room prices + the spend plan to `SKILL.md` (it doesn't mention them yet).
4. **~9:00pm:** Miles saves Yahoo's Draft Results page after the nomination order is set and
   uses the page's **Check Yahoo page…** button (or sends it to chat → `draft_state.py sync`).
   - It sets `t1`–`t12`. Typing `order <12 team prefixes in order>` also works.
   - If keepers/budgets CHANGED: `yahoo_sync.py <page>` → `build_board.py fantasy-draft` →
     `web/build_web.py data` → `web/build_web.py page` → republish (step 2). Do it before the
     first sale.
5. **During the draft**, when Miles asks a question needing live state: `ArtifactData get`,
   url above, collection `draft`, doc_id `state`, with `out_dir` → `python3
   fantasy-draft/scripts/draft_state.py import <saved json>` → answer with `me`/`teams`/`nom`/
   `<player>?`. **Never write `draft/state` from chat during the draft.**

**Tests to rerun after any engine change** (all were passing at handoff):
```bash
python3 -I fantasy-draft/scripts/build_board.py fantasy-draft | grep -E 'PASS|FAIL'   # 4 PASS
python3 -I fantasy-draft/web/build_web.py data
for s in 1 2 3; do python3 -I fantasy-draft/web/build_web.py parity $s /tmp/fx$s.json; done
node fantasy-draft/web/parity_test.js /tmp/fx1.json /tmp/fx2.json /tmp/fx3.json        # 3 PASS
node fantasy-draft/web/plan_test.js                                                    # 600/600
python3 -I fantasy-draft/web/build_web.py page
```
Run Python with `DRAFT_STATE_DIR=<scratch dir>` when testing `draft_state.py` by hand, so the
real `fantasy-draft/state/` is never touched (the parity generator already uses a temp dir).

**Numbers worth knowing tonight** (pre-draft, waiver-fill board, room k 1.334):
- Room overpays: Giannis room ~$77 vs worth ~$10 to Miles; Cooper Flagg ~$65 vs $29; Anthony
  Edwards ~$72 vs $44. Nominate these early.
- Room undervalues: Kevin Porter Jr. ~$1 vs $26; Mikal Bridges ~$10 vs $34; Jimmy Butler ~$1
  vs $24; also Queta, Sheppard, Vucevic, Quickley, Wiggins, Suggs. Nominate these late.
- Pre-draft spend plan: Maxey ~$75 + Bridges, Porter Jr., Butler, Suggs, Sheppard, Wiggins,
  Queta, DeRozan, Vucevic at $9–21 = $185.

---

## 1. What this is

A Claude Code skill that acts as a live copilot during Miles's Yahoo salary-cap auction.
Before the draft it computes a price board correct for *this* league; during the draft
Miles logs each sale with terse shorthand and asks about players he's about to bid on.

**Why it beats a public board.** Every public dollar value assumes a 12-team no-keeper
redraft. This league has 35 keepers held at escalated prices, non-uniform budgets, and 11
(not 13) drafted roster spots. Those distortions are computable, and ignoring them is how
you under-bid all night and finish holding unspendable cash.

Decisions Miles made during design (all still binding):

| Topic | Decision |
|---|---|
| Core job | Live in-draft copilot, not a static sheet |
| Runtime | **Draft Room web page** is the primary log (built 2026-10-09); chat skill for questions; cheat sheet is the last fallback |
| Draft loop | Front-load the math; log every sale in the page |
| Projections | Imported pre-draft (Basketball Monster), normalized + committed |
| Punt logic | Flexible early, commit by mid-draft — emergent from category weights |
| State input | Typed shorthand + periodic Yahoo screenshot sync |
| Output | MAX + TARGET, terse, **plus proactive alerts** |
| Budget shape | Market-driven; buy surplus, no fixed allocation |
| Availability | **Waiver-fill** (changed 2026-10-09 from α=0.5 blend) — see §4 |
| Keeper source | **Yahoo's draft room** (changed 2026-10-09 from the league sheet) — see §2 |
| Miles's team | **`dynasty`** (dy-nasty warrior), $185, 10 open, Jalen Johnson kept $15 |
| Room prices | Use Yahoo avg cost + Yahoo projected $ from chaqing's public tool (Miles, 2026-10-09) |
| Spend plan | Build it (Miles, 2026-10-09), position-aware |

---

## 2. Hard league facts (verified from source files — do not re-derive)

| Fact | Value | How it was established |
|---|---|---|
| Teams | **12** | Yahoo has exactly 12 `keeperroster` blocks. Sheet's 14 includes departed wingfreak/The City/Maatombo and omits new HR Steve. 14−3+1=12 ✓ |
| Drafted roster spots | **11** | `PG,SG,G,SF,PF,F,C,Util,BN,BN,BN`. The 2 IL slots are not drafted. Last season's draft was exactly 154 picks = 14×11 ✓ |
| Rostered pool | **132** | 12 × 11 |
| Total budget | **$2,422** | Not flat $200 — each team is $200 + bracket-challenge winnings ($200–$207). Sheet and Yahoo agree exactly on all 12. |
| Keeper escalator | **+$6/yr** | Not +$5 as originally stated. 23 keepers at +$6, 5 at +$2 (older/stashed), 6 with no acquisition price. |
| Keepers | **35**, costing **$632** (Yahoo room) | Yahoo's Draft Results page, saved 2026-10-09. Every row reconciles (start − salaries = remaining; keeper costs = salaries). The league sheet said 34 / $594 — see below. |
| Auction | **$1,790 for 97 spots** ($18.45/spot) | |
| Scoring | 9-cat H2H: FG%, FT%, 3PTM, PTS, REB, AST, ST, BLK, TO | |
| Acquisitions | **88/season, 6/week** | Rich waiver wire → absences are streamable → lean the availability blend toward per-game |
| Playoffs | **8 of 12 (67%)** | Getting in is easy; prefer ceiling over floor |

**Strategic consequence of the shallow pool:** at 132 rostered (not the 182 originally
assumed) replacement level is high, the $1 tier is not as bad as in a deep league, stars
are relatively more valuable, and punting is **less forced** than planned.

**Jokić and Wembanyama are both kept.** SGA tops the biddable board at $89 (waiver-fill).

**Yahoo vs the league sheet (resolved 2026-10-09 in favour of Yahoo).** The Yahoo room page
agrees with the sheet on 9 of 12 teams. The three differences: **amens** also keeps Jayson
Tatum $25 ($68 left, not $93); **bbspartan** keeps Austin Reaves $29 *and* Haliburton $9 ($163,
not $192); **theogog** keeps nobody, so **Kevin Durant is in the auction pool** ($207, not $191).
Yahoo enforces its own numbers in the room (bid limits, no nominating keepers), so the engine
uses them. If the commissioner fixes Yahoo before the draft, a fresh page save + `sync` picks it up.

---

## 3. State: Blocks A, B, C and SKILL.md are COMPLETE

`build_board.py` prints four PASS/FAIL checks on every build. Current build (waiver-fill,
Yahoo keepers), all PASS:

1. **Budget conservation** — fair values over the top 132 sum to exactly $2,422; MAX over the
   97-player auction pool sums to exactly $1,790.
2. **Keeper reconciliation** — per-team keeper costs match Yahoo's `Salaries` column, 0/12 mismatches.
3. **Inflation plausibility** — **1.083**, inside the 0.8–1.6 band.
4. **Cross-check vs BBM** — Spearman ρ = **0.839** (was 0.660 under α=0.5). The remaining
   disagreements are near-zero-GP players (Kessler 5 GP, Richmond 3 GP), which waiver-fill
   discounts by design.

The α=0.5 blend still reproduces the 4f2613f board byte-for-byte (regression-checked).

**Live engine** (`draft_state.py` + `opponents.py`) was stress-tested with 5 simulated 97-sale
drafts: after every sale total money is conserved exactly, no team drops below $1/open slot,
and inflation stays in [0, 3]. Simulation surfaced and fixed a real bug: raw live inflation
hit 5.7 late (leftover cash ≫ value left) and the old guard jumped discontinuously to 1.0;
it is now capped at 3.0 with a CASH GLUT alert.

**Block B (screenshot spike) — NOT done as specified.** No draft-room screenshot was
provided; Miles sent a saved Draft Results `.html` instead, which parses deterministically
(`yahoo_sync.py`) and is better pre-draft. Consequence: **budgets come from typed shorthand**
(exact while every sale is logged), and screenshots are a **cross-check only** (`check`
reports mismatches, never overwrites). Reading budgets off a real Yahoo screenshot is still
untested. Whether the Draft Results page updates *during* the draft is also unknown.

### Files

```
fantasy-draft/
  league.json                 league params, per-team budgets, team aliases, tuning knobs
  HANDOFF.md                  this file
  data/
    projections.csv           234 players from BBM (per-game + fga/fta + projected games)
    keepers.csv               the league SHEET's 34 keepers (reference only; Yahoo room is truth)
    teams.csv                 per-team budget, keeper cost, remaining budget, open spots
    player_aliases.json       name overrides (e.g. "Alex Sarr" -> "Alexandre Sarr")
    yahoo_room.json           Yahoo room: 12 teams' keepers, start/salaries/remaining  <- KEEPER TRUTH
    yahoo_prices.csv          265 players: Yahoo avg auction cost + Yahoo projected $ (see §6)
  SKILL.md                    the live copilot instructions + shorthand grammar
  scripts/
    ingest_bbm.py             BBM .xls  -> projections.csv      (needs xlrd 2.x)
    ingest_league.py          league sheet -> keepers.csv + teams.csv (now informational)
    yahoo_sync.py             saved Yahoo Draft Results .html -> data/yahoo_room.json
    valuation.py              z-scores, waiver line, VORP, fair $, inflation, names, σ_match
    build_board.py            -> build/value_board.json + build/cheat_sheet.md
    opponents.py              rival ceilings, category weights, personal pricing, nominations
    draft_state.py            the Python live engine: shorthand in, MAX/TARGET/room/alerts out
  web/
    engine.js                 JS port of draft_state + opponents (+ spend plan, page only)
    app.html                  the page template (UI); build_web.py inlines engine + data
    build_web.py              data | page | parity <seed> <out>
    parity_test.js            replays Python-recorded drafts through engine.js
    plan_test.js              spend-plan optimizer vs brute force
    data.json                 board data for Node tests (same as what the page embeds)
    dist/draft-room.html      the built page that gets published
  state/                      (gitignored) draft.json + append-only journal.txt
  build/
    value_board.json          full board incl. per-category z, tiers, keeper surplus
    cheat_sheet.md            printable MAX/TARGET sheet, 104 biddable players
```

### Rebuild from scratch

```bash
python3 -m pip install xlrd                      # 2.x — .xls only, which is what BBM exports
python3 -I fantasy-draft/scripts/ingest_bbm.py    <BBM.xls>        fantasy-draft/data/projections.csv
python3 -I fantasy-draft/scripts/ingest_league.py <Teams.csv> fantasy-draft/league.json \
        fantasy-draft/data/keepers.csv fantasy-draft/data/teams.csv
python3 -I fantasy-draft/scripts/yahoo_sync.py   <DraftResults.html>  # -> data/yahoo_room.json
python3 -I fantasy-draft/scripts/build_board.py   fantasy-draft
python3 -I fantasy-draft/scripts/draft_state.py   init --force       # only before the first sale
```

Install the skill: `mkdir -p .claude/skills && ln -sfn ../../fantasy-draft .claude/skills/fantasy-draft`
(skills load at session start, so start a new Claude Code session after linking).

Pure stdlib except `xlrd` (ingest only). Nothing to install at draft time.

---

## 4. The math as implemented

**Z-scores** over an iteratively refined pool (top 132; including all 234 drags the means
and inflates everyone). TO inverted.

**Percentage categories are volume-weighted** — `impact = total_attempts × (rate − pool_rate)`,
where `pool_rate` is pool total makes / pool total attempts; then z-score the impacts. A 90%
FT shooter on 2 attempts barely matters; a 60% shooter on 10 is a real drag.

**Availability: waiver-fill** (`tuning.availability_model = "waiver_fill"`). Season line =
`GP × own per-game + (82 − GP) × waiver line`, where the waiver line is the mean per-game
line of per-game ranks 133–156 (11.1 pts, 1.3 3PM, 5.5 reb, 2.4 ast, 46% FG / 76% FT). So value
above replacement is `GP × (per-game − waiver)`: with 2 IL slots and 6 adds/week a missed game
is streamed, and durability only counts on top of above-waiver production. Percentage impact
is `makes − pool_rate × attempts` (identical to the old formula under the blend).
Why not α: at α=0.5 Markkanen/Curry/Butler were $7–$23 underpriced *and* 82-GP below-waiver
players were paid for durability (Kris Dunn $8 → $1 now). Giannis is genuinely ~$10 in 9-cat
under any setting (BBM itself ranks him #67 per-game, FT% −2.8z); a $45 room price is name value.
Caveat: waiver-fill overstates how streamable rest days/DTD absences are (no IL slot frees up).

**VORP** — replacement = the 132nd-ranked player's weighted value.

**Fair dollars** — `fair = 1 + (budget − 132) × max(vorp,0) / Σ positive vorp`. Sums to $2,422.

**Keeper inflation — surplus-only:**
```
k   = (auction_dollars − auction_spots) / (pool_fair_value − auction_spots)
adj = 1 + (fair − 1) × k
```
Inflating only the surplus above $1 is correct because no player can cost under $1. The
naive `fair × k` would price a $1.10 player at $1.18. *Verified numerically earlier: the
difference is ~$0.70 on a $59 player — real but immaterial.* Current k = **1.083**.

**MAX / TARGET** — `MAX = min(adj under current category weights, my_budget − (my_open_spots − 1))`.
The right-hand term is inviolable: always leave $1 per unfilled slot. `TARGET = MAX × (1 − 0.175)`.

**Live inflation** — `k = (Σ budgets − open spots) / (Σ fair of top-N available − N)`,
N = open spots, capped at 3.0. **Personal price** — weights renormalized to mean 1 (they move
relative value, not the price level); replacement = 132nd player under those weights;
`MAX = min(1 + dpv·(v_w − repl_w)·k ..., budget − (open − 1))`.

**Room price** (`opponents.room_k/room_price`, `engine.js roomK/roomPrice`):
`room_anchor = (yahoo_avg + yahoo_proj) / 2`, set at build time. Managers anchor on the two numbers
Yahoo's draft room shows. Live: `room_k = (Σ budgets − N) / Σ(anchor − 1 over top-N available by
anchor)`, capped at 3, and `room = 1 + max(anchor − 1, 0) · room_k`. No Yahoo price → market
value. Nominations: overpay = room ≥ $10, room − my value ≥ $5, and 2+ rivals can afford it;
late = my value ≥ $8 and my value − room ≥ $5.

**Spend plan** (`engine.js spendPlan/planKnapsack`, page only): top 50 available by Miles's value;
expected cost = round(midpoint of room and market), at least $1; DP over (buys, guards capped at 3,
forwards capped at 3, centers ≤ 3, dollars) maximizing value + $1 per filler; keeps $1 per filler.
Groups: PG/SG → guard, SF/PF → forward, C → center (BBM single positions, so approximate).

**Category weights (wired into `opponents.py`; used for Miles AND every rival).**
`w_c = exp(−½(Δ_c/σ_c)²)`, where Δ_c is your projected season category z-sum minus a
league-average team's. Peaks at 1.0 when even (production swings the most weeks), decays to
0 when far ahead (already won) or far behind (**punting, derived not declared**). An empty
roster gives all w=1, so "flexible early, commit by mid" emerges from the math.
**σ_c is calibrated by Monte Carlo, not assumed** — measured **4.49–4.58** per category vs
the closed form `sqrt(2×11)=4.69`. Punt threshold `w<0.3`.

---

## 4b. The Draft Room web page

https://claude.ai/artifact/5uQ4uJacVXoj694L1XTVru, a private claude.ai page with the
`db` capability. It is the primary sale log for the draft.

- `web/engine.js` is a line-for-line port of `draft_state.py` + `opponents.py` + name
  resolution, copying Python's round-half-even and half-even formatting.
- `web/build_web.py parity <seed> <out>` records a simulated draft through the Python engine;
  `node web/parity_test.js <fixtures>` replays it through the JS engine. 3 seeded drafts (412
  commands, 51 rejected) match exactly; 4 planted mutations are each caught.
- State lives in the artifact db doc `draft/state` as `{rev, state, saved_at}`, mirrored to
  localStorage. The page adopts whichever copy has the higher `rev`.
- `draft_state.py import <file>` adopts a saved copy of that doc so chat can answer questions
  from the live log. Round-trip checked: a JS-made state imports with identical budgets and k.
- Commands only the page has: `order <12 teams>` (set nomination order by hand). The page also
  has Copy state (backup), Reset draft (two-click confirm), and Check Yahoo page (file input).
- **Smoke test** (Playwright for Node is installed; Chromium at /opt/pw-browsers): wrap the dist
  file in `<!doctype html><html><head><meta charset=utf8><meta name=viewport
  content="width=device-width,initial-scale=1"></head><body>…</body></html>`, open it with
  `require('/opt/node22/lib/node_modules/playwright').chromium`, type into `#cmd`, read `#result`,
  `#p-nominee`, `#nom`, `#me`, and check `document.documentElement.scrollWidth - innerWidth` at
  400/720/1400px plus console errors. Version 1 passed all of this; the current build hasn't been run.
- Rebuild + republish: `python3 -I fantasy-draft/web/build_web.py data && python3 -I
  fantasy-draft/web/build_web.py page`, then publish `web/dist/draft-room.html` to the same URL.
  The board data is baked into the page, so a board rebuild (e.g. a keeper change at 9pm)
  needs a republish. The db log survives republishes.

## 5. Remaining work

- **~9:00pm CDT:** save the Draft Results page after nomination order is set → `sync`. Enables
  `t1`–`t12` and catches any commissioner keeper fix.
- **Screenshot reading** — still untested against a real Yahoo draft-room screenshot. It is a
  cross-check only, so a misread can't corrupt state, but it shouldn't be trusted until seen.
- **Mid-draft page sync** — the picks-table format is unknown. Saving the "2025 season draft
  results" view of the same page would show it and allow a parser.
- **Positions are BBM single-position** for non-keepers (keepers use Yahoo multi-position), so
  `unfilled`/acute-need signals are approximate.
- **Projected H2H results** (idea from chaqing's tool, deferred): categories won vs each team and
  projected rank at full rosters. Needs every team's roster projected; not done.
- **Block D (if time):** G-score variance correction.

---

## 6. Open items / cautions

- **Availability: settled** — waiver-fill (Miles, 2026-10-09).
- **4 keepers have no projection row** (Lillard, Haliburton, Scoot Henderson, Jared McCain —
  all injury stashes absent from BBM's 234). Their cost is counted, they contribute no value,
  and they are **excluded from the biddable sheet** so they're never recommended. Correct, but
  know that it's deliberate.
- **Keeper set: Yahoo room** (Miles, 2026-10-09; supersedes "sheet is authoritative"). The
  sheet/Yahoo dispute narrowed from 6 players to 3 teams once Yahoo's keeper salaries were filled
  in. If a Yahoo-kept player is ever nominated, log the sale with a trailing `!`
  (`tatum 5 am!`); the engine removes him from the keeper list.
- **Team names differ between sources** ("O Captain" vs "O Captains", "Whyy" vs "Whyyy",
  "AND TAI 1" vs "AND TAI1"). Aliases are explicit in `league.json`; an unmapped name is
  **fatal by design**, because silent dropping already cost 5 teams' keepers once.
- Testing is compressed (same-day build). Trust the price board more than the live-tracking
  layer; `cheat_sheet.md` is the printable fallback.
- Tests: the four board checks (every build), Python↔JS parity (`web/parity_test.js`, includes
  4 caught mutations), and the spend-plan brute force (`web/plan_test.js`). The early 5-draft
  Python simulation script was scratch and is gone; the parity generator covers the same ground.
- **Gotcha:** `Ctx.room` in `draft_state.py` is the Yahoo room JSON. The room-price method is
  `Ctx.room_price`. Naming it `room` crashed everything once.
- **Gotcha:** Python `round()` is round-half-even. The JS port uses `pyRound`/`pyFixed`. Plain
  `Math.round` changed a TARGET from $16 to $17 in a mutation test.

### chaqing's public draft tool (rival intel + room-price source)
https://claude.ai/artifact/2xZNQ2nW5vE2cxZ677no6m, titled "cha Qing Draft Room", is shared by
public link and built by the **chaqing** team. Read it with `Artifact action:"read"`; the raw HTML
is saved locally and line 317 is `const D = {...}`. Per player: `avg` (Yahoo avg auction cost),
`yp` (Yahoo projected $), `exp` (their room estimate ≈ mean(avg, yp) × 1.269), `our` (their $ under
5 strategies: bal, pft, pftto, past, bigs).
- Its league reading matches ours exactly ($1,790 / 97 spots / $632 kept).
- Its `avg` tracks the Yahoo avg in our keepers.csv with Spearman 0.947, mean |diff| $3 over 30
  keepers. Probably a later Yahoo snapshot; the date is unknown.
- `data/yahoo_prices.csv` is copied from it (265 players; 93/97 of our auction pool covered).
- A Yahoo avg of $0 likely means undrafted in mock drafts. Treat it as "low competition", not
  "free".
- chaqing's own walk-away prices for players they need: Holmgren $28–38 (Miles's MAX $42), Towns
  $36–47, Duren $31–42, Clingan $17–27, Adebayo $29–34. Giannis $65–66 under their punt-FT
  strategies. Their chosen strategy is set inside their tool and isn't visible.
