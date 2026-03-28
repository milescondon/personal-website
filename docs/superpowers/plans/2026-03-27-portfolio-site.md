# Portfolio Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished personal portfolio site for milescondon.com — dark navy/gold theme, responsive, hosted on GitHub Pages.

**Architecture:** Single-page scrolling `index.html` with separate project detail pages under `projects/`. One shared `styles.css` for all pages, one `script.js` for interactions. No frameworks, no build tools.

**Tech Stack:** HTML5, CSS3 (custom properties, Grid, Flexbox), vanilla JS, Google Fonts (Oswald + Lato), GitHub Pages

**Spec:** `docs/superpowers/specs/2026-03-27-portfolio-site-design.md`

---

## File Structure

```
index.html                          — Main single-page site
styles.css                          — All styles (shared across pages)
script.js                           — Nav, scroll animations, hamburger menu
projects/twin-app.html              — Project detail page
projects/recommendation-system.html — Project detail page
projects/data-analytics-agent.html  — Project detail page
404.html                            — Custom 404 page
CNAME                               — GitHub Pages custom domain
assets/images/                      — Headshot, screenshots (user-provided)
```

---

### Task 1: Project Scaffolding & CSS Foundation

**Files:**
- Create: `index.html`
- Create: `styles.css`
- Create: `CNAME`

- [ ] **Step 1: Create `CNAME` file**

```
milescondon.com
```

- [ ] **Step 2: Create `index.html` with boilerplate**

Includes:
- `<!DOCTYPE html>`, lang="en"
- `<meta charset>`, viewport meta
- `<title>Miles Condon — AI/ML Engineer & Researcher</title>`
- Meta description
- Open Graph tags (title, description — image placeholder for later)
- Google Fonts preload + stylesheet links for Oswald (700) and Lato (400, 700) — include `&display=swap` in the Google Fonts URL
- Favicon: `<link rel="icon">` — create a simple SVG favicon inline (gold "M" on navy background using `data:image/svg+xml`)
- Link to `styles.css`
- Empty `<body>` with a single `<h1>Miles Condon</h1>` for verification
- Script tag for `script.js` (deferred)

- [ ] **Step 3: Create `styles.css` with CSS custom properties and resets**

```css
:root {
  --bg-page: #0b1120;
  --bg-card: #111d32;
  --border-card: #1e2d4a;
  --gold: #c9a84c;
  --text-heading: #ffffff;
  --text-body: #a0b0c8;
  --text-secondary: #8a9bb8;
  --font-heading: 'Oswald', sans-serif;
  --font-body: 'Lato', sans-serif;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: smooth; }

body {
  font-family: var(--font-body);
  background: var(--bg-page);
  color: var(--text-body);
  line-height: 1.7;
}

h1, h2, h3, h4 {
  font-family: var(--font-heading);
  color: var(--text-heading);
  text-transform: uppercase;
  letter-spacing: 1px;
}

a { color: var(--gold); text-decoration: none; }

img { max-width: 100%; display: block; }

.container { max-width: 1100px; margin: 0 auto; padding: 0 24px; }
```

- [ ] **Step 4: Verify in browser**

Open `index.html` in browser. Confirm: dark navy background, white "Miles Condon" heading in Oswald font, correct page title in tab.

- [ ] **Step 5: Commit**

```bash
git add index.html styles.css CNAME
git commit -m "feat: scaffold project with HTML boilerplate, CSS foundation, and CNAME"
```

---

### Task 2: Navigation Bar

**Files:**
- Modify: `index.html`
- Modify: `styles.css`

- [ ] **Step 1: Add nav HTML to `index.html`**

```html
<nav class="nav" id="nav">
  <div class="container nav__inner">
    <a href="#" class="nav__logo">Miles Condon</a>
    <button class="nav__toggle" aria-label="Toggle menu" aria-expanded="false">
      <span class="nav__hamburger"></span>
    </button>
    <ul class="nav__links">
      <li><a href="#about">About</a></li>
      <li><a href="#projects">Projects</a></li>
      <li><a href="#contact">Contact</a></li>
    </ul>
  </div>
</nav>
```

- [ ] **Step 2: Add nav styles to `styles.css`**

