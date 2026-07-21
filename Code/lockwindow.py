"""Natives Lock-Fenster (Phase 8, Spike-Ergebnis N11.18).

Der Zweitprofil-Spike (U3/N11.8.3) hat bewiesen: PyWebView bietet keine zwei
WebView2-Profile im selben Prozess an, also gilt der **native Fallback**. Das
Lock-Fenster ist ein schlankes WinForms-Fenster **ohne WebView** (keine Engine
haelt ``PROFILE_DIR`` offen, es gibt kein ``LOCK_PROFILE_DIR``, Aufgabendaten
erreichen es baulich nicht). Es erscheint, sobald ein Tresor existiert und die
App gesperrt/nicht-entsperrt ist, und ruft ``api.unlock``/``api.quit_app``/
``api.reset_vault`` **direkt** (keine Bridge, Spike-Frage 2).

Erfuellt die N4-/N6-Pflichten so weit im nativen Rahmen moeglich (die
Web-Animationen entfallen bewusst): Passwortfeld mit Show/Hide, neutrale
Fehlermeldung bei falscher Passphrase, Caps-Lock-Warnung, Unlocking-Zustand
(Argon2 im Hintergrund-Thread), Rate-Limit-Countdown, Off-Knopf, Reset-Weg
(vergessene Passphrase). DevTools/Remote-Debugging gibt es hier gar nicht
(kein WebView, Spike-Frage 8). Jede druckbare Taste landet im Passwortfeld
(B.8-Regel, Spike-Frage 9): das Feld hat den Fokus, andere Controls sind
Buttons/Links ohne Texteingabe.
"""
from __future__ import annotations

import threading
from typing import Any

# Farben (an die App-Tokens angelehnt, dark).
_BG = (0x1F, 0x1B, 0x14)
_SURFACE = (0x2A, 0x24, 0x1A)
_TEXT = (0xF2, 0xEA, 0xD9)
_FAINT = (0xA8, 0x9C, 0x86)
_ACCENT = (0xD9, 0x77, 0x57)
_DANGER = (0xD9, 0x5C, 0x4A)


