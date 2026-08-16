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
Web-Animationen entfallen bewusst): Passwortfeld (ohne Klartext-Anzeige,
2026-08-10: aufdecken laesst sich die Passphrase nirgends mehr), neutrale
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

import math
import threading
import time
from typing import Any

import wintheme as T

# Off-Knopf (N11.28): Dauer des Ringlaufs und Haltezeit des scharfen Zustands.
# Modulweit, damit ein Test sie kurz drehen kann, ohne die Haltezeit abzuwarten.
#: Wie lange der Ring um das Power-Zeichen braucht (Millisekunden).
OFF_FILL_MS = 1100.0
#: Wie lange der geschlossene Ring auf den Klick wartet, bevor der Knopf wieder
#: in den Ruhezustand faellt (Millisekunden).
OFF_HOLD_MS = 10000.0


# ---------------------------------------------------------------------------
# Ring des Sperrschirms: EINE Quelle fuer Masse und Bild
# ---------------------------------------------------------------------------
# Das Sperrfenster und die Uebergabe-Blende (``Curtain``, N11.25) zeichnen
# denselben Ring an derselben Stelle. Beide holen sich Lage und Bild hier,
# damit beim Fensterwechsel nichts springt.
def _ring_geometry(w: int, h: int, scale: float, extra: int = 0) -> dict:
    """Lage des Sperr-Rings in einem Fenster der Groesse ``w`` x ``h``.

    ``next_y`` ist die Oberkante der ersten Zeile darunter (das Sperrfenster
    setzt sein Layout dort fort). Die Blockhoehe zaehlt bewusst die gesamte
    Sperr-Saeule mit (Eingabe, Caps-Warnung, Statuszeile), damit der Ring in
    der Blende genau dort steht wie im fertigen Fenster, obwohl dort noch
    keine Steuerelemente sichtbar sind.

    ``extra`` sind zusaetzliche Zeilen, die nur ein bestimmter Zustand hat:
    der Fehlerfall (Tresor nicht zu oeffnen) zeigt Titel und Untertitel, der
    normale Sperrschirm zeigt seit 2026-08-08 gar keinen Text mehr. Die Blende
    (``Curtain``) ruft ohne ``extra``, also mit dem Normalfall.
    """
    def s(v: float) -> int:
        return int(round(v * scale))

    ring_d = s(184)
    # Abstand zwischen Ring und Titelzeile, absichtlich viel groesser als der
    # uebrige Zeilenabstand (N11.24): der Schein um den Ring wird von jedem
    # Steuerelement darunter **hart abgeschnitten**, weil die Labels ihren
    # eigenen Hintergrund malen und vom Schein nichts wissen. Er reicht rund
    # 0.42 Durchmesser ueber den Ringrand hinaus (plus die Verschiebung nach
    # unten); erst ab diesem Abstand ist er ausgelaufen, bevor das erste
    # Steuerelement anfaengt, und es bleibt keine sichtbare Kante.
    ring_gap = s(96)
    block = (ring_d + ring_gap + extra + s(40)
             + s(6) + s(20) + s(10) + s(26))
    y = max(s(24), (h - block) // 2 - s(20))
    return {"ring_d": ring_d, "ring_x": w // 2 - ring_d // 2, "ring_y": y,
            "next_y": y + ring_d + ring_gap}


def _paint_ring(g, geom: dict, scale: float, t=None) -> None:
    """Den Ring samt Schein und Schloss zeichnen (style.css ``.lock-ring``).

    ``t`` ist der Fortschritt der Entsperr-Animation (N11.22): ``None`` =
    geschlossenes Schloss in Akzentfarbe (Normalfall), ``0..1`` = das Schloss
    geht auf und der Ring wechselt auf die Sicher-Farbe.
    """
    d = geom["ring_d"]
    x, y = geom["ring_x"], geom["ring_y"]
    if t is None:
        color, wash, line = T.ACCENT, T.ACCENT_WASH, T.ACCENT_LINE
        open_t, grow, glow = 0.0, 0.0, 46
    else:
        # Farbwechsel und Aufklappen laufen im ersten Teil (weich auslaufend),
        # dazu ein einmaliger, kleiner Pulsschlag des Rings.
        e1 = 1.0 - (1.0 - min(1.0, t / 0.55)) ** 3
        color = T.mix(T.SECURE, T.ACCENT, e1)
        wash = T.mix(T.SECURE_WASH, T.ACCENT_WASH, e1)
        line = T.mix(T.SECURE_LINE, T.ACCENT_LINE, e1)
        open_t = e1
        grow = 0.05 * math.sin(math.pi * min(1.0, t / 0.7))
        glow = int(46 + 44 * e1)
    dd = d * (1.0 + grow)
    xx, yy = x + (d - dd) / 2.0, y + (d - dd) / 2.0
    cx, cy = xx + dd / 2.0, yy + dd / 2.0
    # Schein wie box-shadow: 0 18px 48px accent
    T.draw_glow(g, cx, cy + dd * 0.10, dd * 0.92, color, glow)
    T.fill_pill(g, xx, yy, dd, dd, dd / 2.0, wash, line, max(1.0, scale))
    T.draw_lock_glyph(g, cx, cy, dd * (84.0 / 184.0), color, open_t)


def _call(fn, *args) -> None:
    """Einen optionalen Rueckruf ausfuehren; ein Fehler darf nie das Fenster
    mitreissen (die Rueckrufe sind reine Kosmetik: Blende auf/zu).

    Der Fehler wird aber im Debug-Modus gemeldet: ein verschluckter Fehler in
    ``on_painted`` liesse die Blende stehen, und dann sieht man nur noch den
    Ring und kann nichts eingeben (Fehler vom 2026-08-08). Deshalb ruft das
    Sperrfenster ``on_painted`` zusaetzlich ein zweites Mal auf.
    """
    if fn is None:
        return
    try:
        fn(*args)
    except Exception as exc:
        # Eine Quelle fuer den Debug-Schalter: im Release ist er hart aus (G34 a).
        import buildinfo
        if buildinfo.debug_enabled():
            print("[NoaToDo] Rueckruf fehlgeschlagen: %r" % (exc,), flush=True)


class Curtain:
    """Uebergabe-Blende zwischen zwei Fenstern (N11.25).

    Beim Sperren wird das WebView-Fenster abgebaut, danach raeumt main.py
    ``PROFILE_DIR`` (G14, kann Sekunden dauern), und erst dann steht das
    native Sperrfenster. In dieser Luecke gab es **gar kein** Fenster: der
    Bildschirm fiel auf den Desktop zurueck, es sah aus, als minimiere sich
    die App. Dasselbe umgekehrt beim Entsperren (WebView2 braucht Anlaufzeit).

    Die Blende ist ein Fenster im App-Design (Grundton + Raster, dunkle
    Titelleiste, derselbe Ring an derselben Stelle), das **vor** dem Abbau
    aufgelegt und erst weggenommen wird, wenn das naechste Fenster gemalt
    ist. Sie zeigt nur feste Formen: keinen Nutzerinhalt, keine Eingabe,
    keine Bridge, keine Schluessel; sie haelt auch nichts auf (die
    teardown-Sequenz laeuft unveraendert weiter).

    Sie laeuft in einem **eigenen** UI-Thread (STA) mit eigener
    Nachrichtenschleife, weil der Hauptthread waehrend der Uebergabe blockiert
    (``webview.start`` kehrt zurueck, danach der Wisch): ein Fenster ohne
    laufende Schleife wuerde nicht mehr zeichnen und von Windows als "reagiert
    nicht" ausgegraut. Eine Notbremse schliesst sie in jedem Fall wieder.

    ``mode``: ``"lock"`` (geschlossenes Schloss, Weg ins Sperrfenster),
    ``"unlocked"`` (offenes Schloss in der Sicher-Farbe, Weg in die App) oder
    ``"plain"`` (nur der Hintergrund, z.B. Weg ins Onboarding).
    """

    #: Notbremse: laenger darf eine Blende nie stehen (Sekunden).
    GUARD_MS = 15000
    #: Ausblendzeit beim Wegnehmen. Das naechste Fenster steht zu diesem
    #: Zeitpunkt fertig gemalt darunter; die Blende loest sich darueber auf,
    #: statt schlagartig zu verschwinden (harter Schnitt = sichtbarer Wechsel).
    FADE_MS = 160

    def __init__(self, mode: str = "lock", icon_path: str | None = None,
                 on_ready=None):
        self._mode = mode
        self._icon = icon_path
        self._on_ready = on_ready
        self._form = None
        self._closing = False
        self._ready = threading.Event()

    def show(self) -> None:
        """Blende auflegen und warten, bis sie wirklich auf dem Schirm ist."""
        from System.Threading import ApartmentState, Thread as ClrThread, ThreadStart
        thread = ClrThread(ThreadStart(self._run))
        thread.IsBackground = True   # darf das Beenden der App nie aufhalten
        try:
            thread.SetApartmentState(ApartmentState.STA)
        except Exception:
            pass
        thread.Start()
        # Ohne dieses Warten schloesse der Aufrufer sein Fenster womoeglich,
        # bevor die Blende steht: genau die Luecke, die sie schliessen soll.
        self._ready.wait(2.0)

    def close(self, next_hwnd: int = 0) -> None:
        """Blende wegnehmen (aus jedem Thread aufrufbar, idempotent).

        ``next_hwnd`` ist das Fenster, das danach bedient werden soll (das
        frisch gebaute Sperrfenster bzw. das WebView-Fenster). Es bekommt den
        Vordergrund **von der Blende selbst**, siehe ``_fade_out``.

        Kehrt sofort zurueck: das Ausblenden laeuft auf dem eigenen UI-Thread
        der Blende und haelt weder teardown noch Boot-Schleife auf (G35).
        """
        form, self._form = self._form, None
        if form is None:
            return
        from System import Action
        try:
            form.BeginInvoke(Action(lambda: self._fade_out(form, int(next_hwnd or 0))))
        except Exception:
            self._closing = True
            try:
                form.Close()
            except Exception:
                pass

    def _fade_out(self, form, next_hwnd: int = 0) -> None:
        """Weich ausblenden, dann schliessen (laeuft auf dem Blenden-Thread).

        Zwei Dinge halten dabei die Tastatur beim naechsten Fenster (Fehler vom
        2026-08-08: "man kann das Passwort gar nicht mehr eingeben"):

        1. Der Vordergrund wird **zuerst** an ``next_hwnd`` uebergeben, und
           zwar von hier aus, denn nur der Vordergrund-Prozess darf
           ``SetForegroundWindow`` benutzen.
        2. Die Blende wird **erst unsichtbar gemacht und dann geschlossen**.
           Ein sterbendes Fenster, das noch sichtbar (und obendrein TopMost)
           ist, laesst Windows die Aktivierung neu verteilen, und die landet
           dann gern bei einer ganz fremden App statt bei dem Fenster darunter:
           der Sperrschirm stand sichtbar da, aber jeder Tastendruck ging
           woandershin. Ein bereits verstecktes Fenster hat beim Schliessen
           nichts mehr zu vergeben.
        """
        import ctypes

        from System import EventHandler
        from System.Windows.Forms import Timer

        self._closing = True
        if next_hwnd:
            try:
                ctypes.windll.user32.SetForegroundWindow(next_hwnd)
            except Exception:
                pass

        def vanish():
            # Reihenfolge zaehlt: TopMost weg, verstecken, dann schliessen.
            try:
                form.TopMost = False
                form.Hide()
            except Exception:
                pass
            form.Close()

        try:
            steps = max(1, int(self.FADE_MS / 16))
            left = {"n": steps}
            fade = Timer()
            fade.Interval = 16

            def on_fade(_s, _a):
                left["n"] -= 1
                if left["n"] <= 0:
                    fade.Stop()
                    vanish()
                    return
                try:
                    form.Opacity = float(left["n"]) / float(steps)
                except Exception:
                    fade.Stop()
                    vanish()

            fade.Tick += EventHandler(on_fade)
            fade.Start()
        except Exception:
            vanish()

    def _run(self) -> None:
        from System import EventHandler
        from System.Windows.Forms import (
            Application, Form, FormBorderStyle,
            FormWindowState, PaintEventHandler, Timer,
        )

        form = Form()
        form.Text = "NoaToDo"              # B.4/A7: nie Nutzerinhalt im Titel
        form.FormBorderStyle = FormBorderStyle.Sizable
        # Die Titelleiste sieht aus wie die der beiden echten Fenster, samt
        # ihren drei Knoepfen: mit ControlBox=False verschwaende und kaeme das
        # Knopftrio bei jedem Wechsel sichtbar zurueck. Die Knoepfe sind nicht
        # nur Zierde, sie funktionieren auch (siehe die Begruendung bei
        # FormClosing weiter unten): eine Blende, die sich nicht wegklicken
        # laesst, waere im Fehlerfall eine Falle.
        form.ControlBox = True
        form.WindowState = FormWindowState.Maximized
        # Sichtbar in der Taskleiste (sonst blinkt der Eintrag waehrend der
        # Uebergabe weg, was genau nach "minimiert" aussieht) und ueber dem
        # abzubauenden Fenster.
        form.ShowInTaskbar = True
        form.TopMost = True
        T.style_form(form, self._icon)

        def on_paint(_s, e):
            g = e.Graphics
            w, h = form.ClientSize.Width, form.ClientSize.Height
            try:
                scale = T.dpi_scale(int(form.Handle.ToInt64()))
            except Exception:
                scale = 1.0
            # Rastermass wie im Sperrfenster (sonst aendert sich auf einem
            # skalierten Bildschirm sichtbar die Rasterdichte, N11.25).
            T.set_ui_scale(scale)
            T.paint_backdrop(g, 0, 0, w, h, T.TITLE_STRIP)
            if self._mode == "plain":
                return
            _paint_ring(g, _ring_geometry(w, h, scale), scale,
                        1.0 if self._mode == "unlocked" else None)

        form.Paint += PaintEventHandler(on_paint)

        def on_resize(_s, _a):
            # Minimieren waere ein Loch im Bild: sofort zurueck auf maximiert.
            if form.WindowState == FormWindowState.Minimized:
                form.WindowState = FormWindowState.Maximized
            form.Invalidate()

        form.Resize += EventHandler(on_resize)

        # Bewusst KEIN Abfangen von FormClosing: die Blende darf sich vom
        # Nutzer schliessen lassen. Ein Klick auf das X mitten in der (unter
        # einer halben Sekunde langen) Uebergabe reisst hoechstens ein kurzes
        # Loch ins Bild; eine Blende, die sich nicht schliessen laesst, wuerde
        # dagegen im Fehlerfall den Sperrschirm verdecken und den Nutzer aus
        # seinem eigenen Tresor aussperren (Fehler vom 2026-08-08). Das
        # Minimieren bleibt gedreht (on_resize), weil ein minimiertes
        # Blendenfenster genau das waere, was N11.25 verhindern soll.

        def on_shown(_s, _a):
            hwnd = 0
            try:
                hwnd = int(form.Handle.ToInt64())
            except Exception:
                pass
            if hwnd:
                T.apply_titlebar_theme(hwnd, True)
                T.disable_window_transitions(hwnd)
                # Taskleisten-Identitaet wie bei den echten Fenstern (AppID +
                # Logo): ohne sie taucht waehrend jeder Uebergabe kurz ein
                # zweiter Eintrag mit dem generischen Python-Symbol auf.
                _call(self._on_ready, hwnd)
            # Erst wirklich malen, dann den Aufrufer weiterlaufen lassen: er
            # schliesst unmittelbar danach sein Fenster, und ein noch leeres
            # Blendenfenster waere genau die Luecke, die sie schliessen soll.
            try:
                form.Refresh()
            except Exception:
                pass
            self._ready.set()

        form.Shown += EventHandler(on_shown)

        guard = Timer()
        guard.Interval = self.GUARD_MS

        def on_guard(_s, _a):
            # Sollte der Aufrufer die Blende je vergessen (Fehler im Aufbau des
            # naechsten Fensters), verschwindet sie hier von selbst.
            guard.Stop()
            self._form = None
            self._closing = True
            form.Close()

        guard.Tick += EventHandler(on_guard)
        guard.Start()

        self._form = form
        try:
            Application.Run(form)
        finally:
            self._ready.set()   # nie einen Wartenden haengen lassen
            self._form = None
            try:
                form.Dispose()
            except Exception:
                pass


def run_lock_window(api: Any, boot_state: str, boot_reason: str | None,
                    icon_path: str | None, _test_after_shown=None,
                    on_ready=None, on_painted=None, on_leaving=None,
                    resumed: bool = False) -> str:
    """Baut das native Sperr-/Fehlerfenster und laeuft, bis es sich schliesst.

    Rueckgabe: ``"unlocked"`` (Tresor offen, weiter zur WebView-App),
    ``"quit"`` (Off-Knopf / Fenster-X: App beenden) oder ``"onboarding"``
    (Reset: Tresor geloescht, zurueck ins Onboarding).

    ``on_ready`` bekommt (sobald das Fenster steht) dessen HWND; main.py haengt
    daran die Taskleisten-Identitaet (AppID + App-Icon), damit auch der
    Taskleisten-Eintrag des Sperrfensters das NoaToDo-Logo traegt und nicht das
    generische Python-Symbol.

    ``resumed`` sagt, ob dieses Fenster eine **laufende, zwischendurch
    gesperrte** Sitzung bewacht (``True``) oder einen normalen Programmstart
    (``False``; main.py fuehrt den Merker als ``api._resumed``, N11.22). Davon
    haengt die Rueckmeldung beim Entsperren ab: nur bei ``True`` geht das
    Schloss auf (N11.22), beim normalen Start uebernimmt die Willkommens-Blende
    der App mit dem Logo (N11.20). Es gibt also immer genau **eine** Feier,
    nie zwei hintereinander.

    ``on_painted`` und ``on_leaving`` bedienen die nahtlose Fensteruebergabe
    (N11.25): ``on_painted(hwnd)`` laeuft, sobald dieses Fenster wirklich
    gemalt ist (main.py nimmt dort die Blende weg und reicht ihr ``hwnd``, an
    das sie den Vordergrund uebergibt), ``on_leaving(mode)`` laeuft
    unmittelbar bevor das Fenster fuer einen Weiterweg schliesst (main.py legt
    dort die Blende auf, bevor der Bildschirm leer werden kann). Beim Beenden
    wird ``on_leaving`` bewusst NICHT gerufen: dann soll nichts stehenbleiben.

    ``_test_after_shown`` ist eine reine Test-Naht (production ruft ohne sie):
    ein Callback, der nach dem Anzeigen einmal mit den Steuerelementen
    aufgerufen wird, damit ein automatisierter Test den Unlock-Klick
    deterministisch ausloesen kann, ohne auf Fenster-Fokus/Tastatur-Injektion
    in einer nicht-interaktiven Session angewiesen zu sein.
    """
    from System import Action, EventHandler
    from System.Drawing import Point, Rectangle, Size
    from System.Windows.Forms import (
        Application, FormBorderStyle, FormWindowState, Form, KeyEventHandler,
        KeyPressEventHandler, Keys, MouseEventHandler, PaintEventHandler, Timer,
    )

    result = {"value": "quit"}   # Default: Fenster-X = quit (N11.11.1)
    # Wird gesetzt, sobald ein bewusster Ausgang (unlock/quit/reset) das Fenster
    # schliesst; dann darf der FormClosing-Handler NICHT noch einmal quit_app
    # ausloesen.
    state = {"closing_intent": None, "busy": False, "reset_open": False,
             # Rate-Limit-Sperre (N11.4): laeuft ein Countdown, nimmt do_unlock()
             # keinen Versuch an. Seit dem Wegfall des Unlock-Knopfes (N11.24)
             # haengt dieser Zustand hier statt an Button.Enabled.
             "blocked": False,
             # Der Ringlauf des Off-Knopfes laeuft (N11.28): das Beenden ist
             # beschlossen, ein zweiter Klick und ein Entsperr-Versuch waeren
             # ab hier nur noch zwei Wege, die sich gegenseitig ueberholen.
             "quitting": False}
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
        # Der normale Sperrschirm traegt seit 2026-08-08 (Nutzerwunsch) gar
        # keinen Text mehr: nur Ring und Eingabepille. Das Schloss sagt, was
        # los ist, und der Platzhalter "Password" sagt, was zu tun ist; die
        # frueheren Zeilen "NoaToDo is locked" / "Type your passphrase and
        # press Enter." erklaerten beides ein zweites Mal. Die beiden Labels
        # bleiben angelegt, aber unsichtbar: der Fehlerfall benutzt sie.
        title.control.Visible = False
        subtitle.control.Visible = False

    # Kleiner als frueher (320x46, Nutzerwunsch 2026-08-10): die Eingabe ist
    # eine kurze Geste unter einem grossen Ring, keine Formularzeile. Das
    # Seitenverhaeltnis ist dabei Absicht (6:1 statt der frueheren 7:1): die
    # Pille soll wie eine Pille aussehen und nicht wie ein Balken, der Radius
    # ist immer die halbe Hoehe (``fill_pill``), also voll gerundet.
    # Bewusst KEIN Show/Hide-Knopf mehr (2026-08-10): die Passphrase ist an
    # keiner Stelle, an der sie **eingegeben** wird, im Klartext zu sehen. Die
    # einzige Ausnahme ist das erstmalige Festlegen im Onboarding, wo es keine
    # gespeicherte Passphrase gibt, die aufgedeckt werden koennte. Ohne den
    # Knopf hat die Pille auch rechts wieder ihren vollen Innenraum.
    pw_pill = T.PillInput((240, 40), password=True, cue="Password", font_size=11.0)
    pw = pw_pill.box

    caps = T.AppLabel("", 9.0, False, T.DANGER, size=(500, 20))
    # Bewusst KEIN "Unlock"-Knopf (N11.24): entsperrt wird mit Enter im Feld.
    # Der Knopf sass direkt unter dem Ring und schnitt dessen Schein hart ab;
    # ohne ihn hat das Schloss die Flaeche, die es braucht, und die Eingabe
    # bleibt der einzige Weg (Enter ist die gelernte Geste in einem
    # Passwortfeld; die Zeile, die das frueher aussprach, ist weg).
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
        # Rastermass fuer alle gemalten Flaechen dieses Fensters (Formular und
        # Steuerelemente holen es sich aus wintheme), damit das Raster auf
        # skalierten Bildschirmen dieselbe Weite hat wie im WebView.
        T.set_ui_scale(scale["v"])
        w = form.ClientSize.Width
        h = form.ClientSize.Height
        cx = w // 2

        gap = s(26)
        title_h, sub_h = s(38), s(26)
        input_h, caps_h, status_h = s(40), s(20), s(26)
        # Ring-Lage kommt aus der gemeinsamen Quelle (dieselbe benutzt die
        # Uebergabe-Blende, N11.25), damit beim Fensterwechsel nichts springt.
        # Nur der Fehlerfall meldet die zwei Textzeilen als Zusatzhoehe an; der
        # normale Sperrschirm hat sie nicht mehr (siehe oben) und rechnet
        # deshalb genau wie die Blende.
        extra = (title_h + s(4) + sub_h + gap) if vault_error else 0
        geo = _ring_geometry(w, h, scale["v"], extra)
        geom["ring_d"] = geo["ring_d"]
        geom["ring_x"] = geo["ring_x"]
        geom["ring_y"] = geo["ring_y"]
        y = geo["next_y"]

        if vault_error:
            title.control.Size = Size(min(w - s(40), s(700)), title_h)
            title.control.Location = Point(cx - title.control.Width // 2, y)
            y += title_h + s(4)

            subtitle.control.Size = Size(min(w - s(40), s(760)), sub_h)
            subtitle.control.Location = Point(cx - subtitle.control.Width // 2, y)
            y += sub_h + gap

        pill_w = min(w - s(60), s(240))
        pw_pill.control.Size = Size(pill_w, input_h)
        pw_pill.control.Location = Point(cx - pill_w // 2, y)
        pw_pill.layout_box(scale=scale["v"])
        y += input_h + s(6)

        caps.control.Size = Size(min(w - s(40), s(500)), caps_h)
        caps.control.Location = Point(cx - caps.control.Width // 2, y)
        y += caps_h + s(10)

        status.control.Size = Size(min(w - s(40), s(760)), status_h)
        status.control.Location = Point(cx - status.control.Width // 2, y)
        y += status_h

        # Fusszeile: Reset-Weg. Sie sitzt wirklich unten am Fensterrand
        # (Nutzerwunsch 2026-08-08) und nicht dicht unter der Statuszeile: der
        # Reset ist der Nebenausgang und soll der Eingabe nicht ins Bild
        # ruecken. Nur bei niedrigen Fenstern rutscht sie so weit hoch wie
        # noetig, aber nie in den Block hinein.
        foot_h = s(44)
        foot_y = max(y + s(24), h - foot_h - s(48))

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
    # Fortschritt der Entsperr-Animation (N11.22): None = geschlossenes Schloss
    # in Akzentfarbe (Normalfall), 0..1 = das Schloss geht auf.
    anim = {"t": None, "start": 0.0}

    def on_form_paint(_s, e):
        g = e.Graphics
        w, h = form.ClientSize.Width, form.ClientSize.Height
        T.paint_backdrop(g, 0, 0, w, h, T.TITLE_STRIP)
        _paint_ring(g, geom, scale["v"], anim["t"])

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

    def claim_focus():
        """Vordergrund und Eingabefokus wirklich holen (N11.25).

        ``pw.Focus()`` allein genuegt nach einer Fenster-Uebergabe nicht: der
        Fokus liegt dann zwar auf dem Feld, das Fenster ist aber nicht das
        Vordergrundfenster, und Tastendruecke gehen woandershin. Beides muss
        gesetzt werden, und zwar solange die Blende (derselbe Prozess) noch
        vorne ist, denn nur dann laesst Windows ``SetForegroundWindow`` zu.
        """
        import ctypes
        try:
            form.Activate()
        except Exception:
            pass
        try:
            ctypes.windll.user32.SetForegroundWindow(int(form.Handle.ToInt64()))
        except Exception:
            pass
        try:
            if pw.Visible:
                pw.Focus()
        except Exception:
            pass

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
        # Wird per Timer aufgerufen: zeigt "try again in Ns" und gibt die
        # Eingabe wieder frei, wenn die Sperrzeit abgelaufen ist. Ohne
        # Unlock-Knopf (N11.24) haengt die Sperre an ``state["blocked"]``, das
        # do_unlock() prueft; das Feld selbst bleibt bedienbar, damit die
        # Passphrase waehrend der Wartezeit schon getippt werden kann.
        if countdown["remaining"] > 0:
            countdown["remaining"] -= 1
            if countdown["remaining"] <= 0:
                state["blocked"] = False
                set_status("", danger=False)
            else:
                set_status(f"Too many attempts. Try again in {countdown['remaining']}s.")

    timer = Timer()
    timer.Interval = 1000

    def on_tick(_s, _a):
        update_caps()
        tick_countdown()
    timer.Tick += EventHandler(on_tick)

    # ------------------------------------------------------------------
    # Entsperr-Animation (N11.22): das Schloss geht auf, dann schliesst das
    # Fenster. Sie ersetzt die Willkommens-Blende des WebViews beim Entsperren
    # (die laeuft nur noch beim echten Start), gibt die Rueckmeldung also genau
    # dort, wo die Passphrase eingegeben wurde. Bewusst kurz: sie haelt den
    # Uebergang in die App nur um Bruchteile einer Sekunde auf.
    UNLOCK_ANIM_MS = 620.0
    anim_timer = Timer()
    anim_timer.Interval = 16          # ~60 Bilder/s

    def invalidate_ring():
        # Nur den Ring samt Schein neu zeichnen (nicht das ganze Fenster): der
        # Rest des Bildes steht still, und das Formular ist doppelt gepuffert.
        d = geom["ring_d"]
        pad = int(d * 0.6) + 4
        try:
            form.Invalidate(Rectangle(geom["ring_x"] - pad, geom["ring_y"] - pad,
                                      d + 2 * pad, d + 2 * pad))
        except Exception:
            form.Invalidate()

    def leave_unlocked(mode):
        # Nahtlos weiter (N11.25): erst die Blende mit dem passenden Bild
        # auflegen, dann schliessen. Sonst steht bis zum Aufbau des
        # WebView-Fensters gar kein Fenster da.
        state["closing_intent"] = "unlocked"
        result["value"] = "unlocked"
        _call(on_leaving, mode)
        form.Close()

    def on_anim_tick(_s, _a):
        anim["t"] = min(1.0, (time.monotonic() - anim["start"]) * 1000.0 / UNLOCK_ANIM_MS)
        invalidate_ring()
        if anim["t"] >= 1.0:
            anim_timer.Stop()
            leave_unlocked("unlocked")   # Blende zeigt das offene Schloss weiter
    anim_timer.Tick += EventHandler(on_anim_tick)

    def play_unlock_anim():
        timer.Stop()                  # Caps-/Countdown-Takt wird nicht mehr gebraucht
        stop_off_ring()               # der Off-Knopf verschwindet gleich (N11.28)
        # Im Normalfall sind beide Labels unsichtbar (der Sperrschirm traegt
        # keinen Text mehr), das aufgehende Schloss ist die Rueckmeldung. Nur
        # im Fehlerfall, wo sie stehen, ersetzt "Unlocked" die Fehlerzeilen.
        title.set("Unlocked")
        subtitle.set("")
        caps.set("")
        set_status("", danger=False)
        # Alles, was jetzt nur noch ablenkt, verschwindet: der Blick soll auf
        # dem aufgehenden Schloss liegen.
        for ctl in (pw_pill.control, forgot.control,
                    reset_pill.control, reset_btn.control, off.control):
            ctl.Visible = False
        anim["t"] = 0.0
        anim["start"] = time.monotonic()
        form.Invalidate()
        anim_timer.Start()

    def do_unlock():
        # Ausgeloest wird nur noch ueber Enter im Passwortfeld (N11.24).
        if state["busy"] or state["blocked"] or state["quitting"]:
            return
        passphrase = pw.Text or ""
        state["busy"] = True
        set_status("Unlocking…", danger=False)

        def worker():
            res = api.unlock(passphrase)

            def apply():
                state["busy"] = False
                if state["quitting"]:
                    # Waehrend der Pruefung wurde der Off-Knopf gedrueckt: das
                    # Beenden laeuft bereits (teardown schliesst das Fenster),
                    # hier darf kein zweiter Ausgang danebenlaufen.
                    return
                if isinstance(res, dict) and res.get("ok"):
                    if resumed:
                        # Rueckkehr in eine laufende Sitzung: erst aufgehen
                        # lassen, dann schliessen (on_anim_tick setzt den
                        # Ausgang und ruft form.Close()). Die App zeigt danach
                        # keine Willkommens-Blende (N11.22).
                        play_unlock_anim()
                    else:
                        # Normaler Programmstart (2026-08-08, Nutzerwunsch):
                        # das Schloss geht NICHT auf, die Feier ist drueben die
                        # Logo-Animation der App (N11.20). Zwei Animationen
                        # hintereinander waren eine zuviel; die Blende bleibt
                        # deshalb schmucklos ("plain") und traegt nur den
                        # Hintergrund bis zum ersten Bild des WebViews.
                        leave_unlocked("plain")
                    return
                state["blocked"] = False
                pw.Text = ""
                pw.Focus()
                code = res.get("error") if isinstance(res, dict) else "internal"
                if code == "passphrase":
                    set_status("Wrong passphrase.")
                    retry = int(res.get("retry_in") or 0)
                    if retry > 1:
                        countdown["remaining"] = retry
                        state["blocked"] = True
                elif code == "rate_limited":
                    countdown["remaining"] = int(res.get("retry_in") or 0)
                    state["blocked"] = True
                    set_status(f"Too many attempts. Try again in {countdown['remaining']}s.")
                elif code == "memory":
                    set_status("Not enough memory. Close other apps and try again.")
                elif code == "vault":
                    set_status("Vault cannot be opened.")
                else:
                    set_status("Could not unlock.")
            ui(apply)

        threading.Thread(target=worker, daemon=True).start()

    def on_pw_key(_s, args):
        if args.KeyCode == Keys.Enter:
            args.SuppressKeyPress = True
            do_unlock()
    pw.KeyDown += KeyEventHandler(on_pw_key)

    # ------------------------------------------------------------------
    # Off-Knopf: erst der Ring, dann der Klick (N11.28)
    # ------------------------------------------------------------------
    # Der Zeiger auf dem Knopf **loest aus**: der Kreis um das Power-Zeichen
    # faehrt in der Akzentfarbe herum (von oben im Uhrzeigersinn) und laeuft
    # dann **von selbst zu Ende**, auch wenn der Zeiger zwischendurch woanders
    # hinfaehrt. Ist der Kreis zu, wird das Zeichen farbig, und **erst dann**
    # beendet ein Klick die App; vorher passiert bei einem Klick nichts. Der
    # Ring ist damit nicht nur Schmuck, sondern die Sicherung gegen den
    # versehentlichen Klick, die der Knopf vorher nicht hatte.
    # Der scharfe Zustand haelt nicht ewig: kommt binnen zehn Sekunden kein
    # Klick, faellt der Knopf in seinen Ruhezustand zurueck, und ein Zeiger
    # darauf loest ihn neu aus. Sonst stuende ein einmal beruehrter Knopf den
    # ganzen Abend scharf da.
    off_anim = {"t": 0.0, "running": False, "last": 0.0}
    off_timer = Timer()
    off_timer.Interval = 16           # ~60 Bilder/s, wie die Entsperr-Animation
    off_hold = Timer()                # Wartezeit im scharfen Zustand
    off_hold.Interval = int(OFF_HOLD_MS)

    def off_armed() -> bool:
        return off_anim["t"] >= 1.0

    def do_quit():
        state["closing_intent"] = "quit"
        result["value"] = "quit"
        try:
            api.quit_app()   # teardown('quit'); request_teardown schliesst das Fenster
        except Exception:
            form.Close()

    def off_reset():
        """Zurueck in den Ruhezustand (kein Ring, kein farbiges Zeichen)."""
        off_anim["t"] = 0.0
        off_anim["running"] = False
        off_timer.Stop()
        off_hold.Stop()
        off.set_progress(None)

    def on_off_tick(_s, _a):
        now = time.monotonic()
        dt = max(0.0, now - off_anim["last"])
        off_anim["last"] = now
        off_anim["t"] += dt * 1000.0 / OFF_FILL_MS
        if off_anim["t"] >= 1.0:
            off_anim["t"] = 1.0
            off_anim["running"] = False
            off_timer.Stop()
            off.set_progress(1.0)     # voller Kreis: stehen lassen, jetzt scharf
            off_hold.Start()          # ... aber nur fuer OFF_HOLD_MS
            return
        off.set_progress(off_anim["t"])
    off_timer.Tick += EventHandler(on_off_tick)

    def on_off_hold(_s, _a):
        # Niemand hat geklickt: der Knopf wird wieder ein gewoehnlicher Knopf.
        off_hold.Stop()
        if not state["quitting"]:
            off_reset()
    off_hold.Tick += EventHandler(on_off_hold)

    def off_trigger():
        # Aus dem Ruhezustand heraus starten. Ein laufender oder bereits
        # geschlossener Ring wird nicht angefasst: der Lauf gehoert sich selbst,
        # sobald er angestossen ist.
        if state["quitting"] or off_anim["running"] or off_anim["t"] > 0.0:
            return
        off_anim["running"] = True
        off_anim["last"] = time.monotonic()
        off_timer.Start()

    def stop_off_ring():
        # Wird gebraucht, wenn der Knopf verschwindet (Entsperr-Animation):
        # ein weiterlaufender Takt auf einem unsichtbaren Knopf hat nichts mehr
        # zu zeichnen.
        off_reset()

    off.control.MouseEnter += EventHandler(lambda _s, _a: off_trigger())
    # Auch die Bewegung auf dem Knopf loest aus: nach dem Ablauf der Haltezeit
    # liegt der Zeiger unter Umstaenden noch darauf, und ohne diesen Weg muesste
    # man erst herunter und wieder herauf fahren, um den Ring neu zu starten.
    off.control.MouseMove += MouseEventHandler(lambda _s, _a: off_trigger())

    def on_off_click(_s, _a):
        # Vor dem vollen Kreis ist der Knopf bewusst stumm: kein Beenden, keine
        # Meldung. Der Ring sagt bereits, was fehlt.
        if state["quitting"] or not off_armed():
            return
        state["quitting"] = True
        off_timer.Stop()
        off_hold.Stop()
        do_quit()
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
        if state["quitting"]:
            return               # das Beenden laeuft schon (N11.28)
        if (reset_pill.box.Text or "").strip() != "RESET":
            set_status("Type RESET (all caps) to confirm.")
            return
        state["closing_intent"] = "onboarding"
        result["value"] = "onboarding"
        _call(on_leaving, "plain")   # nahtlos ins Onboarding-Fenster (N11.25)
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
        # auch wenn der Fokus gerade auf einem Knopf oder Link steht.
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
        # Layout und erstes Bild duerfen die Blende nicht mit sich reissen:
        # scheitert hier etwas, wird das Fenster zwar unfertig aussehen, aber
        # die Blende MUSS trotzdem weggehen. Sonst steht nur der Ring da und
        # es laesst sich nichts eingeben (Fehler vom 2026-08-08).
        try:
            layout()
            # Erst malen, dann die Uebergabe-Blende wegnehmen (N11.25): sonst
            # blitzt zwischen Blende und fertigem Bild ein leeres Fenster auf.
            form.Refresh()
        except Exception:
            pass
        # Tastatur holen, BEVOR die Blende geht (N11.25): sie ist in diesem
        # Moment das Vordergrundfenster, und wenn sie verschwindet, gibt
        # Windows den Vordergrund NICHT von sich aus an das Fenster darunter
        # weiter. Ohne das steht der Sperrschirm zwar sichtbar da, aber jeder
        # Tastendruck geht ins Leere und die Passphrase laesst sich nicht
        # eingeben. Weil unser eigener Prozess gerade den Vordergrund haelt,
        # darf er ihn auch setzen (Windows erlaubt SetForegroundWindow nur
        # dann); nach dem Ausblenden wird es einmal wiederholt, falls der
        # Wechsel dazwischen doch woanders landete.
        claim_focus()
        # Das eigene Fensterhandle mitgeben: die Blende uebergibt den
        # Vordergrund an genau dieses Fenster, bevor sie sich schliesst.
        _call(on_painted, hwnd)
        again = Timer()
        again.Interval = 320          # nach dem Ausblenden der Blende

        def on_again(_s2, _a2):
            again.Stop()
            # Beides bewusst ein zweites Mal: Wegnehmen der Blende ist
            # idempotent (main.py merkt sich genau eine), und ein einzelner
            # verschluckter Fehler im ersten Anlauf darf nicht dazu fuehren,
            # dass die Blende stehenbleibt und die Eingabe verdeckt.
            _call(on_painted, hwnd)
            claim_focus()

        again.Tick += EventHandler(on_again)
        again.Start()
        timer.Start()
        if _test_after_shown is not None:
            probe = Timer()
            probe.Interval = 800

            def fire(_s2, _a2):
                probe.Stop()
                try:
                    # "submit" ist der Ersatz fuer den frueheren Unlock-Knopf
                    # (N11.24): der Test loest den Entsperr-Versuch direkt aus.
                    # "off_hover" ersetzt das Zeigen mit der Maus (N11.28): ohne
                    # vollen Ring nimmt "off" keinen Klick an.
                    _test_after_shown({"pw": pw, "submit": do_unlock,
                                       "off": off.control,
                                       "off_hover": off_trigger, "form": form})
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
            state["blocked"] = True
            set_status(f"Too many attempts. Try again in {rem}s.")
    form.Shown += EventHandler(on_shown)

    # request_teardown: die Api ruft das (nach teardown-Schritten 1-8), um das
    # aktuelle Fenster abzubauen. Im Sperrfenster heisst das: die Form
    # schliessen (der Ausgang steht schon in state/result). Ueber den UI-Thread.
    api._request_teardown = lambda: ui(form.Close)

    for ctl in (off.control, title.control, subtitle.control, pw_pill.control,
                caps.control, status.control, forgot.control,
                reset_pill.control, reset_btn.control):
        form.Controls.Add(ctl)

    Application.Run(form)
    try:
        form.Dispose()
    except Exception:
        pass
    return result["value"]
