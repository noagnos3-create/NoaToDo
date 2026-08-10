"""Gemeinsame native Oberflaeche im App-Design (WinForms statt Windows-Look).

Warum es diese Datei gibt: NoaToDo hat zwei Fenstersorten. Das Hauptfenster ist
ein WebView und traegt das Designkonzept aus ``frontend/style.css``. Daneben gibt
es schlanke **native** Fenster ohne WebView (das Sperrfenster nach N11.18, dazu
kleine Hinweisfenster wie die Zweitinstanz-Meldung). Diese nativen Fenster sahen
bisher nach Windows aus: weisse Titelleiste, eckige Standard-Steuerelemente. Das
bricht das Designkonzept genau an der Stelle, die der Nutzer beim Start als
erstes sieht.

Dieses Modul ist die eine Quelle fuer das native Erscheinungsbild:

* die Farb-Tokens sind 1:1 die Dark-Tokens aus ``style.css`` (keine neuen Farben),
* Titelleisten werden ueber die DWM-API in Caption-Farbe gesetzt (kein Weiss),
* Flaechen bekommen denselben Hintergrund wie die App (Grundton + 28px-Raster),
* Eingaben und Knoepfe sind Pillen (Radius = halbe Hoehe), wie in der App,
* Text wird in derselben Groessen-/Gewichtsstaffel gesetzt.

Zeichnen statt Standard-Steuerelement: WinForms kann weder runde TextBoxen noch
runde Buttons, deshalb malen die Bausteine hier ihre Pille selbst (GDI+ mit
Kantenglaettung) und tragen die Zeichnung ueber das flache Standardaussehen.

Grenze, ehrlich benannt: **native Systemdialoge** (Datei-/Ordnerauswahl von
Windows) gehoeren dem Betriebssystem und lassen sich nicht umfaerben; sie
bleiben im Windows-Look. Ebenso bleiben die drei Fensterknoepfe (Minimieren,
Maximieren, Schliessen) Windows-gezeichnet, nur ihre Leiste faerbt DWM ein.

Schrift: die App-Schriften (Space Grotesk, JetBrains Mono) liegen nur als
``.woff2`` vor, GDI+ kann daraus keine Familie laden. Die nativen Fenster nehmen
deshalb die letzte Stufe derselben CSS-Schriftkette (``system-ui``), also Segoe
UI Variable bzw. Segoe UI.
"""
from __future__ import annotations

import ctypes

import clr

clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from System import Action, EventHandler, IntPtr  # noqa: E402
from System.Drawing import (  # noqa: E402
    Color, Font, FontStyle, Icon, Point, RectangleF, Size, SolidBrush, Pen,
    StringAlignment, StringFormat,
)
from System.Drawing.Drawing2D import GraphicsPath, LineCap, SmoothingMode  # noqa: E402
from System.Drawing.Text import InstalledFontCollection, TextRenderingHint  # noqa: E402
from System.Reflection import BindingFlags  # noqa: E402
from System.Windows.Forms import (  # noqa: E402
    Application, BorderStyle, Button, Control, Cursors, FlatStyle, Form,
    FormBorderStyle, FormStartPosition, HorizontalAlignment, KeyEventHandler,
    Keys, Label, MouseEventHandler, PaintEventHandler, Panel, TextBox,
)

# "None" ist in Python ein Schluesselwort: .NET-Enumwerte dieses Namens gibt es
# nur ueber getattr (betrifft BorderStyle.None und SmoothingMode.None).
_BORDER_NONE = getattr(BorderStyle, "None")
_SMOOTH_NONE = getattr(SmoothingMode, "None")

# ---------------------------------------------------------------------------
# Design-Tokens (Dark), 1:1 aus frontend/style.css
# ---------------------------------------------------------------------------
BG            = "#15120d"
BG_GRID       = "#1c1812"
SURFACE       = "#1f1b14"
SURFACE_2     = "#272218"
SURFACE_3     = "#322b20"
BORDER        = "#3a3326"
BORDER_STRONG = "#4a4231"
TEXT          = "#ece3d2"
TEXT_DIM      = "#a89a80"
TEXT_FAINT    = "#73684f"
ACCENT        = "#d97757"
ACCENT_INK    = "#ffffff"
SECURE        = "#6fb87f"   # style.css --secure (dark): "entsperrt / sicher"
DANGER        = "#e0623e"

#: Rasterabstand des App-Hintergrunds (style.css: 28px-Gitter).
GRID_STEP = 28
#: Hoehe des Farbstreifens unter der Titelleiste (style.css: .app border-top).
TITLE_STRIP = 6

# Bildschirmskalierung fuer die gemalten Design-Masse (N11.25).
# GRID_STEP und TITLE_STRIP sind Design-Pixel wie in style.css. WinForms malt
# aber in physischen Pixeln: auf einem 150%-Bildschirm waere das native Raster
# nur 28 physische Punkte weit, das WebView-Raster dagegen 42. Beim Fenster-
# wechsel aenderte sich dadurch sichtbar die Rasterdichte. Der Wert wird von
# dem Fenster gesetzt, das gerade malt (Sperrfenster/Blende, aus dpi_scale).
_ui_scale = 1.0


