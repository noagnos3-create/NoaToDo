// NoaToDo, Frontend-Logik (Bauplan Phase 6).
// Vanilla-Portierung der React-Komponenten aus "NoaToDo UI Konzept.html".
// Das Backend (pywebview.api.*) ist die Wahrheitsquelle; state ist nur Cache.
'use strict';

// ===========================================================================
// Icons, 1:1 aus dem Konzept (Anhang 2). 24er-Grid, Strichstärke 1.7.
// ===========================================================================
function _svg(children, extra) {
  const base = {
    viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
    'stroke-width': '1.7', 'stroke-linecap': 'round', 'stroke-linejoin': 'round',
  };
  Object.assign(base, extra || {});
  const attrs = Object.keys(base).map((k) => `${k}="${base[k]}"`).join(' ');
  return `<svg ${attrs}>${children}</svg>`;
}
const _p = (d) => `<path d="${d}"/>`;
const _c = (cx, cy, r) => `<circle cx="${cx}" cy="${cy}" r="${r}"/>`;
const _l = (x1, y1, x2, y2) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
const _r = (x, y, w, h, rx) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}"/>`;

const Icons = {
  Menu: _svg(_l(3, 6, 21, 6) + _l(3, 12, 21, 12) + _l(3, 18, 21, 18)),
  Close: _svg(_l(6, 6, 18, 18) + _l(18, 6, 6, 18)),
  Shield: _svg(_p('M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z') + _p('M9 12l2 2 4-4')),
  Plus: _svg(_l(12, 5, 12, 19) + _l(5, 12, 19, 12)),
  Check: _svg(_p('M5 12l5 5L19 6')),
  Gear: _svg(_c(12, 12, 3) + _p('M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z')),
  Chevron: _svg(_p('M6 9l6 6 6-6')),
  ChevRight: _svg(_p('M9 6l6 6-6 6')),
  ChevLeft: _svg(_p('M15 6l-6 6 6 6')),
  Grip: _svg(_c(9, 6, 1) + _c(15, 6, 1) + _c(9, 12, 1) + _c(15, 12, 1) + _c(9, 18, 1) + _c(15, 18, 1), { fill: 'currentColor', stroke: 'none' }),
  Plane: _svg(_p('M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z')),
  Expand: _svg(_p('M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5')),
  Mini: _svg(_p('M21 9V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h4') + _r(12, 13, 10, 7, 2)),
  Maximize: _svg(_p('M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7')),
  Palette: _svg(_p('M12 3a9 9 0 1 0 0 18c1.5 0 2-1 2-2 0-.7-.5-1.2-.5-2 0-.8.7-1.5 1.5-1.5H17a4 4 0 0 0 4-4c0-4.4-4-8.5-9-8.5z') + _c(7.5, 11, 1) + _c(11, 7.5, 1) + _c(15.5, 8.5, 1), { fill: 'none' }),
  Share: _svg(_p('M12 15V3M8.5 6.5L12 3l3.5 3.5') + _p('M6 11H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-1')),
  Help: _svg(_c(12, 12, 9) + _p('M9.2 9.3a2.8 2.8 0 0 1 5.4 1c0 1.8-2.6 2-2.6 3.7') + _c(12, 17.3, 0.6), { fill: 'none' }),
  Lock: _svg(_r(5, 11, 14, 9, 2.2) + _p('M8 11V8a4 4 0 0 1 8 0v3') + _c(12, 15.5, 0.4)),
  Unlock: _svg(_r(5, 11, 14, 9, 2.2) + _p('M8 11V8a4 4 0 0 1 7.5-2')),
  Alert: _svg(_p('M12 3.5L21.5 20H2.5L12 3.5z') + _l(12, 10, 12, 14) + _c(12, 17, 0.5), { fill: 'none' }),
  Copy: _svg(_r(9, 9, 11, 11, 2.5) + _p('M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1')),
  Pencil: _svg(_p('M4 20h4l10-10-4-4L4 16v4z') + _l(13.5, 6.5, 17.5, 10.5)),
  Trash: _svg(_p('M4 7h16M10 7V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v2M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13')),
  Diag: _svg(_p('M3 12h3l2 6 4-14 2.5 8H21')),
  Globe: _svg(_c(12, 12, 9) + _p('M3 12h18M12 3c2.6 2.4 4 5.6 4 9s-1.4 6.6-4 9c-2.6-2.4-4-5.6-4-9s1.4-6.6 4-9z')),
  Note: _svg(_p('M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6z') + _p('M14 3v6h6')),
  Sun: _svg(_c(12, 12, 4) + _p('M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19')),
  Moon: _svg(_p('M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z')),
  User: _svg(_c(12, 8, 3.4) + _p('M5 20a7 7 0 0 1 14 0')),
  Logout: _svg(_p('M14 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h7a2 2 0 0 0 2-2v-2') + _p('M9 12h12M18 9l3 3-3 3')),
  Pin: _svg(_p('M9 3h6l-1 7 3 3v2H7v-2l3-3-1-7z') + _l(12, 15, 12, 21)),
  Download: _svg(_p('M12 3v12M8 11l4 4 4-4') + _p('M4 19h16')),
  Power: _svg(_l(12, 3, 12, 11) + _p('M7.05 6.3a8 8 0 1 0 9.9 0')),
};

// WLAN-Symbol mit Signalstaerke (wie in den Windows-Schnelleinstellungen):
// ein Punkt plus bis zu drei konzentrische Boegen. "level" 0..3 bestimmt, wie
// viele Boege voll gezeichnet werden; die uebrigen bleiben blass (Resthuelle),
// damit das Symbol seine Form behaelt. 0 = nur Punkt (kein Signal).
function wifiSvg(level) {
  const lv = Math.max(0, Math.min(3, level | 0));
  const arcs = [
    'M9.2 16.1a4 4 0 0 1 5.6 0',       // innerer Bogen
    'M6.7 13.7a7.5 7.5 0 0 1 10.6 0',  // mittlerer Bogen
    'M4.3 11.2a11 11 0 0 1 15.4 0',    // aeusserer Bogen
  ];
  let inner = '<circle cx="12" cy="18.6" r="1.05" fill="currentColor" stroke="none"/>';
  arcs.forEach((d, i) => {
    const on = (i + 1) <= lv;
    inner += `<path d="${d}" opacity="${on ? '1' : '0.22'}"/>`;
  });
  return _svg(inner, { fill: 'none' });
}

const ACCENTS = ['#d97757', '#c75d3a', '#5a9d6b', '#4a86c5', '#d4a23c', '#a66a9c'];

// ===========================================================================
// Zustand (nur Cache; Wahrheit bleibt das Backend)
// ===========================================================================
let state = {
  lists: [], activeId: null, settings: {}, online: true, locked: false,
  menu: null,        // 'profile'
  modal: null,       // 'status' | 'rename' | 'delete' | 'shortcuts' | 'settings'
  ctxList: null,     // Rechtsklick-Kontextmenue einer Liste: { id, x, y } | null
  renamingId: null,  // Liste, die gerade inline (Pille in der Sidebar) umbenannt wird
  confirmDeleteId: null, // Liste, fuer die die Inline-Loeschbestaetigung in der Sidebar offen ist
  listEditDock: false, // true: Inline-Umbenennen/Loeschen wird im unteren Dock gezeigt (Rechtsklick auf den grossen Namen) statt in der Sidebar
  focus: false,
  mini: false,       // kompakter Mini-Fenster-Modus (oben rechts angeheftet)
  railPinned: false, // Tool-Rail fixiert (per Chevron-Griff), bleibt sichtbar
  sidebarWidth: 256, // Sidebar-Breite in px, per Drag veraenderbar
  adding: false,     // Inline-"New list"-Eingabe sichtbar
  addingTask: false, // Inline-"New task"-Eingabe im unteren Dock sichtbar
  doneOpen: false,   // "Completed"-Sektion eingeklappt?
  editingId: null,   // Aufgabe, die gerade inline bearbeitet wird (Doppelklick)
  selectedId: null,  // per Klick ausgewaehlte Aufgabe (Ziel fuer Copy/Edit der Rail)
  panic: null,       // Panik-Flow (N10): { armed:bool, stage:'panel'|'wiping'|'done'|'killing', killArmed:bool } | null
};

const root = document.getElementById('root');
const api = () => window.pywebview.api;

// WLAN-/Flugzeug-Knopf: aktuelle WLAN-Signalstaerke (0..3) und ein einmaliges
// Flag, das beim Umschalten online<->offline die Einflug-Animation ausloest.
// Beides bewusst ausserhalb von "state": rein praesentationsbezogen, kein
// Bestandteil der Backend-Wahrheit.
let wifiLevel = 3;
let netAnim = false;
// HTML-Escaping fuer JEDE Einsetzung von (potenziell) Fremddaten in innerHTML.
// Maskiert & < > " ', deckt damit Text-, doppelt- UND einfach-gequotete
// Attribut-Kontexte ab. Das fehlende ' war eine latente Luecke: sobald ein
// Attribut mit einfachen Anfuehrungszeichen Fremddaten enthaelt, koennte ein
// Wert sonst ausbrechen. Zusammen mit der CSP (index.html) ist das
// Defense-in-Depth.
const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
// Kein Auto-Fallback auf die erste Liste: ist keine Liste ausgewaehlt
// (state.activeId === null), bleibt die Arbeitsflaeche bewusst leer. So startet
// die App immer als leere Flaeche und oeffnet erst eine Liste, wenn man eine
// anklickt.
const activeList = () => state.lists.find((l) => l.id === state.activeId) || null;

// ===========================================================================
// Render-Funktionen (1:1 zu den Konzept-Komponenten)
// ===========================================================================
function renderHeader() {
  return `<button class="sidebar-toggle" data-act="toggle-sidebar" title="Toggle sidebar">${Icons.Plus}</button>`;
}

function sidebarVisible() {
  return (state.settings.sidebar !== 'closed') && !state.focus;
}

// Inline-Pille zum Umbenennen einer Liste (statt grossem Modal). Erscheint an
// der Stelle des Listeneintrags, gleiche Optik wie die "New task"-Pille: kleines
// Label oben, Eingabefeld, X zum Abbrechen. Enter speichert, Esc/X bricht ab.
function renderRenamePill(l) {
  const I = Icons;
  return `
    <div class="list-inline" data-keep data-id="${esc(l.id)}">
      <span class="list-inline-label tag">New name</span>
      <div class="list-pill">
        <input id="rename-list-input" value="${esc(l.name)}" placeholder="List name…" />
        <button class="pill-x" data-act="cancel-rename-list" title="Cancel">${I.Close}</button>
      </div>
    </div>`;
}

// Inline-Bestaetigung zum Loeschen (lokal, kein grosses Fenster). Zeigt den
// Namen, einen roten Lösch-Knopf und ein X zum Abbrechen.
function renderDeletePill(l) {
  const I = Icons;
  return `
    <div class="list-inline" data-keep data-id="${esc(l.id)}">
      <span class="list-inline-label tag danger-tag" title="${esc(l.name)}">Delete ${esc(l.name)}?</span>
      <div class="list-pill confirm">
        <button class="confirm-del" data-act="do-delete-list" title="Delete list">${I.Trash}</button>
        <button class="pill-x" data-act="cancel-delete-list" title="Cancel">${I.Close}</button>
      </div>
    </div>`;
}

