# Gebhart Construction website: shared build rules

Every agent working in `sites/gebhart-construction/` follows this file. Do not touch anything outside it (especially `trading_bot/`).

## Source of truth

- Facts come only from `src/data/*.json`, which is filled from the client handoff (2026-10-03). Never invent years in business, license numbers, insurance claims, warranties, certifications, service cities, review text, stats, or hours.
- A missing fact is shown on the page through `<Todo label="SERVICE AREA" />`, which renders a visible `[SERVICE AREA — TBD]`. Never hide a gap with filler copy.
- Copy voice: plain, direct, short sentences. No corporate filler, no exclamation points in our copy (reviews are quoted as written).
- Core message: communication. Ryan explains the process, returns calls, gives daily updates, sticks to the quote.
- Keep these lines verbatim: "Quality Work. Honest Service. Great Value." and "Dedicated to constructing trust, one project at a time."

## Stack

- Astro (static output) + Tailwind CSS. No client framework; small vanilla JS islands only where needed (mobile nav, before/after slider, photo resize on the form).
- Hosting: Netlify. Forms: Netlify Forms.
- Content lives in `src/data/`: `business.json`, `services.json`, `reviews.json`, `projects.json`. Pages read from data; no business facts hard-coded in components.
- Images: `astro:assets` `<Image>` / `<Picture>`, WebP/AVIF, explicit width/height, descriptive file names (`roof-replacement-huber-heights-01.jpg`, never `20240618_103138.jpg`).

## Palette (design tokens)