def set_ui_scale(scale: float) -> None:
    """Skalierung fuer gemalte Design-Masse setzen (Raster, Titelstreifen)."""
    global _ui_scale
    try:
        _ui_scale = max(1.0, float(scale))
    except Exception:
        _ui_scale = 1.0


def grid_step() -> int:
    """Rasterabstand in physischen Pixeln (Design-28px mal Bildschirmskalierung)."""
    return max(6, int(round(GRID_STEP * _ui_scale)))


def line_w(base: float = 1.0) -> float:
    """Strichstaerke in **ganzen** physischen Pixeln (mindestens 1).

    Gebrochene Strichstaerken sind der Grund, warum eine gemalte Pille
    unsauber wirkt: GDI+ verteilt z.B. 1.4 px auf zwei Pixelreihen. Auf den
    geraden Kanten bleibt die Linie trotzdem kraeftig, in den Rundungen wird
    sie blass und breit, und die Enden sehen ausgefranst aus. Ganze Pixel
    (zusammen mit einem Versatz von genau der halben Strichstaerke, siehe
    ``stroke_pill``) geben rundherum dasselbe Gewicht.
    """
    return float(max(1, int(round(base * _ui_scale))))


def rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mix(a: str, b: str, t: float) -> str:
    """``t`` Anteil von ``a`` auf ``b`` (Ersatz fuer CSS color-mix, sRGB)."""
    ar, ag, ab = rgb(a)
    br, bg, bb = rgb(b)
    return "#%02x%02x%02x" % (
        int(round(ar * t + br * (1 - t))),
        int(round(ag * t + bg * (1 - t))),
        int(round(ab * t + bb * (1 - t))),
    )


# Abgeleitete Tokens (in style.css color-mix, hier vorgemischt).
ACCENT_WASH  = mix(ACCENT, SURFACE, 0.20)
ACCENT_LINE  = mix(ACCENT, BORDER, 0.45)
ACCENT_HOVER = mix(ACCENT, "#000000", 0.88)   # style.css: .btn-primary:hover
ACCENT_DOWN  = mix(ACCENT, "#000000", 0.78)
ACCENT_GLOW  = mix(ACCENT, BG, 0.16)          # Schein um den Sperr-Ring
SECURE_WASH  = mix(SECURE, SURFACE, 0.16)     # style.css --secure-wash (dark)
SECURE_LINE  = mix(SECURE, BORDER, 0.45)
DANGER_WASH  = mix(DANGER, SURFACE, 0.18)
DANGER_LINE  = mix(DANGER, BORDER, 0.55)


def col(hex_color: str) -> Color:
    r, g, b = rgb(hex_color)
    return Color.FromArgb(r, g, b)


# ---------------------------------------------------------------------------
# Schrift
# ---------------------------------------------------------------------------
_families: set[str] | None = None


def _family_exists(name: str) -> bool:
    global _families
    if _families is None:
        try:
            _families = {f.Name for f in InstalledFontCollection().Families}
        except Exception:
            _families = set()
    return name in _families


def _ui_family() -> str:
    # system-ui-Kette wie in style.css (--font-sans faellt auf system-ui zurueck).
    for name in ("Segoe UI Variable Text", "Segoe UI"):
        if _family_exists(name):
            return name
    return "Segoe UI"


def _display_family() -> str:
    for name in ("Segoe UI Variable Display", "Segoe UI Semibold", "Segoe UI"):
        if _family_exists(name):
            return name
    return "Segoe UI"


def font(size: float, bold: bool = False, display: bool = False) -> Font:
    """Schrift in Punkt (skaliert dadurch automatisch mit der Bildschirm-DPI)."""
    family = _display_family() if display else _ui_family()
    style = FontStyle.Bold if bold else FontStyle.Regular
    try:
        return Font(family, float(size), style)
    except Exception:
        return Font("Segoe UI", float(size), style)


# ---------------------------------------------------------------------------
# Titelleiste (DWM) und Fenstergrundlagen
# ---------------------------------------------------------------------------
_DWMWA_USE_IMMERSIVE_DARK_MODE   = 20  # Windows 10 1903+
_DWMWA_TRANSITIONS_FORCEDISABLED = 3   # Windows Vista+
_DWMWA_CAPTION_COLOR             = 35  # Windows 11 22000+
_DWMWA_TEXT_COLOR                = 36  # Windows 11 22000+

_TB_DARK       = SURFACE     # Titelleiste = --surface (dark), wie das WebView-Fenster
_TB_LIGHT      = "#faf6ee"   # --surface (light)
_TB_TEXT_DARK  = "#f2ead9"
_TB_TEXT_LIGHT = "#1f1b14"


