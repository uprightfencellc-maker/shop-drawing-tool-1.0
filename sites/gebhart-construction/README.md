# Gebhart Construction website

Static site built with Astro + Tailwind CSS, hosted on Netlify, with the estimate form on Netlify Forms.

## Run it locally

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # outputs dist/
npm run check    # type check
```

Node 22 or newer.

## Edit content

All business facts live in `src/data/`. Change them there, not in the page files.

| File | What's in it |
|---|---|
| `business.json` | Name, phone, email, address, hours, ratings, social links, "how we work" steps, and the pending fields (`serviceArea`, `yearsInBusiness`, `licenseInsurance`, `bio`, `headshot`) |
| `services.json` | The 7 services: name, Exterior/Interior group, short blurb, scope list, page title and description |
| `reviews.json` | Reviews shown on the site. Add the Google reviews here. `tags` match a service's `reviewTags` to show on that service page |
| `projects.json` | Gallery items. Put photos in `src/assets/projects/` and reference them by file name |

**Placeholders.** Anything not confirmed by the client shows on the page as a highlighted `[LABEL — TBD]`. To find them all:

```bash
grep -rn "Todo label" src/
```

**Hours.** In `business.json`, `opens` and `closes` are 24-hour times like `"08:00"`. A `null` shows as TBD. Once the hours are confirmed, also add `openingHoursSpecification` to `businessJsonLd` in `src/lib/site.ts`.

**Before/after photos.** Give a project both `"before"` and `"after"` file names and it renders as a slider. Use descriptive file names, like `roof-replacement-huber-heights-01.jpg`.

**Gallery filters** appear automatically once projects span more than one service.

## Swap colors, fonts and logo

- **Colors:** edit `src/styles/tokens.css` only. Then re-check contrast (the table and rules are in `CLAUDE.md`). Bright amber must never be used as text on a light background.
- **Fonts:** change the `@fontsource` imports and `--font-heading` / `--font-body` in `src/styles/global.css`, and install the new package (`npm i @fontsource/<name>`).
- **Logo:** the header and footer use a text wordmark. To use a logo file, add it to `src/assets/` and swap the wordmark `<a>` in `src/components/Header.astro` and the matching `<p>` in `Footer.astro` for an `<Image>`. Keep `alt="Gebhart Construction home"` on the header link.
- **Social share image:** `public/og-image.jpg` (1200×630).

## Deploy (Netlify)

1. In Netlify: **Add new site → Import an existing project**, then pick this repo.
2. Set **Base directory** to `sites/gebhart-construction`. The build command and publish folder come from `netlify.toml`.
3. Under **Forms**, turn on form detection, then redeploy so the `estimate` form is picked up.
4. Under **Forms → Form notifications**, add an email notification to gebhartconst@gmail.com.
5. Point the domain gebhartconstruction.com at the Netlify site (Domain management).

### Form limits
Netlify rejects any submission over about 8 MB. Legacy free plans also cap uploads at 10 MB a month. The form shrinks photos in the browser (longest side 1600px, JPEG) and allows at most 3. If the browser can't read a photo format, such as some iPhone HEIC files, it sends the original file. Check the Netlify plan's limits before launch.

## Before launch

- [ ] Confirm the street address: the handoff says 7715 Beldale Dr, Huber Heights; Angi says 775 Beldale Ave, Dayton.
- [ ] Ryan's okay to publish the named reviews (`reviews.json` → set `publishApproved` to `true` as a record).
- [ ] Clear every `[… — TBD]` placeholder.
- [ ] Add the Google review link (`business.json` → `ratings.google.reviewUrl`).
- [ ] Get more project photos.
- [ ] Send a test form submission on the live site and confirm the email arrives.