function renderSidebar() {
  const I = Icons;
  const items = state.lists.map((l) => {
    // Wird gerade ueber das untere Dock umbenannt/geloescht, bleibt der
    // Sidebar-Eintrag normal (sonst doppelte Pille mit doppelter Input-id).
    if (!state.listEditDock && state.renamingId === l.id) return renderRenamePill(l);
    if (!state.listEditDock && state.confirmDeleteId === l.id) return renderDeletePill(l);
    const count = l.open.length;
    const cls = 'list-item' + (l.id === state.activeId ? ' active' : '') + (count === 0 ? ' zero' : '');
    return `
      <button class="${cls}" data-act="select-list" data-id="${esc(l.id)}">
        <span class="li-dot"></span>
        <span class="li-name">${esc(l.name)}</span>
        <span class="li-count">${count}</span>
      </button>`;
  }).join('');

  const foot = state.adding
    ? `<div class="new-list-input"><input id="new-list-input" placeholder="List name…" /></div>`
    : `<button class="new-list-btn" data-act="new-list-show">${I.Plus} New list</button>`;

  return `
    <aside class="sidebar">
      <div class="sidebar-inner">
        <div class="side-label tag"><span>Lists</span><span class="line"></span></div>
        <div class="list-scroll">${items}</div>
        <div class="side-foot">
          ${foot}
          <button class="settings-btn" data-act="settings">${I.Gear} Settings</button>
        </div>
      </div>
      <div class="sidebar-resize-handle" id="sidebar-resize-handle"></div>
    </aside>`;
}

function renderTask(t) {
  const I = Icons;
  // Inline-Bearbeitung (Doppelklick): Text direkt in der Karte aendern (eine
  // Aufgabe ist nur noch text + done, N11.1.3).
  // Enter speichert (edit_task), Esc bricht ab, Klick daneben speichert.
  if (state.editingId === t.id) {
    return `
    <div class="task editing${t.done ? ' done' : ''}" data-task-id="${esc(t.id)}">
      <button class="check" data-act="toggle-task" data-id="${esc(t.id)}" aria-label="toggle">${I.Check}</button>
      <input class="edit-text" id="edit-task-text" value="${esc(t.text)}" />
    </div>`;
  }
  const draggable = t.done ? '' : 'draggable="true"';
  // Klick auf die Karte (ausserhalb der Buttons) waehlt sie aus: die Auswahl
  // ist das Ziel fuer "Copy task" und den Bleistift in der Tool-Rail.
  const selected = state.selectedId === t.id ? ' selected' : '';
  return `
    <div class="task${t.done ? ' done' : ''}${selected}" data-task-id="${esc(t.id)}"
         data-act="select-task" data-id="${esc(t.id)}" ${draggable}>
      <button class="check" data-act="toggle-task" data-id="${esc(t.id)}" aria-label="toggle">${I.Check}</button>
      <span class="t-text">${esc(t.text)}</span>
    </div>`;
}

function renderMain() {
  const I = Icons;
  const list = activeList();
  if (!list) {
    // Keine Liste ausgewaehlt (so startet die App): wirklich leere Arbeitsflaeche,
    // kein Hinweistext.
    return `<main class="main"><div class="main-inner"></div></main>`;
  }
  const openSection = list.open.length === 0
    ? `<div class="empty-note">// all clear</div>`
    : `<div class="task-list" data-tasklist="open">${list.open.map(renderTask).join('')}</div>`;

  const doneSection = list.done.length > 0 ? `
    <div class="section">
      <button class="section-head${state.doneOpen ? ' open' : ' collapsed'}" data-act="toggle-done">
        <span class="s-pill">
          <span class="s-title">Completed</span>
          <span class="s-count">${list.done.length}</span>
        </span>
      </button>
      <div class="collapse-wrap${state.doneOpen ? '' : ' closed'}">
        <div>
          <div class="task-list" style="padding-top:${state.doneOpen ? 2 : 0}px">
            ${list.done.map(renderTask).join('')}
          </div>
        </div>
      </div>
    </div>` : '';

  return `
    <main class="main">
      <div class="main-inner">
        <div class="section">
          <div class="section-head">
            <span class="s-pill">
              <span class="s-title">Open tasks</span>
            </span>
          </div>
          ${openSection}
        </div>
        ${doneSection}
        ${renderListDock(list)}
      </div>
    </main>`;
}

// Unteres, fest am Bildschirmrand verankertes Dock (scrollt NICHT mit der Liste).
// Links die Namens-Pille der Liste, daneben ein runder "+"-Knopf. Ein Klick auf
// "+" laesst rechts daneben eine zweite Pille als Eingabefeld erscheinen; der
// Listenname bleibt sichtbar. Das "+" dreht sich dabei (gleiche Animation wie
// der Sidebar-Schalter oben links) zu einem "x": ein erneuter Klick bricht ab,
// schliesst das Eingabefeld und dreht das "x" zurueck zum "+".
function renderListDock(list) {
  const I = Icons;
  // Rechtsklick auf den grossen Namen oeffnet (wie in der Sidebar) das Rename/
  // Delete-Menue; die gewaehlte Aktion erscheint dann als Inline-Pille HIER im
  // Dock (damit sie auch bei eingeklappter Sidebar sichtbar ist).
  if (state.listEditDock && (state.renamingId === list.id || state.confirmDeleteId === list.id)) {
    return renderDockEdit(list);
  }
  const adding = state.addingTask;
  const inputPill = adding ? `
        <div class="dock-input" data-keep>
          <input id="new-task-input" placeholder="New task…" />
          <button class="dock-close" data-act="dock-toggle" title="Close">${I.Close}</button>
        </div>` : '';
  return `
    <div class="list-dock">
      <div class="dock-pill" title="${esc(list.name)}">
        <span class="dock-name">${esc(list.name)}</span>
      </div>
      <div class="dock-add-wrap">
        <button class="dock-add${adding ? ' active' : ''}" data-act="dock-toggle"
          title="${adding ? 'Cancel' : 'Add task'}">${I.Plus}</button>
        ${inputPill}
      </div>
    </div>`;
}

// Inline-Umbenennen / Loeschbestaetigung im Dock (an Stelle der Namens-Pille).
// Gleiche Optik wie die Sidebar-Pillen, nur auf die Dock-Groesse angepasst; das
// kleine Label sitzt oberhalb des Namens, der "+"-Knopf entfaellt solange.
function renderDockEdit(list) {
  const I = Icons;
  if (state.renamingId === list.id) {
    return `
    <div class="list-dock">
      <div class="dock-edit" data-keep data-id="${esc(list.id)}">
        <span class="dock-edit-label tag">New name</span>
        <div class="dock-edit-pill">
          <input id="rename-dock-input" value="${esc(list.name)}" placeholder="List name…" />
          <button class="pill-x" data-act="cancel-rename-list" title="Cancel">${I.Close}</button>
        </div>
      </div>
    </div>`;
  }
  return `
    <div class="list-dock">
      <div class="dock-edit" data-keep data-id="${esc(list.id)}">
        <span class="dock-edit-label tag danger-tag" title="${esc(list.name)}">Delete ${esc(list.name)}?</span>
        <div class="dock-edit-pill confirm">
          <button class="confirm-del" data-act="do-delete-list" title="Delete list">${I.Trash}</button>
          <button class="pill-x" data-act="cancel-delete-list" title="Cancel">${I.Close}</button>
        </div>
      </div>
    </div>`;
}

// Kompaktes Mini-Fenster: nur die Kopfzeile + die offenen Aufgaben der aktiven
// Liste. Wird genutzt, wenn das Fenster oben rechts angeheftet ist (set_mini).
function renderMini() {
  const I = Icons;
  const list = activeList();
  const open = list ? list.open : [];
  const rows = open.length
    ? `<div class="task-list" data-tasklist="open">${open.map(renderTask).join('')}</div>`
    : `<div class="empty-note">// all clear</div>`;
  // Kein festes "New task"-Feld mehr: nur die Aufgaben stehen oben. Der "+"-Knopf
  // schwebt unten links und klappt (wie im Dock, gleiche Klassen -> gleiche
  // Plus-zu-X-Drehung + einschwingende Pille) die Eingabe auf. Nur bei offener
  // Liste, sonst gaebe es kein Ziel zum Hinzufuegen.
  const adding = state.addingTask;
  const inputPill = adding ? `
        <div class="dock-input" data-keep>
          <input id="new-task-input" placeholder="New task…" />
          <button class="dock-close" data-act="dock-toggle" title="Close">${I.Close}</button>
        </div>` : '';
  const addCtl = list ? `
      <div class="mini-add-wrap dock-add-wrap">
        <button class="dock-add${adding ? ' active' : ''}" data-act="dock-toggle"
          title="${adding ? 'Cancel' : 'Add task'}">${I.Plus}</button>
        ${inputPill}
      </div>` : '';
  return `
    <div class="mini">
      <div class="mini-bar">
        <span class="mini-dot"></span>
        <span class="mini-title">${esc(list ? list.name : 'NoaToDo')}</span>
        <span class="mini-count mono">${open.length}</span>
        <button class="mini-btn" data-act="tb-mini" title="Restore window">${I.Maximize}</button>
      </div>
      <div class="mini-scroll">
        ${rows}
      </div>
      ${addCtl}
    </div>`;
}

// Fokusmodus: alles weg ausser Listenname + Liste. Verlassen nur per Esc oder
// dem kleinen orangenen X unten rechts.
function renderFocus() {
  const I = Icons;
  const list = activeList();
  const exit = `<button class="focus-exit" data-act="exit-focus" title="Exit focus (Esc)">${I.Close}</button>`;
  if (!list) {
    return `<div class="focus-view"><div class="focus-inner">
      <div class="empty-note">// no lists yet</div>
    </div></div>${exit}`;
  }
  const openRows = list.open.length
    ? `<div class="task-list" data-tasklist="open">${list.open.map(renderTask).join('')}</div>`
    : `<div class="empty-note">// all clear</div>`;
  const doneRows = list.done.length ? `
    <div class="section focus-done">
      <button class="section-head${state.doneOpen ? ' open' : ' collapsed'}" data-act="toggle-done">
        <span class="s-pill">
          <span class="s-title">Completed</span>
          <span class="s-count">${list.done.length}</span>
        </span>
      </button>
      <div class="collapse-wrap${state.doneOpen ? '' : ' closed'}">
        <div>
          <div class="task-list" style="padding-top:${state.doneOpen ? 2 : 0}px">
            ${list.done.map(renderTask).join('')}
          </div>
        </div>
      </div>
    </div>` : '';
  return `
    <div class="focus-view">
      <div class="focus-inner">
        <h1 class="list-title">${esc(list.name)}</h1>
        ${openRows}
        <div class="new-task" data-act="focus-newtask">
          <span class="plus">${I.Plus}</span>
          <input id="new-task-input" placeholder="New task…" />
          <span class="kbd">↵</span>
        </div>
        ${doneRows}
      </div>
    </div>${exit}`;
}

// Subtiler Chevron-Griff am rechten Rand: pinnt die Tool-Rail.
// ">" = Auto-Hide (Standard), "<" = fixiert (bleibt sichtbar).
function renderRailPin() {
  const I = Icons;
  const title = state.railPinned ? 'Unpin toolbar' : 'Pin toolbar';
  return `<button class="rail-pin${state.railPinned ? ' pinned' : ''}" data-act="rail-pin" title="${title}">${I.ChevRight}</button>`;
}

function renderToolbar() {
  const I = Icons;
  const btn = (icon, label, hotkey, act, opt) => {
    opt = opt || {};
    const cls = 'tool-btn' + (opt.danger ? ' danger' : '') + (opt.active ? ' active' : '') + (opt.on ? ' on' : '');
    const k = hotkey ? `<span class="k">${hotkey}</span>` : '';
    return `<button class="${cls}" data-act="${act}">${icon}<span class="tip">${label}${k}</span></button>`;
  };
  return `
    <div class="toolbar">
      <div class="toolbar-rail">
        ${btn(I.Mini, 'Mini window', '', 'tb-mini')}
        ${btn(I.Expand, 'Focus mode', 'F', 'tb-focus')}
        ${btn(I.Share, 'Export', 'Ctrl+E', 'tb-export')}
        ${btn(I.Help, 'Shortcuts', '?', 'tb-help')}
        <div class="tool-sep"></div>
        ${btn(state.locked ? I.Lock : I.Unlock, 'Lock app', 'Ctrl+L', 'tb-lock')}
        ${btn(I.Alert, 'Panic', '', 'tb-emergency', { danger: true, on: !!state.panic })}
        <div class="tool-sep"></div>
        ${btn(I.Copy, 'Copy task', '', 'tb-copy')}
        ${btn(I.Pencil, state.selectedId ? 'Edit task' : 'Rename list', '', 'tb-rename')}
        ${btn(I.Trash, 'Delete task', '', 'tb-delete')}
        <div class="tool-sep"></div>
        ${btn(I.Diag, 'App status', '', 'tb-status')}
        ${renderNetBtn()}
      </div>
    </div>`;
}

