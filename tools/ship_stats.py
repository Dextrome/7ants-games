"""Write the fleet's stat cards into docs/fuck-off/index.html from the game's own settings.

Reads E:/DexSpace/configs/dsb.cfg and replaces everything between the fleet:start and fleet:end
comments. The arithmetic follows the simulation (src/simulation/Ship.cpp, World.cpp):
  recharge and boost cost   thousandths of energy per tick, 100 ticks a second
  thrust                    px/10s gained per tick
  rotation                  1/40000 of a turn per tick
  shot                      guns x BulletFireEnergy; each bullet does 134 + 33 per gun level
  bomb                      blast radius 40 px per bomb level; EMP bombs do 10% damage

Each stat has `empty`, the value of an empty bar. A full bar is the best ship in the fleet. When
`empty` is above every ship's value, less is better (costs, reload).

Run: python tools/ship_stats.py
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "fuck-off" / "index.html"
CONFIG = Path("E:/DexSpace/configs/dsb.cfg")

# (config section, name, card color, one line)
TEAMS = [
    ("Team 1", [
        ("Warbird", "Kestrel", "#c6ccd8", "Light, quick and cheap to shoot."),
        ("Javelin", "Shrike", "#e6a94a", "Big guns, no bombs."),
        ("Spider", "Mantis", "#62c384", "The fastest bombs in the fleet."),
        ("Leviathan", "Bastion", "#bcc86a", "EMP bombs and the deepest energy."),
    ]),
    ("Team 2", [
        ("Terrier", "Swift", "#f0626a", "The quickest turn in the fleet."),
        ("Weasel", "Wraith", "#7fa9f2", "The cheapest shots of the big guns."),
        ("Lancaster", "Anvil", "#b583f2", "EMP bombs on a budget."),
        ("Shark", "Hammerhead", "#9a9af0", "Level 3 bombs, slow to turn."),
    ]),
]
ITEMS = [("InitialRocket", "rocket"), ("InitialRepel", "repel"), ("InitialBurst", "burst"),
         ("InitialPortal", "portal"), ("InitialDecoy", "decoy"), ("MaxMines", "mine")]


@dataclass
class Stat:
    label: str
    value: Callable[[dict], Optional[float]]
    empty: float


def read_config(path: Path) -> dict[str, dict[str, int]]:
    sections: dict[str, dict[str, int]] = {}
    current: dict[str, int] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(";")[0].strip()
        if line.startswith("["):
            current = sections.setdefault(line.strip("[]"), {})
        elif "=" in line:
            key, value = line.split("=", 1)
            current[key.strip()] = int(value)
    return sections


def main() -> int:
    cfg = read_config(CONFIG)
    bullet, upgrade = cfg["Bullet"]["BulletDamageLevel"], cfg["Bullet"]["BulletDamageUpgrade"]
    bomb_damage = cfg["Bomb"]["BombDamageLevel"]
    emp_damage = bomb_damage * cfg["Bomb"]["EBombDamagePercent"] / 1000
    blast = cfg["Bomb"]["BombExplodePixels"]

    def volley(s: dict) -> int:
        return (bullet + upgrade * (s["InitialGuns"] - 1)) * (2 if s["DoubleBarrel"] else 1)

    def bombs(field: Callable[[dict], float]) -> Callable[[dict], Optional[float]]:
        return lambda s: field(s) if s["InitialBombs"] else None

    groups = [
        ("Flight", [
            Stat("Energy", lambda s: s["InitialEnergy"], 700),
            Stat("Recharge", lambda s: s["InitialRecharge"] / 10, 150),
            Stat("Top speed", lambda s: s["InitialSpeed"] / 10, 200),
            Stat("Boost speed", lambda s: s["MaximumSpeed"] / 10, 300),
            Stat("Thrust", lambda s: s["InitialThrust"] * 10, 120),
            Stat("Turn rate", lambda s: s["InitialRotation"] * 0.9, 90),
            Stat("Boost cost", lambda s: s["AfterburnerEnergy"] / 10, 800),
        ]),
        ("Guns", [
            Stat("Damage", volley, 150),
            Stat("Fire rate", lambda s: 100 / s["BulletFireDelay"], 2),
            Stat("Bullet speed", lambda s: s["BulletSpeed"] / 10, 150),
            Stat("Shot cost", lambda s: s["BulletFireEnergy"] * s["InitialGuns"], 100),
        ]),
        ("Bombs", [
            Stat("Damage", bombs(lambda s: emp_damage if s["EmpBomb"] else bomb_damage), 0),
            Stat("Blast radius", bombs(lambda s: blast * s["InitialBombs"]), 40),
            Stat("Bomb speed", bombs(lambda s: s["BombSpeed"] / 10), 250),
            Stat("Bomb cost", bombs(lambda s: s["BombFireEnergy"]), 400),
            Stat("Reload", bombs(lambda s: s["BombFireDelay"] / 100), 1.5),
        ]),
    ]

    fleet = [cfg[section] for _, ships in TEAMS for section, *_ in ships]

    def row(stat: Stat, ship: dict) -> str:
        value = stat.value(ship)
        label = escape(stat.label)
        if value is None:
            return (f'<div class="stat stat-none"><dt>{label}</dt><dd><span class="bar" role="img" '
                    f'aria-label="None"></span></dd></div>')
        values = [v for v in map(stat.value, fleet) if v is not None]
        best = min(values) if stat.empty > max(values) else max(values)
        fill = max(0.0, min(1.0, (value - stat.empty) / (best - stat.empty)))
        return (f'<div class="stat" style="--v:{fill:.2f}"><dt>{label}</dt><dd><span class="bar" role="img" '
                f'aria-label="{round(fill * 100)} out of 100"><i></i></span></dd></div>')

    def card(section: str, name: str, color: str, line: str) -> str:
        ship = cfg[section]
        out = [f'          <article class="ship" style="--ship:{color}">',
               '            <div class="ship-head">',
               f'              <img src="/assets/fuck-off/ships/{name.lower()}.png" alt="" width="320" height="320" loading="lazy">',
               f'              <div><h4>{escape(name)}</h4><p class="ship-line">{escape(line)}</p></div>',
               '            </div>']
        for title, stats in groups:
            unused = all(stat.value(ship) is None for stat in stats)
            note = '<span class="h-none"> None</span>' if unused else ""
            out.append(f'            <h5 class="pixel">{title}{note}</h5>')
            out.append('            <dl class="spec">')
            out += [f'              {row(stat, ship)}' for stat in stats]
            out.append('            </dl>')
        items = ["EMP bombs"] if ship["EmpBomb"] else []
        items += [f'{ship[key]} {word}{"s" if ship[key] != 1 else ""}' for key, word in ITEMS if ship[key]]
        out.append('            <ul class="items">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
        out.append('          </article>')
        return "\n".join(out)

    blocks = []
    for team, ships in TEAMS:
        cards = "\n".join(card(*ship) for ship in ships)
        blocks.append(f'      <div class="team reveal">\n        <h3 class="team-name pixel"><span>{team}</span>'
                      f'<span class="swipe-hint" aria-hidden="true">Swipe &gt;</span></h3>\n'
                      f'        <div class="ships">\n{cards}\n        </div>\n      </div>')

    html = PAGE.read_bytes().decode("utf-8")
    block = "<!-- fleet:start (written by tools/ship_stats.py) -->\n" + "\n".join(blocks) + "\n      <!-- fleet:end -->"
    html, found = re.subn(r"<!-- fleet:start.*?<!-- fleet:end -->", lambda _: block, html, flags=re.S)
    if found != 1:
        raise SystemExit("docs/fuck-off/index.html: the fleet:start and fleet:end comments are missing")
    PAGE.write_bytes(html.encode("utf-8"))
    print("fleet cards written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
