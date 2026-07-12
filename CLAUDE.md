# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Writing style (mandatory)

The user does not like dashes (Gedankenstriche). Do NOT use the em-dash (Unicode U+2014) or the en-dash (Unicode U+2013) anywhere: not in code, comments, docstrings, UI strings, commit messages, documentation, or any file in this repo, and not in chat replies. Use commas, colons, parentheses, or separate sentences instead. For numeric ranges use "bis"/"to" or a plain ASCII hyphen (e.g. "0-11"). Plain ASCII hyphens in compound words and code identifiers are fine; only the two long dashes are forbidden.

## Project status

Locally-usable milestone reached (Phases 1 to 6 of the Bauplan, plus the Phase 6.5 UX/security follow-ups: inline task edit via double-click, per-task delete button, click-to-select tasks, hardened single-task copy via `copy_task` (gate G23: backend-side Win32 clipboard, excluded from Win+V history and cloud clipboard, auto-clear after 60 s), Ctrl+C app shortcut removed entirely, contextual rail pencil (selected task: inline edit; otherwise: rename list), mini mode always-on-top). Implemented: `db.py`, `api.py`, `main.py`, `frontend/index.html`, `frontend/style.css`, `frontend/app.js`.

Screenshot protection (gate G26, `SetWindowDisplayAffinity` / `WDA_EXCLUDEFROMCAPTURE`) is **removed from the code and should stay removed** (there is no screenshot code anywhere in `main.py` or `backend/`; commit 45820c2 took out the last attempt). It caused recurring problems: on some GPU/driver combos the affinity flag blocks WebView2 from rendering at all (window stays white / "not responding"), and its startup wiring previously deadlocked the message loop (a blocking `_get_hwnd(window, wait=True)` plus a cross-thread native call on the on_start worker thread). It also blacks out the window in legitimate screen sharing/recording and does nothing against a phone camera. Do not reintroduce it.

**WebView2 profile + single instance (gates G14 partial, G19 done, pulled forward 2026-06-20):** `main.py` no longer runs WebView2 in private mode. It starts PyWebView with `private_mode=False, storage_path=PROFILE_DIR` where `PROFILE_DIR = %LOCALAPPDATA%\NoaToDo\webview`, a single fixed, user-private profile folder. This replaced the old per-start temp profile under `%TEMP%\tmp...\EBWebView` that piled up on hard exit (real: dozens of leftovers, start hangs over a minute). `_cleanup_stale_webview_profiles()` removes those old temp profiles once at startup (only `tmp*` dirs carrying an `EBWebView` signature; locked ones are skipped). A named single-instance mutex (`_acquire_single_instance`, `Local\NoaToDoSingleton`, gate G19) makes a second instance show a message box and exit; the fixed folder is only safe together with this mutex (two instances would lock/corrupt the shared profile). The profile holds only non-sensitive UI cache (own HTML/CSS/JS/fonts, GPU state), never task content. **Still open for Phase 8 (gate G14 rest):** securely wipe `PROFILE_DIR` on `lock()`/`panic()`/clean quit, and clear orphaned `msedgewebview2.exe` that survive a hard kill and lock the folder (next start would otherwise fail with `0x800700AA` ERROR_BUSY). Do NOT reintroduce `private_mode=True`.

**Stale frontend cache (fixed 2026-06-23):** the fixed profile introduced a regression the old per-start temp profile masked: WebView2 caches the `file://` frontend (`index.html`/`app.js`/`style.css`) in `PROFILE_DIR\EBWebView\Default\Cache`, and that cache now survives restarts, so an old frontend is served for hours up to ~a day (Chromium heuristic freshness on files without cache headers). Symptom: "the old version still runs despite closing and restarting". `_purge_webview_cache()` in `main.py` fixes it by deleting only the `Cache` and `Code Cache` dirs under `PROFILE_DIR` on every startup (GPU/shader state is kept); it runs right after `_cleanup_stale_webview_profiles()`. Do not "optimize" this away. CSP `script-src 'self'` rules out an inline cache-busting bootstrap, so the disk purge is the clean fix. Note: the app is typically run via a venv on Microsoft-Store Python, whose `%LOCALAPPDATA%` writes are redirected, so the real folder lives under `...\Packages\PythonSoftwareFoundation.Python.3.11_*\LocalCache\Local\NoaToDo\webview`; in-process `os.walk(PROFILE_DIR)` sees the redirect automatically, external tooling looking at the literal path does not.