// WLAN-/Flugzeug-Knopf der Tool-Rail. Online: WLAN-Symbol mit echter
// Signalstaerke. Offline: Flugzeug (Flugmodus). Beim Umschalten fliegt das neue
// Symbol von der Seite herein und purzelt dabei (CSS-Klasse net-anim, nur fuer
// genau diesen einen Render gesetzt, danach sofort wieder geloescht).
function renderNetBtn() {
  const icon = state.online ? wifiSvg(wifiLevel) : Icons.Plane;
  const label = state.online ? 'Go offline' : 'Go online';
  const anim = netAnim ? ' net-anim' : '';
  netAnim = false;
  // Bewusst OHNE Akzentfarbe/aktive Umrandung: online ist der Normalzustand,
  // der Knopf sieht aus wie jeder andere Rail-Knopf.
  return `<button class="tool-btn" data-act="net">`
    + `<span class="net-ico${anim}">${icon}</span>`
    + `<span class="tip">${label}<span class="k">G</span></span></button>`;
}

function renderProfileMenu() {
  const I = Icons;
  return `
    <div class="menu" style="right:6px" data-keep>
      <div class="menu-head">
        <span class="avatar" style="width:32px;height:32px">NA</span>
        <span class="n-body"><b style="font-size:13px">Noa Andersen</b><small class="mono" style="color:var(--text-faint)">local</small></span>
      </div>
      <button class="menu-item">${I.User} Account</button>
      <button class="menu-item">${I.Shield} Privacy &amp; data</button>
      <button class="menu-item">${I.Download} Export database</button>
    </div>`;
}

// Kontextmenue einer Liste (Rechtsklick in der Sidebar). Frei positioniert am
// Cursor (position:fixed), data-keep schuetzt es vor dem Auto-Schliessen.
function renderListCtx() {
  if (!state.ctxList) return '';
  const I = Icons;
  const { x, y, fromDock } = state.ctxList;
  // Aus dem Dock geoeffnet: das Menue waechst nach OBEN (translateY -100%), damit
  // es ueber dem grossen Namen schwebt und nicht mit dem "+"-Knopf kollidiert.
  const up = fromDock ? ';transform:translateY(-100%)' : '';
  return `
    <div class="menu list-ctx" data-keep
         style="position:fixed;left:${x}px;top:${y}px;min-width:180px${up}">
      <button class="menu-item" data-act="ctx-rename-list">${I.Pencil} Rename list</button>
      <button class="menu-item ctx-danger" data-act="ctx-delete-list">${I.Trash} Delete list</button>
    </div>`;
}

function scrim(inner) {
  return `<div class="scrim" data-act="scrim-close"><div data-keep>${inner}</div></div>`;
}

function renderModal() {
  const I = Icons;
  const list = activeList();
  switch (state.modal) {
    case 'status': {
      const online = state.online;
      const rows = [
        ['Local database', 'tasks.db', 'var(--secure)', 'healthy'],
        // Gate G22: solange der oeffentliche Dev-Schluessel (DEV_AES_KEY) benutzt
        // wird, darf hier keine echte Verschluesselung ("active"/"encrypted") in
        // gruen stehen. Ehrlicher Ist-Zustand in Warnfarbe: einlagiges AES-256 mit
        // oeffentlichem Schluessel, Schicht 2 (ChaCha20) + Passphrase erst ab
        // Phase 8. Ab Phase 8 zeigt diese Zeile echte Werte (siehe get_status).
        ['Encryption', 'AES-256 · dev key, layer 2 pending', 'var(--danger)', 'dev'],
        ['Network', online ? 'local only · online' : 'local only · offline', online ? 'var(--secure)' : 'var(--text-faint)', online ? 'online' : 'offline'],
        ['WebView2 runtime', 'system', 'var(--secure)', 'ok'],
      ];
      const body = rows.map((r, i) => `
        <div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:${i < rows.length - 1 ? '1px dashed var(--border)' : 'none'}">
          <span style="font-size:13.5px;font-weight:500">${r[0]}</span>
          <span class="mono" style="margin-left:auto;font-size:11px;color:var(--text-faint)">${r[1]}</span>
          ${r[3] ? `<span class="tag" style="color:${r[2]};min-width:64px;text-align:right">${r[3]}</span>` : ''}
        </div>`).join('');
      // "Recent errors" (Gate G29 / N11.12.1): der redigierte Fehler-Ringpuffer
      // des Backends, eingeklappt, mit Kopier-Knopf ueber den gehaerteten
      // G23-Clipboard-Pfad (copy_errors). Jede Zeile ist bereits backendseitig
      // redigiert (<path> statt Pfaden, keine Bridge-Argumente).
      const errs = (statusData && statusData.errors) || [];
      const errRows = errs.length
        ? errs.map((er) => `
          <div class="mono" style="font-size:10.5px;color:var(--text-dim);padding:3px 0;border-bottom:1px dashed var(--border);word-break:break-all">
            ${esc(er.ts)} <b>${esc(er.method)}</b> ${esc(er.code)} ${esc(er.exc)}${er.ref ? ' ref=' + esc(er.ref) : ''}${er.msg ? ' &middot; ' + esc(er.msg) : ''}
          </div>`).join('')
        : `<div class="empty-note">// none</div>`;
      const errSection = `
        <div style="margin-top:14px">
          <button class="section-head${errorsOpen ? ' open' : ' collapsed'}" data-act="toggle-errors" style="width:100%">
            <span class="s-pill">
              <span class="s-title">Recent errors</span>
              <span class="s-count">${errs.length}</span>
            </span>
          </button>
          ${errorsOpen ? `
          <div style="max-height:180px;overflow-y:auto;margin-top:6px">${errRows}</div>
          ${errs.length ? `<button class="btn" data-act="copy-errors" style="margin-top:8px">${I.Copy} Copy</button>` : ''}` : ''}
        </div>`;
      return scrim(`
        <div class="modal">
          <div class="modal-body">
            <div class="modal-icon accent">${I.Diag}</div>
            <h3>App status</h3>
            <div style="margin-top:16px;display:flex;flex-direction:column;gap:2px">${body}</div>
            ${errSection}
          </div>
          <div class="modal-actions"><button class="btn btn-primary" data-act="modal-close">Close</button></div>
        </div>`);
    }
    case 'rename':
      return scrim(`
        <div class="modal">
          <div class="modal-body">
            <div class="modal-icon accent">${I.Pencil}</div>
            <h3>Rename list</h3>
            <input id="rename-input" value="${esc(list ? list.name : '')}"
              style="margin-top:14px;width:100%;padding:12px 14px;border-radius:10px;background:var(--surface-2);border:1px solid var(--accent-line);color:var(--text);outline:none;font-size:15px" />
          </div>
          <div class="modal-actions">
            <button class="btn" data-act="modal-close">Cancel</button>
            <button class="btn btn-primary" data-act="do-rename">Save</button>
          </div>
        </div>`);
    case 'delete': {
      const selTask = state.selectedId && list
        ? [...(list.open || []), ...(list.done || [])].find((t) => t.id === state.selectedId)
        : null;
      return scrim(`
        <div class="modal">
          <div class="modal-body">
            <div class="modal-icon danger">${I.Trash}</div>
            <h3>Delete task?</h3>
            <p>${selTask ? `&ldquo;${esc(selTask.text)}&rdquo;` : 'No task selected.'}</p>
          </div>
          <div class="modal-actions">
            <button class="btn" data-act="modal-close">Cancel</button>
            ${selTask ? `<button class="btn btn-danger" data-act="do-delete">Delete</button>` : ''}
          </div>
        </div>`);
    }
    case 'shortcuts': {
      // Anzeige-Vollstaendigkeit nach Bauplan B.5 (einzige Wahrheit): auch Esc und
      // ? selbst listen, Maus-Gesten als eigene Sektion, Rail-only-Hinweis unten.
      const sc = [
        ['New task', ['↵']], ['New task in list', ['Ctrl', 'N']],
        ['New list', ['Ctrl', 'Shift', 'N']],
        ['Toggle sidebar', ['Ctrl', 'B']], ['Focus mode', ['F']],
        ['Switch list', ['Ctrl', '↑/↓']],
        ['Open list 1-9', ['Ctrl', '1-9']],
        ['Lock app', ['Ctrl', 'L']],
        ['Export open list', ['Ctrl', 'E']],
        ['Toggle theme', ['Ctrl', 'J']], ['Online / offline', ['G']],
        ['This help', ['?']],
        ['Close all / exit mini', ['Esc']],
      ];
      const mouse = [
        ['Select task', ['click']],
        ['Edit task', ['2× click']],
        ['Reorder tasks', ['drag']],
      ];
      const row = (s) => `
        <div class="sc-row"><span>${s[0]}</span>
          <span class="sc-keys">${s[1].map((k) => `<kbd>${k}</kbd>`).join('')}</span></div>`;
      return scrim(`
        <div class="modal" style="width:min(560px,100%)">
          <div class="modal-body" style="padding-bottom:4px">
            <div class="modal-icon accent">${I.Help}</div>
            <h3>Keyboard shortcuts</h3>
          </div>
          <div class="shortcuts-grid">${sc.map(row).join('')}
            <div class="sc-head">Mouse</div>
            ${mouse.map(row).join('')}
            <div class="sc-note">Panic, copy and mini mode are toolbar buttons only, on purpose.</div>
          </div>
        </div>`);
    }
    case 'settings':
      return scrim(renderSettings());
    default:
      return '';
  }
}

// Settings-Modal: steuert die persistierten Einstellungen (Bauplan B.6).
// Desktop-Layout statt "Handy-Liste": breites Modal, zwei Spalten
// ("Appearance" links, "Workspace" rechts), Sektionskoepfe im
// Stil des Sidebar-Labels (Mono-Eyebrow + Hairline). Alle Zustandswechsel
// laufen in-place ueber syncSettingsUi(), NIE ueber ein Voll-Render.
function renderSettings() {
  const I = Icons;
  const s = state.settings;
  const seg = (key, opts, cur) => `<div class="seg">` + opts.map(([val, label]) =>
    `<button class="seg-btn${cur === val ? ' on' : ''}" data-act="set" data-key="${key}" data-value="${val}">${label}</button>`
  ).join('') + `</div>`;
  const sw = ACCENTS.map((c) =>
    `<button class="swatch${c === s.accent ? ' sel' : ''}" data-act="set-accent" data-color="${c}" style="background:${c}"></button>`
  ).join('');
  const row = (label, control, hint) =>
    `<div class="set-row">
       <span class="set-label">${label}${hint ? `<small class="set-hint">${hint}</small>` : ''}</span>
       <span class="set-ctl">${control}</span></div>`;
  const head = (label) => `<div class="settings-head"><span>${label}</span><span class="line"></span></div>`;
  return `
    <div class="modal modal-settings">
      <div class="modal-body">
        <div class="modal-icon accent">${I.Gear}</div>
        <h3>Settings</h3>
        <div class="settings-grid">
          <div class="settings-col">
            ${head('Appearance')}
            ${row('Theme', seg('dark', [['true', 'Dark'], ['false', 'Light']], String(!!s.dark)))}
            ${row('Density', seg('density', [['comfortable', 'Comfortable'], ['compact', 'Compact']], s.density))}
            ${row('Accent', `<div class="swatches">${sw}</div>`)}
          </div>
          <div class="settings-col">
            ${head('Workspace')}
            ${row('Sidebar', seg('sidebar', [['open', 'Open'], ['closed', 'Closed']], s.sidebar))}
          </div>
        </div>
      </div>
      <div class="modal-actions"><button class="btn btn-primary" data-act="modal-close">Done</button></div>
    </div>`;
}

