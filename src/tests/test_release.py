# NoaToDo, a local encrypted to-do app for Windows.
# Copyright (C) 2026 Noa Gnos
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Auslieferungs- und Regressionspruefungen (Bauplan Phase 9).

Diese Datei prueft Zusagen, die man dem laufenden Programm nicht ansieht,
sondern nur dem Quellbaum und dem Bau: die Release-Haertung (G34), die
Frontend-Integritaet (G27), die Logging-Politik (G29/N11.12.2), die
XSS-Grundregel (B.9 Regel 1) und drei Regressionen, die schon einmal weh getan
haben (G9 Entwicklungs-Schluessel, G26 Screenshot-Schutz, `private_mode`).
"""
from __future__ import annotations

import os
import re

import pytest

import buildinfo
import integrity

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _quelle(*teile: str) -> str:
    with open(os.path.join(CODE, *teile), "r", encoding="utf-8") as fh:
        return fh.read()


def _kompakt(text: str) -> str:
    """Ohne jeden Leerraum vergleichen (``a=1`` und ``a = 1`` sind dasselbe)."""
    return re.sub(r"\s+", "", text)


def _nur_code(pfad: str) -> str:
    """Quelltext ohne Kommentare und Zeichenketten.

    Noetig fuer die Regressionspruefungen weiter unten: Begriffe wie
    ``DEV_AES_KEY`` oder ``private_mode=True`` stehen voellig zu Recht in
    Kommentaren ("ersatzlos entfernt", "nicht wieder einbauen"). Ein
    Textvergleich ueber die ganze Datei wuerde genau die Dokumentation
    bestrafen, die das Wiedereinbauen verhindern soll.
    """
    import io
    import tokenize

    with open(pfad, "rb") as fh:
        quelle = fh.read()
    teile = []
    try:
        for tok in tokenize.tokenize(io.BytesIO(quelle).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            teile.append(tok.string)
    except tokenize.TokenError:
        return quelle.decode("utf-8", "replace")
    return " ".join(teile)


def _alle_python_dateien():
    for root, dirs, files in os.walk(CODE):
        dirs[:] = [d for d in dirs
                   if d not in ("venv", "__pycache__", "build", "dist", "tests")]
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(root, name)


# ---------------------------------------------------------------------------
# G34: Release-Haertung
# ---------------------------------------------------------------------------

def test_debug_ist_im_release_hart_aus(monkeypatch):
    """G34 (a): im gefrorenen Build ist NOATODO_DEBUG wirkungslos."""
    monkeypatch.setenv("NOATODO_DEBUG", "1")
    monkeypatch.setattr(buildinfo.sys, "frozen", True, raising=False)
    assert buildinfo.is_frozen() is True
    assert buildinfo.debug_enabled() is False, "Release darf DevTools nie oeffnen"
    monkeypatch.delattr(buildinfo.sys, "frozen", raising=False)
    assert buildinfo.debug_enabled() is True     # im Quellbaum weiter moeglich


def test_es_gibt_nur_einen_debug_schalter():
    """Ein zweiter Schalter wuerde G34 (a) lautlos aushebeln."""
    treffer = []
    for pfad in _alle_python_dateien():
        if os.path.basename(pfad) == "buildinfo.py":
            continue
        with open(pfad, "r", encoding="utf-8") as fh:
            for nr, zeile in enumerate(fh, 1):
                if "NOATODO_DEBUG" in zeile and "environ" in zeile:
                    treffer.append(f"{os.path.relpath(pfad, CODE)}:{nr}")
    assert treffer == [], f"NOATODO_DEBUG direkt gelesen statt ueber buildinfo: {treffer}"


def test_text_select_ist_ausdruecklich_aus():
    """G34 (b): keine Textselektion (und damit kein natives Strg+C daran)."""
    assert "text_select=False" in _quelle("main.py")


def test_release_haertung_setzt_die_drei_webview_schalter():
    quelle = _quelle("main.py")
    for name in ("AreDevToolsEnabled", "AreBrowserAcceleratorKeysEnabled",
                 "AreDefaultContextMenusEnabled"):
        assert name in quelle, f"{name} fehlt (G34 c)"
    assert "buildinfo.is_release()" in quelle


def test_build_spec_liefert_keinen_quelltext_und_kein_upx():
    """G27: optimize=2 (keine Docstrings/asserts), kein UPX, fensterlos."""
    spec = _quelle("NoaToDo.spec")
    assert "optimize=2" in spec
    assert "upx=False" in spec
    assert "console=CONSOLE" in spec        # Default ist False (nur Debug an)
    for werkzeug in ('"pytest"', '"PyInstaller"', '"tkinter"'):
        assert werkzeug in spec, "Entwicklerwerkzeug nicht aus dem Bundle geschlossen"


# ---------------------------------------------------------------------------
# G27: Frontend-Integritaet
# ---------------------------------------------------------------------------

def test_manifest_deckt_die_ausfuehrbaren_frontend_dateien_ab():
    manifest = integrity.build_manifest(buildinfo.frontend_dir())
    for pflicht in ("index.html", "app.js", "style.css"):
        assert pflicht in manifest
        assert len(manifest[pflicht]) == 64        # SHA-256 als Hex
    assert any(k.startswith("fonts/") for k in manifest)


def test_ohne_manifest_wird_nicht_geprueft(monkeypatch):
    """Der Entwicklerstart darf nicht bei jeder Frontend-Aenderung Alarm schlagen."""
    monkeypatch.setattr(buildinfo, "FRONTEND_MANIFEST", {})
    assert integrity.check() == []


def test_veraenderte_datei_faellt_auf(monkeypatch, tmp_path):
    """G27-Nachweis in klein: ein Byte genuegt (im Bundle verhindert das den Start)."""
    quelle = buildinfo.frontend_dir()
    manifest = integrity.build_manifest(quelle)
    monkeypatch.setattr(buildinfo, "FRONTEND_MANIFEST", manifest)
    assert integrity.check() == []

    # Kopie mit einem geaenderten Byte, Frontend-Ordner darauf umbiegen.
    kopie = tmp_path / "frontend"
    kopie.mkdir()
    for rel in manifest:
        ziel = kopie / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        with open(os.path.join(quelle, rel.replace("/", os.sep)), "rb") as fh:
            ziel.write_bytes(fh.read())
    with open(kopie / "app.js", "ab") as fh:
        fh.write(b" ")
    monkeypatch.setattr(buildinfo, "frontend_dir", lambda: str(kopie))
    assert integrity.check() == ["app.js"]
    assert "integrity check failed" in integrity.message(["app.js"])

    # Fehlende Datei zaehlt ebenso als Beanstandung.
    os.remove(kopie / "style.css")
    assert "style.css (missing)" in integrity.check()


# ---------------------------------------------------------------------------
# G29 / N11.12.2: keine Logdatei, kein Traceback auf Platte
# ---------------------------------------------------------------------------

def test_kein_logfile_und_kein_traceback_ziel():
    verboten = ("FileHandler", "basicConfig(filename", "faulthandler.enable(",
                "traceback.print_exc(file=")
    treffer = []
    for pfad in _alle_python_dateien():
        code = _kompakt(_nur_code(pfad))
        for muster in verboten:
            if _kompakt(muster) in code:
                treffer.append(f"{os.path.relpath(pfad, CODE)}: {muster}")
    assert treffer == [], f"Logging-Politik verletzt: {treffer}"


def test_fehlercodes_sind_der_katalog_aus_b2():
    """G29: nur Codes aus der kanonischen Tabelle erreichen das Frontend."""
    from backend import api as api_module

    assert set(api_module.ERROR_MESSAGES) == {
        "not_found", "invalid", "locked", "passphrase", "rate_limited",
        "vault", "canceled", "busy", "memory", "internal",
    }
    for code, text in api_module.ERROR_MESSAGES.items():
        assert text and text[0].isupper() and text.endswith(".")


def test_ringpuffer_redigiert_pfade():
    from backend import api as api_module

    redigiert = api_module._redact(
        r"failed on C:\Users\jemand\Dokumente\tasks.db.enc weil x")
    assert "C:\\Users" not in redigiert
    assert "<path>" in redigiert
    assert len(api_module._redact("x" * 500)) <= 200


# ---------------------------------------------------------------------------
# B.9 Regel 1 (XSS) und Regel 2 (CSP)
# ---------------------------------------------------------------------------

def test_csp_steht_im_index():
    html = _quelle("frontend", "index.html")
    assert "Content-Security-Policy" in html
    for direktive in ("default-src 'self'", "script-src 'self'",
                      "object-src 'none'"):
        assert direktive in html


def test_fremde_werte_gehen_nur_escaped_ins_html():
    """B.9 Regel 1: jede Interpolation von Nutzertext traegt ``esc()``.

    Gesucht werden Template-Einsetzungen, die einen der bekannten Fremdwerte
    nennen (Aufgabentext, Listenname, IDs). Jede davon muss ``esc(``
    enthalten. Das ist die Trockenpruefung zum XSS-Traegheitstest: sie kostet
    nichts und faellt sofort auf, wenn jemand eine neue Zeile ohne ``esc``
    schreibt.
    """
    js = _quelle("frontend", "app.js")
    fremd = re.compile(r"\$\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")
    verdaechtig = []
    for treffer in fremd.finditer(js):
        ausdruck = treffer.group(1)
        if not re.search(r"\b(t|task|l|list|er)\.(text|name|id|msg|method)\b",
                         ausdruck):
            continue
        if "esc(" in ausdruck:
            continue
        verdaechtig.append(ausdruck.strip()[:80])
    assert verdaechtig == [], f"unescaped Interpolation: {verdaechtig}"


def test_esc_maskiert_alle_fuenf_zeichen():
    """B.9: ``esc()`` maskiert auch ``'`` (einfach gequotete Attribute)."""
    js = _quelle("frontend", "app.js")
    start = js.index("const esc =")
    block = js[start:start + 400]
    for ersatz in ("&amp;", "&lt;", "&gt;", "&quot;", "&#39;"):
        assert ersatz in block, f"{ersatz} fehlt in esc()"


# ---------------------------------------------------------------------------
# Regressionen: Dinge, die nicht zurueckkommen duerfen
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("muster, warum", [
    ("DEV_AES_KEY", "G9: statischer Entwicklungs-Schluessel"),
    ("SetWindowDisplayAffinity", "G26: verworfener Screenshot-Schutz"),
    ("private_mode=True", "G14: Privatmodus legte pro Start ein Temp-Profil an"),
    ("WTSRegisterSessionNotification", "N11.8.4: Win+L loest keine App-Sperre aus"),
])
def test_verworfenes_bleibt_verworfen(muster, warum):
    gesucht = _kompakt(muster)
    treffer = [os.path.relpath(p, CODE) for p in _alle_python_dateien()
               if gesucht in _kompakt(_nur_code(p))]
    assert treffer == [], f"{warum} (gefunden in {treffer})"
