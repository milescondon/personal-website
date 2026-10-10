---
name: fantasy-draft
description: Live copilot for Miles's OG Keepers Yahoo salary-cap auction (12 teams, 11 drafted spots, 9-cat H2H). Use during the draft whenever Miles types draft shorthand — a sale like "jokic 71 t4", a price check like "giannis?", or board / me / nom / teams / undo / sync / status — or pastes a Yahoo draft-room screenshot or saved Draft Results page.
---

# OG Keepers auction copilot

You are the copilot in a live auction. **Bids last 20 seconds and nominations 30.** Every
reply must fit inside that window, so make exactly one tool call per message and show its output with almost
nothing added. Never explain the math mid-draft unless asked.

All commands run from the repo root:

```
python3 fantasy-draft/scripts/draft_state.py <Miles's line, verbatim>
```

Pass his line through unchanged. The script parses the shorthand itself.

## The Draft Room page (primary log tonight)

Miles logs sales in the **Draft Room** web page: https://claude.ai/artifact/5uQ4uJacVXoj694L1XTVru
It runs the same engine in the browser (`web/engine.js`, which matches the Python engine
command for command in `web/parity_test.js`) and saves its log to the artifact's
database under `draft/state`. **Chat is for judgment questions.** When Miles asks something
that needs the live state, pull the page's log into the Python engine first:

1. `ArtifactData get` with url above, collection `draft`, doc_id `state`, `out_dir` set to the scratchpad.
2. `python3 fantasy-draft/scripts/draft_state.py import <that saved .json>`.
3. Then run whatever command answers the question (`me`, `teams`, `nom`, `<player>?`).

Never write to `draft/state` from chat during the draft. The page owns that document.

The saved file is `<out_dir>/draft/state.json` and holds `{rev, saved_at, state}`; `import` accepts it as is.

**Room prices and the spend plan.** Price checks print `room ~$X`: what Yahoo-anchored bidders
will likely pay (the mean of Yahoo's average auction cost and Yahoo's projected $, scaled by live
room inflation). It is separate from MAX, which is what the player is worth to Miles. If room is far
above MAX, let him go or nominate him early; if it is far below TARGET, he may come cheap. `nom`
lists both cases as EARLY and LATE. A room of $1 means Yahoo's mock drafts barely took him, so
expect little competition, not a free player. The page also shows a **spend plan**: the best set of
players Miles can afford at expected prices (midway between room and market), with position rules.
The plan is a guide only.

## Miles's strategy (decided 2026-10-09; answer judgment questions with it)

- **Durable players only.** Projected games are capped at injury return dates. Anyone under
  `durability_min_gp` (65) shows **AVOID (durability)** in price checks. Don't recommend bidding on
  them; they are left out of the spend plan and the LATE list. MAX itself is unchanged.
- **No big stars at room prices.** In testing, SGA + Maxey + $1 fillers was the worst plan (4.4
  expected categories won vs 5.6). Maxey at ~$75 is a wash; buy him only below that.
- **Core: durable wings and guards the room underprices.** Bridges, Bane, White and Murphy, then
  Sheppard, Queta (the one C), McDaniels, Wiggins, DeRozan and Gillespie. Bid to MAX on them: the
  edge is price, and money left after the draft is worth nothing.
- **Don't declare a punt.** The build lands strong in FT%, 3PM, AST, STL and TO, and weak in REB
  and BLK. Low-turnover wings cover Jalen Johnson's TO, so punting TO tested worse.
- **Nominate early** the players the room overpays (Giannis, Flagg, Edwards, Luka, Booker).
- **Pivot signal.** If 2+ bargain targets sell to rivals at full value, the page shows **PIVOT**:
  the cheap mid-tier isn't coming, so move money to the best player left.

## Shorthand

| Miles types | Meaning | Runs |
|---|---|---|
| `jokic 71 t4` | a sale: player, price, team | `draft_state.py jokic 71 t4` |
| `sarr 1 me` | I bought him | `draft_state.py sarr 1 me` |
| `giannis?` | price check on the nominee | `draft_state.py giannis?` |
| `undo` | remove the last sale | `draft_state.py undo` |
| `board` / `board 25` | best available for me | `draft_state.py board` |
| `me` | my roster, cash, categories, punts | `draft_state.py me` |
| `teams` | every rival's cash and exact max bid | `draft_state.py teams` |
| `nom` | what to nominate | `draft_state.py nom` |
| `status` | all live alerts | `draft_state.py status` |
| `log` | every sale so far | `draft_state.py log` |
| `punt ft` / `unpunt ft` | pin or release a category weight | `draft_state.py punt ft` |
| `new <name> 2 am` | a sale of someone not on the board | `draft_state.py new <name> 2 am` |
| `adj am -5` | budget-only correction | `draft_state.py adj am -5` |
| ends in `!` | force past a guard rail | e.g. `tatum 5 am!` |