**Microsoft To Do sync removed (2026-07-09):** the app is purely local with no cloud/sync of any kind. The former `backend/auth.py` (MSAL login) and `backend/graph_sync.py` (Graph sync) files were deleted, and the `sign_in`/`sign_out`/`sync_now` bridge methods, the `synced`/`source`/`graph_etag` columns, the `sync_state` table, and `due_at` were all removed. The online/offline (airplane) toggle stays; **today it is only a local flag, but the target (Bauplan N11.5) is a REAL Windows airplane-mode control:** `set_online(false)` switches on the actual Windows airplane mode (all radios off, WiFi/Bluetooth) via the WinRT radio APIs, mirrors external changes back into the UI (event-driven), and restores the pre-app radio state as the **last** shutdown step (after the room is cleared).

**Phase 7 is OPEN:** `export_list` generates content, but no file is ever written (no save dialog); see gates G20-G22 in the Bauplan. **Target shape (Bauplan N11.2):** export is two-step (first scope: current list vs all lists, then format), **only `md` and `txt` (JSON was dropped, N11.1.5)**, all-lists as one file with list names as larger headings; an `export_all(format)` bridge method covers the all-lists case. Phase 7 also adds `move_task(id, target_list_id)` and `reorder_lists(ordered_ids)` (N7), and Undo only for list deletion (single-task delete stays immediate). There is intentionally no whole-list copy (`copy_list` was removed; export covers that). **Still an empty 1-line stub:** `backend/security.py`, i.e. the lock/panic + dual-layer-encryption work (Phase 8) is **not yet built**.

**Notifications removed (2026-07-09):** the app has no notifications of any kind (neither in-app alerts nor Windows toasts). The former `backend/notify.py` (winotify) file was deleted, the `winotify` dependency dropped, the `notify`/`notifyInApp`/`notifyWindows` settings and their Settings-modal section removed, and the `onNotification` backend -> frontend event removed. The general `pushToast` helper in `app.js` is unrelated: those are transient action confirmations ("List created"), not the notification feature, and stay. The former "Phase 8 (notifications)" no longer exists; lock/panic/encryption is now Phase 8.

**Planned per Bauplan N11 (2026-07-09), decided but NOT yet in code (do not assume these are implemented; implement them per the Bauplan, do not re-add what N11 drops):**
- **Task `meta` field is being removed entirely (N11.1.3):** a task will be only `text` + `done`. The DB column, the `add_task`/`edit_task` meta arg, the render, the inline-edit meta input, and the export meta all go away. Until then the code still has `meta`; do not build new features on it.
- **Export is `md`/`txt` only (N11.1.5), two-step (scope then format), plus `export_all` (N11.2).** JSON export is dropped.
- **`set_online` becomes a real Windows airplane-mode control (N11.5),** see the sync-removed note above.
- **Theme auto-follows Windows (N11.6):** the `dark` setting key is replaced by `theme` = `auto|light|dark` (default `auto`); auto mirrors the OS light/dark state live (event-driven), `Ctrl+J` sets a manual override until switched back to `auto`.
- **New settings keys:** `sound` (bool, completion sound on/off, default on) and `autoLock` (minutes to auto-lock, `0` = never, default `15`). The `toolbar` key is retired.
- **Vault file location is chosen by the user on first run (N11.3);** its path lives in a small unencrypted config (e.g. `%LOCALAPPDATA%\NoaToDo\config.json`), never inside the vault.
- **Passphrase policy (N11.3/N11.4):** minimum length 12 (no other rules) with a prominent "no recovery" warning; **no pepper recovery export** (the vault is bound to this Windows account, forgetting the passphrase means data loss); a lock-screen **Reset** path (killswitch-style confirm, then type `RESET`) wipes the vault and restarts full onboarding; passphrase changeable in Settings; unlock rate-limit is 2 s after each wrong try, 3 free tries, then an escalating lockout ladder 10 s / 30 s / 1 min / 5 min / 15 min / 30 min / 1 h / 5 h / 10 h (each stage allows 2 tries before advancing).
- **`move_task(id, target_list_id)` and `reorder_lists(ordered_ids)`** are added in Phase 7 (N7). No `clear_completed`, no full-text search (both dropped).
- **The window starts maximized (N11.6).**

