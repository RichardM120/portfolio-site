# Richard Morland — Portfolio

Personal portfolio site for Richard Morland: player-coach digital, AI & experience design leader. 25 years across HSBC, Diageo, Nike, BBC, Ford, Samsung and more.

## Structure

- `index.html` — homepage (hero, approach, capabilities, brand wall, case study grid, experience, contact)
- `case-studies/` — 15 individual case study pages
- `assets/css/style.css` — single shared stylesheet
- `assets/js/gate.js` — session password gate (see below)
- `assets/js/main.js` — case study filter
- `assets/img/` — optimised case study imagery and brand logos
- `assets/Richard-Morland-CV.pdf` — downloadable CV

## Password protection

All pages are gated client-side via `assets/js/gate.js`. The password is stored as a SHA-256 hash, not plain text. The gate deters casual access and the site carries a `noindex` tag; for stronger protection use host-level password protection (Netlify / Vercel / Cloudflare Pages).

## Deploying

The site is fully static — no build step. Point any static host at the repository root.
