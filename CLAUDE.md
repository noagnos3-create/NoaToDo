# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Writing style (mandatory)

The user does not like dashes (Gedankenstriche). Do NOT use the em-dash (Unicode U+2014) or the en-dash (Unicode U+2013) anywhere: not in code, comments, docstrings, UI strings, commit messages, documentation, or any file in this repo, and not in chat replies. Use commas, colons, parentheses, or separate sentences instead. For numeric ranges use "bis"/"to" or a plain ASCII hyphen (e.g. "0-11"). Plain ASCII hyphens in compound words and code identifiers are fine; only the two long dashes are forbidden.

## Project status

Locally-usable milestone reached (Phases 1 to 6 of the Bauplan, plus the Phase 6.5 UX/security follow-ups: inline task edit via double-click, per-task delete button, click-to-select tasks, hardened single-task copy via `copy_task` (gate G23: backend-side Win32 clipboard, excluded from Win+V history and cloud clipboard, auto-clear after 60 s), Ctrl+C app shortcut removed entirely, contextual rail pencil (selected task: inline edit; otherwise: rename list), mini mode always-on-top). Implemented: `db.py`, `api.py`, `main.py`, `frontend/index.html`, `frontend/style.css`, `frontend/app.js`.

Screenshot protection (gate G26, `SetWindowDisplayAffinity` / `WDA_EXCLUDEFROMCAPTURE`) is **removed from the code and should stay removed** (there is no screenshot code anywhere in `main.py` or `backend/`; commit 45820c2 took out the last attempt). It caused recurring problems: on some GPU/driver combos the affinity flag blocks WebView2 from rendering at all (window stays white / "not responding"), and its startup wiring previously deadlocked the message loop (a blocking `_get_hwnd(window, wait=True)` plus a cross-thread native call on the on_start worker thread). It also blacks out the window in legitimate screen sharing/recording and does nothing against a phone camera. Do not reintroduce it.

**WebView2 profile + single instance (gates G14 partial, G19 done, pulled forward 2026-06-20):** `main.py` no longer runs WebView2 in private mode. It starts PyWebView with `private_mode=False, storage_path=PROFILE_DIR` where `PROFILE_DIR = %LOCALAPPDATA%\NoaToDo\webview`, a single fixed, user-private profile folder. This replaced the old per-start temp profile under `%TEMP%\tmp...\EBWebView` that piled up on hard exit (real: dozens of leftovers, start hangs over a minute). `_cleanup_stale_webview_profiles()` removes those old temp profiles once at startup (only `tmp*` dirs carrying an `EBWebView` signature; locked ones are skipped). A named single-instance mutex (`_acquire_single_instance`, `Local\NoaToDoSingleton`, gate G19) makes a second instance show a message box and exit; the fixed folder is only safe together with this mutex (two instances would lock/corrupt the shared profile). The profile holds only non-sensitive UI cache (own HTML/CSS/JS/fonts, GPU state), never task content. **Still open for Phase 11 (gate G14 rest):** securely wipe `PROFILE_DIR` on `lock()`/`panic()`/clean quit, and clear orphaned `msedgewebview2.exe` that survive a hard kill and lock the folder (next start would otherwise fail with `0x800700AA` ERROR_BUSY). Do NOT reintroduce `private_mode=True`.

**Phase 7 is OPEN:** `export_list` generates content, but no file is ever written (no save dialog); see gates G20-G22 in the Bauplan. There is intentionally no whole-list copy anymore (`copy_list` was removed; export covers that). **Still empty 1-line stubs:** `backend/auth.py`, `backend/graph_sync.py`, `backend/notify.py`, `backend/security.py`, i.e. MSAL login, Graph sync, notifications, and the lock/panic + dual-layer-encryption work (Phases 8-11) are **not yet built**.

Consequently the running app today is single-layer only: `db.connect()` opens SQLCipher with a fixed `DEV_AES_KEY` (`db.py`). The working DB file on disk is `data/tasks.db` (plain SQLCipher, no ChaCha20 wrapper yet). The ChaCha20 outer wrapper, Argon2id key derivation, passphrase unlock, and lock triggers described under "Critical constraints" / "Lock policy" are the **target design**, not the current behavior. `api.lock/unlock/panic/sign_in/sign_out/sync_now` are placeholders; the lock is currently frontend-only and NOT enforced by the backend (gate G13). Treat those sections as the spec to build toward.

