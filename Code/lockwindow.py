"""Natives Sperrfenster im App-Design (Phase 8, Spike-Ergebnis N11.18).

Der Zweitprofil-Spike (U3/N11.8.3) hat bewiesen: PyWebView bietet keine zwei
WebView2-Profile im selben Prozess an, also gilt der **native Fallback**. Das
Sperrfenster ist ein WinForms-Fenster **ohne WebView** (keine Engine haelt
``PROFILE_DIR`` offen, es gibt kein ``LOCK_PROFILE_DIR``, Aufgabendaten
erreichen es baulich nicht). Es erscheint, sobald ein Tresor existiert und die
App gesperrt/nicht-entsperrt ist, und ruft ``api.unlock``/``api.quit_app``/
``api.reset_vault`` **direkt** (keine Bridge, Spike-Frage 2).

**Optik (2026-07-25):** das Fenster ist kein kleiner Windows-Dialog mehr,
sondern uebernimmt den Sperrbildschirm aus dem Designkonzept: es startet
**maximiert** wie das Hauptfenster, traegt dieselbe dunkle Titelleiste (DWM,
Caption in ``--surface``), denselben Hintergrund (Grundton plus 28px-Raster),
den grossen Akzent-Ring mit dem Schloss-Zeichen aus ``Icons.Lock`` und
Pillenformen fuer Eingabe und Knoepfe. Alle Bausteine kommen aus
``wintheme.py``, damit natives Fenster und WebView-App dieselben Tokens
benutzen. Beim Sperren aus der laufenden App bleibt der Bildschirm dadurch
optisch stehen: gleiche Groesse, gleiche Farben, gleiches Bild.

Erfuellt die N4-/N6-Pflichten so weit im nativen Rahmen moeglich (die
Web-Animationen entfallen bewusst): Passwortfeld mit Show/Hide, neutrale
Fehlermeldung bei falscher Passphrase, Caps-Lock-Warnung, Unlocking-Zustand
(Argon2 im Hintergrund-Thread), Rate-Limit-Countdown, Off-Knopf, Reset-Weg
(vergessene Passphrase). DevTools/Remote-Debugging gibt es hier gar nicht
(kein WebView, Spike-Frage 8). Jede druckbare Taste landet im Passwortfeld
(B.8-Regel, Spike-Frage 9): das Feld hat den Fokus, andere Controls sind
Buttons/Links ohne Texteingabe.

Das Fenster ist immer dunkel: waehrend der Sperre ist der Tresor zu, die
Theme-Einstellung liegt **in** ihm und ist nicht lesbar (config.json haelt nur
Nicht-Geheimes, B.11). Dark ist die Vorgabe der App.
"""
from __future__ import annotations

import threading
from typing import Any

import wintheme as T


