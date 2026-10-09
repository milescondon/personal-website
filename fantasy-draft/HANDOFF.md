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
redraft. This league has 34 keepers held at escalated prices, non-uniform budgets, and 11
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
| Availability | Blend weighted toward totals (α=0.5) |
| Keeper source | **The league sheet is authoritative**, not Yahoo |

---

## 2. Hard league facts (verified from source files — do not re-derive)

| Fact | Value | How it was established |
|---|---|---|
| Teams | **12** | Yahoo has exactly 12 `keeperroster` blocks. Sheet's 14 includes departed wingfreak/The City/Maatombo and omits new HR Steve. 14−3+1=12 ✓ |
| Drafted roster spots | **11** | `PG,SG,G,SF,PF,F,C,Util,BN,BN,BN`. The 2 IL slots are not drafted. Last season's draft was exactly 154 picks = 14×11 ✓ |
| Rostered pool | **132** | 12 × 11 |
| Total budget | **$2,422** | Not flat $200 — each team is $200 + bracket-challenge winnings ($200–$207). Sheet and Yahoo agree exactly on all 12. |
| Keeper escalator | **+$6/yr** | Not +$5 as originally stated. 23 keepers at +$6, 5 at +$2 (older/stashed), 6 with no acquisition price. |
| Keepers | **34**, costing **$594** | From the sheet's `Is Keeper (input 1)` column. Reconciles to the sheet's own per-team `Keeper cost` totals with **zero mismatches**. |
| Auction | **$1,828 for 98 spots** ($18.65/spot vs $18.35 flat) | |
| Scoring | 9-cat H2H: FG%, FT%, 3PTM, PTS, REB, AST, ST, BLK, TO | |
| Acquisitions | **88/season, 6/week** | Rich waiver wire → absences are streamable → lean the availability blend toward per-game |
| Playoffs | **8 of 12 (67%)** | Getting in is easy; prefer ceiling over floor |

**Strategic consequence of the shallow pool:** at 132 rostered (not the 182 originally
assumed) replacement level is high, the $1 tier is not as bad as in a deep league, stars
are relatively more valuable, and punting is **less forced** than planned.

**Jokić and Wembanyama are both kept.** SGA tops the biddable board at $74.

---

## 3. State: Block A is COMPLETE and verified

Four independent checks pass:

1. **Budget conservation** — fair values sum to exactly $2,422 over the top 132; after
   inflation, MAX over the top 98 available sums to exactly $1,828. Both exact.
