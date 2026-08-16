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

"""Spike U3 / N11.8.3 (Phase 8, erster Handgriff): Zweitprofil vs. nativer Fallback.

**Kein toter Code, sondern der Beleg fuer Entscheid N11.18.** Dass der
Sperrbildschirm ein natives WinForms-Fenster ist (``lockwindow.py``) und kein
zweites WebView, ist keine Geschmacksfrage: dieses Skript zeigt nachpruefbar,
dass PyWebView zwei getrennte WebView2-Profile in einem Prozess gar nicht
anbietet. Wer die Entscheidung anzweifelt oder umdrehen will, laesst zuerst das
hier laufen, statt sich auf den Satz im Plan zu verlassen. Genau dafuer liegt es
im Repository.

Der Bauplan verlangt BEWEISE, keine Annahmen (N11.8.3, U3-Entscheid). Dieses
Skript beantwortet die empirisch pruefbaren Spike-Fragen:

  A) Kernfrage 1: Bietet PyWebView zwei Fenster mit getrennten storage_path im
     selben Prozess an? (API-Inspektion: storage_path ist Parameter von
     webview.start(), also global pro Prozess.)
  B) Traegt die Fallback-Architektur (natives Lock-Fenster ohne WebView)?
     Dazu muss gelten:
       B1: webview.start() kehrt nach window.destroy() zurueck,
       B2: die msedgewebview2.exe-Kindprozesse enden danach und der
           Profilordner laesst sich vollstaendig loeschen (G14-Wisch),
       B3: ein ZWEITER webview.create_window()+start()-Zyklus im selben
           Prozess funktioniert (Boot: Lock-Fenster -> Unlock -> Hauptfenster;
           spaeter Lock -> Fenster weg -> wieder Unlock -> neues Fenster).
  C) Laeuft ein reines WinForms-Fenster (pythonnet, Application.Run) im selben
     Prozess vor, zwischen und nach den WebView-Zyklen?
  D) G6-Nebenfrage: exponiert sqlcipher3 Connection.serialize/deserialize?
     (Nein -> N11.9-Fallback "SQLCipher-verschluesselte Arbeitsdatei" ist
     verbindlich.)

Aufruf:  .\venv\Scripts\python.exe tools\spike_u3_lockwindow.py
Das Skript ist ein Einmal-Werkzeug (Spike), kein Teil der App.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

RESULTS: list[str] = []


def report(name: str, ok: bool, detail: str) -> None:
    RESULTS.append(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    print(RESULTS[-1], flush=True)


def webview2_procs_with(profile: str) -> int:
    """Anzahl msedgewebview2.exe, deren Kommandozeile den Profilpfad traegt."""
    try:
        out = subprocess.run(
            [
                "powershell.exe", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_Process -Filter \"name='msedgewebview2.exe'\""
                " | Where-Object { $_.CommandLine -like '*" + profile.replace("\\", "\\\\") + "*' }"
                " | Measure-Object).Count",
            ],
            capture_output=True, timeout=30,
        )
        return int(out.stdout.decode("ascii", "ignore").strip() or "0")
    except Exception as exc:
        print(f"  (Prozesszaehlung fehlgeschlagen: {exc})", flush=True)
        return -1


def test_a_api() -> None:
    import inspect

    import webview

    cw = inspect.signature(webview.create_window).parameters
    st = inspect.signature(webview.start).parameters
    per_window = "storage_path" in cw or "private_mode" in cw
    global_only = "storage_path" in st and "private_mode" in st
    report(
        "A Zwei-Profile-API",
        (not per_window) and global_only,
        "storage_path/private_mode sind NUR Parameter von webview.start() "
        "(global pro Prozess), create_window() kennt sie nicht -> zwei Fenster "
        "mit getrennten Profilen bietet die API nicht an"
        if (not per_window) and global_only
        else "unerwartet: per-Window-Profil-Parameter vorhanden",
    )


def run_webview_cycle(profile: str, label: str, lifetime: float = 4.0) -> bool:
    import webview

    win = webview.create_window(f"Spike {label}", html="<h1>spike</h1>", width=400, height=300)

    def killer():
        time.sleep(lifetime)
        try:
            win.destroy()
        except Exception as exc:
            print(f"  destroy() warf: {exc}", flush=True)

    threading.Thread(target=killer, daemon=True).start()
    t0 = time.monotonic()
    webview.start(private_mode=False, storage_path=profile)
    took = time.monotonic() - t0
    returned = took < lifetime + 20
    report(f"B1 webview.start kehrt zurueck ({label})", returned, f"nach {took:.1f} s")
    return returned


def wait_procs_gone(profile: str, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        n = webview2_procs_with(profile)
        if n == 0:
            return True
        time.sleep(1.0)
    return False


def test_b_and_c() -> None:
    profile = os.path.join(tempfile.gettempdir(), "noatodo-spike-profile")
    shutil.rmtree(profile, ignore_errors=True)
    os.makedirs(profile, exist_ok=True)

    # C (vorher): reines WinForms-Fenster vor jedem WebView.
    ok_native_before = run_native_form_cycle("vor WebView")

    # Zyklus 1
    ok1 = run_webview_cycle(profile, "Zyklus 1")

    gone = wait_procs_gone(profile)
    report(
        "B2 WebView2-Prozesse beendet",
        gone,
        "alle msedgewebview2.exe mit Spike-Profil beendet"
        if gone else "Prozesse halten das Profil weiter offen",
    )
    wipe_ok = False
    try:
        shutil.rmtree(profile)
        wipe_ok = not os.path.exists(profile)
    except OSError as exc:
        print(f"  rmtree warf: {exc}", flush=True)
    report("B2 Profilordner wischbar", wipe_ok, "shutil.rmtree ohne Rest" if wipe_ok else "Ordner gesperrt")

    # C (zwischen): natives Fenster zwischen zwei WebView-Zyklen.
    ok_native_between = run_native_form_cycle("zwischen den Zyklen")

    # Zyklus 2 (frisches Profil, wie nach einem Unlock).
    os.makedirs(profile, exist_ok=True)
    ok2 = run_webview_cycle(profile, "Zyklus 2")
    report(
        "B3 zweiter WebView-Zyklus",
        ok1 and ok2,
        "create_window+start funktionieren im selben Prozess erneut"
        if (ok1 and ok2) else "zweiter Zyklus scheitert",
    )
    wait_procs_gone(profile)
    shutil.rmtree(profile, ignore_errors=True)

    ok_native_after = run_native_form_cycle("nach WebView")
    report(
        "C natives WinForms-Fenster",
        ok_native_before and ok_native_between and ok_native_after,
        "Application.Run-Zyklen laufen vor, zwischen und nach WebView",
    )


def run_native_form_cycle(label: str) -> bool:
    """Schlankes natives Fenster (Logo-los) mit Passwortfeld: der Fallback-Kern."""
    try:
        import clr

        clr.AddReference("System.Windows.Forms")
        clr.AddReference("System.Drawing")
        # Zentrale Spike-Erkenntnis: PyWebViews setup_app() ruft
        # SetCompatibleTextRenderingDefault auf, das VOR dem ersten
        # IWin32Window laufen muss. Es ist aber idempotent geschuetzt
        # (_already_set_up_app), darf also von uns VOR dem nativen
        # Lock-Fenster aufgerufen werden; der spaetere webview.start()
        # ueberspringt es dann. Ohne diesen Aufruf wirft der erste
        # webview.start() nach einem nativen Fenster InvalidOperationException.
        from webview.platforms.winforms import setup_app
        setup_app()
        from System import Action
        from System.Windows.Forms import Application, Form, TextBox
        from System.Drawing import Size

        form = Form()
        form.Text = "NoaToDo"
        form.Size = Size(360, 180)
        pw = TextBox()
        pw.UseSystemPasswordChar = True
        pw.Width = 240
        form.Controls.Add(pw)

        def closer():
            time.sleep(1.5)
            try:
                form.BeginInvoke(Action(form.Close))
            except Exception:
                pass

        threading.Thread(target=closer, daemon=True).start()
        Application.Run(form)
        try:
            form.Dispose()
        except Exception:
            pass
        print(f"  natives Fenster ok ({label})", flush=True)
        return True
    except Exception as exc:
        print(f"  natives Fenster scheiterte ({label}): {exc}", flush=True)
        return False


def test_d_serialize() -> None:
    import sqlcipher3

    conn = sqlcipher3.connect(":memory:")
    has = hasattr(conn, "serialize") and hasattr(conn, "deserialize")
    conn.close()
    report(
        "D sqlcipher3 serialize",
        True,
        ("vorhanden -> :memory:-Weg pruefbar" if has
         else "NICHT vorhanden -> G6-:memory:-Serialisierung nicht verfuegbar, "
              "N11.9-Fallback (SQLCipher-verschluesselte Arbeitsdatei) verbindlich"),
    )


def main() -> None:
    print("Spike U3 / N11.8.3\n" + "=" * 60, flush=True)
    test_a_api()
    test_d_serialize()
    test_b_and_c()
    print("\nZusammenfassung:\n" + "\n".join(RESULTS), flush=True)


if __name__ == "__main__":
    main()