def apply_titlebar_theme(hwnd: int, dark: bool = True) -> None:
    """Titelleiste in App-Farbe statt Windows-Weiss (Caption + Titeltext).

    Einzige Umsetzung im Projekt: das WebView-Fenster (main.py) und die nativen
    Fenster benutzen dieselbe Funktion, damit beide exakt gleich aussehen.
    """
    if not hwnd:
        return
    try:
        dwm = ctypes.windll.dwmapi
        dm = ctypes.c_int(1 if dark else 0)
        dwm.DwmSetWindowAttribute(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE,
                                  ctypes.byref(dm), ctypes.sizeof(dm))
        r, g, b = rgb(_TB_DARK if dark else _TB_LIGHT)
        colorref = ctypes.c_int(r | (g << 8) | (b << 16))
        dwm.DwmSetWindowAttribute(hwnd, _DWMWA_CAPTION_COLOR,
                                  ctypes.byref(colorref), ctypes.sizeof(colorref))
        tr, tg, tb = rgb(_TB_TEXT_DARK if dark else _TB_TEXT_LIGHT)
        text_ref = ctypes.c_int(tr | (tg << 8) | (tb << 16))
        dwm.DwmSetWindowAttribute(hwnd, _DWMWA_TEXT_COLOR,
                                  ctypes.byref(text_ref), ctypes.sizeof(text_ref))
        # Rahmen neu berechnen lassen, damit die Farbe sofort steht (nicht erst
        # beim naechsten Fensterereignis).
        ctypes.windll.user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            0x0001 | 0x0002 | 0x0004 | 0x0200 | 0x0020,  # NOSIZE|NOMOVE|NOZORDER|NOOWNERZORDER|FRAMECHANGED
        )
    except Exception:
        pass


def disable_window_transitions(hwnd: int) -> None:
    """Windows' eigene Fenster-Animationen fuer dieses Fenster abschalten (N11.25).

    DWM blendet ein Fenster beim Oeffnen ein und beim Schliessen aus (kurzes
    Auf-/Zuziehen). Genau das machte den Fensterwechsel beim Sperren und
    Entsperren sichtbar: das abzubauende Fenster zog sich vor der Blende
    zusammen, das neue schob sich danach auf. Mit
    ``DWMWA_TRANSITIONS_FORCEDISABLED`` erscheint und verschwindet ein Fenster
    schlagartig, sodass unter der Blende nichts mehr zu sehen ist. Betrifft nur
    die eigenen Fenster (WebView, Sperrfenster, Blende), nie systemweite
    Einstellungen. Best effort.
    """
    if not hwnd:
        return
    try:
        on = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, _DWMWA_TRANSITIONS_FORCEDISABLED,
            ctypes.byref(on), ctypes.sizeof(on))
    except Exception:
        pass


def enable_double_buffer(control) -> None:
    """Doppelpufferung einschalten (geschuetzte Eigenschaft, daher Reflection).

    Ohne sie flackert ein selbst gezeichneter Hintergrund (Grundton + Raster)
    bei jeder Groessenaenderung sichtbar.
    """
    try:
        prop = clr.GetClrType(Control).GetProperty(
            "DoubleBuffered", BindingFlags.Instance | BindingFlags.NonPublic)
        prop.SetValue(control, True, None)
    except Exception:
        pass


def dpi_scale(hwnd: int) -> float:
    """Skalierungsfaktor des Fensters (96 dpi = 1.0).

    Der Prozess ist Per-Monitor-DPI-aware (main.py), WinForms rechnet aber in
    physischen Pixeln. Layoutmasse werden deshalb hier skaliert; Schriftgroessen
    stehen in Punkt und skalieren von selbst.
    """
    try:
        return max(1.0, float(ctypes.windll.user32.GetDpiForWindow(hwnd)) / 96.0)
    except Exception:
        return 1.0


def style_form(form, icon_path: str | None = None) -> None:
    """Grundausstattung eines nativen Fensters im App-Design."""
    form.BackColor = col(BG)
    form.ForeColor = col(TEXT)
    form.Font = font(9.5)
    enable_double_buffer(form)
    if icon_path:
        try:
            form.Icon = Icon(icon_path)
        except Exception:
            pass

    def on_handle(_s, _a):
        # Beides NOCH BEVOR das Fenster sichtbar wird (HandleCreated laeuft vor
        # dem ersten Anzeigen): sonst blitzt eine Windows-helle Titelleiste auf
        # und Windows spielt seine Oeffnen-Animation (N11.25).
        try:
            hwnd = int(form.Handle.ToInt64())
        except Exception:
            return
        apply_titlebar_theme(hwnd, True)
        disable_window_transitions(hwnd)

    form.HandleCreated += EventHandler(on_handle)


# ---------------------------------------------------------------------------
# Zeichen-Bausteine
# ---------------------------------------------------------------------------
def abs_pos(ctl) -> tuple[int, int]:
    """Position eines Steuerelements im Formular-Koordinatensystem.

    Wird gebraucht, damit ein Steuerelement das Hintergrundraster genau dort
    fortsetzt, wo das Formular es hat (sonst entstehen Raster-Bruchkanten).
    """
    x, y = 0, 0
    cur = ctl
    # Nach oben laufen, bis ein Element ohne Elternteil kommt (das Formular);
    # dessen eigene Left/Top sind Bildschirmkoordinaten und zaehlen nicht mit.
    while cur is not None and cur.Parent is not None:
        x += cur.Left
        y += cur.Top
        cur = cur.Parent
    return x, y


