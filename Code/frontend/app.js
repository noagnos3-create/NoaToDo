// NoaToDo — Frontend-Logik (Bauplan Phase 6).
// Vanilla-Portierung der React-Komponenten aus "NoaToDo UI Konzept.html".
// Das Backend (pywebview.api.*) ist die Wahrheitsquelle; state ist nur Cache.
'use strict';

// ===========================================================================
// Icons — 1:1 aus dem Konzept (Anhang 2). 24er-Grid, Strichstärke 1.7.
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
  Bell: _svg(_p('M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6z') + _p('M10 19a2 2 0 0 0 4 0')),
  Plus: _svg(_l(12, 5, 12, 19) + _l(5, 12, 19, 12)),
  Check: _svg(_p('M5 12l5 5L19 6')),
  Gear: _svg(_c(12, 12, 3) + _p('M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1')),
  Chevron: _svg(_p('M6 9l6 6 6-6')),
  Grip: _svg(_c(9, 6, 1) + _c(15, 6, 1) + _c(9, 12, 1) + _c(15, 12, 1) + _c(9, 18, 1) + _c(15, 18, 1), { fill: 'currentColor', stroke: 'none' }),
  Plane: _svg(_p('M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z')),
  Wifi: _svg(_p('M5 12.5a10 10 0 0 1 14 0M8 15.8a5.5 5.5 0 0 1 8 0') + _c(12, 19, 0.6), { fill: 'currentColor' }),
  Expand: _svg(_p('M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5')),
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
};

const ACCENTS = ['#d97757', '#c75d3a', '#5a9d6b', '#4a86c5', '#d4a23c', '#a66a9c'];

// ===========================================================================
// Zustand (nur Cache; Wahrheit bleibt das Backend)
// ===========================================================================
let state = {
  lists: [], activeId: null, settings: {}, online: true, locked: false,
  menu: null,        // 'notif' | 'profile'
  modal: null,       // 'emergency' | 'status' | 'rename' | 'delete' | 'shortcuts' | 'settings'
  focus: false,
  colorOpen: false,
  adding: false,     // Inline-"New list"-Eingabe sichtbar
  doneOpen: false,   // "Completed"-Sektion eingeklappt?
};

const root = document.getElementById('root');
const api = () => window.pywebview.api;
const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');
const activeList = () => state.lists.find((l) => l.id === state.activeId) || state.lists[0] || null;

// ===========================================================================
// Render-Funktionen (1:1 zu den Konzept-Komponenten)
// ===========================================================================
function renderHeader() {
  const I = Icons;
  const notifCount = 3;
  return `
    <header class="header">
      <button class="h-icon-btn" data-act="toggle-sidebar" title="Toggle lists">
        ${state.focus || !sidebarVisible() ? I.Menu : I.Close}
      </button>
      <div class="brand">
        <span class="brand-mark">${I.Shield}</span>
        <span class="brand-name">Noa<b>ToDo</b></span>
        <span class="brand-status mono"><span class="dot"></span>LOCAL · ENCRYPTED</span>
      </div>
      <div class="header-spacer"></div>
      <div class="header-right">
        <div class="notif-wrap">
          <button class="h-icon-btn" data-act="open-notif" title="Notifications">
            ${I.Bell}${notifCount > 0 ? `<span class="badge">${notifCount}</span>` : ''}
          </button>
          ${state.menu === 'notif' ? renderNotifMenu() : ''}
        </div>
        <div class="notif-wrap">
          <button class="avatar" data-act="open-profile" title="Profile">NA</button>
          ${state.menu === 'profile' ? renderProfileMenu() : ''}
        </div>
      </div>
    </header>`;
}

function sidebarVisible() {
  return (state.settings.sidebar !== 'closed') && !state.focus;
}

