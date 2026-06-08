# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Early scaffold phase. `Code/backend/__init__.py` exists; all other source files are yet to be created. Planning documents are in `Planung/`.

## Running the app

```powershell
# From Code/ directory, after setting up a venv and installing requirements:
python main.py
```

No build step — the frontend is vanilla HTML/CSS/JS loaded directly by PyWebView.

## Architecture

NoaToDo is a **local-first Windows desktop app**: a Python backend and a vanilla JS frontend run together in a single native window via **PyWebView** (uses Windows WebView2, no bundled Chromium).

```
PyWebView window
├── frontend/         # HTML + CSS + JS — rendering only, holds no truth
│   ├── index.html
│   ├── style.css     # CSS extracted 1:1 from NoaToDo UI Konzept.html
│   ├── app.js        # all UI logic, calls pywebview.api.*
│   └── fonts/        # JetBrains Mono + Space Grotesk as local .woff2
└── backend/
    ├── api.py         # js_api class — the bridge (see Bridge API below)
    ├── db.py          # SQLCipher CRUD
    ├── graph_sync.py  # one-way MS Graph → SQLite sync
    ├── auth.py        # MSAL PKCE login, tokens via keyring
    ├── notify.py      # winotify Windows toasts
    └── security.py    # lock/unlock/panic, key derivation
data/tasks.db.enc      # ChaCha20-Poly1305(SQLCipher-AES-256 blob) — permanent on-disk artifact
main.py                # entry point
requirements.txt
```

## Critical constraints

**Dual-layer encryption (mandatory — both layers always present):**
- Layer 1 — SQLCipher (AES-256): use `sqlcipher3-binary`, not `sqlite3`. Immediately after `connect()`, set `PRAGMA key = ?` with the derived `aes_key`, then `PRAGMA foreign_keys = ON`.
- Layer 2 — ChaCha20-Poly1305 (outer wrapper, `cryptography` package): the permanent file on disk is `data/tasks.db.enc` = ChaCha20-Poly1305(SQLCipher blob). On unlock: unwrap → write SQLCipher working copy to `%TEMP%` (restricted permissions) → open with `aes_key`. On lock/quit/panic: re-wrap to `tasks.db.enc` → securely delete the working copy → discard keys from RAM.
- Both keys (`aes_key`, `chacha_key`) live only in RAM while unlocked; never written to disk.

**Passphrase / key derivation:** User passphrase → Argon2id KDF with stored random salt → derive both `aes_key` and `chacha_key` as separate slices of KDF output. Store only the Argon2 hash (for unlock verification) and the salt. Never store the passphrase or derived keys.

**Microsoft tokens:** Stored in Windows Credential Manager via `keyring`, never in the DB.

**Sync direction:** Strictly one-way — MS Graph → SQLite. Local tasks (`source='local'`) are never touched by sync and never uploaded. Scope is `Tasks.Read` only. Conflict default: cloud overwrites local changes to imported tasks (see `Bauplan – NoaToDo.md` §D.1).

**Frontend fonts:** JetBrains Mono and Space Grotesk must be local `.woff2` files. No external font CDN — this is a local-first app.

**CSS:** The complete `<style>` section from `Planung/NoaToDo UI Konzept.html` is extracted verbatim into `frontend/style.css`. Do not rebuild it from scratch. The design tokens (colors, spacing, fonts) are defined there and must not be reinvented.

## Security rules (mandatory — all untrusted input must follow these)

Task text, list names, and meta fields from MS Graph are **untrusted input**. These rules apply everywhere they touch code:

**No `innerHTML` for user data (anti-XSS):** The frontend runs with full `pywebview.api.*` access — an XSS is effectively RCE against the backend. Always:
```js
element.textContent = task.text;           // correct
element.appendChild(document.createTextNode(task.text));  // correct
element.innerHTML = task.text;             // FORBIDDEN
```

**Content Security Policy:** `index.html` must have in `<head>`:
```html
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;">
```

**Parameterized SQL only:** All queries in `db.py` and `graph_sync.py` use `?` placeholders — no f-strings, no `.format()`, no string concatenation for values.

**Input validation in `graph_sync.py`:** Truncate task text > 4096 chars, list names > 256 chars; strip control characters U+0000–U+001F (except newline/tab) from all imported strings.

## Lock policy (B.8)