def paint_backdrop(g, off_x: int, off_y: int, w: int, h: int,
                   strip: int = 0) -> None:
    """App-Hintergrund: Grundton plus 28px-Raster (style.css .lock-screen).

    ``off_x``/``off_y`` ist die Lage der Flaeche im Formular, damit das Raster
    ueber Steuerelementgrenzen hinweg durchlaeuft. ``strip`` malt oben den
    Titelleisten-Verlaengerungsstreifen (style.css: .app border-top).
    """
    g.SmoothingMode = _SMOOTH_NONE
    brush = SolidBrush(col(BG))
    try:
        g.FillRectangle(brush, 0, 0, w, h)
    finally:
        brush.Dispose()
    step = grid_step()
    pen = Pen(col(BG_GRID), 1.0)
    try:
        x = -(off_x % step)
        while x < w:
            if x >= 0:
                g.DrawLine(pen, x, 0, x, h)
            x += step
        y = -(off_y % step)
        while y < h:
            if y >= 0:
                g.DrawLine(pen, 0, y, w, y)
            y += step
    finally:
        pen.Dispose()
    if strip > 0 and off_y == 0:
        sb = SolidBrush(col(SURFACE))
        try:
            g.FillRectangle(sb, 0, 0, w, int(round(strip * _ui_scale)))
        finally:
            sb.Dispose()


def rounded_path(x: float, y: float, w: float, h: float, r: float) -> GraphicsPath:
    r = max(0.0, min(r, min(w, h) / 2.0))
    p = GraphicsPath()
    d = r * 2.0
    if d <= 0:
        p.AddRectangle(RectangleF(x, y, w, h))
        return p
    p.AddArc(x, y, d, d, 180.0, 90.0)
    p.AddArc(x + w - d, y, d, d, 270.0, 90.0)
    p.AddArc(x + w - d, y + h - d, d, d, 0.0, 90.0)
    p.AddArc(x, y + h - d, d, d, 90.0, 90.0)
    p.CloseFigure()
    return p


def fill_pill(g, x: float, y: float, w: float, h: float, r: float,
              fill: str | None, border: str | None = None,
              border_w: float = 1.0) -> None:
    g.SmoothingMode = SmoothingMode.AntiAlias
    path = rounded_path(x, y, w, h, r)
    try:
        if fill:
            brush = SolidBrush(col(fill))
            try:
                g.FillPath(brush, path)
            finally:
                brush.Dispose()
        if border:
            pen = Pen(col(border), float(border_w))
            try:
                g.DrawPath(pen, path)
            finally:
                pen.Dispose()
    finally:
        path.Dispose()


def stroke_pill(g, w: float, h: float, fill: str | None, border: str | None,
                border_w: float = 1.0, inset: float = 0.0) -> None:
    """Eine Pille, die eine Steuerelementflaeche ``w`` x ``h`` sauber ausfuellt.

    Der Pfad liegt um die **halbe Strichstaerke** nach innen, damit der Strich
    genau auf ganzen Pixeln sitzt und nicht halb ueber den Rand haengt; der
    Radius ist immer die halbe Hoehe, die Form ist also eine echte Kapsel.
    Zusammen mit ganzzahligen Strichstaerken (``line_w``) hat der Rand damit
    auf den Geraden und in den Rundungen dasselbe Gewicht.

    ``inset`` rueckt die ganze Pille zusaetzlich ein (Knopf im Druckzustand).
    """
    o = border_w / 2.0 + inset
    ww, hh = w - 2 * o, h - 2 * o
    fill_pill(g, o, o, ww, hh, hh / 2.0, fill, border, border_w)


_CENTER = None


def _center_format() -> StringFormat:
    global _CENTER
    if _CENTER is None:
        f = StringFormat()
        f.Alignment = StringAlignment.Center
        f.LineAlignment = StringAlignment.Center
        _CENTER = f
    return _CENTER


def draw_text(g, text: str, fnt: Font, color: str,
              x: float, y: float, w: float, h: float) -> None:
    g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit
    brush = SolidBrush(col(color))
    try:
        g.DrawString(text, fnt, brush, RectangleF(x, y, w, h), _center_format())
    finally:
        brush.Dispose()


def draw_glow(g, cx: float, cy: float, radius: float, color: str,
              alpha: int = 70) -> None:
    """Weicher Schein hinter einer Flaeche (Ersatz fuer den CSS box-shadow)."""
    try:
        from System import Array
        from System.Drawing.Drawing2D import PathGradientBrush
        path = GraphicsPath()
        try:
            path.AddEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
            brush = PathGradientBrush(path)
            try:
                r, gg, b = rgb(color)
                brush.CenterColor = Color.FromArgb(alpha, r, gg, b)
                brush.SurroundColors = Array[Color]([Color.FromArgb(0, r, gg, b)])
                g.SmoothingMode = SmoothingMode.AntiAlias
                g.FillPath(brush, path)
            finally:
                brush.Dispose()
        finally:
            path.Dispose()
    except Exception:
        pass