2. **Keeper reconciliation** — per-team keeper costs match the sheet's own totals, 0/12 mismatches.
3. **Inflation plausibility** — **1.072**, comfortably inside the 0.8–1.6 sanity band.
4. **Cross-check vs BBM's own ranking** — Spearman ρ = 0.660. *Investigated: not a bug.*
   The divergence is entirely availability handling — BBM ranks ~per-game, we blend toward
   totals. Anthony Davis (20 projected games) is BBM #22 but ours #108; Tyler Herro (33 GP)
   is BBM #46, ours #117; full-82-game role players (LaRavia, Keldon Johnson, Kris Dunn) sit
   ~70 ranks higher for us. **This is the single most consequential tuning knob** —
   `tuning.availability_blend` in `league.json`. α=0.5 now; α→1.0 restores BBM-like per-game
   ranking.

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
  scripts/
    ingest_bbm.py             BBM .xls  -> projections.csv      (needs xlrd 2.x)
    ingest_league.py          league sheet -> keepers.csv + teams.csv
    valuation.py              z-scores, VORP, fair $, inflation, name resolution, σ_match
    build_board.py            -> build/value_board.json + build/cheat_sheet.md
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
python3 -I fantasy-draft/scripts/build_board.py   fantasy-draft
```

Pure stdlib except `xlrd` (ingest only). Nothing to install at draft time.

---

## 4. The math as implemented

**Z-scores** over an iteratively refined pool (top 132; including all 234 drags the means
and inflates everyone). TO inverted.

**Percentage categories are volume-weighted** — `impact = total_attempts × (rate − pool_rate)`,
where `pool_rate` is pool total makes / pool total attempts; then z-score the impacts. A 90%
FT shooter on 2 attempts barely matters; a 60% shooter on 10 is a real drag.

**Availability blend** — `blended_games = (1−α)·games + α·ref_games`, α=0.5, `ref` = pool
median (64). Counting stats and attempt volumes both scale by `blended_games`.

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

**Category weights (implemented in `valuation.py`, NOT yet wired into the board).**
`w_c = exp(−½(Δ_c/σ_c)²)`, where Δ_c is your projected season category z-sum minus a
league-average team's. Peaks at 1.0 when even (production swings the most weeks), decays to
0 when far ahead (already won) or far behind (**punting, derived not declared**). An empty
roster gives all w=1, so "flexible early, commit by mid" emerges from the math.
**σ_c is calibrated by Monte Carlo, not assumed** — measured **4.49–4.58** per category vs
the closed form `sqrt(2×11)=4.69`. Punt threshold `w<0.3`.

---

## 5. Remaining work

**Block B — screenshot spike, then live tracking.** *Highest-risk item, still unverified.*
Live inflation and opponent ceilings both assume a Yahoo auction-board screenshot reliably
yields all 12 budgets and rosters. **Test this with one real screenshot before building on
it.** If unreliable, degrade to typed-shorthand budget tracking and say so plainly rather
than silently trusting bad numbers. Then: `draft_state.py` — log/undo picks, track budgets,
live inflation `(Σ remaining budgets − Σ open spots)/(Σ fair of top undrafted − open spots)`,
MAX/TARGET under current state. Persist to `state/draft.json`.

**Block C — opponent model + category drift.** `opponents.py`: per-rival
`max_bid_r = budget_r − (spots_r − 1)` (exact, the strongest available signal) →
"nobody left can outbid you", fold signals, and price-push nomination picks. Then wire the
`w_c` weights into board re-scoring, add punt detection + confirmation, and live positional
replacement (1 C slot + Util, so center scarcity is milder than first assumed).

**Block D — if time.** G-score variance correction; tier-cliff and budget-pace alerts.

**`SKILL.md` is not written yet.** Needs the shorthand grammar
(`jokic 71 t4` / `sart 1 me` / `giannis?` / `board` / `me` / `nom` / `undo` / `sync`),
output format, and alert triggers. Install step: symlink `fantasy-draft/` into
`.claude/skills/` (`.claude/` is gitignored, which is why the skill lives at repo root).

---

## 6. Open items / cautions

- **`availability_blend` (α=0.5) is the biggest unvalidated judgement call.** It's what
  separates our board from BBM's. Miles chose "blend toward totals"; he should eyeball
  Anthony Davis at ~$4 and decide whether that's right for him.
- **4 keepers have no projection row** (Lillard, Haliburton, Scoot Henderson, Jared McCain —
  all injury stashes absent from BBM's 234). Their cost is counted, they contribute no value,
  and they are **excluded from the biddable sheet** so they're never recommended. Correct, but
  know that it's deliberate.
- **The keeper set came from the sheet, which disagrees with Yahoo on 6 players**
  (Reaves vs Haliburton for BB®; Lillard for batmanu; four rookies for cha Qing). Miles chose
  the sheet. If a disputed player gets nominated tonight, the sheet was wrong — log him and
  the board self-corrects.
- **Team names differ between sources** ("O Captain" vs "O Captains", "Whyy" vs "Whyyy",
  "AND TAI 1" vs "AND TAI1"). Aliases are explicit in `league.json`; an unmapped name is
  **fatal by design**, because silent dropping already cost 5 teams' keepers once.
- Testing is compressed (same-day build). Trust the price board more than the live-tracking
  layer; `cheat_sheet.md` is the printable fallback.
- No unit tests yet. The four verification checks above run inside `build_board.py` and print
  on every build.