**Security gates:** the Bauplan defines mandatory gates G1-G12 plus the 2026-06-10 audit addendum G13-G25 (section "NACHTRAG: Gates G13 bis G25" in B.9). None of them are optional. When implementing any phase, read its gate list in the Bauplan first; the quick overview table is at the end of the Bauplan.

## Running the app

```powershell
# From Code/ directory (venv must be active or use the venv python directly):
.\venv\Scripts\python.exe main.py

# Enable WebView2 DevTools (main.py reads this env var):
$env:NOATODO_DEBUG = "1"; .\venv\Scripts\python.exe main.py
```

No build step, the frontend is vanilla HTML/CSS/JS loaded directly by PyWebView.

**No test suite exists yet**, there is no `tests/` dir and pytest is not a dependency. There is currently no lint/typecheck config. Verify changes by running the app.

**First run:** if `data/tasks.db` does not exist, `db.seed_if_empty()` inserts demo lists and tasks (Reading List, Ideas, Homework, Programming, Travel, Life Goals) plus default settings. Delete `data/tasks.db` to reset to demo state.

## Architecture

NoaToDo is a **local-first Windows desktop app**: a Python backend and a vanilla JS frontend run together in a single native window via **PyWebView** (uses Windows WebView2, no bundled Chromium).

All application code lives under the `Code/` subdirectory (the repo root holds only `CLAUDE.md`, `Code/`, and `Planung/`). Paths below are relative to `Code/`; this is also why every command runs from `Code/`.

```
Code/                      # run everything from here
├── main.py                # entry point
├── requirements.txt       # loose deps; requirements.lock.txt is the pinned set
├── frontend/              # HTML + CSS + JS, rendering only, holds no truth
│   ├── index.html
│   ├── style.css          # CSS extracted 1:1 from Planung/weiteres/NoaToDo UI Konzept.html
│   ├── app.js             # all UI logic, calls pywebview.api.*
│   ├── icon.ico           # window icon (generated by tools/make_icon.py)
│   └── fonts/             # JetBrains Mono + Space Grotesk as local .woff2
├── backend/
│   ├── api.py             # js_api class, the bridge (see Bridge API below)
│   ├── db.py              # SQLCipher CRUD
│   ├── graph_sync.py      # one-way MS Graph -> SQLite sync (stub)
│   ├── auth.py            # MSAL PKCE login, tokens via keyring (stub)
│   ├── notify.py          # winotify Windows toasts (stub)
│   └── security.py        # lock/unlock/panic, key derivation (stub)
├── data/
│   ├── tasks.db           # current working DB (SQLCipher-AES-256, no outer wrapper yet)
│   └── tasks.db.enc       # Phase 11 target: ChaCha20-Poly1305(SQLCipher blob)
└── tools/
    └── make_icon.py       # one-off build tool: generates frontend/icon.ico from logo
```

## Implementation details

**`@bridge` decorator (`api.py`):** wraps every public `Api` method. Catches `KeyError` as `"not_found"` and any other exception as `"internal"`. All bridge methods return a JSON-serializable dict or `{"error": code, "message": ...}` on failure.

**PyWebView introspection rule:** PyWebView recursively scans all public attributes of the `js_api` object to build the JS bridge. Any attribute that is not a plain method (e.g. the `Window` object stored in `api._window`) must have a `_` prefix; otherwise PyWebView descends into it and may call `evaluate_js` before the window is ready, causing "Main window failed to start". All private state in `Api` uses `_` prefix for this reason.

**WinForms thread safety:** `set_mini` runs in PyWebView's API worker thread. All native window mutations (size, position, `TopMost`, `FormBorderStyle`) must be dispatched to the WinForms UI thread via `form.Invoke(Action(work))`. Direct calls from the worker thread cause the message loop to deadlock.

