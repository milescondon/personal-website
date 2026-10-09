# Session handoff — OG Keepers auction draft agent

**Draft: Fri Oct 9 2026, 9:30pm CDT.** Nomination 30s, bid 20s.
This file is the durable record; the plan file under `/root/.claude/plans/` does **not**
survive container recycling (it was already lost once this session).

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
| Runtime | Claude Code skill, chat-driven (latency accepted; cheat sheet is the fallback) |
| Draft loop | Front-load the math; every nomination goes through chat |
| Projections | Imported pre-draft (Basketball Monster), normalized + committed |
| Punt logic | Flexible early, commit by mid-draft — emergent from category weights |
| State input | Typed shorthand + periodic Yahoo screenshot sync |
| Output | MAX + TARGET, terse, **plus proactive alerts** |
| Budget shape | Market-driven; buy surplus, no fixed allocation |
| Availability | **Waiver-fill** (changed 2026-10-09 from α=0.5 blend) — see §4 |
| Keeper source | **Yahoo's draft room** (changed 2026-10-09 from the league sheet) — see §2 |
| Miles's team | **`dynasty`** (dy-nasty warrior), $185, 10 open, Jalen Johnson kept $15 |

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
    keepers.csv               34 keepers w/ owner, acq price, keeper cost, escalator
    teams.csv                 per-team budget, keeper cost, remaining budget, open spots
    player_aliases.json       name overrides (e.g. "Alex Sarr" -> "Alexandre Sarr")
    yahoo_room.json           Yahoo room: 12 teams' keepers, start/salaries/remaining  <- KEEPER TRUTH
  SKILL.md                    the live copilot instructions + shorthand grammar
  scripts/
    ingest_bbm.py             BBM .xls  -> projections.csv      (needs xlrd 2.x)
    ingest_league.py          league sheet -> keepers.csv + teams.csv (now informational)
    yahoo_sync.py             saved Yahoo Draft Results .html -> data/yahoo_room.json
    valuation.py              z-scores, waiver line, VORP, fair $, inflation, names, σ_match
    build_board.py            -> build/value_board.json + build/cheat_sheet.md
    opponents.py              rival ceilings, category weights, personal pricing, nominations
    draft_state.py            THE LIVE ENGINE: shorthand in, MAX/TARGET/alerts out
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
difference is ~$0.70 on a $59 player — real but immaterial.* Current k = **1.072**.

**MAX / TARGET** — `MAX = min(adj under current category weights, my_budget − (my_open_spots − 1))`.
The right-hand term is inviolable: always leave $1 per unfilled slot. `TARGET = MAX × (1 − 0.175)`.

**Live inflation** — `k = (Σ budgets − open spots) / (Σ fair of top-N available − N)`,
N = open spots, capped at 3.0. **Personal price** — weights renormalized to mean 1 (they move
relative value, not the price level); replacement = 132nd player under those weights;
`MAX = min(1 + dpv·(v_w − repl_w)·k ..., budget − (open − 1))`.

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
  from the live log.
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
- **Room-price model** — "market" is our value, not the room's. Yahoo's average auction cost per
  player would let push nominations target players the room overpays for.
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
- No unit tests. The four checks print PASS/FAIL on every build. The live engine was checked
  by full-draft simulation (scratch script, not committed).