def draw_lock_glyph(g, cx: float, cy: float, size: float, color: str,
                    open_t: float = 0.0) -> None:
    """Das Schloss aus Icons.Lock (app.js), 24er-Raster, Strichstaerke 1.7.

    ``open_t`` (0..1) klappt den Buegel auf: er dreht sich um sein rechtes
    Standbein nach oben/rechts weg und hebt sich dabei leicht an, wie bei einem
    echten Vorhaengeschloss. 0 ist das geschlossene Zeichen (Vorgabe), 1 das
    offene. Der Koerper und das Schluesselloch bleiben stehen.
    """
    s = size / 24.0
    g.SmoothingMode = SmoothingMode.AntiAlias
    pen = Pen(col(color), max(1.2, 1.7 * s))
    pen.StartCap = LineCap.Round
    pen.EndCap = LineCap.Round

    def px(u):   # Einheit -> Bildschirm
        return cx - size / 2.0 + u * s

    def py(u):
        return cy - size / 2.0 + u * s

    try:
        # Koerper: rect(5,11,14,9) mit Radius 2.2
        body = rounded_path(px(5), py(11), 14 * s, 9 * s, 2.2 * s)
        try:
            g.DrawPath(pen, body)
        finally:
            body.Dispose()
        # Buegel: M8 11 V8 a4 4 0 0 1 8 0 v3
        shackle = GraphicsPath()
        try:
            shackle.AddLine(px(8), py(11), px(8), py(8))
            shackle.AddArc(px(8), py(4), 8 * s, 8 * s, 180.0, 180.0)
            shackle.AddLine(px(16), py(8), px(16), py(11))
            saved = None
            if open_t > 0.0:
                # Drehpunkt ist der Fuss des rechten Standbeins (16, 11); GDI+
                # dreht bei positiven Winkeln im Uhrzeigersinn (y zeigt nach
                # unten), der Buegel schwingt also nach oben rechts weg.
                saved = g.Save()
                g.TranslateTransform(float(px(16)), float(py(11) - 1.8 * s * open_t))
                g.RotateTransform(34.0 * float(open_t))
                g.TranslateTransform(float(-px(16)), float(-py(11)))
            try:
                g.DrawPath(pen, shackle)
            finally:
                if saved is not None:
                    g.Restore(saved)
        finally:
            shackle.Dispose()
        # Schluesselloch: Punkt bei (12, 15.5)
        dot = SolidBrush(col(color))
        try:
            rr = 1.05 * s
            g.FillEllipse(dot, px(12) - rr, py(15.5) - rr, rr * 2, rr * 2)
        finally:
            dot.Dispose()
    finally:
        pen.Dispose()


def draw_ring_progress(g, x: float, y: float, w: float, h: float, t: float,
                       color: str, width: float) -> None:
    """Einen Kreisbogen von oben im Uhrzeigersinn ziehen (Fortschritt 0..1).

    Gedacht fuer den **runden** Icon-Knopf: der Bogen liegt genau auf dessen
    Pillenrand (bei w == h ist die Pille ein Kreis) und faerbt ihn Stueck fuer
    Stueck ein. GDI+ zaehlt Winkel im Uhrzeigersinn (y zeigt nach unten), -90
    Grad ist also oben.
    """
    t = max(0.0, min(1.0, float(t)))
    if t <= 0.0:
        return
    g.SmoothingMode = SmoothingMode.AntiAlias
    pen = Pen(col(color), float(width))
    pen.StartCap = LineCap.Round
    pen.EndCap = LineCap.Round
    try:
        g.DrawArc(pen, float(x), float(y), float(w), float(h), -90.0, 360.0 * t)
    finally:
        pen.Dispose()


def draw_power_glyph(g, cx: float, cy: float, size: float, color: str) -> None:
    """Ein-/Aus-Zeichen (Kreis mit Luecke oben plus Strich), wie .lock-off."""
    g.SmoothingMode = SmoothingMode.AntiAlias
    r = size / 2.0
    pen = Pen(col(color), max(1.4, size * 0.11))
    pen.StartCap = LineCap.Round
    pen.EndCap = LineCap.Round
    try:
        g.DrawArc(pen, cx - r, cy - r, r * 2, r * 2, -65.0, 310.0)
        g.DrawLine(pen, cx, cy - r * 1.15, cx, cy - r * 0.05)
    finally:
        pen.Dispose()