The same applies to `on_start` and the `_on_setting_change` / `_on_frame_changed` callbacks in `main.py`: they also run on a worker thread. Setting `window.native.Icon` (in `_apply_window_icon`) directly from there deadlocked against the UI thread while it was still initializing the WebView2 control (`edgechromium.py:__init__`), so the window never appeared (intermittently white, "not responding", or nothing, depending on timing; root cause found 2026-06-13 via thread stack dump). Fix: all startup window operations (icon, DWM titlebar theme, `SetWindowPos`) are dispatched through `_run_on_ui_thread(window, work)`, which uses `window.native.BeginInvoke(Action(work))` (async, non-blocking) after the window handle exists. Never call WinForms members on `window.native` directly from a worker thread; route them through `_run_on_ui_thread`.

**`db.edit_task` SQL:** builds a dynamic SET clause from a whitelisted `allowed` set (`{"text", "meta", "due_at", "done"}`). The f-string in the query is safe because only those four column names can appear. This is an intentional tradeoff and not a SQL injection risk.

## Critical constraints

**Dual-layer encryption (mandatory, both layers always present in Phase 11+):**
- Layer 1, SQLCipher (AES-256): the package is **`sqlcipher3-wheels`** (imported as `import sqlcipher3`), not `sqlite3`, `sqlcipher3-binary` has no Windows wheels, `sqlcipher3-wheels` provides them with an identical API. Immediately after `connect()`, set `PRAGMA key = ?` with the derived `aes_key`, then `PRAGMA foreign_keys = ON`.
- Layer 2, ChaCha20-Poly1305 (outer wrapper, `cryptography` package): the permanent file on disk is `data/tasks.db.enc` = ChaCha20-Poly1305(SQLCipher blob). On unlock: unwrap -> write SQLCipher working copy to `%TEMP%` (restricted permissions) -> open with `aes_key`. On lock/quit/panic: re-wrap to `tasks.db.enc` -> securely delete the working copy -> discard keys from RAM.
- Both keys (`aes_key`, `chacha_key`) live only in RAM while unlocked; never written to disk.

**Passphrase / key derivation:** User passphrase -> Argon2id KDF with stored random salt -> derive both `aes_key` and `chacha_key` as separate slices of KDF output. Store only the Argon2 hash (for unlock verification) and the salt. Never store the passphrase or derived keys.

**Microsoft tokens:** Stored in Windows Credential Manager via `keyring`, never in the DB.

**Sync direction:** Strictly one-way, MS Graph -> SQLite. Local tasks (`source='local'`) are never touched by sync and never uploaded. Scope is `Tasks.Read` only. Conflict default: cloud overwrites local changes to imported tasks (see `Bauplan - NoaToDo.md` §D.1).

**Frontend fonts:** JetBrains Mono and Space Grotesk must be local `.woff2` files. No external font CDN, this is a local-first app.

**CSS:** The complete `<style>` section from `Planung/weiteres/NoaToDo UI Konzept.html` is extracted verbatim into `frontend/style.css`. Do not rebuild it from scratch. The design tokens (colors, spacing, fonts) are defined there and must not be reinvented.

**Completion sound:** Checking a task off plays a short "Datenstrom" blip (`playDoneSound` in `app.js`). It is synthesized live with the Web Audio API (square-wave oscillators, no audio file), specifically so it needs no `media-src` and stays compatible with the strict CSP (`default-src 'self'`). Do not replace it with a bundled `.mp3`/`.wav` (that would require loosening the CSP). The `AudioContext` is created lazily on the first check (browsers require a user gesture before audio) and reused. `Code/sound-preview.html` is a standalone dev scratch file for auditioning sound variants, not part of the app and not loaded by it.

## Security rules (mandatory: all untrusted input must follow these)

Task text, list names, and meta fields from MS Graph are **untrusted input**. These rules apply everywhere they touch code:

**Escape every foreign value before it reaches `innerHTML` (anti-XSS):** The frontend runs with full `pywebview.api.*` access, an XSS is effectively RCE against the backend. `app.js` renders by building HTML strings from template literals and assigning them to `root.innerHTML` (full re-render via `render()`); it does NOT use `textContent`/`createTextNode` per node. The mandatory rule is therefore: any (potentially) foreign value interpolated into one of those template strings (task text, list name, meta, ids) MUST be wrapped in the `esc()` helper near the top of `app.js`, which escapes `& < > " '`.
```js
`<span class="t-text">${esc(t.text)}</span>`   // correct: foreign data wrapped in esc()
`<span class="t-text">${t.text}</span>`         // FORBIDDEN: unescaped interpolation
```
A bare `element.textContent = task.text` is also fine where a single node is set directly, but the prevailing pattern in this codebase is template literal + `esc()`. Never interpolate a value you did not escape. The CSP (below) is defense in depth, not a substitute for `esc()`.

