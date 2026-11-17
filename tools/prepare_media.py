"""Build docs/assets from the game projects' own media.

Sources (local, not in this repo):
  E:/DexSpace/build/media/      FUCK OFF clips and videos (rendered by the game, tools/media/make_media.py)
  E:/DexSpace/assets/ships/     the eight ship sprites
  E:/SlotTheory/promo/          Slot Theory's Steam gallery and logo

Needs ffmpeg on PATH and Pillow. Run: python tools/prepare_media.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

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
SHIPS = ["kestrel", "shrike", "mantis", "bastion", "swift", "wraith", "anvil", "hammerhead"]
SLOT_SHOTS = [
    "01_breach_aegis", "02_choose_your_tower", "03_nyx7_bass_drop",
    "05_astra_singularity", "07_detonator_chain_explosions", "10_warden_lockdown",
]


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def main() -> int:
    fo = OUT / "fuck-off"
    st = OUT / "slot-theory"
    for d in (fo / "clips", fo / "maps", fo / "ships", st):
        d.mkdir(parents=True, exist_ok=True)

    # Hero: a busy stretch of a 16 v 16 pub on The Hollow, centre-cropped (the camera follows a
    # pilot, so the action is in the middle), silent, small.
    hero_src = VIDEOS / "video-pub-hollow.none.mp4"
    vf = "crop=1280:720,setsar=1"
    ff("-ss", "30", "-t", "18", "-i", str(hero_src), "-an", "-vf", vf, "-c:v", "libx264",
       "-crf", "27", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
       str(fo / "hero.mp4"))
    ff("-ss", "30", "-i", str(hero_src), "-frames:v", "1", "-vf", vf, "-q:v", "4", str(fo / "hero.jpg"))

    # Vertical clips: drawn at 540x960 and doubled by the recorder, so 540x960 loses nothing.
    for name, src, version, start, length in REEL:
        path = CLIPS / f"{src}.{version}.mp4"
        vf = "scale=540:960:flags=neighbor"
        ff("-ss", str(start), "-t", str(length), "-i", str(path), "-vf", vf, "-c:v", "libx264",
           "-crf", "26", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
           "-movflags", "+faststart", str(fo / "clips" / f"{name}.mp4"))
        ff("-ss", "4", "-i", str(path), "-frames:v", "1", "-vf", vf, "-q:v", "4",
           str(fo / "clips" / f"{name}.jpg"))

    # Map stills from the caption-free map tours.
    for name, at in MAPS:
        path = CLIPS / f"map-{name}.none.mp4"
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                    "-of", "csv=p=0", str(path)], capture_output=True, text=True,
                                   check=True).stdout)
        ff("-ss", f"{dur * at:.2f}", "-i", str(path), "-frames:v", "1",
           "-vf", "scale=540:960:flags=neighbor", "-q:v", "3", str(fo / "maps" / f"{name}.jpg"))

    for ship in SHIPS:
        shutil.copy2(DEX / "assets/ships" / f"{ship}.png", fo / "ships" / f"{ship}.png")

    # Slot Theory: native 2560x1440 Steam captures, resized for the web.
    gallery = SLOT / "promo/steam_gallery_2026_10_25/gallery"
    for shot in SLOT_SHOTS:
        im = Image.open(gallery / f"{shot}.png").convert("RGB")
        im.resize((1600, 900), Image.LANCZOS).save(st / f"{shot}.jpg", quality=84, optimize=True)
        im.resize((640, 360), Image.LANCZOS).save(st / f"{shot}.thumb.jpg", quality=80, optimize=True)
    logo = Image.open(SLOT / "promo/slot_theory_logo_oneline.png")
    logo.thumbnail((1100, 1100), Image.LANCZOS)
    logo.save(st / "logo.png", optimize=True)

    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"assets: {total / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
