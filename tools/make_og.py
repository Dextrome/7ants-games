"""Draw the social preview cards (Open Graph / X) from the site's own fonts and game art.

Writes 1200x630 JPEGs to docs/assets/og/: studio.jpg (the home page), fuck-off.jpg and
slot-theory.jpg. Each card is an HTML page rendered by headless Chrome or Edge, so the type is
the site's Space Grotesk and Silkscreen. Run it after the hero frame, the Slot Theory gallery or
the logo changes.

Run: python tools/make_og.py      (needs Pillow and Chrome or Edge)
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "assets" / "og"
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
W, H = 1200, 630


def url(rel: str) -> str:
    return (DOCS / rel).resolve().as_uri()


BASE_CSS = f"""
@font-face {{ font-family: "Space Grotesk"; src: url("{url('fonts/SpaceGrotesk-400_700.woff2')}") format("woff2"); font-weight: 400 700; }}
@font-face {{ font-family: "Silkscreen"; src: url("{url('fonts/Silkscreen-400.woff2')}") format("woff2"); font-weight: 400; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #05060a; color: #eef1f7; }}
body {{ font-family: "Space Grotesk", sans-serif; position: relative; }}
.bg {{ position: absolute; inset: 0; background-size: cover; background-position: center; image-rendering: pixelated; }}
.pixel {{ font-family: "Silkscreen", monospace; text-transform: uppercase; letter-spacing: .02em; }}
.brand {{ display: flex; align-items: center; gap: 14px; font-weight: 700; font-size: 30px; letter-spacing: .01em; }}
.brand svg {{ width: 44px; height: 44px; color: #f2c94c; fill: #f2c94c; }}
.wordmark {{ display: flex; align-items: center; font-weight: 700; line-height: .86; letter-spacing: -0.055em; text-transform: uppercase; }}
.wordmark span {{ background: linear-gradient(180deg, #fff 30%, #ffe08a 75%, #f2c94c 100%); -webkit-background-clip: text; background-clip: text; color: transparent; }}
.wordmark img {{ width: .62em; height: .62em; margin: 0 .03em 0 .02em; transform: rotate(180deg); filter: drop-shadow(0 0 18px rgba(242, 201, 76, .6)); }}
.scan {{ position: absolute; inset: 0; opacity: .3; mix-blend-mode: multiply; background: repeating-linear-gradient(180deg, transparent 0 2px, rgba(0,0,0,.55) 2px 3px); }}
"""
MARK = ('<svg viewBox="0 0 32 32"><path d="M7 6h18l-9 21" fill="none" stroke="currentColor" stroke-width="3.2" '
        'stroke-linejoin="round"/><circle cx="23.5" cy="21" r="2.6"/><circle cx="26.8" cy="25.6" r="2"/>'
        '<circle cx="20.6" cy="26.4" r="1.6"/></svg>')
SHIP = url("assets/fuck-off/ships/kestrel.png")
WORDMARK = f'<span>F</span><img src="{SHIP}" alt=""><span>CK OFF</span>'

CARDS = {
    "studio": f"""
<div class="bg" style="background-image:url('{url('assets/fuck-off/hero.jpg')}'); clip-path: polygon(0 0, 62% 0, 46% 100%, 0 100%); filter: saturate(1.15)"></div>
<div class="bg" style="background-image:url('{url('assets/slot-theory/03_nyx7_bass_drop.jpg')}'); image-rendering:auto; clip-path: polygon(62% 0, 100% 0, 100% 100%, 46% 100%)"></div>
<div style="position:absolute; inset:0; background: linear-gradient(180deg, rgba(5,6,10,.97) 0%, rgba(5,6,10,.9) 24%, rgba(5,6,10,.35) 44%, rgba(5,6,10,.45) 62%, rgba(5,6,10,.94) 100%)"></div>
<div style="position:absolute; left:0; right:0; top:0; height:230px; background: linear-gradient(180deg, #05060a 62%, rgba(5,6,10,0))"></div>
<div style="position:absolute; top:0; bottom:0; left:46%; width:16%; background: linear-gradient(100deg, transparent 49.6%, #f2c94c 49.8%, #f2c94c 50.4%, transparent 50.6%)"></div>
<div style="position:absolute; left:56px; top:48px" class="brand">{MARK}<span style="font-size:46px">7 Ants Games</span></div>
<p class="pixel" style="position:absolute; left:58px; top:118px; font-size:20px; color:#98a1b5">Two games. One plays in your browser.</p>
<div style="position:absolute; left:56px; bottom:52px">
  <div class="wordmark" style="font-size:96px">{WORDMARK}</div>
  <p class="pixel" style="font-size:18px; color:#ff4fa3; margin-top:14px">Plays in your browser</p>
</div>
<div style="position:absolute; right:56px; bottom:52px; text-align:right">
  <img src="{url('assets/slot-theory/logo.png')}" alt="" style="width:470px; filter: drop-shadow(0 0 24px rgba(255,63,164,.45))">
  <p class="pixel" style="font-size:18px; color:#33e3c9; margin-top:14px">On Steam</p>
</div>
""",
    "fuck-off": f"""
<div class="bg" style="background-image:url('{url('assets/fuck-off/hero.jpg')}'); filter: saturate(1.15) contrast(1.05)"></div>
<div style="position:absolute; inset:0; background: linear-gradient(90deg, rgba(5,6,10,.94) 0%, rgba(5,6,10,.75) 55%, rgba(5,6,10,.35) 100%)"></div>
<div class="scan"></div>
<div style="position:absolute; left:64px; top:150px">
  <div class="wordmark" style="font-size:168px">{WORDMARK}</div>
  <p class="pixel" style="font-size:34px; color:#ff4fa3; margin-top:26px; text-shadow: 0 0 22px rgba(255,79,163,.5)">Mo' Mentum Mo' Problems</p>
  <p style="font-size:30px; color:#d6dbe6; margin-top:22px; max-width:900px; line-height:1.3">Multiplayer space combat with no brakes. Plays in your browser.</p>
</div>
<div style="position:absolute; left:64px; top:48px" class="brand">{MARK}<span>7 Ants Games</span></div>
""",
    "slot-theory": f"""
<div class="bg" style="background-image:url('{url('assets/slot-theory/02_choose_your_tower.jpg')}'); image-rendering:auto"></div>
<div style="position:absolute; inset:0; background: linear-gradient(180deg, rgba(10,13,32,.6) 0%, rgba(10,13,32,.9) 45%, rgba(10,13,32,.97) 100%)"></div>
<div style="position:absolute; left:0; right:0; top:150px; display:grid; justify-items:center; text-align:center">
  <img src="{url('assets/slot-theory/logo.png')}" alt="" style="width:960px; filter: drop-shadow(0 0 30px rgba(255,63,164,.45))">
  <p style="font-size:40px; font-weight:700; margin-top:40px">Roguelike tower defense. One draft every wave.</p>
  <p class="pixel" style="font-size:22px; color:#33e3c9; margin-top:22px">Solo campaigns | Online co-op | Daily Rift | Map editor</p>
</div>
<div style="position:absolute; left:56px; bottom:40px" class="brand">{MARK}<span>7 Ants Games</span></div>
<p class="pixel" style="position:absolute; right:56px; bottom:50px; font-size:20px; color:#c4ff3d">On Steam</p>
""",
}


def browser() -> str:
    for b in BROWSERS:
        if Path(b).exists():
            return b
    raise SystemExit("needs Chrome or Edge")


def shoot(exe: str, tmp: Path, name: str, html: str, w: int, h: int) -> Image.Image:
    page = tmp / f"{name}.html"
    page.write_text(html, encoding="utf-8")
    png = tmp / f"{name}.png"
    subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    f"--window-size={w},{h}", "--virtual-time-budget=3000", f"--screenshot={png}",
                    page.as_uri()], check=True, capture_output=True)
    im = Image.open(png).convert("RGB")
    return im if im.size == (w, h) else im.crop((0, 0, w, h))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    exe = browser()
    with tempfile.TemporaryDirectory() as tmp:
        for name, body in CARDS.items():
            html = f"<!doctype html><meta charset=utf-8><style>{BASE_CSS}</style><body>{body}</body>"
            out = OUT / f"{name}.jpg"
            shoot(exe, Path(tmp), name, html, W, H).save(out, quality=84, optimize=True, progressive=True)
            print(f"{out.relative_to(ROOT)}  {out.stat().st_size / 1e3:.0f} kB")
        # The studio logo for structured data (Organization.logo): the favicon's mark at 512 px.
        brand = DOCS / "assets" / "brand"
        brand.mkdir(parents=True, exist_ok=True)
        html = ("<!doctype html><meta charset=utf-8><style>*{margin:0}html,body{width:512px;height:512px;"
                f"background:#05060a}}img{{display:block;width:512px;height:512px}}</style><img src=\"{url('assets/favicon.svg')}\">")
        out = brand / "logo.png"
        shoot(exe, Path(tmp), "logo", html, 512, 512).save(out, optimize=True)
        print(f"{out.relative_to(ROOT)}  {out.stat().st_size / 1e3:.0f} kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