def run_lock_window(api: Any, boot_state: str, boot_reason: str | None,
                    icon_path: str | None, _test_after_shown=None) -> str:
    """Baut das native Lock-/Fehler-Fenster und laeuft, bis es sich schliesst.

    Rueckgabe: ``"unlocked"`` (Tresor offen, weiter zur WebView-App),
    ``"quit"`` (Off-Knopf / Fenster-X: App beenden) oder ``"onboarding"``
    (Reset: Tresor geloescht, zurueck ins Onboarding).

    ``_test_after_shown`` ist eine reine Test-Naht (production ruft ohne sie):
    ein Callback, der nach dem Anzeigen einmal mit den Steuerelementen
    aufgerufen wird, damit ein automatisierter Test den Unlock-Klick
    deterministisch ausloesen kann, ohne auf Fenster-Fokus/Tastatur-Injektion
    in einer nicht-interaktiven Session angewiesen zu sein.
    """
    import clr

    clr.AddReference("System.Windows.Forms")
    clr.AddReference("System.Drawing")
    from System import Action, EventHandler
    from System.Drawing import Color, ContentAlignment, Font, FontStyle, Point, Size
    from System.Windows.Forms import (
        AnchorStyles, Application, BorderStyle, Button, CheckBox, FlatStyle,
        Form, FormBorderStyle, FormStartPosition, Keys, Label, LinkLabel,
        TextBox, Timer,
    )

    def col(rgb):
        return Color.FromArgb(rgb[0], rgb[1], rgb[2])

    result = {"value": "quit"}   # Default: Fenster-X = quit (N11.11.1)
    # Wird True, sobald ein bewusster Ausgang (unlock/quit/reset) das Fenster
    # schliesst; dann darf der FormClosing-Handler NICHT noch einmal quit_app
    # ausloesen.
    state = {"closing_intent": None, "busy": False, "reset_stage": 0}

    form = Form()
    form.Text = "NoaToDo"
    form.StartPosition = FormStartPosition.CenterScreen
    form.FormBorderStyle = FormBorderStyle.FixedDialog
    form.MaximizeBox = False
    form.MinimizeBox = True
    form.ClientSize = Size(440, 380)
    form.BackColor = col(_BG)
    form.ForeColor = col(_TEXT)
    if icon_path:
        try:
            from System.Drawing import Icon
            form.Icon = Icon(icon_path)
        except Exception:
            pass

    # --- Off-Knopf oben rechts (N10.2) ------------------------------------
    off = Button()
    off.Text = "⏻"
    off.Font = Font("Segoe UI", 12.0)
    off.FlatStyle = FlatStyle.Flat
    off.FlatAppearance.BorderSize = 0
    off.BackColor = col(_BG)
    off.ForeColor = col(_FAINT)
    off.Size = Size(34, 30)
    off.Location = Point(form.ClientSize.Width - 44, 10)
    off.Anchor = AnchorStyles.Top | AnchorStyles.Right
    off.TabStop = False

    # --- Titel ------------------------------------------------------------
    title = Label()
    title.AutoSize = False
    title.TextAlign = ContentAlignment.MiddleCenter
    title.Font = Font("Segoe UI Semibold", 15.0, FontStyle.Bold)
    title.ForeColor = col(_TEXT)
    title.Size = Size(400, 30)
    title.Location = Point(20, 64)

    subtitle = Label()
    subtitle.AutoSize = False
    subtitle.TextAlign = title.TextAlign
    subtitle.Font = Font("Segoe UI", 9.5)
    subtitle.ForeColor = col(_FAINT)
    subtitle.Size = Size(400, 40)
    subtitle.Location = Point(20, 96)

    vault_error = boot_state == "vault_error"
    if vault_error:
        title.Text = "Vault cannot be opened"
        reasons = {
            "config_damaged": "The configuration is unreadable and the vault path is unknown.",
            "vault_unreachable": "The vault file is not reachable (drive removed or path gone).",
            "vault_damaged": "The vault file looks damaged. Try a backup, or reset.",
        }
        subtitle.Text = reasons.get(boot_reason or "", "The vault could not be opened.")
    else:
        title.Text = "NoaToDo is locked"
        subtitle.Text = "Enter your passphrase to unlock."

    # --- Passwortfeld -----------------------------------------------------
    pw = TextBox()
    pw.UseSystemPasswordChar = True
    pw.Font = Font("Segoe UI", 12.0)
    pw.BackColor = col(_SURFACE)
    pw.ForeColor = col(_TEXT)
    pw.BorderStyle = BorderStyle.FixedSingle
    pw.Size = Size(300, 30)
    pw.Location = Point(70, 150)

    show = CheckBox()
    show.Text = "Show"
    show.Font = Font("Segoe UI", 8.5)
    show.ForeColor = col(_FAINT)
    show.Size = Size(60, 22)
    show.Location = Point(70, 186)
    show.FlatStyle = off.FlatStyle
    show.TabStop = False

    caps = Label()
    caps.AutoSize = False
    caps.TextAlign = title.TextAlign
    caps.Font = Font("Segoe UI", 8.5)
    caps.ForeColor = col(_DANGER)
    caps.Size = Size(200, 20)
    caps.Location = Point(170, 187)
    caps.Text = ""

    # --- Unlock-Knopf -----------------------------------------------------
    unlock = Button()
    unlock.Text = "Unlock"
    unlock.Font = Font("Segoe UI Semibold", 10.5, FontStyle.Bold)
    unlock.FlatStyle = off.FlatStyle
    unlock.FlatAppearance.BorderSize = 0
    unlock.BackColor = col(_ACCENT)
    unlock.ForeColor = col(_BG)
    unlock.Size = Size(300, 36)
    unlock.Location = Point(70, 220)

    # --- Statuszeile (Fehler / Countdown / Unlocking) ---------------------
    status = Label()
    status.AutoSize = False
    status.TextAlign = title.TextAlign
    status.Font = Font("Segoe UI", 9.5)
    status.ForeColor = col(_DANGER)
    status.Size = Size(400, 24)
    status.Location = Point(20, 266)
    status.Text = ""

    # --- Reset-Bereich (vergessene Passphrase, N11.3) ---------------------
    forgot = LinkLabel()
    forgot.Text = "Forgot passphrase?"
    forgot.Font = Font("Segoe UI", 9.0)
    forgot.LinkColor = col(_FAINT)
    forgot.ActiveLinkColor = col(_ACCENT)
    forgot.AutoSize = True
    forgot.Location = Point(160, 300)

    reset_box = TextBox()
    reset_box.Font = Font("Segoe UI", 11.0)
    reset_box.BackColor = col(_SURFACE)
    reset_box.ForeColor = col(_TEXT)
    reset_box.Size = Size(180, 28)
    reset_box.Location = Point(70, 300)
    reset_box.Visible = False

    reset_btn = Button()
    reset_btn.Text = "Reset"
    reset_btn.Font = Font("Segoe UI", 9.0)
    reset_btn.FlatStyle = off.FlatStyle
    reset_btn.FlatAppearance.BorderSize = 1
    reset_btn.BackColor = col(_BG)
    reset_btn.ForeColor = col(_DANGER)
    reset_btn.Size = Size(90, 28)
    reset_btn.Location = Point(260, 300)
    reset_btn.Visible = False

    # ------------------------------------------------------------------
    # Verhalten
    # ------------------------------------------------------------------
    def ui(fn):
        try:
            form.BeginInvoke(Action(fn))
        except Exception:
            pass

    def set_status(text, danger=True):
        status.ForeColor = col(_DANGER if danger else _FAINT)
        status.Text = text

    def on_show_changed(sender, args):
        pw.UseSystemPasswordChar = not show.Checked
        pw.Focus()
    show.CheckedChanged += EventHandler(on_show_changed)

    def update_caps():
        try:
            caps.Text = "Caps Lock is on" if (Application.OpenForms and
                                              form.IsHandleCreated and
                                              _caps_on()) else ""
        except Exception:
            caps.Text = ""

    def _caps_on():
        import ctypes
        return bool(ctypes.windll.user32.GetKeyState(0x14) & 0x0001)

    countdown = {"remaining": 0}

    def tick_countdown():
        # Wird per Timer aufgerufen: zeigt "try again in Ns" und schaltet den
        # Unlock-Knopf frei, wenn die Sperrzeit abgelaufen ist.
        if countdown["remaining"] > 0:
            countdown["remaining"] -= 1
            set_status(f"Too many attempts. Try again in {countdown['remaining']}s.")
            if countdown["remaining"] <= 0:
                unlock.Enabled = True
                set_status("", danger=False)

    timer = Timer()
    timer.Interval = 1000

    def on_tick(sender, args):
        update_caps()
        tick_countdown()
    timer.Tick += EventHandler(on_tick)

    def do_unlock():
        if state["busy"]:
            return
        passphrase = pw.Text or ""
        state["busy"] = True
        unlock.Enabled = False
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
                unlock.Enabled = True
                pw.Text = ""
                pw.Focus()
                code = res.get("error") if isinstance(res, dict) else "internal"
                if code == "passphrase":
                    set_status("Wrong passphrase.")
                    retry = int(res.get("retry_in") or 0)
                    if retry > 1:
                        countdown["remaining"] = retry
                        unlock.Enabled = False
                elif code == "rate_limited":
                    countdown["remaining"] = int(res.get("retry_in") or 0)
                    unlock.Enabled = False
                    set_status(f"Too many attempts. Try again in {countdown['remaining']}s.")
                elif code == "memory":
                    set_status("Not enough memory. Close other apps and try again.")
                elif code == "vault":
                    set_status("Vault cannot be opened.")
                else:
                    set_status("Could not unlock.")
            ui(apply)

        threading.Thread(target=worker, daemon=True).start()

    def on_unlock_click(sender, args):
        do_unlock()
    unlock.Click += EventHandler(on_unlock_click)

    def on_pw_key(sender, args):
        if args.KeyCode == Keys.Enter:
            args.SuppressKeyPress = True
            do_unlock()
    pw.KeyDown += EventHandler(on_pw_key)

    def on_off_click(sender, args):
        state["closing_intent"] = "quit"
        result["value"] = "quit"
        try:
            api.quit_app()   # teardown('quit'); request_teardown schliesst das Fenster
        except Exception:
            form.Close()
    off.Click += EventHandler(on_off_click)

    def on_forgot(sender, args):
        # Reset ist wie der Killswitch abgesichert: erst sichtbar machen, dann
        # muss "RESET" getippt werden, dann loescht der Knopf wirklich.
        forgot.Visible = False
        reset_box.Visible = True
        reset_btn.Visible = True
        reset_box.Focus()
        set_status("Type RESET to erase the vault and start over.", danger=True)
    forgot.LinkClicked += EventHandler(on_forgot)

    def on_reset_click(sender, args):
        if (reset_box.Text or "").strip() != "RESET":
            set_status("Type RESET (all caps) to confirm.")
            return
        state["closing_intent"] = "onboarding"
        result["value"] = "onboarding"
        try:
            api.reset_vault()   # teardown('reset'); request_teardown schliesst
        except Exception:
            form.Close()
    reset_btn.Click += EventHandler(on_reset_click)

    def on_form_closing(sender, args):
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

    def on_shown(sender, args):
        pw.Focus()
        timer.Start()
        if _test_after_shown is not None:
            probe = Timer()
            probe.Interval = 800

            def fire(_s, _a):
                probe.Stop()
                try:
                    _test_after_shown({"pw": pw, "unlock": unlock,
                                       "off": off, "form": form})
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
            unlock.Enabled = False
            set_status(f"Too many attempts. Try again in {rem}s.")
    form.Shown += EventHandler(on_shown)

    # request_teardown: die Api ruft das (nach teardown-Schritten 1-8), um das
    # aktuelle Fenster abzubauen. Im Lock-Fenster heisst das: die Form
    # schliessen (der Ausgang steht schon in state/result). Ueber den UI-Thread.
    api._request_teardown = lambda: ui(form.Close)

    for ctl in (off, title, subtitle, pw, show, caps, unlock, status,
                forgot, reset_box, reset_btn):
        form.Controls.Add(ctl)

    if vault_error:
        # Bei Tresor-Fehler den Reset-Weg sofort anbieten (N6): der Nutzer kann
        # ohnehin nicht entsperren. Unlock bleibt fuer den Fall, dass die Datei
        # doch da ist (z.B. Stick wieder eingesteckt).
        forgot.Text = "Reset vault"

    Application.Run(form)
    try:
        form.Dispose()
    except Exception:
        pass
    return result["value"]
