# Embed Paper PDFs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three outbound "Read Paper" publisher links with self-hosted reader pages that embed the full article PDFs.

**Architecture:** Three static HTML pages (one per paper) reuse the existing `resume-bar` header and `styles.css`. Each shows title, journal/year, the existing summary, Download + View-on-publisher buttons, and a native `<object>` PDF embed with an always-visible button fallback for mobile. PDFs move into a `papers/` folder. The research cards in `index.html` re-point to the local pages.

**Tech Stack:** Static HTML + CSS (no framework, no JS on the new pages, no build step). Verification is manual (browser + grep). There is no test framework in this repo, so TDD steps are replaced with concrete verification steps.

**Spec:** `docs/superpowers/specs/2026-06-24-embed-paper-pdfs-design.md`

---

## File Structure

| File | Responsibility |
|------|----------------|
| `papers/brand-community-dissolution.pdf` | PDF asset (moved + renamed from root) |
| `papers/nonprofit-rebranding.pdf` | PDF asset (moved + renamed from root) |
| `papers/heat-aggression-terrorism.pdf` | PDF asset (moved + renamed from root) |
| `brand-community-dissolution.html` | Reader page — Brand Community Dissolution |
| `nonprofit-rebranding.html` | Reader page — Nonprofit Rebranding |
| `heat-aggression-terrorism.html` | Reader page — Heat–Aggression / Terrorism |
| `styles.css` | Add `.paper-*` rules (one new block) |
| `index.html` | Re-point 3 research cards; bump cache-buster |
| `tandem.html`, `resume.html`, `404.html` | Bump cache-buster only |

**Per-page substitution values** (the only differences between the three reader pages):

| Page file | Eyebrow | `<title>` / `<h1>` | Summary (verbatim from index.html card) | PDF path | Publisher URL |
|-----------|---------|--------------------|------------------------------------------|----------|---------------|
| `brand-community-dissolution.html` | `Marketing Letters · 2026` | Exploring the Effects of Brand Community Dissolution | When a brand community shuts down, what happens to its members? This study finds that dissolution weakens customers' bonds with the brand, the company, and each other — while their attachment to the product itself stays resilient. | `papers/brand-community-dissolution.pdf` | `https://link.springer.com/article/10.1007/s11002-026-09812-x` |
| `nonprofit-rebranding.html` | `The CASE Journal · 2026` | Rewriting the Story: Navigating Nonprofit Brand Evolution | A teaching case on nonprofit rebranding: a US nonprofit must decide whether to overhaul its brand to match an expanded global mission ahead of its annual gala, weighing brand alignment against the expectations of donors and stakeholders. | `papers/nonprofit-rebranding.pdf` | `https://www.emerald.com/tcj/article-abstract/doi/10.1108/TCJ-06-2025-0219/1368661/Rewriting-the-story-navigating-nonprofit-brand` |
| `heat-aggression-terrorism.html` | `Psychology of Violence · 2025` | Collectivism and the Heat–Aggression Relationship in Terrorism | Does culture shape the well-documented link between heat and aggression? Analyzing decades of global data, this study shows that societies with stronger in-group and family ties exhibit a weaker relationship between rising temperatures and terrorist attacks. | `papers/heat-aggression-terrorism.pdf` | `https://doi.org/10.1037/vio0000652` |

> NOTE: The summaries are copied **verbatim** from the existing cards (`index.html` lines 117, 124, 131), including their existing en/em dashes. Do not rewrite them.

---

## Task 1: Move PDFs into `papers/`

**Files:**
- Create: `papers/brand-community-dissolution.pdf`, `papers/nonprofit-rebranding.pdf`, `papers/heat-aggression-terrorism.pdf`
- Delete (move): `BrandCommunityDissolution.pdf`, `NonprofitReBranding.pdf`, `HeatAggressionTerrorism.pdf`

- [ ] **Step 1: Create folder and move/rename the three PDFs**