def run_lock_window(api: Any, boot_state: str, boot_reason: str | None,
                    icon_path: str | None, _test_after_shown=None,
                    on_ready=None) -> str:
    """Baut das native Sperr-/Fehlerfenster und laeuft, bis es sich schliesst.

    Rueckgabe: ``"unlocked"`` (Tresor offen, weiter zur WebView-App),
    ``"quit"`` (Off-Knopf / Fenster-X: App beenden) oder ``"onboarding"``
    (Reset: Tresor geloescht, zurueck ins Onboarding).

    ``on_ready`` bekommt (sobald das Fenster steht) dessen HWND; main.py haengt
    daran die Taskleisten-Identitaet (AppID + App-Icon), damit auch der
    Taskleisten-Eintrag des Sperrfensters das NoaToDo-Logo traegt und nicht das
    generische Python-Symbol.

    ``_test_after_shown`` ist eine reine Test-Naht (production ruft ohne sie):
    ein Callback, der nach dem Anzeigen einmal mit den Steuerelementen
    aufgerufen wird, damit ein automatisierter Test den Unlock-Klick
    deterministisch ausloesen kann, ohne auf Fenster-Fokus/Tastatur-Injektion
    in einer nicht-interaktiven Session angewiesen zu sein.
    """
    from System import Action, EventHandler
    from System.Drawing import Point, Size
    from System.Windows.Forms import (
        Application, FormBorderStyle, FormWindowState, Form, KeyEventHandler,
        KeyPressEventHandler, Keys, PaintEventHandler, Timer,
    )

    result = {"value": "quit"}   # Default: Fenster-X = quit (N11.11.1)
    # Wird gesetzt, sobald ein bewusster Ausgang (unlock/quit/reset) das Fenster
    # schliesst; dann darf der FormClosing-Handler NICHT noch einmal quit_app
    # ausloesen.
    state = {"closing_intent": None, "busy": False, "reset_open": False}
    vault_error = boot_state == "vault_error"

    # ------------------------------------------------------------------
    # Fenster: maximiert wie das Hauptfenster, App-Farben, dunkle Titelleiste
    # ------------------------------------------------------------------
    form = Form()
    form.Text = "NoaToDo"          # B.4/A7: Titel enthaelt nie Nutzerinhalt
    form.FormBorderStyle = FormBorderStyle.Sizable
    form.MinimumSize = Size(560, 620)
    form.WindowState = FormWindowState.Maximized
    T.style_form(form, icon_path)

    scale = {"v": 1.0}

    def s(v: float) -> int:
        return int(round(v * scale["v"]))

    # Masse des gezeichneten Rings (setzt layout(), malt on_form_paint).
    geom = {"ring_x": 0, "ring_y": 0, "ring_d": 184}

    # ------------------------------------------------------------------
    # Steuerelemente (alle aus wintheme, also in App-Optik)
    # ------------------------------------------------------------------
    off = T.PillButton("", "icon", (42, 42), glyph="power")

    title = T.AppLabel("", 16.5, True, T.TEXT, display=True, size=(600, 38))
    subtitle = T.AppLabel("", 10.5, False, T.TEXT_DIM, size=(700, 26))

    if vault_error:
        title.text = "Vault cannot be opened"
        reasons = {
            "config_damaged": "The configuration is unreadable and the vault path is unknown.",
            "vault_unreachable": "The vault file is not reachable (drive removed or path gone).",
            "vault_damaged": "The vault file looks damaged. Try a backup, or reset.",
        }
        subtitle.text = reasons.get(boot_reason or "", "The vault could not be opened.")
    else:
        title.text = "NoaToDo is locked"
        subtitle.text = "Enter your passphrase to unlock."

    pw_pill = T.PillInput((380, 52), password=True, cue="Password", font_size=12.0)
    pw = pw_pill.box

    # Show/Hide sitzt IN der Pille (Fuellfarbe der Pille als Hintergrund).
    show = T.PillButton("Show", "ghost", (62, 32), font_size=8.5, bold=False,
                        backdrop=T.SURFACE)
    pw_pill.control.Controls.Add(show.control)

    caps = T.AppLabel("", 9.0, False, T.DANGER, size=(500, 20))
    unlock = T.PillButton("Unlock", "primary", (380, 50), font_size=11.0)
    status = T.AppLabel("", 10.0, False, T.DANGER, size=(700, 26))

    forgot = T.TextLink("Reset vault" if vault_error else "Forgot passphrase?",
                        9.5, width=300, height=26)
    reset_pill = T.PillInput((240, 44), cue="Type RESET", font_size=10.5)
    reset_btn = T.PillButton("Erase vault", "danger", (150, 44), font_size=9.5)
    reset_pill.control.Visible = False
    reset_btn.control.Visible = False

    # ------------------------------------------------------------------
    # Layout: eine mittige Spalte wie .lock-card, bei jeder Groesse neu gesetzt
    # ------------------------------------------------------------------
    def layout():
        try:
            scale["v"] = T.dpi_scale(int(form.Handle.ToInt64()))
        except Exception:
            scale["v"] = 1.0
        w = form.ClientSize.Width
        h = form.ClientSize.Height
        cx = w // 2

        ring_d = s(184)
        gap = s(26)
        title_h, sub_h = s(38), s(26)
        input_h, caps_h, btn_h, status_h = s(52), s(20), s(50), s(26)
        block = (ring_d + gap + title_h + s(4) + sub_h + gap + input_h
                 + s(6) + caps_h + s(10) + btn_h + s(8) + status_h)
        y = max(s(24), (h - block) // 2 - s(20))

        geom["ring_d"] = ring_d
        geom["ring_x"] = cx - ring_d // 2
        geom["ring_y"] = y
        y += ring_d + gap

        title.control.Size = Size(min(w - s(40), s(700)), title_h)
        title.control.Location = Point(cx - title.control.Width // 2, y)
        y += title_h + s(4)

        subtitle.control.Size = Size(min(w - s(40), s(760)), sub_h)
        subtitle.control.Location = Point(cx - subtitle.control.Width // 2, y)
        y += sub_h + gap

        pill_w = min(w - s(60), s(380))
        pw_pill.control.Size = Size(pill_w, input_h)
        pw_pill.control.Location = Point(cx - pill_w // 2, y)
        show.control.Size = Size(s(62), s(32))
        show.control.Location = Point(pill_w - s(62) - s(10),
                                      (input_h - s(32)) // 2)
        pw_pill.layout_box(right_reserve=s(62) + s(18), scale=scale["v"])
        y += input_h + s(6)

        caps.control.Size = Size(min(w - s(40), s(500)), caps_h)
        caps.control.Location = Point(cx - caps.control.Width // 2, y)
        y += caps_h + s(10)

        unlock.control.Size = Size(pill_w, btn_h)
        unlock.control.Location = Point(cx - pill_w // 2, y)
        y += btn_h + s(8)

        status.control.Size = Size(min(w - s(40), s(760)), status_h)
        status.control.Location = Point(cx - status.control.Width // 2, y)
        y += status_h

        # Fusszeile: Reset-Weg. Mit Abstand unter dem Block, aber nie unter den
        # Fensterrand (kleine Fenster: direkt anschliessen).
        foot_h = s(44)
        foot_y = min(h - foot_h - s(30), y + s(52))
        foot_y = max(foot_y, y + s(16))

        forgot.control.Size = Size(s(300), s(26))
        forgot.control.Location = Point(cx - s(150), foot_y + (foot_h - s(26)) // 2)

        row_w = s(240) + s(12) + s(150)
        reset_pill.control.Size = Size(s(240), foot_h)
        reset_pill.control.Location = Point(cx - row_w // 2, foot_y)
        reset_pill.layout_box(scale=scale["v"])
        reset_btn.control.Size = Size(s(150), foot_h)
        reset_btn.control.Location = Point(cx - row_w // 2 + s(240) + s(12), foot_y)

        off.control.Size = Size(s(42), s(42))
        off.control.Location = Point(w - s(42) - s(22), s(18))

        form.Invalidate()

    # ------------------------------------------------------------------
    # Hintergrund + Ring zeichnen (style.css .lock-screen / .lock-ring)
    # ------------------------------------------------------------------
    def on_form_paint(_s, e):
        g = e.Graphics
        w, h = form.ClientSize.Width, form.ClientSize.Height
        T.paint_backdrop(g, 0, 0, w, h, T.TITLE_STRIP)
        d = geom["ring_d"]
        x, y = geom["ring_x"], geom["ring_y"]
        cx, cy = x + d / 2.0, y + d / 2.0
        # Schein wie box-shadow: 0 18px 48px accent
        T.draw_glow(g, cx, cy + d * 0.10, d * 0.92, T.ACCENT, 46)
        T.fill_pill(g, x, y, d, d, d / 2.0, T.ACCENT_WASH, T.ACCENT_LINE,
                    max(1.0, scale["v"]))
        T.draw_lock_glyph(g, cx, cy, d * (84.0 / 184.0), T.ACCENT)

    form.Paint += PaintEventHandler(on_form_paint)
    form.Resize += EventHandler(lambda _s, _a: layout())

    # ------------------------------------------------------------------
    # Verhalten
    # ------------------------------------------------------------------
    def ui(fn):
        try:
            form.BeginInvoke(Action(fn))
        except Exception:
            pass

    def set_status(text, danger=True):
        status.set(text, T.DANGER if danger else T.TEXT_DIM)

    def on_show_click(_s, _a):
        visible = pw.UseSystemPasswordChar
        pw.UseSystemPasswordChar = not visible
        show.set_text("Hide" if visible else "Show")
        pw.Focus()
    show.control.Click += EventHandler(on_show_click)

    def _caps_on():
        import ctypes
        return bool(ctypes.windll.user32.GetKeyState(0x14) & 0x0001)

    def update_caps():
        try:
            caps.set("Caps Lock is on" if _caps_on() else "")
        except Exception:
            caps.set("")

    countdown = {"remaining": 0}

    def tick_countdown():
        # Wird per Timer aufgerufen: zeigt "try again in Ns" und schaltet den
        # Unlock-Knopf frei, wenn die Sperrzeit abgelaufen ist.
        if countdown["remaining"] > 0:
            countdown["remaining"] -= 1
            if countdown["remaining"] <= 0:
                unlock.set_enabled(True)
                set_status("", danger=False)
            else:
                set_status(f"Too many attempts. Try again in {countdown['remaining']}s.")

    timer = Timer()
    timer.Interval = 1000

    def on_tick(_s, _a):
        update_caps()
        tick_countdown()
    timer.Tick += EventHandler(on_tick)

    def do_unlock():
        if state["busy"] or not unlock.control.Enabled:
            return
        passphrase = pw.Text or ""
        state["busy"] = True
        unlock.set_enabled(False)
        set_status("Unlocking…", danger=False)

        def worker():
            res = api.unlock(passphrase)

            def apply():
                state["busy"] = False
                if isinstance(res, dict) and res.get("ok"):
                    state["closing_intent"] = "unlocked"
                    result["value"] = "unlocked"
                    form.Close()
                    return
                unlock.set_enabled(True)
                pw.Text = ""
                pw.Focus()
                code = res.get("error") if isinstance(res, dict) else "internal"
                if code == "passphrase":
                    set_status("Wrong passphrase.")
                    retry = int(res.get("retry_in") or 0)
                    if retry > 1:
                        countdown["remaining"] = retry
                        unlock.set_enabled(False)
                elif code == "rate_limited":
                    countdown["remaining"] = int(res.get("retry_in") or 0)
                    unlock.set_enabled(False)
                    set_status(f"Too many attempts. Try again in {countdown['remaining']}s.")
                elif code == "memory":
                    set_status("Not enough memory. Close other apps and try again.")
                elif code == "vault":
                    set_status("Vault cannot be opened.")
                else:
                    set_status("Could not unlock.")
            ui(apply)

        threading.Thread(target=worker, daemon=True).start()

    unlock.control.Click += EventHandler(lambda _s, _a: do_unlock())

    def on_pw_key(_s, args):
        if args.KeyCode == Keys.Enter:
            args.SuppressKeyPress = True
            do_unlock()
    pw.KeyDown += KeyEventHandler(on_pw_key)

    def on_off_click(_s, _a):
        state["closing_intent"] = "quit"
        result["value"] = "quit"
        try:
            api.quit_app()   # teardown('quit'); request_teardown schliesst das Fenster
        except Exception:
            form.Close()
    off.control.Click += EventHandler(on_off_click)

    def open_reset():
        # Reset ist wie der Killswitch abgesichert: erst sichtbar machen, dann
        # muss "RESET" getippt werden, dann loescht der Knopf wirklich.
        state["reset_open"] = True
        forgot.control.Visible = False
        reset_pill.control.Visible = True
        reset_btn.control.Visible = True
        reset_pill.box.Focus()
        set_status("Type RESET to erase the vault and start over.", danger=True)
    forgot.control.Click += EventHandler(lambda _s, _a: open_reset())

    def close_reset():
        state["reset_open"] = False
        reset_pill.box.Text = ""
        reset_pill.control.Visible = False
        reset_btn.control.Visible = False
        forgot.control.Visible = True
        set_status("", danger=False)
        pw.Focus()

    def do_reset():
        if (reset_pill.box.Text or "").strip() != "RESET":
            set_status("Type RESET (all caps) to confirm.")
            return
        state["closing_intent"] = "onboarding"
        result["value"] = "onboarding"
        try:
            api.reset_vault()   # teardown('reset'); request_teardown schliesst
        except Exception:
            form.Close()
    reset_btn.control.Click += EventHandler(lambda _s, _a: do_reset())

    def on_reset_key(_s, args):
        if args.KeyCode == Keys.Enter:
            args.SuppressKeyPress = True
            do_reset()
    reset_pill.box.KeyDown += KeyEventHandler(on_reset_key)

    def on_form_key(_s, args):
        # Esc schliesst nur den Reset-Weg; es gibt bewusst keinen Weg an der
        # Sperre vorbei.
        if args.KeyCode == Keys.Escape and state["reset_open"]:
            args.SuppressKeyPress = True
            close_reset()
    form.KeyPreview = True
    form.KeyDown += KeyEventHandler(on_form_key)

    def on_form_keypress(_s, args):
        # B.8-Regel (Spike-Frage 9): jede druckbare Taste landet im Passwortfeld,
        # auch wenn der Fokus gerade auf einem Knopf steht (Klick auf "Unlock").
        ch = args.KeyChar
        if ord(ch) < 32 or pw.Focused or reset_pill.box.Focused:
            return
        pw.Focus()
        pw.AppendText(ch)
        args.Handled = True
    form.KeyPress += KeyPressEventHandler(on_form_keypress)

    def on_form_closing(_s, _a):
        # Fenster-X ohne bewussten Ausgang = quit (N11.11.1, Spike-Frage 5):
        # denselben sicheren Beenden-Pfad nehmen.
        if state["closing_intent"] is None:
            state["closing_intent"] = "quit"
            result["value"] = "quit"
            try:
                api.quit_app()
            except Exception:
                pass
    form.FormClosing += EventHandler(on_form_closing)

    def on_shown(_s, _a):
        try:
            hwnd = int(form.Handle.ToInt64())
        except Exception:
            hwnd = 0
        T.apply_titlebar_theme(hwnd, True)
        if on_ready is not None and hwnd:
            try:
                on_ready(hwnd)
            except Exception:
                pass
        layout()
        pw.Focus()
        timer.Start()
        if _test_after_shown is not None:
            probe = Timer()
            probe.Interval = 800

            def fire(_s2, _a2):
                probe.Stop()
                try:
                    _test_after_shown({"pw": pw, "unlock": unlock.control,
                                       "off": off.control, "form": form})
                except Exception as exc:
                    print("test_after_shown error:", exc, flush=True)
            probe.Tick += EventHandler(fire)
            probe.Start()
        # Falls beim Start schon eine Rate-Limit-Sperre laeuft, sofort zeigen.
        try:
            rem = api._rate.remaining()
        except Exception:
            rem = 0
        if rem > 0:
            countdown["remaining"] = rem
            unlock.set_enabled(False)
            set_status(f"Too many attempts. Try again in {rem}s.")
    form.Shown += EventHandler(on_shown)

    # request_teardown: die Api ruft das (nach teardown-Schritten 1-8), um das
    # aktuelle Fenster abzubauen. Im Sperrfenster heisst das: die Form
    # schliessen (der Ausgang steht schon in state/result). Ueber den UI-Thread.
    api._request_teardown = lambda: ui(form.Close)

    for ctl in (off.control, title.control, subtitle.control, pw_pill.control,
                caps.control, unlock.control, status.control, forgot.control,
                reset_pill.control, reset_btn.control):
        form.Controls.Add(ctl)

    Application.Run(form)
    try:
        form.Dispose()
    except Exception:
        pass
    return result["value"]