**Content Security Policy:** `index.html` must have in `<head>`:
```html
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;">
```

**Parameterized SQL only:** All queries in `db.py` and `graph_sync.py` use `?` placeholders, no f-strings, no `.format()`, no string concatenation for values. (Exception: the whitelisted column name list in `edit_task`; see "Implementation details" above.)

**Input validation in `graph_sync.py`:** Truncate task text > 4096 chars, list names > 256 chars; strip control characters U+0000-U+001F (except newline/tab) from all imported strings.

## Lock policy (B.8)

The app is always fully locked or fully unlocked. Lock triggers (passphrase required on return):
- Lock button / `Ctrl+L`
- Panic / `Ctrl+Shift+!`
- App restart (always starts locked)
- Windows session lock (`WTS_SESSION_LOCK` via `WTSRegisterSessionNotification`)
- Auto-lock after inactivity (configurable, default ~15 min)

**No lock on:** window minimize, focus switch to another app, window resize/move.

## Bridge API (`pywebview.api.*`)

All frontend<->backend communication goes through these methods on the `Api` class in `backend/api.py`. Each returns a JSON-serializable value (or `{ "error": "code", "message": "..." }` on failure). Methods marked (stub) return placeholder values and will be replaced in later phases.

| Method | Args | Returns |
|---|---|---|
| `get_state()` | (keine) | `{ lists, settings, online, locked }` |
| `get_lists()` | (keine) | `[{ id, name, synced, open:[task], done:[task] }]` |
| `add_list(name)` | str | `{ id, name, ... }` |
| `rename_list(id, name)` | str, str | `{ ok }` |
| `delete_list(id)` | str | `{ ok }` |
| `add_task(list_id, text, meta?)` | str, str, str? | `{ ...task }` |
| `toggle_task(id)` | str | `{ id, done }` |
| `edit_task(id, fields)` | str, obj | `{ ...task }` |
| `delete_task(id)` | str | `{ ok }` |
| `reorder(list_id, ordered_ids)` | str, [str] | `{ ok }` |
| `export_list(id, format)` | str, `'md'`\|`'txt'`\|`'json'` | `{ filename, content }` |
| `copy_task(id)` | str | `{ ok, clears_in }` (hardened backend clipboard copy of ONE task) |
| `set_setting(key, value)` | str, * | `{ ok }` |
| `set_mini(flag)` | bool | `{ mini }` |
| `get_status()` | (keine) | `{ db, encryption, graph, last_sync, runtime }` |
| `sign_in()` | (keine) | (stub, Phase 8) |
| `sign_out()` | (keine) | `{ ok }` |
| `sync_now()` | (keine) | (stub, Phase 9) |
| `set_online(flag)` | bool | `{ online }` |
| `get_wifi_signal()` | (keine) | `{ connected, percent, level }` (level 0-3, real WLAN strength via `netsh wlan show interfaces`; cosmetic, drives the rail WiFi icon) |
| `lock()` | (keine) | `{ locked: true }` (frontend-only, gate G13 not enforced) |
| `unlock(passphrase)` | str | `{ ok }` (always succeeds, Phase 11) |
| `panic()` | (keine) | `{ locked: true }` (frontend-only) |

Backend -> frontend events (via `window.evaluate_js`): `window.noa.onSyncDone(summary)`, `window.noa.onNotification(payload)`, `window.noa.onLocked()`.

## SQLite schema (3 main tables + settings)

`lists(id, name, synced, position, created_at, updated_at)`, `synced=1` means imported from MS To Do.  
`tasks(id, list_id, text, meta, done, position, source, graph_etag, due_at, created_at, updated_at)`, `source` is `'local'` or `'graph'`.  
`sync_state(list_id, delta_link, last_sync)`, one row per list, holds the Graph delta link.  
`settings(key, value)`, key/value pairs: `accent`, `dark`, `toolbar`, `density`, `sidebar`, `railPinned`, `sidebarWidth`. All values stored as strings; `dark` is cast to bool on read, `railPinned` is compared to the string `'true'`, `sidebarWidth` is parsed as int (valid range 180-520).