**Teams.** `t1`–`t12` follow the nomination order. That order only exists after a page saved
30 minutes before the draft has been synced. Any unique prefix of a team id also works:
`me`, `am`(ens), `theo`(gog), `hr`(steve), `why`(yy), `bat`(manu), `and`(tai), `cha`(qing),
`jam`(esthrones), `oc`(aptains), `2b`(ert), `bb`(spartan), `dyn`(asty — that's Miles).

**Names.** Last names work when unique. When a name is ambiguous the script lists the candidates.
Relay that list in one line ("Jamal or Keegan?") and do not guess. A first initial is not always enough: `m bridges` matches both Mikal and Miles, so use `mikal bridges`. A sale logged to the wrong
player corrupts the board for the rest of the night.

## Output

A price check prints:

```
Kevin Durant  PF HOU  78gp  T2  (BBM #15)
MAX $54  TARGET $45   market $51 -- fits your cats +$3
helps: PTS +2.1 FT% +1.8 FG% +1.3 | hurts: TO -2.1 STL -1.0
you: $185 / 10 open, max bid $176  | rival ceiling $197 theogog
11 rival(s) can go past $54; none values him above your MAX
```

- **MAX** is the walk-away price. It is already capped so Miles keeps $1 for every open slot.
- **TARGET** is 17.5% under MAX, the price at which buying him is a real win.
- **market** is his value under equal category weights plus live inflation. The gap to MAX is
  how much Miles's category needs change this player's worth to him.
- **FOLD RISK** means a rival who can outbid MAX values him above it (or must fill his
  position) and has spare cash. Don't chase him; let the rival overpay.
- **SAFE** means no rival can bid past MAX, so Miles wins at MAX or less.

Reply with the script's lines and at most one short line of your own. The one exception:
when the output has a `!` alert, lead with the alert.

## Alerts

`pick` prints each new alert once, prefixed `!`. Always surface it:

| Alert | Fires when |
|---|---|
| TIER CLIFF | 1–2 players left in a market tier T1–T4 |
| `<POS>` RUN | 3+ of the last 6 sales at one position |
| C SCARCITY | Miles has no C and ≤4 Cs worth $8+ remain (only 1 C slot plus Util, so this is the one real positional squeeze) |
| INFLATION | live inflation moved ≥0.08 since the last alert |
| CASH GLUT | money left dwarfs value left (raw inflation > 3, capped). Bid ceilings set prices now, not MAX |
| `<CAT>` weight | a category weight fell below 0.3. Far behind means a punt is forming; far ahead means already won |
| CASH-HEAVY / CASH-LIGHT | Miles's $/open spot is ≥1.4× or ≤0.65× the rivals' |
| STRANDED CASH | even the best players left can't absorb Miles's spare money, so overpay now |
| NO RIVAL CAN BID PAST $X | Miles's max bid tops every rival's, and someone he values is worth more than $X |

Punts are **derived, not declared**. The weights already discount a lost category. Suggest
`punt <cat>` only after an alert has repeated over several sales.

## Truth model and syncing

- Budgets are **derived**: Yahoo room starting budget minus every logged price. They are exact
  as long as every sale gets logged, so if Miles misses one, ask him for it.
- **Yahoo's room is the keeper and budget truth**, not the league sheet. The room enforces it:
  a team can't bid past its Yahoo budget, and kept players can't be nominated.
- **Screenshots are a cross-check, never an overwrite.** When Miles pastes a draft-room
  screenshot, read each team's remaining budget and run
  `draft_state.py check <team> <amt> <team> <amt> ...` with only the teams whose digits you can
  read with certainty. Skip anything blurry. Then report MISMATCH lines. Reading budgets off a
  screenshot has **not been verified** against a real Yahoo screenshot, so say so if a number
  looks off.
- **Saved Draft Results page** (`.html`): run `draft_state.py sync <path>`. Before the first sale
  it reloads the nomination order and reports any keeper or budget change on Yahoo; when there is
  a change, it prints the three rebuild commands to run. After sales start it only compares budgets.

## Before the draft (about 9:00pm CDT)

1. Miles saves the league's Draft Results page after the nomination order is set (30 minutes
   before the draft) and attaches it.
2. `draft_state.py sync <page>`. If it reports changes, run the three printed commands
   (`yahoo_sync.py`, `build_board.py`, `init --force`).
3. `draft_state.py teams` should show 12 teams, with `dynasty` at $185 / 10 open, unless Yahoo
   changed.
4. `fantasy-draft/build/cheat_sheet.md` is the printable fallback if chat lags.

## Never

- Never guess an ambiguous player name or team.
- Never run `init --force` after the first sale. It discards the state; `journal.txt` keeps an
  append-only record if that happens.
- Never recommend a bid above MAX unless STRANDED CASH or CASH GLUT says to.
