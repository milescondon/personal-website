# Embed Paper PDFs on Self-Hosted Reader Pages

**Date:** 2026-06-24
**Status:** Approved (design)

## Problem

The three "Read Paper" links in the *Selected Academic Research* section of `index.html`
currently point straight out to publisher sites (Springer, Emerald, APA). Those papers sit
behind paywalls, so visitors without an institutional account cannot actually read them. The
goal is to host the PDFs on the site itself and send "Read Paper" to a self-hosted page that
embeds the full article.

## Decisions (locked with user)

1. **Host the PDFs as-is.** The user accepts that these are the published version-of-record
   PDFs and any associated publisher-agreement risk. (Flagged during brainstorming; user chose
   "host as-is".)
2. **A dedicated HTML page per paper** (not a single reusable viewer, not a raw-PDF link).
   Gives clean, shareable, citable URLs and matches the existing per-page pattern
   (`tandem.html`).
3. **Keep the publisher link** on each page as a secondary `View on publisher ↗` button,
   preserving the "this is peer-reviewed and published" signal.

## Files & structure

Move the three PDFs (currently in the repo root) into a new `papers/` folder with URL-safe
names:

| Source PDF (repo root)            | Destination                                |
|-----------------------------------|--------------------------------------------|
| `BrandCommunityDissolution.pdf`   | `papers/brand-community-dissolution.pdf`   |
| `NonprofitReBranding.pdf`         | `papers/nonprofit-rebranding.pdf`          |
| `HeatAggressionTerrorism.pdf`     | `papers/heat-aggression-terrorism.pdf`     |

The original copies in the repo root are removed after the move (no duplicates committed).

Three new HTML pages at the repo root (clean URLs):

| Page                                  | Paper                                                          |
|---------------------------------------|---------------------------------------------------------------|
| `brand-community-dissolution.html`    | Exploring the Effects of Brand Community Dissolution           |
| `nonprofit-rebranding.html`           | Rewriting the Story: Navigating Nonprofit Brand Evolution      |
| `heat-aggression-terrorism.html`      | Collectivism and the Heat–Aggression Relationship in Terrorism |

## Page anatomy

Each page reuses the existing `resume-bar` header and `styles.css`, so it is on-brand with no
new design system work. Top to bottom:

1. **Back-bar header** — `← Miles Condon` (links to `index.html`) + `Get In Touch`
   (mailto). Identical to the `tandem.html` / `resume.html` header.
2. **Eyebrow** — journal · year (e.g. `Marketing Letters · 2026`).
3. **Title** — the full paper title.
4. **Summary** — the plain-English blurb, reused **verbatim** from the matching card in
   `index.html`. No new copy is written (respects existing copy-style rules).
5. **Action row** — two buttons:
   - `Download PDF` (primary) → the local `papers/*.pdf`, `download` attribute set.
   - `View on publisher ↗` (outline) → the original publisher URL, `target="_blank"
     rel="noopener"`.
6. **Embedded PDF** — fills the remaining width below the actions.

### Per-page data (the only thing that differs between the three pages)

| Page | Eyebrow | Title | Blurb (from card) | PDF | Publisher URL |
|------|---------|-------|-------------------|-----|---------------|
| brand-community | Marketing Letters · 2026 | Exploring the Effects of Brand Community Dissolution | (card line) | papers/brand-community-dissolution.pdf | https://link.springer.com/article/10.1007/s11002-026-09812-x |
| nonprofit-rebranding | The CASE Journal · 2026 | Rewriting the Story: Navigating Nonprofit Brand Evolution | (card line) | papers/nonprofit-rebranding.pdf | https://www.emerald.com/tcj/article-abstract/doi/10.1108/TCJ-06-2025-0219/1368661/Rewriting-the-story-navigating-nonprofit-brand |
| heat-aggression | Psychology of Violence · 2025 | Collectivism and the Heat–Aggression Relationship in Terrorism | (card line) | papers/heat-aggression-terrorism.pdf | https://doi.org/10.1037/vio0000652 |

## The embed (mobile-safe, dependency-free)

Desktop browsers render PDFs inline, so a native embed is used:

```html
<object data="papers/<name>.pdf#view=FitH" type="application/pdf" class="paper-viewer">
  <!-- fallback shown when inline rendering is unavailable (mobile) -->
  <p>Your browser can't display this PDF inline.
     <a href="papers/<name>.pdf">Download the PDF</a> to read it.</p>
</object>
```

**Mobile reality:** iOS Safari and many mobile browsers refuse to render PDFs inline and show a
blank box. Mitigation, no heavy dependency (no PDF.js):

- The **Download / View buttons sit *above* the viewer and are always visible**, so a mobile
  user always has a working path even if the embed is blank.
- The `<object>` contains **fallback content** (a download link) for browsers that render the
  fallback instead of the embed.

## Styling

Add a small set of `.paper-*` classes to `styles.css` (header reuse means only the body
content needs new rules): the eyebrow/title/summary block, the action-button row, and the
`.paper-viewer` embed (full width, a tall fixed/`vh`-based height on desktop, reduced height on
mobile). No new fonts; no changes to existing components.

## Wiring `index.html`

The three research cards change from outbound `<a href="https://...publisher...">` to local
`<a href="brand-community-dissolution.html">` etc. The card markup, classes, and `Read Paper →`
label are otherwise unchanged. The publisher URLs move into the new pages' `View on publisher`
buttons (they are not lost).

## Scripts

The three new paper pages **do not include `script.js`**. They use the static `resume-bar`
header (no hamburger nav) and the same precedent as `resume.html`, which omits the script. The
pages therefore do not rely on the `fade-in` reveal animation.

## Cache busting

New `.paper-*` rules change `styles.css`, so per the project convention the `styles.css?v=`
query string is bumped to a new date stamp in **every** HTML file that links the stylesheet:
`index.html`, `tandem.html`, `resume.html`, `404.html`, and the three new paper pages. The same
bump is applied to the existing `script.js?v=` references in `index.html`, `tandem.html`, and
`404.html` for consistency (`resume.html` and the new paper pages do not load `script.js`). New
stamp: `v=20260624`.

## Out of scope (YAGNI)

- **No PDF.js or custom viewer.** Native `<object>` embed + always-visible fallback buttons is
  sufficient.
- **No full bibliographic citations.** Only journal + year are known; volume/issue/pages are
  not. Citations can be added later if the user supplies them.
- **No new copy.** Summaries are reused verbatim from the existing cards.
- **No changes to other sections** of the site.

## Success criteria

- Clicking "Read Paper" on any of the three research cards lands on the matching local page,
  not the publisher site.
- Each page shows the title, journal/year, summary, a working `Download PDF` button, a working
  `View on publisher` button, and an inline PDF on desktop.
- On mobile, even if the inline embed is blank, the Download/View buttons work.
- The three PDFs live under `papers/` and load from the local site; no duplicate copies remain
  in the repo root.
- Stylesheet cache-buster is bumped across all HTML files.