IDs: local items use `'l'+uuid` (lists) or `'t'+uuid` (tasks); imported items use their stable Graph ID.

## Frontend state model

`app.js` holds a single in-memory cache object:
```js
state = {
  lists, activeId, settings, online, locked,
  menu,            // 'notif' | 'profile' | null
  modal,           // 'emergency' | 'status' | 'rename' | 'delete' | 'shortcuts' | 'settings' | null
  ctxList,         // right-click list context menu: { id, x, y } | null
  renamingId,      // list being renamed inline (sidebar pill) | null
  confirmDeleteId, // list whose inline delete confirmation pill is open | null
  focus,           // focus mode (hides sidebar + toolbar)
  mini,            // compact mini-window mode
  railPinned,      // right toolbar rail pinned (persisted as setting)
  sidebarWidth,    // sidebar width in px, default 256 (persisted as setting)
  colorOpen,       // accent color picker visible
  adding,          // new-list inline input visible
  addingTask,      // new-task inline input visible (bottom dock)
  doneOpen,        // completed section expanded
  editingId,       // task being edited inline (double-click) | null
  selectedId,      // task selected by click (target for rail copy/edit) | null
}
```
The backend is the source of truth. After each mutating action: apply the backend response to state, then re-render the affected part. `railPinned` and `sidebarWidth` are not returned by `get_state()` directly; they are read back from `state.settings` during boot and written to settings via `set_setting()`.

**Rendering and event dispatch:** `render()` rebuilds the whole UI as an HTML string and assigns it to `root.innerHTML`; there is no per-node diffing. Interaction is handled by event delegation, not per-element listeners: clickable elements carry a `data-act="..."` attribute (often with `data-id`), and a central handler dispatches on `data-act`. Add new interactions by emitting a `data-act` in the template and adding a `case` to that dispatcher, not by attaching listeners after render (they would be lost on the next `render()`).

## UI layout

CSS Grid: `Header` (full width, 56px) over three columns: `Sidebar` (width via `--sidebar-width`, default 256px, user-resizable by dragging the right edge) | `Main` (max 720px, centered) | `Toolbar` (right rail). Controlled by `data-theme`, `data-density`, `data-toolbar`, `data-sidebar`, `data-resizing` attributes on `.app`, plus `--accent` and `--sidebar-width` CSS variables. During sidebar resize, `data-resizing` is set on `.app` to suppress the width transition.

## Build phases (from `Planung/Bauplan - NoaToDo.md`)

Phase 0 (scaffold) -> Phase 1 (db.py) -> Phase 2 (api.py) -> Phase 3 (main.py wiring) -> Phase 4 (index.html skeleton) -> Phase 5 (style.css + fonts) -> Phase 6 (app.js full UI) <- *locally usable milestone* -> Phase 7 (export/copy) -> Phase 8 (MSAL login) -> Phase 9 (Graph sync) -> Phase 10 (notifications) -> Phase 11 (lock/panic/encryption).

Complete acceptance criteria for each phase are in `Planung/Bauplan - NoaToDo.md`.

## Keyboard shortcuts (B.5)

| Action | Key |
|---|---|
| New task | `Enter` (in new-task field) |
| New list | `N` |
| Toggle sidebar | `Ctrl+B` |
| Focus mode | `F` |
| Lock app | `Ctrl+L` |
| Panic lock | `Ctrl+Shift+!` |
| Export list | `Ctrl+E` |
| Toggle theme | `Ctrl+J` |
| Online/offline | `G` |
| Shortcut help | `?` |
| Close all | `Esc` |

Letter hotkeys (`N`, `F`, `G`, `?`) must not fire while focus is inside an input or textarea.

## Key dependencies

`pywebview`, `sqlcipher3-wheels` (import `sqlcipher3`), `cryptography`, `argon2-cffi`, `httpx`, `msal`, `keyring`, `winotify`. See `Code/requirements.txt`.