function renderSidebar() {
  const I = Icons;
  const items = state.lists.map((l) => {
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
    </aside>`;
}

function renderTask(t) {
  const I = Icons;
  const meta = (t.meta && !t.done) ? `<span class="t-meta">${esc(t.meta)}</span>` : '';
  const draggable = t.done ? '' : 'draggable="true"';
  return `
    <div class="task${t.done ? ' done' : ''}" data-task-id="${esc(t.id)}" ${draggable}>
      <button class="check" data-act="toggle-task" data-id="${esc(t.id)}" aria-label="toggle">${I.Check}</button>
      <span class="t-text">${esc(t.text)}</span>
      ${meta}
      <span class="t-grip">${I.Grip}</span>
    </div>`;
}

function renderMain() {
  const I = Icons;
  const list = activeList();
  if (!list) {
    return `<main class="main"><div class="main-inner">
      <div class="empty-note">// no lists yet — create one in the sidebar</div>
    </div></main>`;
  }
  const airplane = !state.online;

  const openSection = list.open.length === 0
    ? `<div class="empty-note">// nothing open — you're all caught up</div>`
    : `<div class="task-list" data-tasklist="open">${list.open.map(renderTask).join('')}</div>`;

  const doneSection = list.done.length > 0 ? `
    <div class="section">
      <button class="section-head${state.doneOpen ? '' : ' collapsed'}" data-act="toggle-done">
        <span class="chev">${I.Chevron}</span>
        <span class="s-title">Completed</span>
        <span class="s-count">${list.done.length}</span>
        <span class="line"></span>
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
        <div class="banner-row">
          <button class="airplane-pill${airplane ? '' : ' online'}" data-act="net">
            ${airplane ? I.Plane : I.Globe}${airplane ? 'Airplane mode on' : 'Online'}
          </button>
        </div>
        <h1 class="list-title">${esc(list.name)}</h1>
        <div class="title-meta">
          <span class="tag">${list.open.length} open</span>
          <span class="sep"></span>
          <span class="tag">${list.done.length} done</span>
          <span class="sep"></span>
          <span class="tag" style="color:${list.synced ? 'var(--secure)' : 'var(--text-faint)'}">
            ${list.synced ? '↯ synced from MS To Do' : '✦ local only'}
          </span>
        </div>
        <div class="section">
          <div class="section-head">
            <span class="s-title">Open tasks</span>
            <span class="s-count">${list.open.length}</span>
            <span class="line"></span>
          </div>
          ${openSection}
          <div class="new-task" data-act="focus-newtask">
            <span class="plus">${I.Plus}</span>
            <input id="new-task-input" placeholder="New task…" />
            <span class="kbd">↵</span>
          </div>
        </div>
        ${doneSection}
      </div>
    </main>`;
}

function renderToolbar() {
  const I = Icons;
  if (state.focus) {
    return `
      <div class="toolbar">
        <div class="toolbar-rail" style="background:transparent;border:none;box-shadow:none">
          <button class="tool-btn" data-act="exit-focus" title="Exit focus (Esc)">
            ${I.Close}<span class="tip">Exit focus<span class="k">Esc</span></span>
          </button>
        </div>
      </div>`;
  }
  const btn = (icon, label, hotkey, act, opt) => {
    opt = opt || {};
    const cls = 'tool-btn' + (opt.danger ? ' danger' : '') + (opt.active ? ' active' : '');
    const k = hotkey ? `<span class="k">${hotkey}</span>` : '';
    return `<button class="${cls}" data-act="${act}">${icon}<span class="tip">${label}${k}</span></button>`;
  };
  return `
    <div class="toolbar">
      <div class="toolbar-rail">
        ${btn(I.Expand, 'Focus mode', 'F', 'tb-focus')}
        ${btn(I.Palette, 'Accent color', '', 'tb-color', { active: state.colorOpen })}
        ${btn(I.Share, 'Export', '⌘E', 'tb-export')}
        ${btn(I.Help, 'Shortcuts', '?', 'tb-help')}
        <div class="tool-sep"></div>
        ${btn(state.locked ? I.Lock : I.Unlock, 'Lock app', '⌘L', 'tb-lock')}
        ${btn(I.Alert, 'Emergency', '⌘⇧!', 'tb-emergency', { danger: true })}
        <div class="tool-sep"></div>
        ${btn(I.Copy, 'Copy list', '⌘C', 'tb-copy')}
        ${btn(I.Pencil, 'Rename list', '', 'tb-rename')}
        ${btn(I.Trash, 'Delete list', '', 'tb-delete')}
        <div class="tool-sep"></div>
        ${btn(I.Diag, 'App status', '', 'tb-status')}
        ${btn(I.Globe, state.online ? 'Go offline' : 'Go online', 'G', 'net', { active: state.online })}
      </div>
    </div>`;
}

function renderAccentPop() {
  if (!state.colorOpen) return '';
  const right = state.settings.toolbar === 'floating' ? 84 : 72;
  const sw = ACCENTS.map((c) =>
    `<button class="swatch${c === state.settings.accent ? ' sel' : ''}" data-act="set-accent" data-color="${c}" style="background:${c}"></button>`
  ).join('');
  return `
    <div class="accent-pop" style="position:fixed;top:118px;right:${right}px;z-index:32;
      background:var(--surface);border:1px solid var(--border);border-radius:14px;
      box-shadow:var(--shadow-lg);padding:12px;animation:rise .16s ease">
      <div class="tag" style="color:var(--text-faint);padding:2px 4px 8px">Accent</div>
      <div class="swatches">${sw}</div>
    </div>`;
}

function renderNotifMenu() {
  const I = Icons;
  const items = [
    { t: 'Reminder: "Going Zero"', s: 'Reading List · due today', dot: 'var(--accent)' },
    { t: 'Sync complete', s: 'Microsoft To Do · 4 lists · 2m ago', dot: 'var(--secure)' },
    { t: 'Backup written', s: 'tasks.db · local · 14:02', dot: 'var(--text-faint)' },
  ];
  const rows = items.map((n) => `
    <button class="menu-item notif-item">
      <span class="m-dot" style="background:${n.dot};margin-left:0;margin-top:5px"></span>
      <span class="n-body"><span style="color:var(--text)">${esc(n.t)}</span><small>${esc(n.s)}</small></span>
    </button>`).join('');
  return `
    <div class="menu" style="right:50px" data-keep>
      <div class="menu-head">${I.Bell}<b style="font-size:13px">Notifications</b>
        <span class="tag" style="margin-left:auto;color:var(--text-faint)">3 new</span></div>
      ${rows}
    </div>`;
}

function renderProfileMenu() {
  const I = Icons;
  return `
    <div class="menu" style="right:6px" data-keep>
      <div class="menu-head">
        <span class="avatar" style="width:32px;height:32px">NA</span>
        <span class="n-body"><b style="font-size:13px">Noa Andersen</b><small class="mono" style="color:var(--text-faint)">signed in · local</small></span>
      </div>
      <button class="menu-item">${I.User} Account</button>
      <button class="menu-item">${I.Shield} Privacy &amp; data</button>
      <button class="menu-item">${I.Download} Export database</button>
      <button class="menu-item" data-act="sign-out">${I.Logout} Sign out</button>
    </div>`;
}

function scrim(inner) {
  return `<div class="scrim" data-act="scrim-close"><div data-keep>${inner}</div></div>`;
}

function renderModal() {
  const I = Icons;
  const list = activeList();
  switch (state.modal) {
    case 'emergency':
      return scrim(`
        <div class="modal modal-emergency">
          <div class="modal-stripe"></div>
          <div class="modal-body">
            <div class="modal-icon danger">${I.Alert}</div>
            <h3>Panic — lock everything?</h3>
            <p>This immediately locks NoaToDo, drops the in-memory cache, and pulls the local database offline. Cloud sync stays paused until you unlock with your passphrase.
            Nothing is deleted — <span class="mono">tasks.db</span> stays encrypted on this machine.</p>
          </div>
          <div class="modal-actions">
            <button class="btn" data-act="modal-close">Cancel</button>
            <button class="btn btn-danger" data-act="do-panic">Lock now</button>
          </div>
        </div>`);
    case 'status': {
      const online = state.online;
      const rows = [
        ['Local database', 'tasks.db', 'var(--secure)', 'healthy'],
        ['Encryption', 'AES-256 + ChaCha20 · Argon2id', 'var(--secure)', 'active'],
        ['Microsoft Graph', online ? 'Tasks.Read · token valid' : 'offline — sync paused', online ? 'var(--secure)' : 'var(--text-faint)', online ? 'connected' : 'paused'],
        ['Last sync', online ? 'while online' : 'while online', 'var(--text-faint)', ''],
        ['WebView2 runtime', 'system', 'var(--secure)', 'ok'],
      ];
      const body = rows.map((r, i) => `
        <div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:${i < rows.length - 1 ? '1px dashed var(--border)' : 'none'}">
          <span style="font-size:13.5px;font-weight:500">${r[0]}</span>
          <span class="mono" style="margin-left:auto;font-size:11px;color:var(--text-faint)">${r[1]}</span>
          ${r[3] ? `<span class="tag" style="color:${r[2]};min-width:64px;text-align:right">${r[3]}</span>` : ''}
        </div>`).join('');
      return scrim(`
        <div class="modal">
          <div class="modal-body">
            <div class="modal-icon accent">${I.Diag}</div>
            <h3>App status</h3>
            <div style="margin-top:16px;display:flex;flex-direction:column;gap:2px">${body}</div>
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
    case 'delete':
      return scrim(`
        <div class="modal">
          <div class="modal-body">
            <div class="modal-icon danger">${I.Trash}</div>
            <h3>Delete &ldquo;${esc(list ? list.name : '')}&rdquo;?</h3>
            <p>This removes the list and its tasks from your local database. Lists synced from Microsoft To Do reappear on the next sync.</p>
          </div>
          <div class="modal-actions">
            <button class="btn" data-act="modal-close">Cancel</button>
            <button class="btn btn-danger" data-act="do-delete">Delete</button>
          </div>
        </div>`);
    case 'shortcuts': {
      const sc = [
        ['New task', ['↵']], ['New list', ['N']],
        ['Toggle sidebar', ['⌘', 'B']], ['Focus mode', ['F']],
        ['Lock app', ['⌘', 'L']], ['Emergency lock', ['⌘', '⇧', '!']],
        ['Export list', ['⌘', 'E']], ['Copy list', ['⌘', 'C']],
        ['Toggle theme', ['⌘', 'J']], ['Online / offline', ['G']],
      ];
      const grid = sc.map((s) => `
        <div class="sc-row"><span>${s[0]}</span>
          <span class="sc-keys">${s[1].map((k) => `<kbd>${k}</kbd>`).join('')}</span></div>`).join('');
      return scrim(`
        <div class="modal" style="width:min(560px,100%)">
          <div class="modal-body" style="padding-bottom:4px">
            <div class="modal-icon accent">${I.Help}</div>
            <h3>Keyboard shortcuts</h3>
          </div>
          <div class="shortcuts-grid">${grid}</div>
        </div>`);
    }
    case 'settings':
      return scrim(renderSettings());
    default:
      return '';
  }
}

// Settings-Modal: steuert die persistierten Einstellungen (Bauplan B.6).
function renderSettings() {
  const I = Icons;
  const s = state.settings;
  const seg = (key, opts, cur) => `<div class="seg">` + opts.map(([val, label]) =>
    `<button class="seg-btn${cur === val ? ' on' : ''}" data-act="set" data-key="${key}" data-value="${val}">${label}</button>`
  ).join('') + `</div>`;
  const sw = ACCENTS.map((c) =>
    `<button class="swatch${c === s.accent ? ' sel' : ''}" data-act="set-accent" data-color="${c}" style="background:${c}"></button>`
  ).join('');
  const row = (label, control) =>
    `<div style="display:flex;align-items:center;gap:12px;padding:11px 0;border-bottom:1px dashed var(--border)">
       <span style="font-size:13.5px;font-weight:500">${label}</span>
       <span style="margin-left:auto">${control}</span></div>`;
  return `
    <div class="modal">
      <div class="modal-body">
        <div class="modal-icon accent">${I.Gear}</div>
        <h3>Settings</h3>
        <div style="margin-top:14px;display:flex;flex-direction:column">
          ${row('Theme', seg('dark', [['true', 'Dark'], ['false', 'Light']], String(!!s.dark)))}
          ${row('Density', seg('density', [['comfortable', 'Comfortable'], ['compact', 'Compact']], s.density))}
          ${row('Toolbar', seg('toolbar', [['floating', 'Floating'], ['flush', 'Flush']], s.toolbar))}
          ${row('Sidebar', seg('sidebar', [['open', 'Open'], ['closed', 'Closed']], s.sidebar))}
          <div style="display:flex;align-items:center;gap:12px;padding:11px 0">
            <span style="font-size:13.5px;font-weight:500">Accent</span>
            <span style="margin-left:auto"><div class="swatches">${sw}</div></span>
          </div>
        </div>
      </div>
      <div class="modal-actions"><button class="btn btn-primary" data-act="modal-close">Done</button></div>
    </div>`;
}

function renderLock() {
  if (!state.locked) return '';
  const I = Icons;
  return `
    <div class="lock-screen">
      <div class="lock-card">
        <div class="lock-ring">${I.Lock}</div>
        <h2>NoaToDo is locked</h2>
        <p>LOCAL VAULT · ENCRYPTED · OFFLINE</p>
        <div class="lock-dots">${[0, 1, 2, 3].map((i) => `<i class="${i < lockDots ? 'fill' : ''}"></i>`).join('')}</div>
        <button class="lock-btn" data-act="lock-tap">${lockDots === 0 ? 'Enter passphrase' : lockDots >= 4 ? 'Unlocking…' : 'Tap to continue'}</button>
      </div>
    </div>`;
}
let lockDots = 0;

// ===========================================================================
// Haupt-Render
// ===========================================================================
function applyChrome() {
  root.setAttribute('data-theme', state.settings.dark ? 'dark' : 'light');
  root.setAttribute('data-density', state.settings.density || 'comfortable');
  root.setAttribute('data-toolbar', state.settings.toolbar || 'floating');
  root.setAttribute('data-sidebar', sidebarVisible() ? 'open' : 'closed');
  root.style.setProperty('--accent', state.settings.accent || '#d97757');
}

function render() {
  applyChrome();
  root.innerHTML =
    renderHeader() +
    renderSidebar() +
    renderMain() +
    renderToolbar() +
    renderAccentPop() +
    renderModal() +
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
  if (res && res.error) return pushToast(res.message || 'Error');
  list.open.push(res);
  refocusNewTask = true;
  render();
}

async function commitNewList(name) {
  name = (name || '').trim();
  state.adding = false;
  if (!name) { render(); return; }
  const res = await api().add_list(name);
  if (res && res.error) { render(); return pushToast(res.message || 'Error'); }
  state.lists.push(res);
  state.activeId = res.id;
  render();
  pushToast('List created', name);
}

async function toggleTask(id) {
  const res = await api().toggle_task(id);
  if (res && res.error) return pushToast(res.message || 'Error');
  // Aufgabe lokal zwischen open/done verschieben (wie im Konzept).
  for (const l of state.lists) {
    let i = l.open.findIndex((x) => x.id === id);
    if (i >= 0) { const [t] = l.open.splice(i, 1); t.done = true; l.done.unshift(t); break; }
    i = l.done.findIndex((x) => x.id === id);
    if (i >= 0) { const [t] = l.done.splice(i, 1); t.done = false; l.open.push(t); break; }
  }
  render();
}

async function doRename(name) {
  const list = activeList();
  const res = await api().rename_list(list.id, name);
  if (res && res.error) return pushToast(res.message || 'Error');
  list.name = name;
  state.modal = null;
  render();
  pushToast('List renamed', name);
}

async function doDelete() {
  const list = activeList();
  const res = await api().delete_list(list.id);
  if (res && res.error) return pushToast(res.message || 'Error');
  state.lists = state.lists.filter((l) => l.id !== list.id);
  if (!state.lists.find((l) => l.id === state.activeId)) {
    state.activeId = state.lists.length ? state.lists[0].id : null;
  }
  state.modal = null;
  render();
  pushToast('List deleted');
}

async function setOnline(flag) {
  const res = await api().set_online(flag);
  state.online = res && typeof res.online === 'boolean' ? res.online : flag;
  render();
  pushToast(flag ? 'Back online — syncing' : 'Going offline', flag ? 'MS To Do' : 'sync paused');
}

async function setSetting(key, value) {
  // Typkonvertierung für die Anwendung im Frontend.
  let applied = value;
  if (key === 'dark') applied = (value === true || value === 'true');
  state.settings[key] = applied;
  if (key === 'dark') flashThemeSwitch();
  applyChrome();
  await api().set_setting(key, value);
  render();
}

async function setAccent(color) {
  state.settings.accent = color;
  root.style.setProperty('--accent', color);
  await api().set_setting('accent', color);
  render();
}

async function doExport() {
  const list = activeList();
  if (!list) return;
  const res = await api().export_list(list.id, 'md');
  if (res && res.error) return pushToast(res.message || 'Error');
  // Phase 7 ergänzt den echten Speicher-Dialog; vorerst Bestätigung.
  pushToast('Exported list', res.filename);
}

async function doCopy() {
  const list = activeList();
  if (!list) return;
  const res = await api().copy_list(list.id);
  if (res && res.error) return pushToast(res.message || 'Error');
  try { await navigator.clipboard.writeText(res.text); } catch (e) { /* ignore */ }
  pushToast('Copied to clipboard', list.open.length + ' tasks');
}

async function doLock() {
  await api().lock();
  state.locked = true; lockDots = 0;
  render();
}

async function doPanic() {
  await api().panic();
  state.locked = true; state.online = false; state.modal = null; lockDots = 0;
  render();
}

async function lockTap() {
  lockDots += 1;
  if (lockDots >= 4) {
    lockDots = 4; render();
    const res = await api().unlock('');   // Phase 11: echte Passphrase
    setTimeout(() => {
      state.locked = !(res && res.ok);
      lockDots = 0;
      render();
    }, 280);
  } else {
    render();
  }
}

// Theme-Wechsel-Flackern vermeiden (ein Frame ohne Transitions).
function flashThemeSwitch() {
  root.classList.add('theme-switching');
  requestAnimationFrame(() => requestAnimationFrame(() => root.classList.remove('theme-switching')));
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

// ===========================================================================
// Klick-Delegation
// ===========================================================================
function closeMenusIfOutside(e, a) {
  let changed = false;
  const act = a ? a.dataset.act : null;
  if (state.menu && !e.target.closest('[data-keep]') && act !== 'open-notif' && act !== 'open-profile') {
    state.menu = null; changed = true;
  }
  if (state.colorOpen && !e.target.closest('.accent-pop') && act !== 'tb-color') {
    state.colorOpen = false; changed = true;
  }
  return changed;
}

async function onClick(e) {
  const a = e.target.closest('[data-act]');
  const needRender = closeMenusIfOutside(e, a);
  if (!a) { if (needRender) render(); return; }
  const act = a.dataset.act;
  const id = a.dataset.id;

  switch (act) {
    case 'toggle-sidebar':
      state.focus = false;
      state.settings.sidebar = sidebarVisible() ? 'closed' : 'open';
      api().set_setting('sidebar', state.settings.sidebar);
      render(); break;
    case 'open-notif': state.menu = state.menu === 'notif' ? null : 'notif'; render(); break;
    case 'open-profile': state.menu = state.menu === 'profile' ? null : 'profile'; render(); break;
    case 'sign-out': state.menu = null; await api().sign_out(); render(); pushToast('Signed out'); break;
    case 'select-list': state.activeId = id; state.doneOpen = false; render(); break;
    case 'new-list-show': state.adding = true; render(); break;
    case 'settings': state.menu = null; state.modal = 'settings'; render(); break;
    case 'toggle-task': await toggleTask(id); break;
    case 'toggle-done': state.doneOpen = !state.doneOpen; render(); break;
    case 'focus-newtask': { const i = document.getElementById('new-task-input'); if (i) i.focus(); break; }
    case 'net': await setOnline(!state.online); break;
    case 'tb-focus': state.focus = !state.focus; state.menu = null; render(); break;
    case 'tb-color': state.colorOpen = !state.colorOpen; state.menu = null; render(); break;
    case 'tb-export': await doExport(); break;
    case 'tb-help': state.modal = 'shortcuts'; render(); break;
    case 'tb-lock': await doLock(); break;
    case 'tb-emergency': state.modal = 'emergency'; render(); break;
    case 'tb-copy': await doCopy(); break;
    case 'tb-rename': state.modal = 'rename'; render(); break;
    case 'tb-delete': state.modal = 'delete'; render(); break;
    case 'tb-status': state.modal = 'status'; render(); break;
    case 'exit-focus': state.focus = false; render(); break;
    case 'set-accent': await setAccent(a.dataset.color); break;
    case 'set': await setSetting(a.dataset.key, a.dataset.value); break;
    case 'scrim-close':
    case 'modal-close': state.modal = null; render(); break;
    case 'do-rename': { const i = document.getElementById('rename-input'); if (i && i.value.trim()) await doRename(i.value.trim()); break; }
    case 'do-delete': await doDelete(); break;
    case 'do-panic': await doPanic(); break;
    case 'lock-tap': await lockTap(); break;
    default: if (needRender) render();
  }
}

// ===========================================================================
// Tastenkürzel (Bauplan B.5)
// ===========================================================================
function onKeyGlobal(e) {
  const typing = /^(INPUT|TEXTAREA)$/.test(e.target.tagName);
  const meta = e.metaKey || e.ctrlKey;
  if (e.key === 'Escape') {
    state.menu = null; state.modal = null; state.colorOpen = false;
    state.focus = false; state.adding = false; render(); return;
  }
  if (typing) return;
  if (state.locked) return;
  const k = e.key.toLowerCase();
  if (meta && k === 'b') { e.preventDefault(); state.focus = false; state.settings.sidebar = sidebarVisible() ? 'closed' : 'open'; api().set_setting('sidebar', state.settings.sidebar); render(); }
  else if (meta && k === 'j') { e.preventDefault(); setSetting('dark', !state.settings.dark); }
  else if (meta && k === 'l') { e.preventDefault(); doLock(); }
  else if (meta && k === 'e') { e.preventDefault(); doExport(); }
  else if (meta && k === 'c') { e.preventDefault(); doCopy(); }
  else if (meta && e.shiftKey && (e.key === '!' || k === '1')) { e.preventDefault(); state.modal = 'emergency'; render(); }
  else if (!meta && e.key === '?') { state.modal = 'shortcuts'; render(); }
  else if (!meta && k === 'f') { state.focus = !state.focus; render(); }
  else if (!meta && k === 'g') { setOnline(!state.online); }
  else if (!meta && k === 'n') { state.adding = true; render(); }
}

// ===========================================================================
// Drag & Drop — Reihenfolge offener Aufgaben (Bridge: reorder)
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
  await api().reorder(list.id, ids);
  dragId = null;
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
  onSyncDone(summary) {
    if (summary && summary.changed) refreshLists();
    pushToast('Sync complete', summary && summary.lists ? summary.lists + ' lists' : '');
  },
  onNotification(payload) {
    if (payload && payload.title) pushToast(payload.title, payload.body);
  },
  onLocked() { state.locked = true; lockDots = 0; render(); },
};

async function refreshLists() {
  const lists = await api().get_lists();
  if (Array.isArray(lists)) { state.lists = lists; render(); }
}

// ===========================================================================
// Boot
// ===========================================================================
async function boot() {
  try {
    const st = await api().get_state();
    Object.assign(state, st);
    if (state.lists.length && !state.activeId) state.activeId = state.lists[0].id;
  } catch (err) {
    root.innerHTML = '<pre style="padding:24px">boot error: ' + err + '</pre>';
    return;
  }
  document.addEventListener('click', onClick);
  document.addEventListener('keydown', onKeyGlobal);
  document.addEventListener('dragstart', onDragStart);
  document.addEventListener('dragover', onDragOver);
  document.addEventListener('drop', onDrop);
  document.addEventListener('dragend', onDragEnd);
  render();
}

if (window.pywebview) boot();
else window.addEventListener('pywebviewready', boot);
