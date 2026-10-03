# Gebhart Construction website: shared build rules

Every agent working in `website/` follows this file. Do not touch anything outside `website/` (especially `trading_bot/`).

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

**PENDING:** colors and logo will match the current gebhartconstruction.com. Values come from the client's screenshot. Until then the tokens below hold neutral placeholder values. Change colors **only** here and in `src/styles/tokens.css`; components use the Tailwind names, never raw hex.

| Token | Tailwind name | Use | Value |
|---|---|---|---|
| `--color-brand` | `brand` | Header/footer background, headings | `PENDING-SCREENSHOT` |
| `--color-accent` | `accent` | Primary buttons, links, highlights | `PENDING-SCREENSHOT` |
| `--color-accent-ink` | `accent-ink` | Text on accent buttons | `PENDING-SCREENSHOT` |
| `--color-surface` | `surface` | Page background | `PENDING-SCREENSHOT` |
| `--color-surface-alt` | `surface-alt` | Alternating section bands | `PENDING-SCREENSHOT` |
| `--color-ink` | `ink` | Body text | `PENDING-SCREENSHOT` |
| `--color-muted` | `muted` | Secondary text | `PENDING-SCREENSHOT` |

Contrast rules (checked when values are set): body text ≥ 4.5:1 on its background; large text (≥ 24px, or ≥ 18.66px bold) and UI borders/icons ≥ 3:1. If a brand color fails as text, use it for fills only and pick a darker shade for text.

## Logo

- `src/assets/logo.svg` (or PNG at 2x if no vector exists). PENDING from the client.
- Header logo links to `/`, with `alt="Gebhart Construction home"`. Until the file arrives, use a text wordmark "GEBHART CONSTRUCTION" in the heading font.

## Typography

PENDING the screenshot. If the current site's fonts can be identified, use them; otherwise the defaults are:
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
3. Colors, logo, and fonts from the screenshot.
4. Every `TODO-CLIENT` placeholder: service area, years in business, license/insurance, weekday hours, bio/headshot, photos.