Consequently the running app today is single-layer only: `db.connect()` opens SQLCipher with a fixed `DEV_AES_KEY` (`db.py`). The working DB file on disk is `data/tasks.db` (plain SQLCipher, no ChaCha20 wrapper yet). The ChaCha20 outer wrapper, Argon2id key derivation, passphrase unlock, and lock triggers described under "Critical constraints" / "Lock policy" are the **target design**, not the current behavior. `api.lock/unlock/panic` are placeholders; the lock is currently frontend-only and NOT enforced by the backend (gate G13). Treat those sections as the spec to build toward.

**Strengthened lock, lock-screen off button, panic end screen + killswitch (Bauplan Nachtrag N10, UI implemented 2026-07-08):** Locking (button or `Ctrl+L`) now first "clears the room" like panic (`clearWorkspace()` in `app.js`: lists/selection/menus/modals discarded in memory, sidebar closed, offline), then shows the lock screen; nothing is deleted, unlocking re-fetches everything via `get_state()` (the app stays offline until the user re-enables it). The lock screen has a power button top right (`quit_app()`: closes the WinForms form via `BeginInvoke` on the UI thread; quits without a passphrase, never deletes data). The panic flow no longer returns to the app: confirm -> real cleanup + wipe progress screen -> end screen ("All data securely wiped", a deliberate outward claim) with two exits: **Finish** (accent, just quits) and **Killswitch** (gray, two-stage in-button: first click slides the label right and an "OK" slides in, handled in-place without re-render so the CSS transition survives; "OK" runs `api.killswitch()` -> `db.killswitch()`, which really and irreversibly deletes all lists/tasks/settings, rewrites default settings, sets the `seeded` marker, runs `PRAGMA secure_delete` + `VACUUM`, then the app quits itself). Next start behaves like a first run without demo data: `seed_if_empty()` skips seeding when `settings.seeded == "true"` (the marker is also written on a normal first seed). The Phase 8 duties remain: secure `PROFILE_DIR` wipe on the `quit_app()` path (G14), key zeroing (G25), and G13 must whitelist `unlock`/`quit_app`/`killswitch` as the only methods allowed while locked.

**Security gates:** the Bauplan defines mandatory security gates in section B.9 (the original set plus the 2026-06-10 audit addendum "NACHTRAG: Gates G13 bis G25"). The sync/login-only gates (G1-G5, G10, G24) were removed together with the Microsoft integration. None of the remaining gates are optional. When implementing any phase, read its gate list in the Bauplan first; the quick overview table is at the end of the Bauplan.

## Running the app

```powershell
# From Code/ directory (venv must be active or use the venv python directly):
.\venv\Scripts\python.exe main.py

# Enable WebView2 DevTools (main.py reads this env var):
$env:NOATODO_DEBUG = "1"; .\venv\Scripts\python.exe main.py
```

`Code/run.ps1` is a convenience launcher: it always starts `main.py` with the project's own `venv` python regardless of the current directory, so you can double-click or call it from anywhere.

No build step, the frontend is vanilla HTML/CSS/JS loaded directly by PyWebView. There is no hot-reload: frontend edits need a full app restart (close the window AND make sure the python process is gone, a still-running instance also blocks relaunch via the single-instance mutex). The WebView2 cache is purged on each startup (see "Stale frontend cache" above), so a clean restart always shows the latest code. `main.py` prints `[NoaToDo] Start. Frontend: index.html HH:MM:SS, app.js ..., style.css ...` at launch; if those mtimes do not match your last edit, an old window is still running.

**No test suite exists yet**, there is no `tests/` dir and pytest is not a dependency. There is currently no lint/typecheck config. Verify changes by running the app.

**First run:** if `data/tasks.db` does not exist, `db.seed_if_empty()` writes only the default settings plus the `seeded` marker; **no demo lists or tasks are created**, the app starts empty. Delete `data/tasks.db` to reset to that empty first-run state.

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
│   └── security.py        # lock/unlock/panic, key derivation (stub)
├── data/
│   ├── tasks.db           # current working DB (SQLCipher-AES-256, no outer wrapper yet)
│   └── tasks.db.enc       # Phase 8 target: ChaCha20-Poly1305(SQLCipher blob)
└── tools/
    └── make_icon.py       # one-off build tool: generates frontend/icon.ico from logo
