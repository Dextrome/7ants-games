# 7 Ants Games

The studio site: **FUCK OFF** (Mo' Mentum Mo' Problems), playable in the browser at
[play.7antsgames.com](https://play.7antsgames.com/?connect), and **Slot Theory**
([Steam](https://store.steampowered.com/app/4523160/Slot_Theory/)).

## Open it

Published at [7antsgames.com](https://7antsgames.com) with GitHub Pages from `main` → `/docs`
(`docs/CNAME`; DNS at Cloudflare: CNAME `@` and `www` → `dextrome.github.io`, DNS only). Preview locally by serving `docs`
(`python -m http.server 8080 -d docs`). No build step, no dependencies, no cookies or
analytics; fonts are self-hosted (Silkscreen and Space Grotesk, SIL Open Font License). The Slot
Theory trailer comes from YouTube's privacy-enhanced player, loaded only when someone presses play.

## Pages

| URL | File | What it is |
| --- | --- | --- |
| `/` | `docs/index.html` | Studio home: the FUCK OFF hero, clips and toy, a Slot Theory teaser, the studio |
| `/fuck-off/` | `docs/fuck-off/index.html` | FUCK OFF: intro, fleet cards, the pub, maps, tutorial |
| `/fuck-off/momentum-physics/` | `docs/fuck-off/momentum-physics/index.html` | Guide: how flight works |
| `/slot-theory/` | `docs/slot-theory/index.html` | Slot Theory: trailer, gallery, how a run works, modes |
| `/slot-theory/how-to-play/` | `docs/slot-theory/how-to-play/index.html` | Guide: a first run |
| `/privacy/` | `docs/privacy/index.html` | Privacy notice: the online zone and this site (source: the game repo's `docs/privacy-notice.md`) |
| (any missing URL) | `docs/404.html` | Not found, not indexed |

Every page has its own title, description, canonical URL, Open Graph/Twitter tags and JSON-LD
(`@graph`; the studio is `https://7antsgames.com/#organization`). Paths are root-relative
(`/assets/...`). `docs/sitemap.xml` lists the six indexable pages and `docs/robots.txt` points to it:
add a new page to both. Guides state only what the games really do; check facts against the
game before changing them.

## Update it

- Page copy and links: the files above. Play links go to `play.7antsgames.com`
  (`?connect` online, `?tutorial`, `?mode=duel`).
- Styling: `docs/style.css` (shared by every page). Clip reel, lightbox, trailer and the Mo'
  Mentum toy: `docs/app.js`; each feature runs only on pages that have its elements. After
  changing either, bump `?v=` where the pages include them.
- Media: `python tools/prepare_media.py` rebuilds `docs/assets` from the game projects
  (FUCK OFF clips rendered by the game's own `tools/media/make_media.py`, the HD fleet drawn by
  its `tools/art/hd_fleet.html`, Slot Theory's Steam gallery, the portrait hero video for phones,
  the WebP logo). Needs ffmpeg, Pillow and Chrome or Edge. Name parts to rebuild only those:
  `python tools/prepare_media.py ships maps`.
- Share images: `python tools/make_og.py` renders `docs/assets/og/*.jpg` (1200x630) and
  `docs/assets/brand/logo.png` with Chrome or Edge and Pillow.
- Fleet cards: `python tools/ship_stats.py` writes them into `docs/fuck-off/index.html` from the
  game's `configs/dsb.cfg`. Run it after a balance change; edit the cards there, not in the page.

## Check it

`python tools/check_site.py` (standard library only) checks every page before a push: one H1,
unique titles and descriptions, canonical/OG/Twitter tags, valid JSON-LD with resolving `@id`s,
local links, anchors and images, alt text, sitemap and robots agreement, no em dashes, and
`node --check` on `app.js` when Node is installed. It also serves `docs` and fetches every path over
HTTP. It exits non-zero on any problem.

Copy rule: no em dashes.