// Zustaende aller Settings-Controls in-place nachziehen (Seg-Knoepfe,
// Farbfelder, Kippschalter samt Kanal-Dimmen). KEIN render(): das Modal
// bleibt im DOM stehen, nichts flackert, Transitions laufen sauber durch.
function syncSettingsUi() {
  const s = state.settings;
  document.querySelectorAll('.seg-btn[data-key]').forEach((b) => {
    const key = b.dataset.key;
    const cur = key === 'dark' ? String(!!s.dark) : s[key];
    b.classList.toggle('on', b.dataset.value === cur);
  });
  document.querySelectorAll('.swatch[data-color]').forEach((el) => {
    el.classList.toggle('sel', el.dataset.color === s.accent);
  });
}

function renderLock() {
  if (!state.locked) return '';
  const I = Icons;
  // Die Passwort-Pille ist IMMER die Eingabepille (kein Klick-zum-Aufklappen):
  // wireInputs() fokussiert sie, tippen schreibt direkt hinein. Die Breite
  // waechst erst, wenn die Eingabe laenger als die Grundpille wird (JS, s.u.).
  // Waehrend der Aufschliess-Animation (lockUnlocking) verschwindet die Pille
  // und der Ring wird gruen, der Buegel des Schlosses geht auf.
  const pill = lockUnlocking ? '' : `
        <div class="lock-input" data-keep>
          <input id="lock-pass" type="password" placeholder="Password" autocomplete="off" spellcheck="false" />
        </div>`;
  // Off-Knopf oben rechts (N10): beendet die App sofort ohne Passphrase
  // (quit_app). Loescht nie Nutzer- oder App-Daten; der Raum wurde beim
  // Sperren bereits bereinigt, das sichere Spuren-Wischen kommt in Phase 8.
  const off = lockUnlocking ? '' : `
      <button class="lock-off" data-act="lock-off" title="Quit NoaToDo">${I.Power}</button>`;
  return `
    <div class="lock-screen${lockUnlocking ? ' unlocking' : ''}">
      ${off}
      <div class="lock-card">
        <div class="lock-ring">${lockUnlocking ? I.Unlock : I.Lock}</div>
        <h2>${lockUnlocking ? 'NoaToDo unlocked' : 'NoaToDo is locked'}</h2>
        ${pill}
      </div>
    </div>`;
}
// true, solange die Aufschliess-Animation nach richtigem Passwort laeuft.
let lockUnlocking = false;
// Frisch geholtes get_status()-Ergebnis fuer das Status-Modal (transient),
// plus Auf/Zu-Zustand der "Recent errors"-Sektion (G29). Kein Teil von state:
// rein praesentationsbezogen, verfaellt mit dem Modal.
let statusData = null;
let errorsOpen = false;

// ===========================================================================
// Panik-Flow (Nachtrag N10). Entsichert wie eine Cockpit-Waffenabdeckung,
// bewusst KEIN Tastenkuerzel. Stufe 1: Kippschalter von "No" auf "Yes" (armen).
// Stufe 2: die separate "Confirm"-Pille faehrt darunter aus. Beim Bestaetigen
// wird real bereinigt (Raum leeren, offline), der "Wipe"-Fortschritt laeuft,
// danach der Endschirm mit zwei Ausgaengen: Finish (Akzent, App beenden, nichts
// geloescht) und Killswitch (grau, zweistufig im Knopf; loescht ueber
// api.killswitch() UNWIDERRUFLICH alle Datenbank-Inhalte und beendet die App).
// Zurueck in die App fuehrt ab dem Wipe kein Weg mehr.
// ===========================================================================
function renderPanic() {
  if (!state.panic) return '';
  const I = Icons;
  const p = state.panic;

  // Vollbild-Schirme: "Wipe"-Fortschritt, Endschirm, Killswitch-Fortschritt.
  if (p.stage === 'wiping' || p.stage === 'done' || p.stage === 'killing') {
    if (p.stage === 'done') {
      // Endschirm: links Finish (Akzent), rechts der zweistufige Killswitch.
      // killArmed steuert die Im-Knopf-Animation (Schriftzug faehrt nach
      // rechts, "OK" faehrt herein); der Klick-Handler schaltet die Klasse
      // in-place um, damit die CSS-Transition sichtbar laeuft (ein Re-Render
      // wuerde den Knopf neu erzeugen und die Animation verschlucken).
      const killArmed = !!p.killArmed;
      return `
        <div class="panic-screen done">
          <div class="panic-screen-card">
            <div class="panic-screen-ring ok">${I.Shield}</div>
            <h2>All data securely wiped</h2>
            <p class="panic-screen-sub">The workspace, the in-memory cache and the cached keys were destroyed and the app went offline. Nothing readable remains on this machine.</p>
            <div class="panic-exit-row">
              <button class="btn btn-primary panic-finish" data-act="panic-finish">Finish</button>
              <button class="kill-btn${killArmed ? ' armed' : ''}" data-act="${killArmed ? 'kill-ok' : 'kill-arm'}" title="Irreversibly erase the database">
                <span class="kill-label">Killswitch</span>
                <span class="kill-ok mono">OK</span>
              </button>
            </div>
          </div>
        </div>`;
    }
    const killing = p.stage === 'killing';
    return `
      <div class="panic-screen">
        <div class="panic-screen-card">
          <div class="panic-screen-ring">${I.Alert}</div>
          <h2>${killing ? 'Erasing user data' : 'Wiping all data'}</h2>
          <div class="panic-bar"><div class="panic-bar-fill" id="panic-fill"></div></div>
          <div class="panic-wipe-row">
            <span class="mono" id="panic-step">${killing ? 'Deleting user data' : 'Shredding tasks.db'}</span>
            <span class="mono panic-pct" id="panic-pct">0%</span>
          </div>
        </div>
      </div>`;
  }

  // Stufe 1/2: schwebende Pille links neben dem Panik-Knopf der Rail.
  const armed = !!p.armed;
  const confirm = armed
    ? `<div class="panic-confirm-wrap">
         <button class="panic-confirm" data-act="panic-confirm">${I.Alert}<span>Confirm</span></button>
       </div>`
    : '';
  return `
    <div class="panic-panel" data-keep>
      <div class="panic-head">
        <span class="panic-head-icon">${I.Alert}</span>
        <span class="panic-head-text">Activate panic mode?</span>
        <button class="panic-x" data-act="panic-close" title="Cancel">${I.Close}</button>
      </div>
      <button class="panic-switch${armed ? ' armed' : ''}" data-act="panic-toggle"
              role="switch" aria-checked="${armed}">
        <span class="panic-switch-label off">No</span>
        <span class="panic-switch-label on">Yes</span>
        <span class="panic-knob"></span>
      </button>
      ${confirm}
    </div>`;
}

// Gemeinsamer Fortschritts-Laeufer fuer beide Panik-Schirme: Balken und
// Prozentzahl per requestAnimationFrame von 0 auf 100 %, die Statuszeile
// wechselt entlang der Schritte, am Ende feuert onDone. Bricht ab, wenn der
// Panik-Zustand die erwartete Stage verlassen hat.
function runPanicProgress(stage, steps, dur, onDone) {
  const fill = document.getElementById('panic-fill');
  const pct = document.getElementById('panic-pct');
  const step = document.getElementById('panic-step');
  const t0 = performance.now();
  function frame(now) {
    if (!state.panic || state.panic.stage !== stage) return;
    const r = Math.min(1, (now - t0) / dur);
    if (fill) fill.style.width = (r * 100).toFixed(1) + '%';
    if (pct) pct.textContent = Math.floor(r * 100) + '%';
    if (step) step.textContent = steps[Math.min(steps.length - 1, Math.floor(r * steps.length))];
    if (r < 1) { requestAnimationFrame(frame); }
    else { onDone(); }
  }
  requestAnimationFrame(frame);
}

// "Wipe"-Schirm nach dem Bestaetigen: die echte Bereinigung (Raum leeren,
// offline, Backend-panic) ist beim Confirm schon passiert; der Balken hier ist
// die Aussendarstellung. Danach der Endschirm mit Finish/Killswitch.
function startPanicWipe() {
  runPanicProgress(
    'wiping',
    ['Shredding tasks.db', 'Overwriting key material', 'Clearing memory cache', 'Zeroing free space'],
    2600,
    () => { state.panic.stage = 'done'; render(); }
  );
}

// Killswitch (N10): loescht REAL und unwiderruflich alle Datenbank-Inhalte
// (api.killswitch: lists/tasks/settings weg, Standard-Settings neu,
// VACUUM; naechster Start wie ein Erststart ohne Demo-Daten). Der Backend-Call
// laeuft parallel zum Balken; beendet wird erst, wenn beides fertig ist.
function startKillswitch() {
  state.panic.stage = 'killing';
  state.panic.killArmed = false;
  render();
  const req = api().killswitch();
  runPanicProgress(
    'killing',
    ['Deleting user data', 'Deleting lists', 'Deleting settings', 'Rebuilding empty database'],
    2800,
    async () => {
      const res = await req;
      if (res && res.error) {
        // Loeschen fehlgeschlagen: NICHT so tun, als waere es passiert.
        handleError(res);
        return;
      }
      await api().quit_app();
    }
  );
}

// ===========================================================================
// Haupt-Render
// ===========================================================================
function applyChrome() {
  root.setAttribute('data-theme', state.settings.dark ? 'dark' : 'light');
  root.setAttribute('data-density', state.settings.density || 'comfortable');
  // Die Tool-Rail ist immer "floating"; die frühere Floating/Flush-Einstellung
  // wurde aus den Settings entfernt (ein evtl. gespeicherter Wert wird ignoriert).
  root.setAttribute('data-toolbar', 'floating');
  root.setAttribute('data-sidebar', sidebarVisible() ? 'open' : 'closed');
  root.setAttribute('data-mini', state.mini ? 'on' : 'off');
  root.setAttribute('data-focus', state.focus ? 'on' : 'off');
  applyRail();
  root.style.setProperty('--accent', state.settings.accent || '#d97757');
  root.style.setProperty('--sidebar-width', (state.sidebarWidth || 256) + 'px');
}

// Sichtbarkeit der rechten Tool-Rail (ausserhalb von Fokus/Mini):
//  - fixiert (Pin),
//  - oder linke Sidebar offen,
//  - oder Cursor nahe am rechten Rand (railHover).
function railVisible() {
  if (state.focus || state.mini) return false;
  if (state.panic) return true;   // Panik-Panel haengt an der Rail, sie bleibt sichtbar
  return state.railPinned || sidebarVisible() || railHover;
}
function applyRail() {
  root.setAttribute('data-rail', railVisible() ? 'shown' : 'hidden');
}

function render() {
  applyChrome();
  // Panik-Wipe: sobald geloescht wird bzw. der "wiped"-Schirm steht, ist die App
  // theoretisch weg. Es darf NICHTS vom normalen UI mehr dahinter liegen (kein
  // Header mit "+", keine Sidebar, keine Rail), sonst kann man versehentlich
  // durch das Overlay hindurch etwas anklicken.
  if (state.panic && state.panic.stage !== 'panel') {
    root.innerHTML = renderPanic();
    return;
  }
  if (state.mini) {
    root.innerHTML = renderMini() + renderLock();
    wireInputs();
    return;
  }
  if (state.focus) {
    root.innerHTML = renderFocus() + renderLock();
    wireInputs();
    return;
  }
  root.innerHTML =
    renderHeader() +
    renderSidebar() +
    renderMain() +
    renderToolbar() +
    renderRailPin() +
    renderListCtx() +
    renderModal() +
    renderPanic() +
    renderLock();
  wireInputs();
}