Chosen palette: charcoal slate, amber accent, warm off-white. It replaces the plan to match the current site (owner's call, 2026-10-03). Set colors **only** here and in `src/styles/tokens.css`; components use the Tailwind names, never raw hex. If Ryan later supplies brand colors, swap them in the tokens and re-run the contrast check.

| Token | Tailwind name | Use | Value |
|---|---|---|---|
| `--color-brand` | `brand` | Header/footer/hero background, headings on light | `#1E293B` |
| `--color-accent` | `accent` | Primary button fill, highlights on dark | `#F59E0B` |
| `--color-accent-ink` | `accent-ink` | Text on accent buttons | `#1E293B` |
| `--color-link` | `link` | Text links on light backgrounds | `#92400E` |
| `--color-surface` | `surface` | Page background | `#FAF8F5` |
| `--color-surface-alt` | `surface-alt` | Alternating section bands | `#F1EDE6` |
| `--color-ink` | `ink` | Body text | `#1F2937` |
| `--color-muted` | `muted` | Secondary text | `#4B5563` |
| `--color-on-brand` | `on-brand` | Text on brand (dark) backgrounds | `#FFFFFF` |
| `--color-on-brand-muted` | `on-brand-muted` | Secondary text on brand | `#CBD5E1` |

Checked contrast (WCAG 2.1 AA needs 4.5:1 for normal text, 3:1 for large text and UI):

| Pair | Ratio |
|---|---|
| ink on surface / surface-alt | 13.85 / 12.58 |
| muted on surface / surface-alt | 7.13 / 6.48 |
| link on surface / surface-alt | 6.69 / 6.08 |
| accent-ink on accent (button text) | 6.81 |
| on-brand on brand | 14.63 |
| on-brand-muted on brand | 9.85 |
| accent on brand (text/icons on dark) | 6.81 |
| brand on surface (headings) | 13.80 |

**Never use `accent` (amber) as text, icons, or borders on light backgrounds:** it is only 2.03:1 on surface. On light sections, amber appears only as a button fill with `accent-ink` text; use `link` for colored text.

## Logo

- `src/assets/logo.svg` (or PNG at 2x if no vector exists). PENDING from the client; optional.
- Header logo links to `/`, with `alt="Gebhart Construction home"`. Until the file arrives, use a text wordmark "GEBHART CONSTRUCTION" in the heading font.

## Typography

Fonts:
- Headings: bold sans-serif (default **Archivo**, 700/800), self-hosted via `@fontsource`, no Google Fonts CDN.
- Body: **Inter**, 400/600, self-hosted.
- Scale: body 18px / 1.6 line height; H1 40–56px (clamp), H2 30–36px, H3 22–24px. Max line length about 70ch.
- One `<h1>` per page. No skipped heading levels.

## Layout and nav

- Container: `max-w-6xl mx-auto px-4 sm:px-6`. Section spacing `py-16 md:py-24`.
- Header (all pages): logo · Home · Services (Exterior / Interior groups) · Projects · About · Reviews · Contact · phone number as a `tel:` link · "Free Estimate" accent button.
- Mobile: a hamburger that opens a full-height panel (a `<button>` with `aria-expanded` and `aria-controls`; Esc closes it and focus returns to the button).
- Sticky mobile bottom bar under `md`: **Call** (`tel:+19375597385`) · **Text** (`sms:+19375597385`) · **Free Estimate** (`/contact/`). Add bottom padding so it never covers content.
- Footer: NAP block (from `business.json`), hours, Facebook/Instagram links, service-area placeholder, copyright.
- URLs: `/`, `/services/`, `/services/<slug>/`, `/projects/`, `/about/`, `/reviews/`, `/contact/`. Trailing slash on all of them.

## Shared components (lead-owned; other agents use them and do not edit them)

`BaseLayout`, `Header`, `Footer`, `MobileCallBar`, `Button`, `Section`, `Todo`, `ReviewCard`, `ServiceCard`, `CTABand`, `SEO` (title, description, canonical, OG, JSON-LD slot).

## Contact form (Netlify Forms)

- `<form name="estimate" method="POST" data-netlify="true" netlify-honeypot="bot-field" enctype="multipart/form-data" action="/thanks/">` with a hidden `form-name` input.
- Fields: name*, phone*, email, address, service (a dropdown fed from `services.json`), message, photos (`accept="image/*"`, up to 3).
- Netlify rejects any request over about 8 MB, and legacy free plans cap uploads at 10 MB/month. Resize photos in the browser (longest side 1600px, JPEG 0.8) before submit, and show the size limit in the field hint.
- Notification email to gebhartconst@gmail.com is set in the Netlify dashboard, not in code (README covers it).
- Every input has a visible `<label>`; required fields are marked in text, not by color alone; errors use `aria-describedby` and appear in an `aria-live="polite"` summary.

## Accessibility (WCAG 2.1 AA, required)

- `<html lang="en">`, a skip link to `#main`, and landmarks (`header`, `nav`, `main`, `footer`).
- Visible focus ring on every interactive element (`focus-visible:outline-2 outline-offset-2`, ≥ 3:1).
- Touch targets ≥ 44×44px.
- Meaningful `alt` on content images; `alt=""` on decorative ones.
- Before/after slider: a native `<input type="range">` with a label, so it works by keyboard and screen reader.
- Respect `prefers-reduced-motion`; no autoplaying carousels.
- Links say where they go ("View roofing projects", not "Click here").
- Content reflows at 320px wide with no horizontal scroll, and text resizes to 200%.

## SEO

- Titles like `Roofing Contractor in Huber Heights, OH | Gebhart Construction`; unique meta descriptions, 150–160 characters.
- JSON-LD `HomeAndConstructionBusiness` sitewide (name, phone, address, hours that are known, sameAs Facebook/Instagram, aggregateRating 5.0/22 per the handoff). Add `Service` on service pages and `BreadcrumbList` on inner pages.
- `sitemap.xml` via `@astrojs/sitemap`, plus `robots.txt`.

## Launch blockers (must be resolved before going live)

1. Address house number: the handoff says 7715 Beldale Dr, Huber Heights; Angi says 775 Beldale Ave, Dayton.
2. Ryan's okay to publish named reviews.
3. Logo file (text wordmark until then).
4. Every `TODO-CLIENT` placeholder: service area, years in business, license/insurance, weekday hours, bio/headshot, photos.