The PDFs are currently untracked in the repo root. Use plain `mv` (not `git mv`, since they aren't tracked yet), then `git add` the new folder.

```bash
cd "C:/Users/miles/OneDrive/Desktop/personal_website"
mkdir -p papers
mv BrandCommunityDissolution.pdf papers/brand-community-dissolution.pdf
mv NonprofitReBranding.pdf        papers/nonprofit-rebranding.pdf
mv HeatAggressionTerrorism.pdf    papers/heat-aggression-terrorism.pdf
```

- [ ] **Step 2: Verify the move**

```bash
ls papers/
ls *.pdf 2>/dev/null   # expect: no PDFs left in root
```
Expected: three renamed PDFs in `papers/`, none in the root.

- [ ] **Step 3: Confirm `.gitignore` does not exclude PDFs or the folder**

```bash
cat .gitignore
git check-ignore papers/brand-community-dissolution.pdf || echo "NOT IGNORED (good)"
```
Expected: prints `NOT IGNORED (good)`. If a PDF rule exists, stop and surface it.

- [ ] **Step 4: Commit**

```bash
git add papers/
git commit -m "assets: add paper PDFs under papers/"
```

---

## Task 2: Add `.paper-*` styles to `styles.css`

**Files:**
- Modify: `styles.css` (append a new block at end of file)

- [ ] **Step 1: Append the paper-page styles**

Add this block at the **end** of `styles.css`:

```css

/* ── Paper reader pages ── */

.paper {
  padding: 48px 0 80px;
}

.paper__eyebrow {
  color: var(--gold-ink);
  font-family: var(--font-heading);
  text-transform: uppercase;
  letter-spacing: 2px;
  font-size: 0.85rem;
}

.paper__title {
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  line-height: 1.15;
  margin: 8px 0 16px;
}

.paper__summary {
  max-width: 720px;
  font-size: 1.05rem;
  line-height: 1.75;
  color: var(--text-body);
  margin-bottom: 28px;
}

.paper__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 28px;
}

.paper-viewer {
  width: 100%;
  height: 85vh;
  min-height: 500px;
  border: 1px solid var(--border-card);
  border-radius: 6px;
  background: var(--bg-card);
}

.paper-viewer__fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 56px 24px;
  text-align: center;
  color: var(--text-secondary);
}

@media (max-width: 600px) {
  .paper-viewer { height: 70vh; min-height: 360px; }
  .paper__actions .btn { flex: 1 1 auto; text-align: center; }
}
```

- [ ] **Step 2: Verify the rules are present and balanced**

```bash
grep -n "Paper reader pages" styles.css
grep -c "paper-viewer" styles.css   # expect: 3 (definition + height override + fallback)
```
Expected: the comment line is found; `.paper-viewer` appears 3 times.

- [ ] **Step 3: Commit**

```bash
git add styles.css
git commit -m "style: add .paper-* reader-page styles"
```

---

## Task 3: Create the three reader pages

**Files:**
- Create: `brand-community-dissolution.html`, `nonprofit-rebranding.html`, `heat-aggression-terrorism.html`

- [ ] **Step 1: Create `brand-community-dissolution.html`**

Use this as the canonical template. For the other two pages, substitute the five values from the per-page table above (`<title>`, `meta description`, eyebrow, `<h1>`, summary, both PDF paths, publisher URL).

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Exploring the Effects of Brand Community Dissolution — Miles Condon</title>
  <meta name="description" content="Read the full paper: Exploring the Effects of Brand Community Dissolution (Marketing Letters, 2026) by Miles Condon." />

  <!-- Favicon: gold "M" on navy (matches portfolio) -->
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='8' fill='%230b1120'/><text x='50%25' y='54%25' dominant-baseline='middle' text-anchor='middle' font-family='Georgia,serif' font-weight='700' font-size='42' fill='%23c9a84c'>M</text></svg>" />

  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Oswald:wght@700&family=Lato:wght@400;700&display=swap" />
  <link rel="stylesheet" href="styles.css?v=20260624" />
</head>
<body>

  <header class="resume-bar">
    <div class="container resume-bar__inner">
      <a href="index.html" class="nav__logo">&larr; Miles Condon</a>
      <a href="mailto:milescondon@gmail.com" class="btn btn--primary btn--sm">Get In Touch</a>
    </div>
  </header>

  <main class="container paper">
    <p class="paper__eyebrow">Marketing Letters · 2026</p>
    <h1 class="paper__title">Exploring the Effects of Brand Community Dissolution</h1>
    <p class="paper__summary">When a brand community shuts down, what happens to its members? This study finds that dissolution weakens customers' bonds with the brand, the company, and each other — while their attachment to the product itself stays resilient.</p>

    <div class="paper__actions">
      <a href="papers/brand-community-dissolution.pdf" class="btn btn--primary" download>Download PDF</a>
      <a href="https://link.springer.com/article/10.1007/s11002-026-09812-x" class="btn btn--outline" target="_blank" rel="noopener">View on publisher &#8599;</a>
    </div>

    <object data="papers/brand-community-dissolution.pdf#view=FitH" type="application/pdf" class="paper-viewer">
      <div class="paper-viewer__fallback">
        <p>Your browser can't display this PDF inline.</p>
        <a href="papers/brand-community-dissolution.pdf" class="btn btn--primary" download>Download the PDF</a>
      </div>
    </object>
  </main>

  <footer class="footer">
    <div class="container">
      <p>© 2026 Miles Condon</p>
    </div>
  </footer>

</body>
</html>
```

- [ ] **Step 2: Create `nonprofit-rebranding.html`** — copy the template, substitute:
  - `<title>`: `Rewriting the Story: Navigating Nonprofit Brand Evolution — Miles Condon`
  - meta description: `Read the full teaching case: Rewriting the Story: Navigating Nonprofit Brand Evolution (The CASE Journal, 2026) by Miles Condon.`
  - eyebrow: `The CASE Journal · 2026`
  - `<h1>`: `Rewriting the Story: Navigating Nonprofit Brand Evolution`
  - summary: the nonprofit summary from the table (verbatim)
  - both PDF references: `papers/nonprofit-rebranding.pdf`
  - publisher URL: `https://www.emerald.com/tcj/article-abstract/doi/10.1108/TCJ-06-2025-0219/1368661/Rewriting-the-story-navigating-nonprofit-brand`

- [ ] **Step 3: Create `heat-aggression-terrorism.html`** — copy the template, substitute:
  - `<title>`: `Collectivism and the Heat–Aggression Relationship in Terrorism — Miles Condon`
  - meta description: `Read the full paper: Collectivism and the Heat–Aggression Relationship in Terrorism (Psychology of Violence, 2025) by Miles Condon.`
  - eyebrow: `Psychology of Violence · 2025`
  - `<h1>`: `Collectivism and the Heat–Aggression Relationship in Terrorism`
  - summary: the heat–aggression summary from the table (verbatim)
  - both PDF references: `papers/heat-aggression-terrorism.pdf`
  - publisher URL: `https://doi.org/10.1037/vio0000652`

- [ ] **Step 4: Verify all three pages reference correct assets**

```bash
grep -l "styles.css?v=20260624" brand-community-dissolution.html nonprofit-rebranding.html heat-aggression-terrorism.html
grep -o "papers/[a-z-]*\.pdf" brand-community-dissolution.html nonprofit-rebranding.html heat-aggression-terrorism.html
```
Expected: all three files listed; each file shows its own PDF path exactly twice (button + object). Confirm no page points at another page's PDF.

- [ ] **Step 5: Verify in browser**

Open each page (e.g. `start brand-community-dissolution.html` on Windows, or via a local server). Confirm: back-bar header renders, title/eyebrow/summary show, both buttons work (Download saves the file; View opens the publisher in a new tab), and the PDF renders inline on desktop.

- [ ] **Step 6: Commit**

```bash
git add brand-community-dissolution.html nonprofit-rebranding.html heat-aggression-terrorism.html
git commit -m "feat: add self-hosted reader pages for the three papers"
```

---

## Task 4: Re-point the research cards in `index.html`

**Files:**
- Modify: `index.html:115` (Brand Community card `href`), `index.html:122` (Nonprofit card `href`), `index.html:129` (Heat–Aggression card `href`), plus the `styles.css?v=` link.

- [ ] **Step 1: Change the three card `href`s to the local pages**

Replace each outbound publisher `href` (and remove the now-redundant `target="_blank" rel="noopener"` since these are same-site links) so each card links to its reader page:

- Card 1 (`Exploring the Effects of Brand Community Dissolution`):
  `<a href="brand-community-dissolution.html" class="card fade-in">`
- Card 2 (`Rewriting the Story...`):
  `<a href="nonprofit-rebranding.html" class="card fade-in">`
- Card 3 (`Collectivism and the Heat–Aggression...`):
  `<a href="heat-aggression-terrorism.html" class="card fade-in">`

Leave the card inner markup (`card__title`, `card__description`, `card__tech`, `card__link` "Read Paper →") unchanged.

- [ ] **Step 2: Bump the cache-buster in `index.html`**

Change `styles.css?v=20260616b` → `styles.css?v=20260624`, and `script.js?v=20260616b` → `script.js?v=20260624`.

- [ ] **Step 3: Verify**

```bash
grep -n "research-item\|card fade-in" index.html
grep -n "link.springer\|emerald.com\|doi.org/10.1037" index.html   # expect: no matches (publisher links removed from cards)
grep -c "v=20260624" index.html                                    # expect: 2 (styles + script)
```
Expected: the three cards now point to local `.html` pages; no publisher URLs remain in `index.html`; cache-buster bumped.

- [ ] **Step 4: Verify in browser**

Open `index.html`, scroll to "Selected Academic Research", click each "Read Paper →" card, confirm it lands on the matching local reader page (not the publisher).

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: point research cards to self-hosted reader pages"
```

---

## Task 5: Bump cache-buster in remaining HTML files

**Files:**
- Modify: `tandem.html`, `resume.html`, `404.html`

- [ ] **Step 1: Bump the stylesheet (and script where present) version**

In each file, change `styles.css?v=20260616b` → `styles.css?v=20260624`. Also bump `script.js?v=20260616b` → `script.js?v=20260624` in **`tandem.html` and `404.html`** (both load `script.js`). `resume.html` does not load `script.js` — stylesheet only.

- [ ] **Step 2: Verify no stale version remains anywhere**

```bash
grep -rn "v=20260616b" .   # expect: no matches outside docs/
grep -rln "v=20260624" *.html   # expect: index, tandem, resume, 404 + 3 paper pages = 7 files
```
Expected: zero `20260616b` references in shipped HTML; seven HTML files now reference `v=20260624`.

- [ ] **Step 3: Commit**

```bash
git add tandem.html resume.html 404.html
git commit -m "chore: bump styles cache-buster to v=20260624"
```

---

## Final Verification

- [ ] From `index.html`, all three "Read Paper" cards open local reader pages.
- [ ] Each reader page: header, title, journal/year, summary, working Download button, working View-on-publisher button, inline PDF on desktop.
- [ ] On a narrow viewport (DevTools mobile), buttons remain visible and tappable even if the inline embed is blank.
- [ ] `papers/` holds the three renamed PDFs; no PDFs remain in the repo root.
- [ ] `grep -rn "v=20260616b" *.html` returns nothing.
