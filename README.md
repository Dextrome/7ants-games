# 7 Ants Games

The studio site: **FUCK OFF** (Mo' Mentum Mo' Problems), playable in the browser at
[play.7antsgames.com](https://play.7antsgames.com/?connect), and **Slot Theory**
([Steam](https://store.steampowered.com/app/4523160/Slot_Theory/)).

## Open it

Published at [7antsgames.com](https://7antsgames.com) with GitHub Pages from `main` → `/docs`
(`docs/CNAME`; DNS at Cloudflare: CNAME `@` and `www` → `dextrome.github.io`, DNS only). Preview locally by serving `docs`
(`python -m http.server 8080 -d docs`). No build step, no dependencies, no cookies or
analytics; fonts are self-hosted (Silkscreen and Space Grotesk, SIL Open Font License).

## Update it

- Page copy and links: `docs/index.html`. Play links go to `play.7antsgames.com`
  (`?connect` online, `?tutorial`, `?mode=duel`).
- Styling: `docs/style.css`. Clip reel, lightbox and the Mo' Mentum toy: `docs/app.js`.
- Media: `python tools/prepare_media.py` rebuilds `docs/assets` from the game projects
  (FUCK OFF clips rendered by the game's own `tools/media/make_media.py`, the HD fleet drawn by
  its `tools/art/hd_fleet.html`, Slot Theory's Steam gallery). Needs ffmpeg, Pillow and Chrome or
  Edge. Name parts to rebuild only those: `python tools/prepare_media.py ships maps`.
- Fleet cards: `python tools/ship_stats.py` writes them into `docs/index.html` from the game's
  `configs/dsb.cfg`. Run it after a balance change; edit the cards there, not in the page.

Copy rule: no em dashes.