// Eingabefelder brauchen eigene Listener (Fokus, Enter/Esc/Blur).
function wireInputs() {
  const nt = document.getElementById('new-task-input');
  if (nt) {
    nt.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); submitNewTask(nt.value); }
    });
    if (refocusNewTask) { nt.focus(); refocusNewTask = false; }
  }
  const nl = document.getElementById('new-list-input');
  if (nl) {
    nl.focus();
    nl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); commitNewList(nl.value); }
      else if (e.key === 'Escape') { state.adding = false; render(); }
    });
    nl.addEventListener('blur', () => { if (state.adding) commitNewList(nl.value); });
  }
  const rn = document.getElementById('rename-input');
  if (rn) {
    rn.focus(); rn.select();
    rn.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && rn.value.trim()) { e.preventDefault(); doRename(rn.value.trim()); }
    });
  }
  // Inline-Umbenennen-Pille in der Sidebar: Enter speichert, Esc bricht ab.
  const rl = document.getElementById('rename-list-input');
  if (rl && state.renamingId) {
    rl.focus(); rl.select();
    rl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); doRenameList(state.renamingId, rl.value); }
      else if (e.key === 'Escape') { e.preventDefault(); state.renamingId = null; render(); }
    });
  }
  // Inline-Umbenennen-Pille im Dock (Rechtsklick auf den grossen Namen).
  const rdk = document.getElementById('rename-dock-input');
  if (rdk && state.renamingId) {
    rdk.focus(); rdk.select();
    rdk.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); doRenameList(state.renamingId, rdk.value); }
      else if (e.key === 'Escape') { e.preventDefault(); state.renamingId = null; state.listEditDock = false; render(); }
    });
  }
  const lp = document.getElementById('lock-pass');
  if (lp) {
    // Pillenbreite: die Punkte werden ECHT vermessen (Canvas measureText mit
    // der Schrift des Feldes), die Pille waechst also erst, wenn die Eingabe
    // wirklich am rechten Rand ankommt, nicht schon vorher. Nach oben ist sie
    // auf etwa die Breite der "NoaToDo is locked"-Zeile begrenzt; laengere
    // Eingaben laufen einfach im Feld weiter, ohne die Pille zu verbreitern.
    const h2 = document.querySelector('.lock-card h2');
    const cs = getComputedStyle(lp);
    const meter = document.createElement('canvas').getContext('2d');
    meter.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const basePx = lp.offsetWidth || 120;
    const maxPx = Math.max(basePx, (h2 ? h2.offsetWidth : 300) - 40);
    const fit = () => {
      const dots = '•'.repeat(lp.value.length);
      const w = Math.ceil(meter.measureText(dots).width) + 14; // Luft fuer den Cursor
      lp.style.width = Math.min(maxPx, Math.max(basePx, w)) + 'px';
    };
    fit();
    lp.addEventListener('input', fit);
    lp.focus();
    lp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); lockSubmit(lp.value); }
      else if (e.key === 'Escape') { e.preventDefault(); lp.value = ''; fit(); }
    });
  }
  const rh = document.getElementById('sidebar-resize-handle');
  if (rh) rh.addEventListener('mousedown', onSidebarResizeStart);
  const et = document.getElementById('edit-task-text');
  if (et) {
    et.focus(); et.select();
    et.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); commitTaskEdit(); }
      else if (e.key === 'Escape') { e.stopPropagation(); state.editingId = null; render(); }
    });
  }
}
let refocusNewTask = false;

// ===========================================================================
// Aktionen (rufen das Backend, aktualisieren state, rendern)
// ===========================================================================
async function submitNewTask(text) {
  text = (text || '').trim();
  if (!text) return;
  const list = activeList();
  const res = await api().add_task(list.id, text);
  if (handleError(res)) return;
  list.open.push(res);
  // Pille nach dem Absenden wieder schliessen: zum Hinzufuegen einer weiteren
  // Aufgabe muss erneut auf das Plus gedrueckt werden.
  state.addingTask = false;
  render();
}

async function commitNewList(name) {
  name = (name || '').trim();
  state.adding = false;
  if (!name) { render(); return; }
  const res = await api().add_list(name);
  if (res && res.error) { render(); handleError(res); return; }
  state.lists.push(res);
  state.activeId = res.id;
  render();
  pushToast('List created', name);
}

// ===========================================================================
// Ton beim Abhaken: "Datenstrom", heller digitaler Aufstieg (Web Audio API).
// Kein Audio-File noetig, daher CSP-kompatibel (default-src 'self').
// AudioContext wird beim ersten Klick (pointerdown, siehe boot()) erzeugt und
// danach wiederverwendet. Damit der Blip beim Abhaken WIRKLICH sofort kommt,
// bleibt der Context dauerhaft warm: ein stiller Dauerton (ConstantSource mit
// gain 0, als DC-Signal ohnehin unhoerbar) haelt das Ausgabegeraet offen, sonst
// laesst WebView2 es bei Stille einschlafen und der naechste Ton hat eine
// spuerbare Kaltstart-Verzoegerung.
// ===========================================================================
let _audioCtx = null;
function _ac() {
  if (!_audioCtx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    _audioCtx = new AC({ latencyHint: 'interactive' });
    try {
      const keep = _audioCtx.createConstantSource();
      const kg = _audioCtx.createGain();
      kg.gain.value = 0;
      keep.connect(kg).connect(_audioCtx.destination);
      keep.start();
    } catch (e) { /* Keep-alive ist nur Optimierung, Fehler egal */ }
  }
  if (_audioCtx.state === 'suspended') _audioCtx.resume();
  return _audioCtx;
}

// Ein kurzer Digital-Blip mit weicher Huellkurve (Attack + exp. Abfall).
function _blip(ctx, freq, at, dur, gain) {
  const t0 = ctx.currentTime + at;
  const osc = ctx.createOscillator();
  const g = ctx.createGain();
  osc.type = 'square';
  osc.frequency.setValueAtTime(freq, t0);
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(gain, t0 + 0.006);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  osc.connect(g).connect(ctx.destination);
  osc.start(t0);
  osc.stop(t0 + dur + 0.03);
}

// "Datenstrom": vier helle Blips, schnell aufsteigend wie herabfallender Code.
// Bewusst NICHT auf ctx.resume() warten: die Blips werden sofort geplant, damit
// kein Lag entsteht. Ist der Context ausnahmsweise suspendiert, hat _ac() das
// Aufwecken schon (nicht blockierend) angestossen und die geplanten Toene kommen,
// sobald er laeuft.
function playDoneSound() {
  const ctx = _ac();
  if (!ctx) return;
  [1046, 1318, 1568, 2093].forEach((hz, i) => _blip(ctx, hz, i * 0.045, 0.05, 0.10));
}

async function toggleTask(id) {
  // Sound sofort abspielen (vor dem await, ohne await), damit kein Lag entsteht.
  // Nur beim Abhaken (Aufgabe ist gerade noch offen).
  const isChecking = state.lists.some((l) => l.open.some((t) => t.id === id));
  if (isChecking) playDoneSound();

  const res = await api().toggle_task(id);
  if (handleError(res)) return;
  // Aufgabe lokal zwischen open/done verschieben. Positions-Invariante (B.1,
  // U13): die Aufgabe haengt ans ENDE der Zielsektion, exakt wie im Backend
  // (push in beide Richtungen, kein unshift).
  for (const l of state.lists) {
    let i = l.open.findIndex((x) => x.id === id);
    if (i >= 0) { const [t] = l.open.splice(i, 1); t.done = true; l.done.push(t); break; }
    i = l.done.findIndex((x) => x.id === id);
    if (i >= 0) { const [t] = l.done.splice(i, 1); t.done = false; l.open.push(t); break; }
  }
  render();
}

// Inline-Bearbeitung speichern: nur der Text (kein Meta mehr, N11.1.3).
async function commitTaskEdit() {
  const id = state.editingId;
  const ti = document.getElementById('edit-task-text');
  if (!id || !ti) { state.editingId = null; return; }
  const text = ti.value.trim();
  if (!text) return pushToast('Task text cannot be empty');
  const res = await api().edit_task(id, { text: text });
  state.editingId = null;
  if (res && res.error) { render(); handleError(res); return; }
  for (const l of state.lists) {
    const t = l.open.find((x) => x.id === id) || l.done.find((x) => x.id === id);
    if (t) { t.text = res.text; break; }
  }
  render();
  pushToast('Task updated');
}

async function deleteTask(id) {
  const res = await api().delete_task(id);
  if (handleError(res)) return;
  for (const l of state.lists) {
    l.open = l.open.filter((t) => t.id !== id);
    l.done = l.done.filter((t) => t.id !== id);
  }
  if (state.editingId === id) state.editingId = null;
  if (state.selectedId === id) state.selectedId = null;
  render();
  pushToast('Task deleted');
}

async function doRename(name) {
  const list = activeList();
  const res = await api().rename_list(list.id, name);
  if (handleError(res)) return;
  list.name = name;
  state.modal = null;
  render();
  pushToast('List renamed', name);
}

async function doDelete() {
  if (!state.selectedId) return;
  state.modal = null;
  await deleteTask(state.selectedId);
}

// Inline-Umbenennen committen (Pille in der Sidebar, Enter oder gueltige Eingabe).
async function doRenameList(id, name) {
  const list = state.lists.find((l) => l.id === id);
  if (!list) { state.renamingId = null; render(); return; }
  const trimmed = name.trim();
  // Leer oder unveraendert: stillschweigend abbrechen.
  if (!trimmed || trimmed === list.name) { state.renamingId = null; state.listEditDock = false; render(); return; }
  const res = await api().rename_list(id, trimmed);
  if (handleError(res)) return;
  list.name = trimmed;
  state.renamingId = null;
  state.listEditDock = false;
  render();
  pushToast('List renamed', trimmed);
}

async function doDeleteList() {
  const id = state.confirmDeleteId;
  if (!id) return;
  const res = await api().delete_list(id);
  if (handleError(res)) return;
  const removed = state.lists.find((l) => l.id === id);
  state.lists = state.lists.filter((l) => l.id !== id);
  // Aktive Liste neu setzen, falls die geloeschte ausgewaehlt war.
  if (state.activeId === id) {
    state.activeId = state.lists.length ? state.lists[0].id : null;
    state.doneOpen = false; state.editingId = null; state.selectedId = null;
  }
  state.confirmDeleteId = null;
  state.listEditDock = false;
  render();
  // Undo-Toast (N11.2.1): stellt die Liste samt Aufgaben an alter Position
  // wieder her. not_found (Puffer inzwischen ersetzt/verfallen) laeuft still
  // ueber handleError -> refreshState, es entsteht nie eine zweite Kopie.
  pushUndoToast('List deleted', removed ? removed.name : '', async () => {
    const undoRes = await api().undo_delete_list(id);
    if (handleError(undoRes)) return;
    await refreshState();
    pushToast('List restored', removed ? removed.name : '');
  });
}

async function setOnline(flag) {
  const res = await api().set_online(flag);
  state.online = res && typeof res.online === 'boolean' ? res.online : flag;
  netAnim = true;              // naechster Render: Symbol fliegt herein und purzelt
  if (state.online) startWifiPoll();
  else stopWifiPoll();
  render();
  pushToast(flag ? 'Back online' : 'Offline mode', flag ? 'network enabled' : 'working offline');
}

// Echte WLAN-Signalstaerke vom Backend holen und nur das Symbol aktualisieren
// (kein Voll-Render, damit Inline-Bearbeitung o.ae. ungestoert bleibt und das
// Symbol beim Pollen nicht erneut "hereinfliegt").
let wifiTimer = null;
async function refreshWifi() {
  if (!state.online) return;
  try {
    const r = await api().get_wifi_signal();
    if (r && typeof r.level === 'number') {
      wifiLevel = r.level;
      const host = document.querySelector('.net-ico');
      if (host && state.online) host.innerHTML = wifiSvg(wifiLevel);
    }
  } catch (e) { /* WLAN-Abfrage ist nur Kosmetik, Fehler still ignorieren */ }
}
function startWifiPoll() {
  stopWifiPoll();
  refreshWifi();
  wifiTimer = setInterval(refreshWifi, 15000);
}
function stopWifiPoll() {
  if (wifiTimer) { clearInterval(wifiTimer); wifiTimer = null; }
}