# ---------------------------------------------------------------------------
# Bausteine: Pillen-Knopf, Pillen-Eingabe, Textlink
# ---------------------------------------------------------------------------
class PillButton:
    """Knopf in App-Optik: Pille (Radius = halbe Hoehe), eigene Zeichnung.

    ``kind``: ``primary`` (Akzentfuellung), ``ghost`` (Flaeche + Rand),
    ``danger`` (Warnfarbe), ``icon`` (runder Geisterknopf mit Zeichen).

    ``progress`` (nur ``icon``, N11.28): ``None`` = Ruhezustand, ``0..1`` faehrt
    den Rand des Knopfes in der Akzentfarbe herum (von oben im Uhrzeigersinn);
    bei ``1.0`` ist der Kreis zu und das Zeichen wird farbig. Der Off-Knopf des
    Sperrschirms fuellt den Ring, solange der Zeiger darauf steht, und nimmt den
    Klick erst beim vollen Kreis an. Wer den Wert setzt, treibt ihn auch weiter
    (der Knopf hat keine eigene Uhr) und legt damit auch fest, was der volle
    Kreis bedeutet.
    """

    def __init__(self, text: str = "", kind: str = "primary",
                 size: tuple[int, int] = (340, 48), font_size: float = 11.0,
                 bold: bool = True, glyph: str | None = None,
                 backdrop: str | None = None):
        self.kind = kind
        self.text = text
        self.glyph = glyph          # None | 'power' | 'lock'
        self.backdrop = backdrop    # None = App-Raster, sonst Fuellfarbe
        self.progress = None        # None | 0..1 (Ringlauf, siehe set_progress)
        self._hover = False
        self._down = False
        self._font = font(font_size, bold)

        b = Button()
        b.Text = ""                 # Beschriftung malen wir selbst
        b.FlatStyle = FlatStyle.Flat
        b.FlatAppearance.BorderSize = 0
        b.BackColor = col(BG if backdrop is None else backdrop)
        b.FlatAppearance.MouseOverBackColor = b.BackColor
        b.FlatAppearance.MouseDownBackColor = b.BackColor
        b.ForeColor = col(TEXT)
        b.Size = Size(int(size[0]), int(size[1]))
        b.Cursor = Cursors.Hand
        b.TabStop = False
        b.Paint += PaintEventHandler(self._on_paint)
        b.MouseEnter += EventHandler(self._enter)
        b.MouseLeave += EventHandler(self._leave)
        b.MouseDown += MouseEventHandler(self._mdown)
        b.MouseUp += MouseEventHandler(self._mup)
        self.control = b

    # -- Zustand ---------------------------------------------------------
    def _enter(self, _s, _a):
        self._hover = True
        self.control.Invalidate()

    def _leave(self, _s, _a):
        self._hover = False
        self._down = False
        self.control.Invalidate()

    def _mdown(self, _s, _a):
        self._down = True
        self.control.Invalidate()

    def _mup(self, _s, _a):
        self._down = False
        self.control.Invalidate()

    def set_text(self, text: str) -> None:
        self.text = text
        self.control.Invalidate()

    def set_progress(self, value: float | None) -> None:
        """Ringlauf setzen (``None`` = aus, sonst 0..1) und neu zeichnen."""
        self.progress = None if value is None else max(0.0, min(1.0, float(value)))
        self.control.Invalidate()

    def set_enabled(self, flag: bool) -> None:
        self.control.Enabled = bool(flag)
        self.control.Cursor = Cursors.Hand if flag else Cursors.Default
        self.control.Invalidate()

    # -- Zeichnung -------------------------------------------------------
    def _colors(self) -> tuple[str | None, str | None, str]:
        on = self.control.Enabled
        if self.kind == "primary":
            fill = ACCENT
            if self._hover:
                fill = ACCENT_HOVER
            if self._down:
                fill = ACCENT_DOWN
            if not on:
                fill = mix(ACCENT, SURFACE, 0.35)
            return fill, None, (ACCENT_INK if on else mix(ACCENT_INK, SURFACE, 0.55))
        if self.kind == "danger":
            fill = DANGER_WASH if not self._down else mix(DANGER, SURFACE, 0.30)
            if self._hover:
                fill = mix(DANGER, SURFACE, 0.28)
            return fill, DANGER_LINE, (DANGER if on else mix(DANGER, SURFACE, 0.5))
        if self.kind == "icon":
            # Bewusst OHNE eigenen Hover-Zustand (N11.28, Nutzerwunsch): der
            # Knopf springt beim Darueberfahren nicht mehr in die Warnfarbe.
            # Die Hover-Rueckmeldung ist der Ringlauf (siehe _on_paint), ein
            # zusaetzlicher Farbsprung wuerde sie nur uebertoenen.
            return mix(SURFACE, BG, 0.70), BORDER, TEXT_FAINT
        # ghost
        fill = SURFACE_2 if not self._hover else SURFACE_3
        return fill, BORDER, (TEXT if on else TEXT_FAINT)

    def _on_paint(self, _s, e):
        g = e.Graphics
        b = self.control
        w, h = b.Width, b.Height
        if self.backdrop is None:
            ax, ay = abs_pos(b)
            paint_backdrop(g, ax, ay, w, h)
        else:
            brush = SolidBrush(col(self.backdrop))
            try:
                g.FillRectangle(brush, 0, 0, w, h)
            finally:
                brush.Dispose()
        fill, border, fg = self._colors()
        # Ringlauf (N11.28): waehrend er faehrt, waermt sich nur die Flaeche
        # leicht an. Das Zeichen bleibt gedaempft und wird erst farbig, wenn der
        # Kreis **zu** ist, denn genau dann nimmt der Knopf den Klick an: das
        # farbige Zeichen ist die Ansage dafuer, nicht blosse Zierde.
        t = self.progress
        armed = t is not None and t >= 1.0
        if t is not None:
            ease = 1.0 - (1.0 - t) ** 2
            fill = mix(ACCENT_WASH, fill, 0.55 * ease)
            if armed:
                fill, fg = ACCENT_WASH, ACCENT
        # Beim Druecken minimal einruecken (CSS: .btn:active transform scale(.98)).
        inset = 1.0 if self._down else 0.0
        stroke_pill(g, w, h, fill, border, line_w(1.0), inset)
        if t is not None:
            # Der Bogen liegt auf dem Rand des Knopfes und ist so weit nach
            # innen gerueckt, dass ihn die eigene Strichstaerke nicht am
            # Steuerelementrand abschneidet.
            arc_w = max(1.8, min(w, h) * 0.06)
            pad = arc_w / 2.0 + inset
            draw_ring_progress(g, pad, pad, w - 2 * pad, h - 2 * pad, t,
                               ACCENT, arc_w)
        if self.glyph == "power":
            draw_power_glyph(g, w / 2.0, h / 2.0, min(w, h) * 0.44, fg)
        elif self.text:
            draw_text(g, self.text, self._font, fg, 0, 0, w, h)


