"""Erzeugt frontend/icon.ico aus dem NoaToDo-Logo (Build-Tool, kein Runtime-Code).

Schneidet das Logo auf seinen sichtbaren Inhalt zu, zentriert es quadratisch mit
etwas Rand und schreibt ein .ico mit mehreren Auflösungen (16 bis 256), damit
Titelleiste, Taskbar und Alt+Tab das Logo scharf statt das Python-Icon zeigen.

Die Quelle liegt in ``assets/noatodo-logo.png`` im Wurzelverzeichnis, nicht im
Quellbaum: das Logo ist ein Projekt-Gut wie das Icon, kein Modul. Frueher zeigte
dieser Pfad auf ``Planung/NoaToDo Logo.png``; die Datei war laengst nach
``Planung/weiteres/`` umgezogen, das Werkzeug lief also gar nicht mehr, und
``Planung/`` gehoert seit der Oeffnung des Repos nicht mehr dazu.

Braucht ``pillow``, das bewusst nur in ``requirements-dev.txt`` steht: die App
selbst importiert kein PIL, und in das Bundle gehoert es nicht.

Aufruf (aus src/):  .\venv\Scripts\python.exe tools\make_icon.py
"""
from __future__ import annotations

import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
# HERE = <repo>/src/tools, also zwei Ebenen hoch in die Wurzel und dann assets/.
SRC = os.path.join(HERE, "..", "..", "assets", "noatodo-logo.png")
OUT = os.path.join(HERE, "..", "frontend", "icon.ico")

SIZES = [16, 24, 32, 48, 64, 128, 256]
PAD_RATIO = 0.06  # transparenter Rand, damit der Kreis nicht am Icon-Rand klebt


def main() -> None:
    img = Image.open(SRC).convert("RGBA")

    # Auf den sichtbaren Inhalt (nicht-transparente Pixel) zuschneiden, sonst
    # erbt das Icon die leeren Ränder des 1280x1024-Quellbildes.
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    # Quadratische, transparente Leinwand mit Rand, Logo mittig platzieren.
    side = max(img.size)
    pad = int(side * PAD_RATIO)
    canvas_side = side + 2 * pad
    canvas = Image.new("RGBA", (canvas_side, canvas_side), (0, 0, 0, 0))
    canvas.paste(img, ((canvas_side - img.width) // 2,
                       (canvas_side - img.height) // 2), img)

    canvas.save(OUT, format="ICO", sizes=[(s, s) for s in SIZES])
    print("geschrieben:", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