The app is always fully locked or fully unlocked. Lock triggers (passphrase required on return):
- Lock button / `Ctrl+L`
- Panic / `Ctrl+Shift+!`
- App restart (always starts locked)
- Windows session lock (`WTS_SESSION_LOCK` via `WTSRegisterSessionNotification`)
- Auto-lock after inactivity (configurable, default ~15 min)

**No lock on:** window minimize, focus switch to another app, window resize/move.

## Bridge API (`pywebview.api.*`)

All frontend↔backend communication goes through these methods on the `Api` class in `backend/api.py`. Each returns a JSON-serializable value (or `{ "error": "code", "message": "…" }` on failure).

| Method | Args | Returns |
|---|---|---|
| `get_state()` | — | `{ lists, settings, online, locked }` |
| `get_lists()` | — | `[{ id, name, synced, open:[task], done:[task] }]` |
| `add_list(name)` | str | `{ id, name, … }` |
| `rename_list(id, name)` | str, str | `{ ok }` |
| `delete_list(id)` | str | `{ ok }` |
| `add_task(list_id, text, meta?)` | str, str, str? | `{ …task }` |
| `toggle_task(id)` | str | `{ id, done }` |
| `edit_task(id, fields)` | str, obj | `{ …task }` |
| `delete_task(id)` | str | `{ ok }` |
| `reorder(list_id, ordered_ids)` | str, [str] | `{ ok }` |
| `export_list(id, format)` | str, `'md'`\|`'txt'`\|`'json'` | `{ filename, content }` |
| `copy_list(id)` | str | `{ text }` |
| `set_setting(key, value)` | str, * | `{ ok }` |
| `get_status()` | — | `{ db, encryption, graph, last_sync, runtime }` |
| `sign_in()` | — | `{ ok, account }` |
| `sign_out()` | — | `{ ok }` |
| `sync_now()` | — | `{ changed, lists }` |
| `set_online(flag)` | bool | `{ online }` |
| `lock()` | — | `{ locked: true }` |
| `unlock(passphrase)` | str | `{ ok }` |
| `panic()` | — | `{ locked: true }` |

Backend → frontend events (via `window.evaluate_js`): `window.noa.onSyncDone(summary)`, `window.noa.onNotification(payload)`, `window.noa.onLocked()`.

## SQLite schema (3 main tables + settings)

`lists(id, name, synced, position, created_at, updated_at)` — `synced=1` means imported from MS To Do.  
`tasks(id, list_id, text, meta, done, position, source, graph_etag, due_at, created_at, updated_at)` — `source` is `'local'` or `'graph'`.  
`sync_state(list_id, delta_link, last_sync)` — one row per list, holds the Graph delta link.  
`settings(key, value)` — key/value pairs: `accent`, `dark`, `toolbar`, `density`, `sidebar`.

IDs: local items use `'l'+uuid` (lists) or `'t'+uuid` (tasks); imported items use their stable Graph ID.

## Frontend state model

`app.js` holds a single in-memory cache object:
```js
state = { lists, activeId, settings, online, locked, menu, modal, focus, colorOpen, toasts }
```
The backend is the source of truth. After each mutating action: apply the backend response to state, then re-render the affected part.

## UI layout

CSS Grid: `Header` (full width, 56px) over three columns: `Sidebar` (256px) | `Main` (max 720px, centered) | `Toolbar` (right rail). Controlled by `data-theme`, `data-density`, `data-toolbar`, `data-sidebar` attributes on `.app`, plus `--accent` CSS variable.

## Build phases (from `Planung/Bauplan – NoaToDo.md`)

Phase 0 (scaffold) → Phase 1 (db.py) → Phase 2 (api.py) → Phase 3 (main.py wiring) → Phase 4 (index.html skeleton) → Phase 5 (style.css + fonts) → Phase 6 (app.js full UI) ← *locally usable milestone* → Phase 7 (export/copy) → Phase 8 (MSAL login) → Phase 9 (Graph sync) → Phase 10 (notifications) → Phase 11 (lock/panic/encryption).

Complete acceptance criteria for each phase are in `Planung/Bauplan – NoaToDo.md`.

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
| Copy list | `Ctrl+C` |
| Toggle theme | `Ctrl+J` |
| Online/offline | `G` |
| Shortcut help | `?` |
| Close all | `Esc` |

Letter hotkeys (`N`, `F`, `G`, `?`) must not fire while focus is inside an input or textarea.

## Key dependencies

`pywebview`, `sqlcipher3-binary`, `cryptography`, `argon2-cffi`, `httpx`, `msal`, `keyring`, `winotify`
