# Portfolio Website Design Spec — milescondon.com

## Overview

A personal portfolio site for Miles Condon, a former professor transitioning to industry in AI/ML. Primary audience is hiring managers and recruiters. The site showcases 3 AI/ML projects and 3 academic papers. Hosted on GitHub Pages with a custom domain.

## Goals

- Look polished and professional — not like a template or AI-generated
- Scannable by hiring managers who skim fast
- Showcase both technical projects (with Loom video demos) and academic work
- Signal technical competence by being self-built
- Zero ongoing cost beyond domain registration (~$12-20/year)

## Tech Stack

- Static HTML / CSS / vanilla JS
- No frameworks, no build tools, no dependencies
- GitHub Pages for hosting
- Google Fonts: Oswald (headings), Lato (body)
- Formspree or mailto: for contact

## Design Language

### Colors
- Page background: `#0b1120` (deep navy)
- Card/section background: `#111d32` (lighter navy)
- Card borders: `#1e2d4a`
- Gold accent: `#c9a84c` (borders, CTAs, highlights)
- Heading text: `#ffffff`
- Body text: `#8a9bb8` (muted blue-gray)
- Secondary text: `#6b7c98`

### Typography
- Headings: Oswald (uppercase, bold, letter-spaced)
- Body: Lato (regular weight, generous line-height ~1.7)
- Gold underline bar beneath section headings (40px wide, 3px tall)

### Tone
- Minimal and clean with a touch of warmth
- Generous whitespace
- Conversational bio copy, not stiff CV language

## File Structure

```
index.html
styles.css
script.js
projects/
  twin-app.html
  recommendation-system.html
  data-analytics-agent.html
  paper-1.html
  paper-2.html
  paper-3.html
assets/
  images/
    headshot.jpg
    (project screenshots as added)
```

## Page Structure — index.html

### 1. Navigation (fixed top)
- Name/logo on the left
- Links: About, Projects, Contact — smooth-scroll to sections
- Styled as simple text links, no heavy nav treatment
- Collapses to hamburger menu on mobile

### 2. Hero Section
- Full viewport height
- Left side: Name in large Oswald, one-line tagline (e.g., "AI/ML Engineer · Researcher · Builder"), short conversational sentence about what he does, two buttons — "View Work" (filled gold) and "Contact" (outlined gold)
- Right side: Reserved space for a graphic element (abstract geometric pattern, data visualization motif, or decorative gradient shape — to be iterated on). Placeholder for now.
- Navy gradient background

### 3. About Section
- Photo on the left (circular, gold border)
- Bio paragraph on the right — conversational tone, 3-4 sentences
- Social links below bio (LinkedIn, GitHub as circular icon buttons)
- Gold accent bar beneath "About Me" heading

### 4. Projects — AI/ML (section heading with gold underline)
- 3-column card grid
- Each card: dark card background, gold left border accent, project title (Oswald), short description (Lato), tech stack as understated middot-separated text, "Learn More →" link in gold
- Cards link to individual project detail pages
- Hover effect: border brightens to full gold, subtle lift/shadow

**Projects:**
1. Twin Sleep App — RAG-based clinical consultation & adaptive scheduling
2. Recommendation System — Collaborative filtering for content discovery
3. Data Analytics Agent — NLP-powered natural language data queries

### 5. Projects — Academic Research (section heading with gold underline)
- Lighter treatment than AI/ML cards — a clean list, not a forced grid
- Each entry: paper title (Oswald, smaller), publication/conference name, year, and a link to the paper
- More like a curated bibliography — simple, scannable
- Links to detail pages for papers that warrant deeper explanation

**Papers:** (titles TBD by user — 3 academic papers)

### 6. Contact Section
- Centered layout
- "Get In Touch" heading with gold underline
- Short blurb: "Interested in working together or have a question?"
- Email button (filled gold)
- LinkedIn icon below
- Simple, zero-maintenance

### 7. Footer
- Minimal — copyright line, maybe a "Built by Miles Condon" note

## Project Detail Pages

Each project gets its own page with consistent layout:

1. **Back link** — "← Back to Portfolio" at top
2. **Loom video embed** — full-width at top of content area (when available)
3. **Project title** (Oswald, large)
4. **Structured content:**
   - **Problem** — what challenge this addresses
   - **Approach** — how it was built, key technical decisions
   - **Results / Impact** — outcomes, metrics, what was learned
   - **Tech Stack** — languages, frameworks, tools used
   - **Links** — GitHub repo, live demo, paper, slides (as applicable)
5. Same nav bar as index.html for consistency

## Interactions & Polish

- Scroll-triggered fade-in animations (CSS + IntersectionObserver)
- Smooth-scroll for nav links
- Card hover: gold border brightens, subtle translateY(-2px) lift
- Button hover: slight brightness shift
- Responsive: cards collapse to single column on mobile, hero stacks vertically
- Page load: subtle fade-in on hero content

## Responsive Behavior

- **Desktop (>1024px):** Full 3-column card grid, side-by-side hero/about layouts
- **Tablet (768-1024px):** 2-column card grid, side-by-side layouts maintained
- **Mobile (<768px):** Single column everything, hamburger nav, stacked hero/about, full-width cards

## Open Items

- Hero graphic element — to be designed/iterated after initial build
- Academic paper titles and details — user to provide
- Headshot photo — user to provide
- Loom recordings — user to create and embed later
- Body font final pick — Lato recommended, user open to alternatives
- Specific project descriptions — user to write