async function setSetting(key, value) {
  // Typkonvertierung für die Anwendung im Frontend.
  let applied = value;
  if (key === 'dark') applied = (value === true || value === 'true');
  state.settings[key] = applied;
  if (key === 'dark') flashThemeSwitch();
  // Bewusst KEIN render(): Theme/Density/Sidebar wirken ueber die Attribute
  // in applyChrome (CSS uebernimmt), die Settings-Controls werden in-place
  // nachgezogen. Ein Voll-Render wuerde bei jedem Umschalten kurz flackern.
  applyChrome();
  syncSettingsUi();
  await api().set_setting(key, value);
}

async function setAccent(color) {
  state.settings.accent = color;
  // Sofort und ohne Voll-Render anwenden: nur die CSS-Variable umsetzen und
  // die Controls in-place nachziehen (kein Flackern).
  root.style.setProperty('--accent', color);
  syncSettingsUi();
  await api().set_setting('accent', color);
}


async function doExport() {
  const list = activeList();
  if (!list) return;
  const res = await api().export_list(list.id, 'md');
  if (handleError(res)) return;
  // Phase 7 ergänzt den echten Speicher-Dialog; vorerst Bestätigung.
  pushToast('Exported list', res.filename);
}

// Kopiert die AUSGEWAEHLTE Aufgabe. Das eigentliche Kopieren passiert im
// Backend (gehaertete Clipboard-Formate, kein Win+V-Verlauf, kein
// Cloud-Clipboard, Auto-Clear nach 60 s), siehe Bauplan Gate G23.
async function doCopy() {
  if (!state.selectedId) return pushToast('Select a task first');
  const res = await api().copy_task(state.selectedId);
  if (handleError(res)) return;
  pushToast('Task copied', 'clipboard clears in ' + (res.clears_in || 60) + 's');
}

async function doMini(flag) {
  const res = await api().set_mini(flag);
  if (handleError(res)) return;
  state.mini = res && typeof res.mini === 'boolean' ? res.mini : flag;
  // Ein offenes "Neue Aufgabe"-Eingabefeld beim Moduswechsel IMMER schliessen
  // (in beide Richtungen): es soll nicht aus dem Mini- ins grosse Fenster oder
  // umgekehrt mitwandern.
  state.addingTask = false;
  if (state.mini) {
    // Im Mini-Modus alles Überlagernde schließen, damit nur die Liste bleibt.
    state.focus = false; state.menu = null; state.modal = null;
    state.adding = false;
  }
  render();
}

// --- Sidebar Resize -----------------------------------------------------------
let _resizing = false;
let _resizeStartX = 0;
let _resizeStartW = 0;

function onSidebarResizeStart(e) {
  if (!sidebarVisible()) return;
  e.preventDefault();
  _resizing = true;
  _resizeStartX = e.clientX;
  _resizeStartW = state.sidebarWidth || 256;
  root.setAttribute('data-resizing', '');
  document.body.style.cursor = 'col-resize';
  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onSidebarResizeMove);
  document.addEventListener('mouseup', onSidebarResizeEnd);
}

function onSidebarResizeMove(e) {
  if (!_resizing) return;
  const w = Math.max(180, Math.min(520, _resizeStartW + (e.clientX - _resizeStartX)));
  state.sidebarWidth = w;
  root.style.setProperty('--sidebar-width', w + 'px');
}

function onSidebarResizeEnd() {
  if (!_resizing) return;
  _resizing = false;
  root.removeAttribute('data-resizing');
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
  document.removeEventListener('mousemove', onSidebarResizeMove);
  document.removeEventListener('mouseup', onSidebarResizeEnd);
  api().set_setting('sidebarWidth', String(Math.round(state.sidebarWidth)));
}

// --- Tool-Rail: Auto-Hide / Pin -------------------------------------------
let railHover = false;  // Cursor nahe rechtem Rand bzw. über der Rail?

function toggleRailPin() {
  state.railPinned = !state.railPinned;
  railHover = false;
  api().set_setting('railPinned', state.railPinned ? 'true' : 'false');
  render();
}

// Pragmatische Naehe-Erkennung: innerhalb von ~100px zum rechten Rand (oder
// direkt ueber der Rail) gleitet sie ein, sonst wieder aus. Kein Re-Render
// nur das data-rail-Attribut wird umgeschaltet (CSS-Transition macht den Rest).
function onMouseMove(e) {
  if (state.focus || state.mini || state.railPinned || sidebarVisible()) {
    railHover = false;
    return;
  }
  const near = e.clientX >= window.innerWidth - 100;
  const overBar = !!(e.target.closest && e.target.closest('.toolbar'));
  const next = near || overBar;
  if (next !== railHover) { railHover = next; applyRail(); }
}

// "Raum leeren" (Nachtrag N10): gemeinsame Bereinigung fuer Lock und Panik.
// Verwirft den kompletten In-Memory-Zustand (Listen, Auswahl, Menues, Modals,
// Eingaben) und stellt auf offline. Loescht NICHTS: das Backend bleibt die
// Wahrheit und liefert nach dem Entsperren alles frisch per get_state().
function clearWorkspace() {
  state.lists = [];
  state.activeId = null;
  state.menu = null; state.modal = null; state.ctxList = null;
  state.renamingId = null; state.confirmDeleteId = null; state.listEditDock = false;
  state.adding = false; state.addingTask = false; state.doneOpen = false;
  state.editingId = null; state.selectedId = null;
  state.focus = false;
  state.settings.sidebar = 'closed';   // nur in-memory, wie beim Boot
  state.railPinned = false;
  state.online = false;
  clearToasts();   // kein Undo-Knopf/Toast darf den Lock-Screen ueberlagern
}

async function doLock() {
  // Verstaerkte Sperre (N10): erst den Raum bereinigen wie bei Panik
  // (Ansicht leeren, In-Memory-Zustand verwerfen, offline schalten), dann
  // sperren. Es wird nichts geloescht.
  clearWorkspace();
  api().set_online(false);
  await api().lock();
  state.locked = true; lockUnlocking = false;
  render();
}

async function lockSubmit(value) {
  const res = await api().unlock(value || '');   // Phase 8: echte Passphrase
  if (!(res && res.ok)) {
    // Falsches Passwort: Feld leeren (input-Event zieht die Breite nach),
    // gesperrt bleiben.
    const lp = document.getElementById('lock-pass');
    if (lp) { lp.value = ''; lp.dispatchEvent(new Event('input')); lp.focus(); }
    return;
  }
  // Richtig: erst die Aufschliess-Animation zeigen (Ring wird gruen, der
  // Schloss-Buegel geht auf), dann wirklich entsperren. Die Dauer muss zu den
  // CSS-Animationen (unlockPop/unlockShackle/lockFadeOut) passen.
  // Bewusst KEIN render(): der bestehende Lock-Screen wird in-place
  // umgeschaltet, ein voller innerHTML-Neuaufbau wuerde sichtbar flackern.
  lockUnlocking = true;
  const ls = document.querySelector('.lock-screen');
  if (ls) {
    ls.classList.add('unlocking');
    const ring = ls.querySelector('.lock-ring');
    if (ring) ring.innerHTML = Icons.Unlock;
    const h2 = ls.querySelector('h2');
    if (h2) h2.textContent = 'NoaToDo unlocked';
    const pill = ls.querySelector('.lock-input');
    if (pill) pill.remove();
    const off = ls.querySelector('.lock-off');
    if (off) off.remove();
  }
  // Der Raum wurde beim Sperren geleert (N10): waehrend die Animation laeuft,
  // den Zustand frisch vom Backend holen (danach leere Arbeitsflaeche wie beim
  // Boot). Offline bleibt die App, bis der Nutzer es bewusst wieder einschaltet.
  let st = null;
  try { st = await api().get_state(); } catch (e) { /* Fallback: leerer Raum */ }
  setTimeout(() => {
    if (st && st.lists) {
      state.lists = st.lists;
      state.settings = Object.assign({}, st.settings, { sidebar: 'closed' });
      state.online = !!st.online;
    }
    lockUnlocking = false;
    state.locked = false;
    render();
  }, 1900);
}

// Theme-Wechsel-Flackern vermeiden (ein Frame ohne Transitions).
function flashThemeSwitch() {
  root.classList.add('theme-switching');
  requestAnimationFrame(() => requestAnimationFrame(() => root.classList.remove('theme-switching')));
}

// ===========================================================================
// Zentrale Fehlerbehandlung nach dem B.2-Fehlercode-Katalog (Gate G29).
// Das Backend liefert nur noch Codes + statische Texte (nie str(exc), nie
// Pfade). Toast-Politik (B.2): Toast NUR bei not_found, invalid, busy und
// internal (mit ref); locked und canceled sind bewusst stumm; passphrase/
// rate_limited/vault/memory haben ihre eigene Darstellung im Lock-/
// Fehlerbildschirm und bekommen ebenfalls nie einen Toast.
// Liefert true, wenn res ein Fehler war (Aufrufer bricht dann ab).
// ===========================================================================
function handleError(res) {
  if (!res || !res.error) return false;
  const code = res.error;
  if (code === 'not_found') {
    // Die Ansicht war veraltet: Toast, danach still frisch laden (B.2).
    pushToast(res.message || 'Item not found.');
    refreshState();
  } else if (code === 'invalid' || code === 'busy') {
    pushToast(res.message || 'Invalid input.');
  } else if (code === 'internal') {
    pushToast(res.message || 'Something went wrong.', res.ref ? 'ref ' + res.ref : '');
  } else if (code === 'locked') {
    // Stumm (Renn-Fall, z.B. Auto-Lock waehrend einer laufenden Aktion):
    // einfach den Lock-Screen zeigen.
    state.locked = true;
    render();
  }
  // canceled (und alles Uebrige): stumm, kein Toast.
  return true;
}

// Gesamtzustand still neu vom Backend laden (nach not_found: die eigene
// Ansicht war veraltet). UI-Zustand bleibt, eine verschwundene aktive Liste
// wird geschlossen.
async function refreshState() {
  try {
    const st = await api().get_state();
    if (st && st.lists) {
      state.lists = st.lists;
      state.online = !!st.online;
      if (state.activeId && !state.lists.some((l) => l.id === state.activeId)) {
        state.activeId = null; state.selectedId = null; state.editingId = null;
      }
    }
  } catch (e) { /* Backend nicht erreichbar: bestehende Ansicht behalten */ }
  render();
}

// ===========================================================================
// Toasts (eigener Layer außerhalb von #root -> kein Re-Render/Fokusverlust)
// ===========================================================================
let toastLayer = null;
function pushToast(text, mono) {
  if (!toastLayer) {
    toastLayer = document.createElement('div');
    toastLayer.className = 'toast-wrap';
    document.body.appendChild(toastLayer);
  }
  const node = document.createElement('div');
  node.className = 'toast';
  node.innerHTML = Icons.Check + esc(text) + (mono ? `<span class="mono">${esc(mono)}</span>` : '');
  toastLayer.appendChild(node);
  setTimeout(() => { if (node.parentNode) node.parentNode.removeChild(node); }, 2400);
}

// Toast mit Undo-Knopf (N11.2.1, nur fuers Listen-Loeschen): steht ca. 6 s,
// der Knopf ruft onUndo genau einmal und raeumt den Toast sofort weg. Der
// 6-s-Timer gehoert der UI; der Backend-Puffer lebt unabhaengig davon weiter
// (ein spaetes Undo ueber einen neuen Weg duerfte gelingen, das ist gewollt).
function pushUndoToast(text, mono, onUndo) {
  if (!toastLayer) {
    toastLayer = document.createElement('div');
    toastLayer.className = 'toast-wrap';
    document.body.appendChild(toastLayer);
  }
  const node = document.createElement('div');
  node.className = 'toast';
  node.innerHTML = Icons.Trash + esc(text) + (mono ? `<span class="mono">${esc(mono)}</span>` : '');
  const btn = document.createElement('button');
  btn.className = 'toast-undo';
  btn.textContent = 'Undo';
  btn.addEventListener('click', () => {
    if (node.parentNode) node.parentNode.removeChild(node);
    onUndo();
  });
  node.appendChild(btn);
  toastLayer.appendChild(node);
  setTimeout(() => { if (node.parentNode) node.parentNode.removeChild(node); }, 6000);
}