```

## Implementation details

**`@bridge` decorator (`api.py`):** wraps every public `Api` method. Catches `KeyError` as `"not_found"` and any other exception as `"internal"`. All bridge methods return a JSON-serializable dict or `{"error": code, "message": ...}` on failure.

**PyWebView introspection rule:** PyWebView recursively scans all public attributes of the `js_api` object to build the JS bridge. Any attribute that is not a plain method (e.g. the `Window` object stored in `api._window`) must have a `_` prefix; otherwise PyWebView descends into it and may call `evaluate_js` before the window is ready, causing "Main window failed to start". All private state in `Api` uses `_` prefix for this reason.

**WinForms thread safety:** `set_mini` runs in PyWebView's API worker thread. All native window mutations (size, position, `TopMost`, `FormBorderStyle`) must be dispatched to the WinForms UI thread via `form.Invoke(Action(work))`. Direct calls from the worker thread cause the message loop to deadlock.

The same applies to `on_start` and the `_on_setting_change` / `_on_frame_changed` callbacks in `main.py`: they also run on a worker thread. Setting `window.native.Icon` (in `_apply_window_icon`) directly from there deadlocked against the UI thread while it was still initializing the WebView2 control (`edgechromium.py:__init__`), so the window never appeared (intermittently white, "not responding", or nothing, depending on timing; root cause found 2026-06-13 via thread stack dump). Fix: all startup window operations (icon, DWM titlebar theme, `SetWindowPos`) are dispatched through `_run_on_ui_thread(window, work)`, which uses `window.native.BeginInvoke(Action(work))` (async, non-blocking) after the window handle exists. Never call WinForms members on `window.native` directly from a worker thread; route them through `_run_on_ui_thread`.

**`db.edit_task` SQL:** builds a dynamic SET clause from a whitelisted `allowed` set (currently `{"text", "meta", "done"}`; `meta` drops out with N11.1.3, leaving `{"text", "done"}`). The f-string in the query is safe because only those whitelisted column names can appear. This is an intentional tradeoff and not a SQL injection risk.

## Critical constraints

**Dual-layer encryption (mandatory, both layers always present in Phase 8+):**
- Layer 1, SQLCipher (AES-256): the package is **`sqlcipher3-wheels`** (imported as `import sqlcipher3`), not `sqlite3`, `sqlcipher3-binary` has no Windows wheels, `sqlcipher3-wheels` provides them with an identical API. Immediately after `connect()`, set `PRAGMA key = ?` with the derived `aes_key`, then `PRAGMA foreign_keys = ON`.
- Layer 2, ChaCha20-Poly1305 (outer wrapper, `cryptography` package): the permanent file on disk is `data/tasks.db.enc` = ChaCha20-Poly1305(SQLCipher blob). On unlock: unwrap -> write SQLCipher working copy to `%TEMP%` (restricted permissions) -> open with `aes_key`. On lock/quit/panic: re-wrap to `tasks.db.enc` -> securely delete the working copy -> discard keys from RAM.
- Both keys (`aes_key`, `chacha_key`) live only in RAM while unlocked; never written to disk.

**Passphrase / key derivation (gate G15, N11.3):** User passphrase (plus the DPAPI pepper below) -> Argon2id -> one 32-byte master secret -> HKDF-SHA256 with separate `info` labels -> `aes_key` and `chacha_key` (domain separation, not raw slices). Store only the salt and Argon2 params; **no passphrase/verification hash is stored** (that would be an offline oracle). Unlock is verified implicitly by the ChaCha20-Poly1305 tag: the wrong passphrase makes the AEAD decryption fail. Passphrase minimum length is 12 (N11.3). Never store the passphrase or derived keys.

**DPAPI pepper:** A random 32-byte pepper (second factor of the key derivation, gate G18) is stored in the Windows Credential Manager via `keyring`, never in the DB. This is the only use of `keyring` (there are no Microsoft tokens anymore). **No pepper recovery export (N11.3):** the vault is deliberately bound to this Windows account, so losing the account (or forgetting the passphrase) means the data is unrecoverable; the only escape is the lock-screen Reset (which wipes the vault).

**No cloud / no sync:** the app is purely local. There is no external service, no Microsoft integration, and nothing ever leaves the machine.

**Frontend fonts:** JetBrains Mono and Space Grotesk must be local `.woff2` files. No external font CDN, this is a local-first app.

**CSS:** The complete `<style>` section from `Planung/weiteres/NoaToDo UI Konzept.html` is extracted verbatim into `frontend/style.css`. Do not rebuild it from scratch. The design tokens (colors, spacing, fonts) are defined there and must not be reinvented.

**Completion sound:** Checking a task off plays a short "Datenstrom" blip (`playDoneSound` in `app.js`). It is synthesized live with the Web Audio API (square-wave oscillators, no audio file), specifically so it needs no `media-src` and stays compatible with the strict CSP (`default-src 'self'`). Do not replace it with a bundled `.mp3`/`.wav` (that would require loosening the CSP). The `AudioContext` is created lazily on the first check (browsers require a user gesture before audio) and reused. The sound will become toggleable via the `sound` setting (default on, N11.6). `Code/sound-preview.html` is a standalone dev scratch file for auditioning sound variants, not part of the app and not loaded by it.

## Security rules (mandatory: all untrusted input must follow these)

Task text, list names, and meta fields are user-entered free text and treated as **untrusted input** (the app is local, so there is no external data source, but the defensive rules cost nothing and stay mandatory). These rules apply everywhere such values touch code:

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

**Parameterized SQL only:** All queries in `db.py` use `?` placeholders, no f-strings, no `.format()`, no string concatenation for values. (Exception: the whitelisted column name list in `edit_task`; see "Implementation details" above.)

**Input validation (gate G20, Phase 7):** In `api.py`, truncate task text > 4096 chars, list names > 256 chars (no more `meta` after N11.1.3); strip control characters U+0000-U+001F (except newline/tab) from stored strings; `reorder`/`reorder_lists` reject non-list input, `move_task` validates its ids, and `set_setting` only accepts whitelisted keys (`accent`, `theme`, `density`, `sidebar`, `railPinned`, `sidebarWidth`, `sound`, `autoLock`).

## Lock policy (B.8)

The app is always fully locked or fully unlocked. Lock triggers (passphrase required on return):
- Lock button / `Ctrl+L`
- Panic / `Ctrl+Shift+!`
- App restart (always starts locked)
- Windows session lock (`WTS_SESSION_LOCK` via `WTSRegisterSessionNotification`)
- Auto-lock after inactivity (configurable via the `autoLock` setting, default 15 min, `0` = never; N11.4)

**No lock on:** window minimize, focus switch to another app, window resize/move.

**Unlock, reset, rate-limit (Phase 8 target, N11.3/N11.4):** first run lets the user choose the vault file location (path stored in an unencrypted config, N11.3) and set a passphrase (min 12 chars, prominent "no recovery" warning). A forgotten passphrase has no recovery; the lock screen offers a **Reset** (killswitch-style confirm, then type `RESET`) that wipes the vault and restarts full onboarding (choose location + new passphrase). Passphrase is changeable in Settings. Wrong-passphrase rate-limit: 2 s after each attempt, 3 free tries, then an escalating lockout ladder 10 s / 30 s / 1 min / 5 min / 15 min / 30 min / 1 h / 5 h / 10 h (each stage allows 2 tries before advancing).

## Bridge API (`pywebview.api.*`)

All frontend<->backend communication goes through these methods on the `Api` class in `backend/api.py`. Each returns a JSON-serializable value (or `{ "error": "code", "message": "..." }` on failure). Methods marked (stub) return placeholder values and will be replaced in later phases.

| Method | Args | Returns |
|---|---|---|
| `get_state()` | (keine) | `{ lists, settings, online, locked }` |
| `get_lists()` | (keine) | `[{ id, name, open:[task], done:[task] }]` |
| `add_list(name)` | str | `{ id, name, ... }` |
| `rename_list(id, name)` | str, str | `{ ok }` |
| `delete_list(id)` | str | `{ ok }` |
| `add_task(list_id, text, meta?)` | str, str, str? | `{ ...task }` (N11: `meta` slated for removal) |
| `toggle_task(id)` | str | `{ id, done }` |
| `edit_task(id, fields)` | str, obj | `{ ...task }` (N11: text only, no meta) |
| `delete_task(id)` | str | `{ ok }` |
| `reorder(list_id, ordered_ids)` | str, [str] | `{ ok }` (task order within a list) |
| `reorder_lists(ordered_ids)` | [str] | `{ ok }` (planned, N11.2: sidebar list order) |
| `move_task(id, target_list_id)` | str, str | `{ ...task }` (planned, N11.2: move task to another list) |
| `export_list(id, format)` | str, `'md'`\|`'txt'` | `{ filename, content }` (N11: JSON dropped) |
| `export_all(format)` | `'md'`\|`'txt'` | `{ filename, content }` (planned, N11.2: all lists in one file) |
| `copy_task(id)` | str | `{ ok, clears_in }` (hardened backend clipboard copy of ONE task) |
| `set_setting(key, value)` | str, * | `{ ok }` |
| `set_mini(flag)` | bool | `{ mini }` |
| `get_status()` | (keine) | `{ db, encryption, runtime }` |
| `set_online(flag)` | bool | `{ online }` (today a local flag; N11.5 target: real Windows airplane-mode toggle, all radios) |
| `get_wifi_signal()` | (keine) | `{ connected, percent, level }` (level 0-3, real WLAN strength via `netsh wlan show interfaces`; cosmetic, drives the rail WiFi icon) |
| `lock()` | (keine) | `{ locked: true }` (frontend-only, gate G13 not enforced; the frontend clears the workspace and goes offline before calling it, N10) |
| `unlock(passphrase)` | str | `{ ok }` (always succeeds, Phase 8; frontend re-fetches `get_state()` afterwards) |
| `panic()` | (keine) | `{ locked: true }` (frontend-only; flow ends in the end screen with Finish/Killswitch, N10) |
| `killswitch()` | (keine) | `{ ok }` (REALLY and irreversibly wipes all DB content, rewrites default settings + `seeded` marker; only reachable from the panic end screen) |
| `quit_app()` | (keine) | `{ ok }` (closes the app window via `BeginInvoke` on the UI thread; lock-screen off button, panic Finish, killswitch end) |

Backend -> frontend events (via `window.evaluate_js`): `window.noa.onLocked()`.

## SQLite schema (2 main tables + settings)

`lists(id, name, position, created_at, updated_at)`.  
`tasks(id, list_id, text, meta, done, position, created_at, updated_at)` (N11.1.3: the `meta` column is slated for removal, a task will be only `text` + `done`).  
`settings(key, value)`, current key/value pairs: `accent`, `dark`, `toolbar`, `density`, `sidebar`, `railPinned`, `sidebarWidth`. All values stored as strings; the bool-typed keys read back as bool via `_BOOL_SETTINGS` in `api.py` (`dark`), `railPinned` is compared to the string `'true'`, `sidebarWidth` is parsed as int (valid range 180-520). `toolbar` is still stored/seeded but no longer exposed in the settings UI (the rail is always `floating`; any saved value is ignored on read in `applyChrome`). **Planned (N11.6/N11.7):** `dark` is replaced by `theme` (`auto|light|dark`, default `auto`), `toolbar` is retired, and `sound` (bool) plus `autoLock` (minutes, `0` = never) are added; update the `set_setting` whitelist accordingly. `seeded` (`"true"`) is a backend-only marker written on the first run (by `seed_if_empty()`) and by `killswitch()`; `seed_if_empty()` only writes the default settings and this marker, it never creates demo lists/tasks, so the app always starts with empty lists.

IDs: local items use `'l'+uuid` (lists) or `'t'+uuid` (tasks).

## Frontend state model

`app.js` holds a single in-memory cache object:
```js
state = {
  lists, activeId, settings, online, locked,
  menu,            // 'profile' | null
  modal,           // 'status' | 'rename' | 'delete' | 'shortcuts' | 'settings' | null
  ctxList,         // right-click list context menu: { id, x, y } | null
  renamingId,      // list being renamed inline (sidebar pill) | null
  confirmDeleteId, // list whose inline delete confirmation pill is open | null
  listEditDock,    // inline rename/delete shown in the bottom dock instead of the sidebar
  focus,           // focus mode (hides sidebar + toolbar)
  mini,            // compact mini-window mode
  railPinned,      // right toolbar rail pinned (persisted as setting)
  sidebarWidth,    // sidebar width in px, default 256 (persisted as setting)
  adding,          // new-list inline input visible
  addingTask,      // new-task inline input visible (bottom dock)
  doneOpen,        // completed section expanded
  editingId,       // task being edited inline (double-click) | null
  selectedId,      // task selected by click (target for rail copy/edit) | null
  panic,           // panic flow (N10): { armed, stage:'panel'|'wiping'|'done'|'killing', killArmed } | null
}
```
`clearWorkspace()` resets the volatile part of this state (lists, active list, selection, menus, inputs, offline) and is called by both `doLock()` and the panic confirm; the lock/unlock cycle therefore always ends in a fresh `get_state()`.

The backend is the source of truth. After each mutating action: apply the backend response to state, then re-render the affected part. `railPinned` and `sidebarWidth` are not returned by `get_state()` directly; they are read back from `state.settings` during boot and written to settings via `set_setting()`.

**Rendering and event dispatch:** `render()` rebuilds the whole UI as an HTML string and assigns it to `root.innerHTML`; there is no per-node diffing. Interaction is handled by event delegation, not per-element listeners: clickable elements carry a `data-act="..."` attribute (often with `data-id`), and a central handler dispatches on `data-act`. Add new interactions by emitting a `data-act` in the template and adding a `case` to that dispatcher, not by attaching listeners after render (they would be lost on the next `render()`).

## UI layout

CSS Grid: `Header` (full width, 56px) over three columns: `Sidebar` (width via `--sidebar-width`, default 256px, user-resizable by dragging the right edge) | `Main` (max 720px, centered) | `Toolbar` (right rail). Controlled by `data-theme`, `data-density`, `data-toolbar`, `data-sidebar`, `data-resizing` attributes on `.app`, plus `--accent` and `--sidebar-width` CSS variables. During sidebar resize, `data-resizing` is set on `.app` to suppress the width transition.

## Build phases (from `Planung/Bauplan - NoaToDo.md`)

Phase 0 (scaffold) -> Phase 1 (db.py) -> Phase 2 (api.py) -> Phase 3 (main.py wiring) -> Phase 4 (index.html skeleton) -> Phase 5 (style.css + fonts) -> Phase 6 (app.js full UI) <- *locally usable milestone* -> Phase 7 (export + Undo + move_task/reorder_lists) -> Phase 8 (lock/panic/encryption) -> Phase 9 (build/packaging, portable .exe). The former Microsoft login and Graph sync phases were removed on 2026-07-09, the notifications phase on 2026-07-09, and the later phases renumbered accordingly.

Complete acceptance criteria for each phase are in `Planung/Bauplan - NoaToDo.md`.

## Keyboard shortcuts (B.5)

| Action | Key |
|---|---|
| New task | `Enter` (in new-task field) |
| New task in open list | `Ctrl+N` (opens the bottom new-task field and focuses it; needs an open list) |
| New list | `Ctrl+Shift+N` |
| Toggle sidebar | `Ctrl+B` |
| Focus mode | `F` (needs an open list; exit always works) |
| Switch list | `Ctrl+ArrowUp` / `Ctrl+ArrowDown` (sidebar open and a list open; stops at the ends, no wrap-around) |
| Open list 1-9 | `Ctrl+1` bis `Ctrl+9` (opens the n-th sidebar list, 1 = topmost; same key again toggles it closed; only when the sidebar is open, a list open with the sidebar closed does not count) |
| Lock app | `Ctrl+L` |
| Panic lock | `Ctrl+Shift+!` |
| Export list | `Ctrl+E` |
| Toggle theme | `Ctrl+J` |
| Online/offline | `G` |
| Shortcut help | `?` |
| Close all | `Esc` |

Letter hotkeys (`F`, `G`, `?`) must not fire while focus is inside an input or textarea. `Ctrl+N` (new list) calls `e.preventDefault()` so the triggering letter does not land in the freshly focused new-list input (and to suppress the browser's default new-window action). While the app is locked, all shortcuts are disabled; any printable key instead focuses the lock-screen password input (the character itself is then inserted normally).

## Key dependencies

`pywebview`, `sqlcipher3-wheels` (import `sqlcipher3`), `cryptography`, `argon2-cffi`, `keyring` (only for the DPAPI pepper, gate G18). See `Code/requirements.txt`.
