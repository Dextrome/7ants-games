"""Build docs/assets from the game projects' own media.

Sources (local, not in this repo):
  E:/DexSpace/build/media/      FUCK OFF clips and videos (rendered by the game, tools/media/make_media.py)
  E:/DexSpace/tools/art/        the HD fleet, drawn in code by hd_fleet.html
  E:/SlotTheory/promo_images/   Slot Theory's Steam gallery (the 2026-11-18 captures, game 1.9.4) and logo

Needs ffmpeg on PATH, Pillow and Chrome or Edge.
Run: python tools/prepare_media.py [hero clips maps ships slot]   (default: all of them)
"""
from __future__ import annotations

import base64
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets"
DEX = Path("E:/DexSpace")
SLOT = Path("E:/SlotTheory")
CLIPS = DEX / "build/media/clips"
VIDEOS = DEX / "build/media/videos"

# (output name, source clip, caption version, start s, length s)
REEL = [
    ("tutorial-boss", "feature-tutorial-boss", "loud", 0, 30),
    ("momentum", "mech-momentum", "loud", 0, 30),
    ("bot-pilots", "feature-bot-pilots", "plain", 0, 30),
    ("hundred-pilots", "feature-100-pilots", "plain", 0, 30),
    ("burst", "mech-burst", "plain", 0, 30),
    ("orbs", "mech-orbs", "plain", 0, 30),
]
MAPS = [("hollow", 0.30), ("compass", 0.45), ("bulwark", 0.40), ("drift", 0.45)]
# The game's fleet page draws each hull at 64 px in an 80 px cell; here four times that, for the web.
SHIP_CELL, SHIP_MASTER, SHIP_OUTLINE_PX = 320, 256, 3
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
SLOT_SHOTS = [
    "01_breach_aegis", "02_choose_your_tower", "03_nyx7_bass_drop", "05_astra_singularity",
    "06_draft_your_modifiers", "07_detonator_chain_explosions", "08_rift_warp", "10_warden_lockdown",
]


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def caption_gap(name: str, at: float) -> float:
    """The moment between two captions of a clip nearest to the fraction `at` of its length."""
    spec = json.loads((DEX / "tools/media/specs" / f"{name}.json").read_text(encoding="utf-8"))
    cues = spec["captions"]
    gaps = [(a[1] + b[0]) / 2 for a, b in zip(cues, cues[1:]) if b[0] > a[1]]
    return min(gaps, key=lambda t: abs(t - spec["duration_s"] * at))


def render_ships(out: Path) -> None:
    """Draw the game's HD hulls with its own page, nose up, at four times the game's size."""
    page = (DEX / "tools/art/hd_fleet.html").read_text(encoding="utf-8")
    page = page.replace("const CELL = 80, MASTER = 64,", f"const CELL = {SHIP_CELL}, MASTER = {SHIP_MASTER},")
    page, found = re.subn(r"const sheet = document\.getElementById\('view'\);.*?toDataURL\('image/png'\);",
                          "document.getElementById('sheet').textContent = NAMES.map(n => "
                          "n + '=' + cell(n, 0).toDataURL('image/png')).join(' ');", page, flags=re.S)
    if found != 1:
        raise SystemExit("hd_fleet.html: the sheet code has changed")
    browser = next(b for b in BROWSERS if Path(b).exists())
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        path = Path(tmp) / "fleet.html"
        path.write_text(page, encoding="utf-8")
        dom = subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-first-run",
                              f"--user-data-dir={tmp}/profile", "--virtual-time-budget=20000",
                              "--dump-dom", path.as_uri()],
                             capture_output=True, text=True, timeout=300, check=True).stdout
    hulls = re.findall(r"([A-Za-z]+)=data:image/png;base64,([A-Za-z0-9+/=]+)", dom)
    if len(hulls) != 8:
        raise SystemExit(f"hd_fleet.html: expected 8 hulls, got {len(hulls)}")
    for name, data in hulls:
        hull = Image.open(io.BytesIO(base64.b64decode(data))).convert("RGBA")
        # The page's outline is one pixel at any size: thicken it to the game's proportion.
        grown = hull.getchannel("A").filter(ImageFilter.MaxFilter(SHIP_OUTLINE_PX * 2 + 1))
        ship = Image.new("RGBA", hull.size, (5, 6, 10, 0))
        ship.paste((5, 6, 10, 255), mask=grown)
        ship.alpha_composite(hull)
        ship.save(out / f"{name.lower()}.png", optimize=True)


def main() -> int:
    parts = set(sys.argv[1:]) or {"hero", "clips", "maps", "ships", "slot"}
    fo = OUT / "fuck-off"
    st = OUT / "slot-theory"
    for d in (fo / "clips", fo / "maps", fo / "ships", st):
        d.mkdir(parents=True, exist_ok=True)

    # Hero: a busy stretch of a 16 v 16 pub on The Hollow, between two of its captions (38 to 56 s),
    # centre-cropped (the camera follows a pilot, so the action is in the middle), silent, small.
    if "hero" in parts:
        hero_src = VIDEOS / "video-pub-hollow.plain.mp4"
        vf = "crop=1280:720,setsar=1"
        ff("-ss", "38", "-t", "18", "-i", str(hero_src), "-an", "-vf", vf, "-c:v", "libx264",
           "-crf", "27", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           str(fo / "hero.mp4"))
        ff("-ss", "42", "-i", str(hero_src), "-frames:v", "1", "-vf", vf, "-q:v", "4", str(fo / "hero.jpg"))

    # Vertical clips: drawn at 540x960 and doubled by the recorder, so 540x960 loses nothing.
    if "clips" in parts:
        for name, src, version, start, length in REEL:
            path = CLIPS / f"{src}.{version}.mp4"
            vf = "scale=540:960:flags=neighbor"
            ff("-ss", str(start), "-t", str(length), "-i", str(path), "-vf", vf, "-c:v", "libx264",
               "-crf", "26", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
               "-movflags", "+faststart", str(fo / "clips" / f"{name}.mp4"))
            ff("-ss", "4", "-i", str(path), "-frames:v", "1", "-vf", vf, "-q:v", "4",
               str(fo / "clips" / f"{name}.jpg"))

    # Map stills from the map tours, taken between two captions.
    if "maps" in parts:
        for name, at in MAPS:
            ff("-ss", f"{caption_gap(f'map-{name}', at):.2f}", "-i", str(CLIPS / f"map-{name}.plain.mp4"),
               "-frames:v", "1", "-vf", "scale=540:960:flags=neighbor", "-q:v", "3",
               str(fo / "maps" / f"{name}.jpg"))

    if "ships" in parts:
        render_ships(fo / "ships")

    # Slot Theory: native 2560x1440 Steam captures, resized for the web.
    if "slot" in parts:
        gallery = SLOT / "promo_images/screenshots/steam_gallery_2026_11_18/gallery"
        for shot in SLOT_SHOTS:
            im = Image.open(gallery / f"{shot}.png").convert("RGB")
            im.resize((1600, 900), Image.LANCZOS).save(st / f"{shot}.jpg", quality=84, optimize=True)
            im.resize((640, 360), Image.LANCZOS).save(st / f"{shot}.thumb.jpg", quality=80, optimize=True)
        logo = Image.open(SLOT / "promo_images/promo/slot_theory_logo_oneline.png")
        logo.thumbnail((1100, 1100), Image.LANCZOS)
        logo.save(st / "logo.png", optimize=True)

    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"assets: {total / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