// Alle sichtbaren Toasts sofort wegraeumen (beim Sperren/Panik: kein
// Undo-Knopf und keine Meldung darf den Lock-Screen ueberlagern).
function clearToasts() {
  if (toastLayer) toastLayer.innerHTML = '';
}

// ===========================================================================
// Klick-Delegation
// ===========================================================================
function closeMenusIfOutside(e, a) {
  let changed = false;
  const act = a ? a.dataset.act : null;
  if (state.menu && !e.target.closest('[data-keep]') && act !== 'open-profile') {
    state.menu = null; changed = true;
  }
  if (state.ctxList && !e.target.closest('.list-ctx')) {
    state.ctxList = null; changed = true;
  }
  // Klick ausserhalb der Inline-Pillen (Sidebar .list-inline ODER Dock .dock-edit)
  // verwirft Umbenennen / Loeschbestaetigung.
  if (state.renamingId && !e.target.closest('.list-inline, .dock-edit')) {
    state.renamingId = null; state.listEditDock = false; changed = true;
  }
  if (state.confirmDeleteId && !e.target.closest('.list-inline, .dock-edit')) {
    state.confirmDeleteId = null; state.listEditDock = false; changed = true;
  }
  return changed;
}

async function onClick(e) {
  // Laeuft eine Inline-Bearbeitung und der Klick geht daneben: speichern
  // (bei leerem Text stattdessen abbrechen), erst dann normal weitermachen.
  if (state.editingId && !e.target.closest('.task.editing')) {
    const ti = document.getElementById('edit-task-text');
    if (ti && ti.value.trim()) await commitTaskEdit();
    else { state.editingId = null; render(); }
  }
  const a = e.target.closest('[data-act]');
  const needRender = closeMenusIfOutside(e, a);
  if (!a) { if (needRender) render(); return; }
  const act = a.dataset.act;
  const id = a.dataset.id;

  switch (act) {
    case 'toggle-sidebar': {
      // Nur das Attribut umschalten (applyChrome), damit die CSS-Transition
      // der bestehenden Sidebar laeuft. Kamen wir aus dem Focus-Modus, ist
      // ein voller Rebuild noetig (anderes Layout).
      const wasFocus = state.focus;
      state.focus = false;
      state.settings.sidebar = sidebarVisible() ? 'closed' : 'open';
      api().set_setting('sidebar', state.settings.sidebar);
      if (wasFocus) render(); else applyChrome();
      break;
    }
    case 'open-profile': state.menu = state.menu === 'profile' ? null : 'profile'; render(); break;
    case 'select-list':
      // Klick auf die bereits ausgewaehlte Liste schliesst sie wieder (zurueck
      // zur leeren Arbeitsflaeche). Sonst die angeklickte Liste oeffnen.
      state.activeId = state.activeId === id ? null : id;
      state.doneOpen = false; state.editingId = null; state.selectedId = null;
      render();
      break;
    case 'select-task': {
      // Klick auf die Karte: Auswahl umschalten (waehrend einer Inline-
      // Bearbeitung nicht, dort gehoeren Klicks den Eingabefeldern).
      // Doppelklick wird HIER von Hand erkannt (zwei Klicks auf dieselbe
      // Karte innerhalb von 450 ms) statt ueber das native dblclick-Event:
      // jeder Einzelklick rendert neu und ersetzt die Karte im DOM, wodurch
      // das native dblclick auf einem abgehaengten Knoten feuert und den
      // document-Listener nicht mehr erreicht. Doppelklick auf eine offene
      // Aufgabe = Inline-Bearbeitung, auf eine ERLEDIGTE = zurueck zu offen.
      // Eine erledigte Aufgabe geht nur bei einem WIRKLICH schnellen Doppelklick
      // (< 250 ms) wieder nach oben. Klickt man langsamer zweimal, wird die
      // Karte nur ent- bzw. ausgewaehlt, nicht bewegt.
      if (state.editingId === id) break;
      const now = performance.now();
      const isDone = a.classList.contains('done');
      const dt = _lastTaskClick.id === id ? now - _lastTaskClick.t : Infinity;
      const isDbl = dt < (isDone ? 250 : 450);
      _lastTaskClick = isDbl ? { id: null, t: 0 } : { id: id, t: now };
      if (isDbl) {
        if (isDone) { await toggleTask(id); break; }
        state.editingId = id;
        render(); break;
      }
      state.selectedId = state.selectedId === id ? null : id;
      render(); break;
    }
    case 'new-list-show': state.adding = true; render(); break;
    case 'settings': state.menu = null; state.modal = 'settings'; render(); break;
    case 'toggle-task': await toggleTask(id); break;
    case 'del-task': await deleteTask(id); break;
    case 'toggle-done': state.doneOpen = !state.doneOpen; render(); break;
    case 'focus-newtask': { const i = document.getElementById('new-task-input'); if (i) i.focus(); break; }
    case 'dock-toggle': {
      state.addingTask = !state.addingTask;
      // Nur Klasse + Eingabefeld in-place umschalten, NICHT neu rendern: so
      // bleibt der "+"-Knopf (svg) im DOM erhalten und die "+"-zu-"x"-Drehung
      // laeuft als CSS-Transition mit Ueberschwung in BEIDE Richtungen, genau
      // wie der Sidebar-Schalter oben links. Ein Re-Render wuerde den Knopf neu
      // erzeugen und damit die Animation verschlucken.
      const addBtn = document.querySelector('.dock-add');
      const wrap = document.querySelector('.dock-add-wrap');
      if (!addBtn || !wrap) { if (state.addingTask) refocusNewTask = true; render(); break; }
      addBtn.classList.toggle('active', state.addingTask);
      addBtn.title = state.addingTask ? 'Cancel' : 'Add task';
      const existing = document.querySelector('.dock-input');
      if (state.addingTask) {
        if (!existing) {
          const pill = document.createElement('div');
          pill.className = 'dock-input';
          pill.setAttribute('data-keep', '');
          const input = document.createElement('input');
          input.id = 'new-task-input';
          input.placeholder = 'New task…';
          input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') { e.preventDefault(); submitNewTask(input.value); }
          });
          const close = document.createElement('button');
          close.className = 'dock-close';
          close.setAttribute('data-act', 'dock-toggle');
          close.title = 'Close';
          close.innerHTML = Icons.Close;
          pill.appendChild(input);
          pill.appendChild(close);
          wrap.appendChild(pill);
        }
        const i = document.getElementById('new-task-input');
        if (i) i.focus();
      } else if (existing) {
        existing.remove();
      }
      break;
    }
    case 'net': await setOnline(!state.online); break;
    // Alle Werkzeuge, die eine Liste brauchen (Mini, Fokus, Umbenennen, Copy,
    // Loeschen, Export), tun ohne offene Liste einfach NICHTS: kein Modal,
    // kein Toast. Verlassen von Mini/Fokus geht dagegen immer.
    case 'tb-mini': if (!state.mini && !activeList()) break; await doMini(!state.mini); break;
    case 'tb-focus':
      if (!state.focus && !activeList()) break;
      state.focus = !state.focus; state.menu = null; render(); break;
    case 'rail-pin': toggleRailPin(); break;
    case 'tb-export': await doExport(); break;
    case 'tb-help': state.modal = 'shortcuts'; render(); break;
    case 'tb-lock': await doLock(); break;
    case 'tb-emergency': state.panic = state.panic ? null : { armed: false, stage: 'panel' }; render(); break;
    case 'tb-copy': if (!activeList()) break; await doCopy(); break;
    case 'tb-rename':
      // Kontextuell: ausgewaehlte Aufgabe -> Inline-Bearbeitung; sonst Liste umbenennen.
      if (!activeList()) break;
      if (state.selectedId) { state.editingId = state.selectedId; render(); }
      else { state.modal = 'rename'; render(); }
      break;
    case 'tb-delete': if (activeList() && state.selectedId) await deleteTask(state.selectedId); break;
    case 'tb-status':
      // Status-Modal sofort zeigen, die Backend-Daten (u.a. den G29-Fehler-
      // Ringpuffer) asynchron nachladen und nur nachrendern, solange das
      // Modal noch offen ist.
      state.modal = 'status'; statusData = null; errorsOpen = false; render();
      api().get_status().then((d) => {
        if (!d || d.error) return;
        statusData = d;
        if (state.modal === 'status') render();
      });
      break;
    case 'toggle-errors': errorsOpen = !errorsOpen; render(); break;
    case 'copy-errors': {
      const res = await api().copy_errors();
      if (handleError(res)) break;
      pushToast('Errors copied', res.clears_in ? 'clipboard clears in ' + res.clears_in + 's' : '');
      break;
    }
    case 'exit-focus': state.focus = false; render(); break;
    case 'set-accent': await setAccent(a.dataset.color); break;
    case 'set': await setSetting(a.dataset.key, a.dataset.value); break;
    case 'scrim-close':
      // Nur schliessen, wenn der Klick WIRKLICH auf dem geblurten Hintergrund
      // landet. Klicks auf nicht-interaktive Flaechen INNERHALB des Modals
      // (data-keep-Huelle) blubbern sonst bis zum Scrim hoch und wuerden das
      // Fenster ungewollt zumachen.
      if (e.target.closest('[data-keep]')) break;
      state.modal = null; render(); break;
    case 'modal-close': state.modal = null; render(); break;
    case 'do-rename': { const i = document.getElementById('rename-input'); if (i && i.value.trim()) await doRename(i.value.trim()); break; }
    case 'do-delete': await doDelete(); break;
    case 'ctx-rename-list': {
      // Inline-Pille oeffnen: in der Sidebar an der Listenposition, oder (bei
      // Rechtsklick auf den Dock-Namen) unten im Dock (listEditDock).
      const fromDock = !!(state.ctxList && state.ctxList.fromDock);
      const cid = state.ctxList && state.ctxList.id;
      state.ctxList = null; state.confirmDeleteId = null;
      state.renamingId = cid;
      state.listEditDock = fromDock;
      render(); break;
    }
    case 'ctx-delete-list': {
      // Inline-Loeschbestaetigung oeffnen (Sidebar oder Dock, siehe oben).
      const fromDock = !!(state.ctxList && state.ctxList.fromDock);
      const cid = state.ctxList && state.ctxList.id;
      state.ctxList = null; state.renamingId = null;
      state.confirmDeleteId = cid;
      state.listEditDock = fromDock;
      render(); break;
    }
    case 'cancel-rename-list': state.renamingId = null; state.listEditDock = false; render(); break;
    case 'cancel-delete-list': state.confirmDeleteId = null; state.listEditDock = false; render(); break;
    case 'do-delete-list': await doDeleteList(); break;
    case 'panic-toggle': if (state.panic) { state.panic.armed = !state.panic.armed; render(); } break;
    case 'panic-close': state.panic = null; render(); break;
    case 'panic-confirm':
      if (state.panic && state.panic.armed) {
        // Ab hier gibt es kein Zurueck in die App mehr (N10): sofort real
        // bereinigen (Raum leeren, offline, Backend-Panik), dann den
        // Wipe-Fortschritt zeigen und in den Endschirm wechseln.
        clearWorkspace();
        api().panic();
        state.panic.stage = 'wiping'; render(); startPanicWipe();
      }
      break;
    // Endschirm-Ausgaenge (N10): Finish beendet nur die App (nichts geloescht).
    case 'panic-finish': await api().quit_app(); break;
    // Killswitch, Stufe 1: nur entsichern. Klasse und data-act werden in-place
    // umgeschaltet (kein render()), damit die Schriftzug/OK-Transition laeuft.
    case 'kill-arm': {
      if (!state.panic || state.panic.stage !== 'done') break;
      state.panic.killArmed = true;
      const btn = a.closest('.kill-btn') || a;
      btn.classList.add('armed');
      btn.dataset.act = 'kill-ok';
      break;
    }
    // Killswitch, Stufe 2 ("OK"): unwiderruflich loeschen, dann beendet
    // sich die App von selbst (startKillswitch).
    case 'kill-ok':
      if (state.panic && state.panic.stage === 'done' && state.panic.killArmed) startKillswitch();
      break;
    // Off-Knopf des Sperrschirms (N10): App sofort beenden, ohne Passphrase,
    // ohne Datenverlust.
    case 'lock-off': await api().quit_app(); break;
    default: if (needRender) render();
  }
}