class PillInput:
    """Eingabepille im App-Design: runder Rahmen, Text linksbuendig.

    Aussen ein selbst gezeichnetes Panel (die Pille), innen eine randlose
    TextBox in derselben Fuellfarbe; WinForms kann Eingabefelder nicht selbst
    runden.
    """

    def __init__(self, size: tuple[int, int] = (380, 52), password: bool = False,
                 cue: str | None = None, font_size: float = 12.0,
                 scale: float = 1.0):
        self._focus = False
        self.cue = cue

        panel = Panel()
        panel.Size = Size(int(size[0]), int(size[1]))
        panel.BackColor = col(BG)
        enable_double_buffer(panel)
        panel.Paint += PaintEventHandler(self._on_paint)

        box = TextBox()
        box.BorderStyle = _BORDER_NONE
        box.BackColor = col(SURFACE)
        box.ForeColor = col(TEXT)
        box.Font = font(font_size)
        # Links, nicht mittig (Nutzerwunsch 2026-08-10): geschrieben wird am
        # linken Rand der Pille, und der Platzhalter steht an derselben Stelle
        # wie das erste Zeichen (das Cue-Banner uebernimmt die Ausrichtung des
        # Feldes), also springt beim Tippen nichts.
        box.TextAlign = HorizontalAlignment.Left
        if password:
            box.UseSystemPasswordChar = True
        pad = int(round(22 * scale))
        box.Location = Point(pad, max(4, (panel.Height - box.Height) // 2))
        box.Width = panel.Width - 2 * pad
        panel.Controls.Add(box)

        box.GotFocus += EventHandler(self._got)
        box.LostFocus += EventHandler(self._lost)

        self.control = panel
        self.box = box
        if cue:
            box.HandleCreated += EventHandler(lambda _s, _a: self._apply_cue())

    def _apply_cue(self) -> None:
        # EM_SETCUEBANNER: Platzhaltertext direkt im Edit-Steuerelement (bleibt
        # auch bei Fokus stehen, wParam=1), spart eine eigene Zeichenebene.
        try:
            ctypes.windll.user32.SendMessageW(
                int(self.box.Handle.ToInt64()), 0x1501, 1,
                ctypes.c_wchar_p(self.cue))
        except Exception:
            pass

    def _got(self, _s, _a):
        self._focus = True
        self.control.Invalidate()

    def _lost(self, _s, _a):
        self._focus = False
        self.control.Invalidate()

    def layout_box(self, right_reserve: int = 0, scale: float = 1.0) -> None:
        """Innenmasse neu setzen (z.B. wenn rechts ein Knopf in der Pille sitzt)."""
        pad = int(round(22 * scale))
        self.box.Location = Point(pad, max(2, (self.control.Height - self.box.Height) // 2))
        self.box.Width = max(40, self.control.Width - pad - max(pad, right_reserve))

    def _on_paint(self, _s, e):
        g = e.Graphics
        p = self.control
        ax, ay = abs_pos(p)
        paint_backdrop(g, ax, ay, p.Width, p.Height)
        border = ACCENT if self._focus else ACCENT_LINE
        # Der Fokusrand war frueher 1.4 px breit und lag auf einer halben
        # Pixelgrenze. GDI+ verteilt so eine Linie ueber zwei Pixelreihen: auf
        # den Geraden blieb sie kraeftig, in den Rundungen wurde sie blass und
        # breit, die Enden der Pille sahen ausgefranst aus (und das Feld hat
        # auf dem Sperrschirm **immer** den Fokus, man sah also immer den
        # schlechteren Fall). Ganze Pixel, halber Versatz, gleiches Gewicht
        # rundherum (N11.27).
        stroke_pill(g, p.Width, p.Height, SURFACE, border,
                    line_w(2.0 if self._focus else 1.0))


class TextLink:
    """Unauffaelliger Textlink (wie ``a`` in der App): dezent, Akzent beim Hover."""

    def __init__(self, text: str, font_size: float = 9.5, on_click=None,
                 width: int = 260, height: int = 24):
        self.text = text
        self._hover = False
        self._font = font(font_size)
        lb = Label()
        lb.AutoSize = False
        lb.Size = Size(int(width), int(height))
        lb.BackColor = col(BG)
        lb.Cursor = Cursors.Hand
        lb.Paint += PaintEventHandler(self._on_paint)
        lb.MouseEnter += EventHandler(self._enter)
        lb.MouseLeave += EventHandler(self._leave)
        if on_click is not None:
            lb.Click += EventHandler(lambda _s, _a: on_click())
        self.control = lb

    def _enter(self, _s, _a):
        self._hover = True
        self.control.Invalidate()

    def _leave(self, _s, _a):
        self._hover = False
        self.control.Invalidate()

    def set_text(self, text: str) -> None:
        self.text = text
        self.control.Invalidate()

    def _on_paint(self, _s, e):
        g = e.Graphics
        lb = self.control
        ax, ay = abs_pos(lb)
        paint_backdrop(g, ax, ay, lb.Width, lb.Height)
        color = ACCENT if self._hover else TEXT_FAINT
        draw_text(g, self.text, self._font, color, 0, 0, lb.Width, lb.Height)
        # Unterstrich in Textbreite (dezent, wie ein Link in der App)
        try:
            size = g.MeasureString(self.text, self._font)
            pen = Pen(col(color), 1.0)
            y = lb.Height / 2.0 + size.Height / 2.0 - 1
            x0 = (lb.Width - size.Width) / 2.0 + 1
            try:
                g.DrawLine(pen, x0, y, x0 + size.Width - 2, y)
            finally:
                pen.Dispose()
        except Exception:
            pass


class AppLabel:
    """Selbst gezeichnete Textzeile (mittig) auf dem App-Hintergrund."""

    def __init__(self, text: str = "", font_size: float = 10.0, bold: bool = False,
                 color: str = TEXT, display: bool = False,
                 size: tuple[int, int] = (400, 26)):
        self.text = text
        self.color = color
        self._font = font(font_size, bold, display)
        lb = Label()
        lb.AutoSize = False
        lb.Size = Size(int(size[0]), int(size[1]))
        lb.BackColor = col(BG)
        lb.Paint += PaintEventHandler(self._on_paint)
        self.control = lb

    def set(self, text: str, color: str | None = None) -> None:
        self.text = text
        if color:
            self.color = color
        self.control.Invalidate()

    def _on_paint(self, _s, e):
        g = e.Graphics
        lb = self.control
        ax, ay = abs_pos(lb)
        paint_backdrop(g, ax, ay, lb.Width, lb.Height)
        if self.text:
            draw_text(g, self.text, self._font, self.color, 0, 0, lb.Width, lb.Height)


# ---------------------------------------------------------------------------
# Themed Hinweisfenster (ersetzt MessageBox)
# ---------------------------------------------------------------------------
def show_message(text: str, title: str = "NoaToDo", icon_path: str | None = None,
                 button: str = "OK", _test_after_shown=None) -> None:
    """Kleines Hinweisfenster im App-Design statt der weissen Windows-MessageBox.

    Blockiert bis zum Schliessen (wie MessageBox). Wird u.a. von der
    Zweitinstanz-Meldung (G19) benutzt. ``_test_after_shown`` ist dieselbe reine
    Test-Naht wie im Sperrfenster (production ruft ohne sie).
    """
    try:
        Application.EnableVisualStyles()
        Application.SetCompatibleTextRenderingDefault(False)
    except Exception:
        # Beides ist nur beim allerersten Fenster im Prozess erlaubt.
        pass

    form = Form()
    form.Text = title
    form.FormBorderStyle = FormBorderStyle.FixedDialog
    form.StartPosition = FormStartPosition.CenterScreen
    form.MaximizeBox = False
    form.MinimizeBox = False
    style_form(form, icon_path)
    # Hoehe waechst mit dem Text: das Hinweisfenster traegt seit Phase 9 auch
    # laengere Meldungen (fehlende WebView2-Runtime, Integritaetsfehler), und
    # ein fester Kasten wuerde sie abschneiden. Kurze Meldungen (G19) behalten
    # exakt die alten Masse.
    body_h = max(90, 22 * (text.count("\n") + 1))
    form.ClientSize = Size(460, 130 + body_h)

    body = AppLabel(text, 10.5, False, TEXT_DIM, size=(400, body_h))
    body.control.Location = Point(30, 40)

    ok = PillButton(button, "primary", (160, 44), 10.5)
    ok.control.Location = Point((form.ClientSize.Width - 160) // 2,
                                form.ClientSize.Height - 44 - 28)
    ok.control.Click += EventHandler(lambda _s, _a: form.Close())

    def on_paint(_s, e):
        paint_backdrop(e.Graphics, 0, 0, form.ClientSize.Width,
                       form.ClientSize.Height, TITLE_STRIP)

    form.Paint += PaintEventHandler(on_paint)
    form.Controls.Add(body.control)
    form.Controls.Add(ok.control)

    def on_key(_s, a):
        if a.KeyCode == Keys.Escape or a.KeyCode == Keys.Enter:
            form.Close()

    form.KeyPreview = True
    form.KeyDown += KeyEventHandler(on_key)

    def on_shown(_s, _a):
        apply_titlebar_theme(int(form.Handle.ToInt64()), True)
        if _test_after_shown is not None:
            _test_after_shown(form)

    form.Shown += EventHandler(on_shown)

    Application.Run(form)
    try:
        form.Dispose()
    except Exception:
        pass