Styles for:
- Fixed positioning, z-index, dark background with slight transparency
- `.nav__inner`: flex, space-between, align-center, height ~70px
- `.nav__logo`: Oswald, gold color, no uppercase
- `.nav__links`: flex row, gap 32px, list-style none
- `.nav__links a`: text-body color, hover transitions to gold
- `.nav__toggle`: hidden on desktop
- `.nav__hamburger`: 3-line CSS hamburger icon (using ::before and ::after pseudo-elements)
- Mobile (<768px): `.nav__links` hidden by default, shown as overlay when `.nav--open` class is present. Slide-in from right. `.nav__toggle` visible.

- [ ] **Step 3: Verify in browser**

Desktop: fixed nav at top, logo left, 3 links right, no hamburger visible.
Resize to mobile: links disappear, hamburger icon appears. (Click won't work yet — JS comes later.)

- [ ] **Step 4: Commit**

```bash
git add index.html styles.css
git commit -m "feat: add responsive navigation bar"
```

---

### Task 3: Hero Section

**Files:**
- Modify: `index.html`
- Modify: `styles.css`

- [ ] **Step 1: Add hero HTML to `index.html`** (after nav)

```html
<section class="hero" id="hero">
  <div class="container hero__inner">
    <div class="hero__text">
      <h1 class="hero__name">Miles Condon</h1>
      <p class="hero__tagline">AI/ML Engineer · Researcher · Builder</p>
      <p class="hero__description">I build intelligent systems at the intersection of machine learning research and real-world impact.</p>
      <div class="hero__buttons">
        <a href="#projects" class="btn btn--primary">View Work</a>
        <a href="#contact" class="btn btn--outline">Contact</a>
      </div>
    </div>
    <div class="hero__graphic" aria-hidden="true"></div>
  </div>
</section>
```

- [ ] **Step 2: Add hero styles to `styles.css`**

Styles for:
- `.hero`: min-height 100vh, display flex, align-items center, gradient background (135deg from #0b1120 to #111d32)
- `.hero__inner`: flex row, align-items center, gap 48px
- `.hero__text`: flex 1
- `.hero__name`: font-size clamp(2.5rem, 5vw, 4rem), margin-bottom 8px
- `.hero__tagline`: gold color, Oswald, font-size 1.1rem, letter-spacing 2px, uppercase
- `.hero__description`: margin-top 16px, font-size 1.1rem, max-width 500px
- `.hero__buttons`: margin-top 32px, flex, gap 16px
- `.btn`: padding 12px 32px, border-radius 4px, font-family Oswald, font-size 0.9rem, uppercase, letter-spacing 1px, transition all 0.3s
- `.btn--primary`: background gold, color #0b1120, hover brightness 1.1
- `.btn--outline`: border 1px solid gold, color gold, hover background gold/10%
- `.hero__graphic`: flex 1, min-height 300px, background — subtle CSS geometric placeholder (radial gradient circles or angled lines in faint navy tones)
- Responsive: hero stacks vertically on mobile, graphic hidden on mobile

- [ ] **Step 3: Verify in browser**

Full-height hero, name large in Oswald, gold tagline, description, two buttons side by side. Right side has a subtle placeholder graphic. Resize to mobile: stacks vertically, graphic disappears.

- [ ] **Step 4: Commit**

```bash
git add index.html styles.css
git commit -m "feat: add hero section with text and placeholder graphic"
```

---

### Task 4: About Section

**Files:**
- Modify: `index.html`
- Modify: `styles.css`

- [ ] **Step 1: Add about HTML to `index.html`** (after hero)

```html
<section class="about" id="about">
  <div class="container about__inner">
    <div class="about__photo">
      <div class="about__photo-placeholder">Photo</div>
      <!-- Replace with: <img src="assets/images/headshot.jpg" alt="Miles Condon"> -->
    </div>
    <div class="about__content">
      <h2 class="section-heading">About Me</h2>
      <div class="section-heading__bar"></div>
      <p>Former professor turned AI/ML engineer. I build intelligent systems that solve real problems — from recommendation engines to clinical consultation tools. My work sits at the intersection of research rigor and practical impact.</p>
      <div class="about__socials">
        <a href="#" class="social-link" aria-label="LinkedIn">
          <svg><!-- LinkedIn icon SVG --></svg>
        </a>
        <a href="#" class="social-link" aria-label="GitHub">
          <svg><!-- GitHub icon SVG --></svg>
        </a>
      </div>
    </div>
  </div>
</section>
```

Note: Use inline SVG icons for LinkedIn and GitHub (no icon library dependency). Simple 24x24 path-based icons.

- [ ] **Step 2: Add about styles to `styles.css`**

Styles for:
- `.about`: padding 100px 0
- `.about__inner`: flex row, gap 48px, align-items center
- `.about__photo img` / `.about__photo-placeholder`: width 200px, height 200px, border-radius 50%, border 3px solid gold, object-fit cover
- `.about__content`: flex 1
- `.section-heading`: Oswald, font-size 1.8rem (reusable class for all section headings)
- `.section-heading__bar`: width 40px, height 3px, background gold, margin 14px 0 20px
- `.about__socials`: flex, gap 12px, margin-top 20px
- `.social-link`: width 36px, height 36px, border-radius 50%, border 1px solid var(--border-card), display flex, align-items center, justify-content center, color var(--text-secondary), transition, hover: border-color gold, color gold
- Responsive: stacks vertically on mobile, photo centered above text

- [ ] **Step 3: Verify in browser**

Scroll past hero: About section with circular photo placeholder on left, heading with gold bar, bio paragraph, and social icon circles on right. Mobile: stacks, photo centered.

- [ ] **Step 4: Commit**

```bash
git add index.html styles.css
git commit -m "feat: add about section with photo and social links"
```

---

### Task 5: AI/ML Projects Section

**Files:**
- Modify: `index.html`
- Modify: `styles.css`

- [ ] **Step 1: Add projects HTML to `index.html`** (after about)

```html
<section class="projects" id="projects">
  <div class="container">
    <h2 class="section-heading" style="text-align:center;">AI/ML Projects</h2>
    <div class="section-heading__bar" style="margin:14px auto 40px;"></div>

    <div class="card-grid">
      <a href="projects/twin-app.html" class="card">
        <div class="card__border"></div>
        <h3 class="card__title">Twin Sleep App</h3>
        <p class="card__description">AI-powered infant sleep management combining RAG-based clinical consultation and adaptive scheduling optimization.</p>
        <span class="card__tech">RAG · Python · Full-Stack</span>
        <span class="card__link">Learn More →</span>
      </a>

      <a href="projects/recommendation-system.html" class="card">
        <div class="card__border"></div>
        <h3 class="card__title">Recommendation System</h3>
        <p class="card__description">Collaborative filtering engine for personalized content discovery and user engagement.</p>
        <span class="card__tech">ML · Python</span>
        <span class="card__link">Learn More →</span>
      </a>

      <a href="projects/data-analytics-agent.html" class="card">
        <div class="card__border"></div>
        <h3 class="card__title">Data Analytics Agent</h3>
        <p class="card__description">NLP-powered system enabling natural language data queries and automated analysis.</p>
        <span class="card__tech">NLP · Python · Data Analytics</span>
        <span class="card__link">Learn More →</span>
      </a>
    </div>
  </div>
</section>
```

- [ ] **Step 2: Add card grid and card styles to `styles.css`**

Styles for:
- `.projects`: padding 100px 0
- `.card-grid`: display grid, grid-template-columns repeat(3, 1fr), gap 24px
- `.card`: display flex, flex-direction column, background var(--bg-card), border 1px solid var(--border-card), border-left 3px solid var(--border-card), border-radius 4px, padding 28px 24px, text-decoration none, transition all 0.3s, position relative
- `.card:hover`: border-left-color gold, transform translateY(-2px), box-shadow 0 8px 24px rgba(0,0,0,0.3)
- `.card__title`: Oswald, font-size 1.1rem, margin-bottom 10px, color white
- `.card__description`: font-size 0.9rem, line-height 1.6, color var(--text-body), flex 1
- `.card__tech`: font-size 0.75rem, color var(--text-secondary), letter-spacing 1px, margin-top 16px
- `.card__link`: font-size 0.85rem, color gold, margin-top 12px
- Responsive: 2 columns on tablet, 1 column on mobile

- [ ] **Step 3: Verify in browser**

3 cards side by side under centered "AI/ML Projects" heading. Hover: gold left border appears, card lifts. Cards are clickable (links won't work yet — detail pages don't exist). Mobile: cards stack.

- [ ] **Step 4: Commit**

```bash
git add index.html styles.css
git commit -m "feat: add AI/ML projects section with card grid"
```

---

### Task 6: Academic Research Section

**Files:**
- Modify: `index.html`
- Modify: `styles.css`

- [ ] **Step 1: Add research HTML to `index.html`** (after AI/ML projects)

```html
<section class="research">
  <div class="container">
    <h2 class="section-heading" style="text-align:center;">Academic Research</h2>
    <div class="section-heading__bar" style="margin:14px auto 40px;"></div>

    <ul class="research-list">
      <li class="research-item">
        <h3 class="research-item__title">Paper Title One</h3>
        <p class="research-item__meta">Conference/Journal Name · 2024</p>
        <a href="#" class="research-item__link">Read Paper →</a>
      </li>
      <li class="research-item">
        <h3 class="research-item__title">Paper Title Two</h3>
        <p class="research-item__meta">Conference/Journal Name · 2023</p>
        <a href="#" class="research-item__link">Read Paper →</a>
      </li>
      <li class="research-item">
        <h3 class="research-item__title">Paper Title Three</h3>
        <p class="research-item__meta">Conference/Journal Name · 2022</p>
        <a href="#" class="research-item__link">Read Paper →</a>
      </li>
    </ul>
  </div>
</section>
```

- [ ] **Step 2: Add research list styles to `styles.css`**

Styles for:
- `.research`: padding 80px 0
- `.research-list`: list-style none, max-width 700px, margin 0 auto
- `.research-item`: padding 24px 0, border-bottom 1px solid var(--border-card)
- `.research-item:last-child`: border-bottom none
- `.research-item__title`: Oswald, font-size 1rem, text-transform none (exception — paper titles shouldn't be uppercase), color white
- `.research-item__meta`: font-size 0.85rem, color var(--text-secondary), margin-top 6px
- `.research-item__link`: font-size 0.85rem, color gold, margin-top 8px, display inline-block

- [ ] **Step 3: Verify in browser**

Clean list of 3 papers, separated by subtle divider lines. No grid, no cards — lighter feel. Centered under heading.

- [ ] **Step 4: Commit**

```bash
git add index.html styles.css
git commit -m "feat: add academic research section with bibliography list"
```

---

### Task 7: Contact Section & Footer

**Files:**
- Modify: `index.html`
- Modify: `styles.css`

- [ ] **Step 1: Add contact and footer HTML to `index.html`**

```html
<section class="contact" id="contact">
  <div class="container contact__inner">
    <h2 class="section-heading">Get In Touch</h2>
    <div class="section-heading__bar" style="margin:14px auto 24px;"></div>
    <p class="contact__blurb">Interested in working together or have a question? I'd love to hear from you.</p>
    <a href="mailto:EMAIL_HERE" class="btn btn--primary contact__btn">Email Me</a>
    <div class="contact__social">
      <a href="#" class="social-link" aria-label="LinkedIn">
        <svg><!-- LinkedIn icon --></svg>
      </a>
    </div>
  </div>
</section>

<footer class="footer">
  <div class="container">
    <p>© 2026 Miles Condon</p>
  </div>
</footer>
```

- [ ] **Step 2: Add contact and footer styles to `styles.css`**

Styles for:
- `.contact`: padding 100px 0, text-align center
- `.contact__blurb`: max-width 400px, margin 0 auto 28px, font-size 1rem
- `.contact__btn`: display inline-block
- `.contact__social`: margin-top 20px, display flex, justify-content center
- `.footer`: padding 32px 0, text-align center, border-top 1px solid var(--border-card)
- `.footer p`: font-size 0.8rem, color var(--text-secondary)

- [ ] **Step 3: Verify in browser**

Centered contact section with heading, blurb, gold email button, LinkedIn icon below. Footer at bottom with copyright.

- [ ] **Step 4: Commit**

```bash
git add index.html styles.css
git commit -m "feat: add contact section and footer"
```

---

### Task 8: JavaScript — Nav, Scroll Animations, Mobile Menu

**Files:**
- Create: `script.js`

- [ ] **Step 1: Create `script.js` with three features**

**Feature 1: Mobile hamburger menu**
- Toggle `.nav--open` class on nav when hamburger is clicked
- Update `aria-expanded` attribute
- Close menu when a nav link is clicked

**Feature 2: Scroll-triggered fade-in animations**
- Add `.fade-in` class to all sections in HTML
- CSS: `.fade-in { opacity: 0; transform: translateY(20px); transition: opacity 0.6s, transform 0.6s; }`
- CSS: `.fade-in--visible { opacity: 1; transform: translateY(0); }`
- JS: IntersectionObserver watches `.fade-in` elements, adds `--visible` when 15% visible

**Feature 3: Hero page-load fade-in**
- Add a CSS `@keyframes heroFadeIn` animation (opacity 0→1, translateY 20px→0, 0.8s ease-out)
- Apply to `.hero__text` via `animation: heroFadeIn 0.8s ease-out both`
- This runs on page load, not scroll-triggered

**Feature 4: Nav background on scroll**
- Add `.nav--scrolled` class when page is scrolled past 50px (adds solid background)
- CSS: `.nav--scrolled { background: rgba(11, 17, 32, 0.95); box-shadow: 0 2px 12px rgba(0,0,0,0.3); }`

- [ ] **Step 2: Add `.fade-in` classes to section elements in `index.html`**

Add `class="fade-in"` to: `.about__inner`, each `.card`, each `.research-item`, `.contact__inner`

- [ ] **Step 3: Add animation CSS to `styles.css`**

The `.fade-in`, `.fade-in--visible`, and `.nav--scrolled` styles.

- [ ] **Step 4: Verify in browser**

- Scroll down: sections fade in as they enter viewport
- Nav gains solid background after scrolling
- Mobile: hamburger opens/closes menu, links close menu on click

- [ ] **Step 5: Commit**

```bash
git add script.js index.html styles.css
git commit -m "feat: add scroll animations, mobile menu, and nav scroll behavior"
```

---

### Task 9: Project Detail Page Template

**Files:**
- Create: `projects/twin-app.html`

- [ ] **Step 1: Create `projects/twin-app.html`**

Full HTML page including:
- Same `<head>` setup as index.html (meta, fonts, styles) — paths adjusted with `../`
- Same nav bar (with links pointing to `../index.html#about`, etc.)
- Content structure:

```html
<main class="project-detail">
  <div class="container">
    <a href="../index.html#projects" class="project-detail__back">← Back to Portfolio</a>

    <div class="project-detail__video">
      <!-- Loom embed placeholder -->
      <div class="project-detail__video-placeholder">Loom video will be embedded here</div>
    </div>

    <h1 class="project-detail__title">Twin Sleep App</h1>

    <div class="project-detail__content">
      <h2>Problem</h2>
      <p>Placeholder — describe the challenge.</p>

      <h2>Approach</h2>
      <p>Placeholder — describe how it was built.</p>

      <h2>Results & Impact</h2>
      <p>Placeholder — outcomes and metrics.</p>

      <h2>Tech Stack</h2>
      <ul class="project-detail__tech">
        <li>Python</li>
        <li>RAG</li>
        <li>Full-Stack</li>
      </ul>

      <h2>Links</h2>
      <div class="project-detail__links">
        <a href="#" class="btn btn--primary">GitHub</a>
        <a href="#" class="btn btn--outline">Live Demo</a>
      </div>
    </div>
  </div>
</main>
```

- [ ] **Step 2: Add project detail page styles to `styles.css`**

Styles for:
- `.project-detail`: padding-top 100px (clear fixed nav)
- `.project-detail__back`: display inline-block, margin-bottom 32px, color gold, font-size 0.9rem
- `.project-detail__video-placeholder`: background var(--bg-card), border 1px solid var(--border-card), border-radius 8px, aspect-ratio 16/9, max-width 800px, display flex, align-items center, justify-content center, color var(--text-secondary), margin-bottom 40px
- `.project-detail__title`: Oswald, font-size 2.2rem, margin-bottom 32px
- `.project-detail__content h2`: Oswald, font-size 1.2rem, color gold, margin-top 36px, margin-bottom 12px, text-transform none
- `.project-detail__content p`: margin-bottom 16px
- `.project-detail__tech`: list-style none, display flex, gap 12px, flex-wrap wrap
- `.project-detail__tech li`: background var(--bg-card), border 1px solid var(--border-card), padding 6px 16px, border-radius 4px, font-size 0.85rem, color var(--text-body)
- `.project-detail__links`: display flex, gap 16px, margin-top 16px

- [ ] **Step 3: Verify in browser**

Navigate to `projects/twin-app.html` directly. Back link works. Video placeholder visible. Structured content sections with gold subheadings. Nav links point back to main page sections.

- [ ] **Step 4: Commit**

```bash
git add projects/twin-app.html styles.css
git commit -m "feat: add project detail page template (twin-app)"
```

---

### Task 10: Remaining Project Detail Pages

**Files:**
- Create: `projects/recommendation-system.html`
- Create: `projects/data-analytics-agent.html`

- [ ] **Step 1: Duplicate twin-app.html for recommendation system**

Copy `projects/twin-app.html` to `projects/recommendation-system.html`. Update:
- Title: "Recommendation System"
- Tech stack: ML, Python
- Placeholder text (user will fill in real content)
- Unique `<title>` and `<meta name="description">` for this project

- [ ] **Step 2: Duplicate for data analytics agent**

Copy to `projects/data-analytics-agent.html`. Update:
- Title: "Data Analytics Agent"
- Tech stack: NLP, Python, Data Analytics
- Placeholder text
- Unique `<title>` and `<meta name="description">` for this project

- [ ] **Step 3: Verify in browser**

Click each "Learn More" card link on the main page. Each should navigate to its detail page. Back links should return to the projects section.

- [ ] **Step 4: Commit**

```bash
git add projects/recommendation-system.html projects/data-analytics-agent.html
git commit -m "feat: add remaining project detail pages"
```

---

### Task 11: 404 Page

**Files:**
- Create: `404.html`

- [ ] **Step 1: Create `404.html`**

Simple branded page:
- Same head/font setup as other pages
- Centered content: "404" in large Oswald, "Page not found" below, "Back to Home" gold button linking to index.html
- Same dark navy background

- [ ] **Step 2: Verify in browser**

Open `404.html` directly. Matches site styling.

- [ ] **Step 3: Commit**

```bash
git add 404.html
git commit -m "feat: add custom 404 page"
```

---

### Task 12: Final Polish & Responsive Testing

**Files:**
- Modify: `styles.css` (as needed)
- Modify: `index.html` (as needed)

- [ ] **Step 1: Full desktop walkthrough**

Open index.html in browser at full width. Verify every section top-to-bottom: nav, hero, about, AI/ML cards, research list, contact, footer. Check all hover effects, scroll animations, link navigation.

- [ ] **Step 2: Tablet testing (768-1024px)**

Resize browser. Verify: 2-column card grid, side-by-side layouts maintained, readable typography.

- [ ] **Step 3: Mobile testing (<768px)**

Resize to mobile width. Verify: hamburger menu works, hero stacks, about stacks with centered photo, cards single column, contact centered, footer clean. Test all nav links close the mobile menu.

- [ ] **Step 4: Fix any responsive issues found**

Adjust breakpoints, spacing, or font sizes as needed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix: responsive polish and cross-breakpoint adjustments"
```

---

### Task 13: Deployment to GitHub Pages

- [ ] **Step 1: Create GitHub repository**

```bash
gh repo create milescondon/personal-website --public --source=. --push
```

- [ ] **Step 2: Enable GitHub Pages**

Go to repo Settings → Pages → Source: Deploy from branch → Branch: `main`, folder: `/ (root)` → Save.

Or via CLI:
```bash
gh api repos/milescondon/personal-website/pages -X POST -f source.branch=main -f source.path=/
```

- [ ] **Step 3: Configure custom domain DNS in Squarespace**

In Squarespace Domains → milescondon.com → DNS Settings, add:
- A record: `185.199.108.153`
- A record: `185.199.109.153`
- A record: `185.199.110.153`
- A record: `185.199.111.153`
- CNAME record: `www` → `milescondon.github.io`

- [ ] **Step 4: Set custom domain in GitHub Pages**

Settings → Pages → Custom domain: `milescondon.com` → Save. Check "Enforce HTTPS" once DNS propagates.

- [ ] **Step 5: Verify**

Visit https://milescondon.com in browser. Confirm site loads, HTTPS works, all pages accessible.