// Rechtsklick auf eine Liste in der Sidebar oeffnet das Kontextmenue
// (Umbenennen / Loeschen). Ueberall sonst wird das native Menue unterdrueckt
// und ein offenes Kontextmenue geschlossen.
function onContextMenu(e) {
  if (state.locked || state.mini) return;
  // In Eingabefeldern das native Menue (Kopieren/Einfuegen) erhalten.
  if (/^(INPUT|TEXTAREA)$/.test(e.target.tagName)) return;
  const item = e.target.closest('.list-item[data-id]');
  if (item) {
    e.preventDefault();
    const x = Math.min(e.clientX, window.innerWidth - 190);
    const y = Math.min(e.clientY, window.innerHeight - 100);
    state.ctxList = { id: item.dataset.id, x, y };
    state.menu = null;
    render();
    return;
  }
  // Rechtsklick auf die grosse Namens-Pille im unteren Dock: dasselbe Rename/
  // Delete-Menue, aber oberhalb des Namens verankert (fromDock).
  const dockPill = e.target.closest('.dock-pill');
  if (dockPill && state.activeId) {
    e.preventDefault();
    const r = dockPill.getBoundingClientRect();
    const x = Math.max(8, Math.min(r.left, window.innerWidth - 190));
    const y = r.top - 8;
    state.ctxList = { id: state.activeId, x, y, fromDock: true };
    state.menu = null;
    render();
    return;
  }
  e.preventDefault();
  if (state.ctxList) { state.ctxList = null; render(); }
}

// ===========================================================================
// Tastenkürzel (Bauplan B.5)
// ===========================================================================
function onKeyGlobal(e) {
  const typing = /^(INPUT|TEXTAREA)$/.test(e.target.tagName);
  const meta = e.metaKey || e.ctrlKey;
  if (state.locked) {
    // Auf dem Sperrschirm landet Tippen IMMER direkt im Passwortfeld: hat das
    // Feld den Fokus verloren (z.B. Klick daneben), holt der erste druckbare
    // Buchstabe ihn zurueck; das Zeichen selbst wird danach regulaer eingefuegt.
    const lp = document.getElementById('lock-pass');
    if (lp && document.activeElement !== lp && !meta && !e.altKey && e.key.length === 1) lp.focus();
    return;
  }
  if (e.key === 'Escape') {
    if (state.mini) { doMini(false); return; }
    state.menu = null; state.modal = null;
    state.focus = false; state.adding = false; state.addingTask = false;
    state.editingId = null; state.selectedId = null; state.ctxList = null;
    state.renamingId = null; state.confirmDeleteId = null; state.listEditDock = false;
    // Panik-Panel schliessen, aber den laufenden/fertigen Wipe-Schirm stehen lassen.
    if (state.panic && state.panic.stage === 'panel') state.panic = null;
    render(); return;
  }
  const k = e.key.toLowerCase();
  // Strg+N / Strg+Shift+N duerfen auch aus dem gerade geoeffneten Eingabefeld
  // heraus feuern: der erste Druck oeffnet das Feld und fokussiert es, ein
  // zweiter Druck soll es wieder schliessen (Toggle). Ohne diese Ausnahme
  // wuerde der "typing"-Riegel den zweiten Druck schlucken. Alle anderen
  // Buchstaben-Kuerzel bleiben waehrend des Tippens blockiert.
  if (typing && !(meta && k === 'n')) return;
  if (meta && k === 'b') { e.preventDefault(); const wasFocus = state.focus; state.focus = false; state.settings.sidebar = sidebarVisible() ? 'closed' : 'open'; api().set_setting('sidebar', state.settings.sidebar); if (wasFocus) render(); else applyChrome(); }
  else if (meta && k === 'j') { e.preventDefault(); setSetting('dark', !state.settings.dark); }
  else if (meta && k === 'l') { e.preventDefault(); doLock(); }
  else if (meta && k === 'e') { e.preventDefault(); doExport(); }
  else if (meta && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
    // Ctrl+Pfeil hoch/runter: durch die Listen der Sidebar wechseln. Nur wenn
    // die Sidebar offen UND bereits eine Liste geoeffnet ist; an den Enden
    // wird gestoppt (kein Umlauf von der untersten Liste zur obersten).
    if (!sidebarVisible() || !state.activeId) return;
    e.preventDefault();
    const idx = state.lists.findIndex((l) => l.id === state.activeId);
    if (idx < 0) return;
    const next = idx + (e.key === 'ArrowDown' ? 1 : -1);
    if (next < 0 || next >= state.lists.length) return;
    state.activeId = state.lists[next].id;
    state.doneOpen = false; state.editingId = null; state.selectedId = null;
    render();
  }
  else if (meta && !e.altKey && !e.shiftKey && e.key >= '1' && e.key <= '9') {
    // Strg+1 bis Strg+9: direkt die n-te Liste der Sidebar oeffnen (1 = oberste).
    // Nochmaliges Druecken derselben Nummer schliesst die Liste wieder (Toggle,
    // gleiches Verhalten wie ein Klick auf die bereits offene Liste). Nur erlaubt,
    // wenn die Sidebar offen ist (eine offene Liste bei geschlossener Sidebar
    // reicht NICHT); an der UI selbst aendert sich nichts (keine sichtbaren Nummern).
    if (!sidebarVisible()) return;
    const idx = parseInt(e.key, 10) - 1;
    if (idx >= state.lists.length) return;
    e.preventDefault();
    const id = state.lists[idx].id;
    state.activeId = state.activeId === id ? null : id;
    state.doneOpen = false; state.editingId = null; state.selectedId = null;
    render();
  }
  // Strg+C ist bewusst KEIN App-Shortcut mehr (Phase 6.5): kopiert wird nur
  // noch gezielt die ausgewaehlte Aufgabe ueber den Rail-Button (Gate G23).
  // Der Panik-Trigger hat bewusst KEIN Tastenkuerzel (nur ueber den Rail-Knopf,
  // zweistufig entsichert).
  else if (!meta && e.key === '?') { state.modal = 'shortcuts'; render(); }
  else if (!meta && k === 'f') {
    // Fokusmodus braucht eine offene Liste; Verlassen geht immer.
    if (!state.focus && !activeList()) return;
    state.focus = !state.focus; render();
  }
  else if (!meta && k === 'g') { setOnline(!state.online); }
  else if (meta && e.shiftKey && k === 'n') {
    // Strg+Shift+N: "New list"-Eingabefeld umschalten. Erster Druck oeffnet es,
    // ein zweiter schliesst es wieder (wie Escape, ohne zu committen), damit die
    // App gut nur mit der Tastatur bedienbar ist. preventDefault unterdrueckt das
    // Browser-Standard (neues Fenster) und verhindert, dass das ausloesende "n"
    // als erster Buchstabe im frisch fokussierten Eingabefeld landet.
    e.preventDefault();
    state.adding = !state.adding; render();
  }
  else if (meta && k === 'n') {
    // Strg+N: "New task"-Eingabefeld in der offenen Liste umschalten. Erster
    // Druck oeffnet, ein zweiter schliesst wieder. Braucht eine offene Liste.
    // Ueber den Dock-"+"-Knopf, damit die Auf/Zu-Animation erhalten bleibt und
    // der Fokus in-place gesetzt wird (dieselbe Logik wie ein Klick darauf).
    e.preventDefault();
    if (!activeList()) return;
    const addBtn = document.querySelector('.dock-add');
    if (addBtn) addBtn.click();
    else {
      state.addingTask = !state.addingTask;
      if (state.addingTask) refocusNewTask = true;
      render();
    }
  }
}

// Doppelklick auf Aufgaben-Karten wird NICHT ueber das native dblclick-Event
// behandelt, sondern von Hand in der Klick-Delegation (case 'select-task'):
// die Einzelklicks rendern neu und haengen die Karte aus dem DOM, das native
// dblclick geht dadurch verloren. Merker fuer die Von-Hand-Erkennung:
let _lastTaskClick = { id: null, t: 0 };

// ===========================================================================
// Drag & Drop, Reihenfolge offener Aufgaben (Bridge: reorder)
// ===========================================================================
let dragId = null;
function onDragStart(e) {
  const row = e.target.closest('.task[draggable="true"]');
  if (!row) return;
  dragId = row.dataset.taskId;
  row.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
}
function onDragOver(e) {
  const listEl = e.target.closest('[data-tasklist="open"]');
  if (!listEl || dragId == null) return;
  e.preventDefault();
  const dragging = listEl.querySelector('.task.dragging');
  if (!dragging) return;
  const after = [...listEl.querySelectorAll('.task:not(.dragging)')].find((el) => {
    const r = el.getBoundingClientRect();
    return e.clientY < r.top + r.height / 2;
  });
  if (after) listEl.insertBefore(dragging, after);
  else listEl.appendChild(dragging);
}
async function onDrop(e) {
  const listEl = e.target.closest('[data-tasklist="open"]');
  if (!listEl || dragId == null) return;
  e.preventDefault();
  const ids = [...listEl.querySelectorAll('.task')].map((el) => el.dataset.taskId);
  const list = activeList();
  list.open.sort((x, y) => ids.indexOf(x.id) - ids.indexOf(y.id));
  // G20/N11.2.2: ordered_ids muss EXAKT die gesamte Aufgabenmenge der Liste
  // sein (offen + erledigt); die Sektionstrennung macht das Backend anhand
  // von done. Die erledigten haengen in ihrer aktuellen Reihenfolge hinten an.
  const res = await api().reorder(list.id, [...ids, ...list.done.map((t) => t.id)]);
  dragId = null;
  if (handleError(res)) return;
  render();
}
function onDragEnd() {
  const d = document.querySelector('.task.dragging');
  if (d) d.classList.remove('dragging');
  dragId = null;
}

// ===========================================================================
// Backend -> Frontend Events (Bauplan B.2)
// ===========================================================================
window.noa = {
  onLocked() { state.locked = true; lockUnlocking = false; render(); },
};

// ===========================================================================
// Boot
// ===========================================================================
async function boot() {
  try {
    const st = await api().get_state();
    Object.assign(state, st);
    // Pin-Zustand der Tool-Rail aus den Settings rekonstruieren (als String abgelegt).
    // Sidebar-Breite wiederherstellen (als String gespeichert).
    const sw = parseInt(state.settings.sidebarWidth || '256', 10);
    state.sidebarWidth = (sw >= 180 && sw <= 520) ? sw : 256;
    // Beim Start immer als leere Arbeitsflaeche: Sidebar eingeklappt, Tool-Rail
    // nicht fixiert, keine Liste geoeffnet. Das ist bewusst unabhaengig von den
    // zuletzt gespeicherten Settings (nur In-Memory erzwungen, die persistierten
    // Werte wie sidebarWidth bleiben unangetastet). Werkzeuge holt man sich erst
    // bei Bedarf auf die Flaeche.
    state.settings.sidebar = 'closed';
    state.railPinned = false;
    state.focus = false;
    state.activeId = null;
  } catch (err) {
    root.innerHTML = '<pre style="padding:24px">boot error: ' + err + '</pre>';
    return;
  }
  document.addEventListener('pointerdown', () => _ac(), { once: true });
  document.addEventListener('click', onClick);
  document.addEventListener('contextmenu', onContextMenu);
  document.addEventListener('keydown', onKeyGlobal);
  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('dragstart', onDragStart);
  document.addEventListener('dragover', onDragOver);
  document.addEventListener('drop', onDrop);
  document.addEventListener('dragend', onDragEnd);
  render();
  if (state.online) startWifiPoll();
}

if (window.pywebview) boot();
else window.addEventListener('pywebviewready', boot);
