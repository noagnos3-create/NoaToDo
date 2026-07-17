# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Writing style (mandatory)

The user does not like dashes (Gedankenstriche). Do NOT use the em-dash (Unicode U+2014) or the en-dash (Unicode U+2013) anywhere: not in code, comments, docstrings, UI strings, commit messages, documentation, or any file in this repo, and not in chat replies. Use commas, colons, parentheses, or separate sentences instead. For numeric ranges use "bis"/"to" or a plain ASCII hyphen (e.g. "0-11"). Plain ASCII hyphens in compound words and code identifiers are fine; only the two long dashes are forbidden.

## The plan is the highest authority (mandatory)

`Planung/Bauplan - NoaToDo.md` is **the** binding document for this project. It outranks
this file, the code, and any assumption: when they disagree, the Bauplan wins and the other
side is the bug. `Planung/Plananalyse - Schwachstellen und Angriffsvektoren.md` is its
standing audit (findings W*/S*/U*/V*; a finding is resolved only when the Bauplan says so).

**Read before you build:** open the Bauplan section for the phase you are touching, plus its
security gates (B.9), *before* writing code. Never implement from memory or from this file
alone.

**Check the plan after every finished task, every time.** When you complete anything
(a feature, a fix, a decision), go back into the Bauplan and ask:
1. Is there a checkbox, a phase line, or a gate row that must now be ticked off or moved to
   "erledigt" (with the date)?
2. Did this change make some part of the plan wrong, stale, or contradictory? Then fix that
   part in the same change. The plan must never claim something the code does not do (that
   is exactly how Plananalyse finding S7 happened: the plan claimed a per-task hover trash
   button that never existed).
3. Does the change touch a place the plan calls a single source of truth (B.2 bridge API +
   error codes, B.5 shortcuts, B.9 gates, the Entscheidungsregister in Anhang 1; since the
   2026-07 Struktur-Umbau a new decision goes into its Teil-B contract plus a register row,
   never into a new Nachtrag block)? Then update that place too,
   in the same change, and mirror it here in CLAUDE.md.

A change that leaves the plan out of sync is not finished.

## Project status

Locally-usable milestone reached (Phases 1 to 6 of the Bauplan, plus the Phase 6.5 UX/security follow-ups: inline task edit via double-click, task delete via the rail trash button (acts on the selected task; **there is no per-task hover trash on the card**, `.t-del` and the `del-task` handler are unused leftovers, corrected 2026-07-13, Plananalyse S7), click-to-select tasks, hardened single-task copy via `copy_task` (gate G23: backend-side Win32 clipboard, excluded from Win+V history and cloud clipboard, auto-clear after 60 s), Ctrl+C app shortcut removed entirely, contextual rail pencil (selected task: inline edit; otherwise: rename list), mini mode always-on-top). Implemented: `db.py`, `api.py`, `main.py`, `frontend/index.html`, `frontend/style.css`, `frontend/app.js`.

Screenshot protection (gate G26, `SetWindowDisplayAffinity` / `WDA_EXCLUDEFROMCAPTURE`) is **removed from the code and should stay removed** (there is no screenshot code anywhere in `main.py` or `backend/`; commit 45820c2 took out the last attempt). It caused recurring problems: on some GPU/driver combos the affinity flag blocks WebView2 from rendering at all (window stays white / "not responding"), and its startup wiring previously deadlocked the message loop (a blocking `_get_hwnd(window, wait=True)` plus a cross-thread native call on the on_start worker thread). It also blacks out the window in legitimate screen sharing/recording and does nothing against a phone camera. Do not reintroduce it.

**WebView2 profile + single instance (gates G14 partial, G19 done, pulled forward 2026-06-20):** `main.py` no longer runs WebView2 in private mode. It starts PyWebView with `private_mode=False, storage_path=PROFILE_DIR` where `PROFILE_DIR = %LOCALAPPDATA%\NoaToDo\webview`, a single fixed, user-private profile folder. This replaced the old per-start temp profile under `%TEMP%\tmp...\EBWebView` that piled up on hard exit (real: dozens of leftovers, start hangs over a minute). `_cleanup_stale_webview_profiles()` removes those old temp profiles once at startup (only `tmp*` dirs carrying an `EBWebView` signature; locked ones are skipped). A named single-instance mutex (`_acquire_single_instance`, `Local\NoaToDoSingleton`, gate G19) makes a second instance show a message box and exit; the fixed folder is only safe together with this mutex (two instances would lock/corrupt the shared profile). **Open rest of G19 (V3, 2026-07-15):** the mutex name must move to `Global\NoaToDo-<User-SID>`; a `Local\` mutex is unique per logon session only, so the same user via RDP or fast user switching could start a second instance on the same DB (exactly the corruption G19 exists to prevent). The code still uses `Local\` today; rename at the latest in Phase 8. The profile holds only non-sensitive UI cache (own HTML/CSS/JS/fonts, GPU state), never task content. **Still open for Phase 8 (gate G14 rest):** securely wipe `PROFILE_DIR` on `lock()`/`panic()`/clean quit, and clear orphaned `msedgewebview2.exe` that survive a hard kill and lock the folder (next start would otherwise fail with `0x800700AA` ERROR_BUSY). Do NOT reintroduce `private_mode=True`.

**Stale frontend cache (fixed 2026-06-23):** the fixed profile introduced a regression the old per-start temp profile masked: WebView2 caches the `file://` frontend (`index.html`/`app.js`/`style.css`) in `PROFILE_DIR\EBWebView\Default\Cache`, and that cache now survives restarts, so an old frontend is served for hours up to ~a day (Chromium heuristic freshness on files without cache headers). Symptom: "the old version still runs despite closing and restarting". `_purge_webview_cache()` in `main.py` fixes it by deleting only the `Cache` and `Code Cache` dirs under `PROFILE_DIR` on every startup (GPU/shader state is kept); it runs right after `_cleanup_stale_webview_profiles()`. Do not "optimize" this away. CSP `script-src 'self'` rules out an inline cache-busting bootstrap, so the disk purge is the clean fix. Note: the app is typically run via a venv on Microsoft-Store Python, whose `%LOCALAPPDATA%` writes are redirected, so the real folder lives under `...\Packages\PythonSoftwareFoundation.Python.3.11_*\LocalCache\Local\NoaToDo\webview`; in-process `os.walk(PROFILE_DIR)` sees the redirect automatically, external tooling looking at the literal path does not. **V8 (2026-07-15, Bauplan G14 + N11.15.5):** any wiping therefore always operates in-process on the effective path, and the Phase 9 `.exe` (which runs without the redirect) gets a one-time first-start step that removes the known old redirected leftovers (the redirected `NoaToDo\webview` folder and its `config.json`, never a `tasks.db.enc`).

**Microsoft To Do sync removed (2026-07-09):** the app is purely local with no cloud/sync of any kind. The former `backend/auth.py` (MSAL login) and `backend/graph_sync.py` (Graph sync) files were deleted, and the `sign_in`/`sign_out`/`sync_now` bridge methods, the `synced`/`source`/`graph_etag` columns, the `sync_state` table, and `due_at` were all removed. The online/offline (airplane) toggle stays; **today it is only a local flag, but the target (Bauplan N11.5) is a REAL Windows airplane-mode control:** `set_online(false)` switches on the actual Windows airplane mode (all radios off, WiFi/Bluetooth) via the WinRT radio APIs, mirrors external changes back into the UI (event-driven), and restores the pre-app radio state as the **last** shutdown step (after the room is cleared).

**Phase 7 is OPEN:** `export_list` generates content, but no file is ever written (no save dialog); see gates G20-G22 in the Bauplan. **Target shape (Bauplan N11.2):** export is two-step (first scope: current list vs all lists, then format), **only `md` and `txt` (JSON was dropped, N11.1.5)**, all-lists as one file with list names as larger headings; an `export_all(format)` bridge method covers the all-lists case. Phase 7 also adds `move_task(id, target_list_id)` and `reorder_lists(ordered_ids)` (N7), and Undo only for list deletion (single-task delete stays immediate). There is intentionally no whole-list copy (`copy_list` was removed; export covers that). **Still an empty 1-line stub:** `backend/security.py`, i.e. the lock/panic + dual-layer-encryption work (Phase 8) is **not yet built**.

**Notifications removed (2026-07-09):** the app has no notifications of any kind (neither in-app alerts nor Windows toasts). The former `backend/notify.py` (winotify) file was deleted, the `winotify` dependency dropped, the `notify`/`notifyInApp`/`notifyWindows` settings and their Settings-modal section removed, and the `onNotification` backend -> frontend event removed. The general `pushToast` helper in `app.js` is unrelated: those are transient action confirmations ("List created"), not the notification feature, and stay. The former "Phase 8 (notifications)" no longer exists; lock/panic/encryption is now Phase 8.

**Planned per Bauplan N11 (2026-07-09), decided but NOT yet in code (do not assume these are implemented; implement them per the Bauplan, do not re-add what N11 drops):**
- **Task `meta` field removed entirely (N11.1.3, DONE 2026-07-17):** a task is only `text` + `done`. The DB column, the `add_task`/`edit_task` meta arg, the render, the inline-edit meta input, and the export meta are all gone. `db._drop_legacy_columns()` drops `meta` (and the orphaned sync-era columns `synced`/`source`/`graph_etag`/`due_at`) from existing dev DBs once at connect. Do not re-add any of them.
- **Export is `md`/`txt` only (N11.1.5), two-step (scope then format), plus `export_all` (N11.2).** JSON export is dropped.
- **`set_online` becomes a real Windows airplane-mode control (N11.5),** see the sync-removed note above.
- **Locking no longer switches offline (N11.10, decided 2026-07-13, resolves finding W1 of the Plananalyse):** every lock (lock button, `Ctrl+L`, auto-lock) leaves the online/radio state exactly as it is, in neither direction (no airplane mode on, no restore). Radios are switched only by the explicit user toggle (pill/`G`) and by the panic flow; the pre-app radio state is restored only on quit, as the last step. Today's `clearWorkspace()` still sets offline on lock; when implementing, remove that from the lock path (keep it in the panic path only).
- **Theme auto-follows Windows (N11.6):** the `dark` setting key is replaced by `theme` = `auto|light|dark` (default `auto`); auto mirrors the OS light/dark state live (event-driven, plus a 60 s fallback re-check). `Ctrl+J` sets a manual override: from `auto` it switches to the opposite of the currently shown (effective) theme, from a fixed theme to the other fixed theme; it never returns to `auto` on its own (only the Appearance settings segment does). The interval and the two `Ctrl+J` rules resolve Plananalyse U16 (2026-07-15).
- **New settings keys:** `sound` (bool, completion sound on/off, default on) and `autoLock` (minutes to auto-lock, `0` = never, default `15`). The `toolbar` key is retired.
- **Vault file location is chosen by the user on first run (N11.3);** its path lives in a small unencrypted config (e.g. `%LOCALAPPDATA%\NoaToDo\config.json`), never inside the vault.
- **Passphrase policy (N11.3/N11.4):** minimum length 12 (no other rules) with a prominent "no recovery" warning; **no pepper recovery export** (the vault is bound to this Windows account, forgetting the passphrase means data loss); a lock-screen **Reset** path (killswitch-style confirm, then type `RESET`) wipes the vault and restarts full onboarding; passphrase changeable in Settings; unlock rate-limit is 2 s after each wrong try, 3 free tries, then an escalating lockout ladder 10 s / 30 s / 1 min / 5 min / 15 min / 30 min / 1 h / 5 h / 10 h (each stage allows 2 tries before advancing).
- **`move_task(id, target_list_id)` and `reorder_lists(ordered_ids)`** are added in Phase 7 (N7). No `clear_completed`, no full-text search (both dropped).
- **The window starts maximized (N11.6).**

Consequently the running app today is single-layer only: `db.connect()` opens SQLCipher with a fixed `DEV_AES_KEY` (`db.py`). The working DB file on disk is `data/tasks.db` (plain SQLCipher, no ChaCha20 wrapper yet). The ChaCha20 outer wrapper, Argon2id key derivation, passphrase unlock, and lock triggers described under "Critical constraints" / "Lock policy" are the **target design**, not the current behavior. `api.lock/unlock/panic` are placeholders; the lock is currently frontend-only and NOT enforced by the backend (gate G13). Treat those sections as the spec to build toward. **Honest status (gate G22, done 2026-07-16):** because `DEV_AES_KEY` is public, `get_status()` and the status modal now report the real state (`encryption.active: false`, `dev_key: true`, "AES-256 · dev key, layer 2 pending" in a warning color), never a false "active"/"encrypted"; `db.Database.dev_key` carries the flag. The panic end screen still claims "All data securely wiped" (false today, Frontend-only lock/panic); making it honest until Phase 8 is the remaining open G22 code item (deadline 2026-07-20).

**Strengthened lock, lock-screen off button, panic end screen + killswitch (Bauplan Nachtrag N10, UI implemented 2026-07-08):** Locking (button or `Ctrl+L`) now first "clears the room" like panic (`clearWorkspace()` in `app.js`: lists/selection/menus/modals discarded in memory, sidebar closed, offline), then shows the lock screen; nothing is deleted, unlocking re-fetches everything via `get_state()`. (The "goes offline / stays offline until re-enabled" part is superseded by N11.10, 2026-07-13: locking must no longer touch the online/radio state at all; that is today's code behavior still to be changed, see the N11 list above.) The lock screen has a power button top right (`quit_app()`: closes the WinForms form via `BeginInvoke` on the UI thread; quits without a passphrase, never deletes data). The panic flow no longer returns to the app: confirm -> real cleanup + wipe progress screen -> end screen ("All data securely wiped", a deliberate outward claim) with two exits: **Finish** (accent, just quits) and **Killswitch** (gray, two-stage in-button: first click slides the label right and an "OK" slides in, handled in-place without re-render so the CSS transition survives; "OK" runs `api.killswitch()` -> `db.killswitch()`, which really and irreversibly deletes all lists/tasks/settings, rewrites default settings, sets the `seeded` marker, runs `PRAGMA secure_delete` + `VACUUM`, then the app quits itself). Next start behaves like a first run without demo data: `seed_if_empty()` skips seeding when `settings.seeded == "true"` (the marker is also written on a normal first seed). The Phase 8 duties remain: secure `PROFILE_DIR` wipe on the `quit_app()` path (G14), key zeroing (G25), and G13 must enforce the lock as an explicit allowlist, `ALLOWED_WHEN_LOCKED = {"unlock", "quit_app", "killswitch", "get_state", "get_boot_state", "choose_vault_dir", "create_vault", "reset_vault"}` (the last four added by the U1 decision, N11.13: onboarding and reset run precisely **without** keys and would otherwise be blocked; `change_passphrase` is deliberately NOT in the list, it needs the unlocked state). Everything else, including `lock`/`panic`, returns `{"error": "locked"}` while locked; `get_state()` returns only `{"locked": true}`. Allowlist, not "every method except X": any newly added bridge method is denied by default and has to be allowed deliberately.

**Security gates:** the Bauplan defines mandatory security gates in section B.9. Since the Struktur-Umbau (Etappe 2, 2026-07-16) they live in **one** merged table sorted by gate number; the former split into an original set plus the audit addendum "NACHTRAG: Gates G13 bis G35" is history, recorded in the Entscheidungsregister (Anhang 1, "Herkunft der Sicherheits-Gates"). Some gate rows carry only a short title plus a full-text anchor into their contract (list in the B.9 head: G13/G20/G29 in B.2, G14/G35 in B.8.5, G16/G28 in B.7, G21 in Phase 7, G27/G34 in Phase 9, G30 in B.10); the other rows still hold their full text inline. G28, the Phase 8 encryption proof, comes from N11.9. The sync/login-only gates (G1-G5, G10, G24) were removed together with the Microsoft integration. None of the remaining gates are optional. When implementing any phase, read its gate list in the Bauplan first; the quick overview table is at the end of the Bauplan.

**Gates G31 to G34 + G27 extension + window-title rule (adopted 2026-07-15 from Plananalyse findings A1 to A7; normative full text is each gate's row in the B.9 table, except G34: since Umbau-Etappe 6 its full text lives in the Phase 9 gate block, the B.9 row keeps status/date/check plus the full-text anchor):**
- **G31 (Phase 8, RAM-to-disk leaks, A1):** BitLocker recommendation in the setup UI plus the real BitLocker status in the status modal (an unreadable WMI query shows "unknown", never a false "protected"); all key `bytearray`s (aes_key, chacha_key, master secret, pepper) locked with `VirtualLock` after derivation and `VirtualUnlock`ed before the G25 zeroing (best effort; documented limit: does NOT keep keys out of `hiberfil.sys` or crash dumps, only BitLocker covers those); no `faulthandler` file target, no traceback/dump files (matches G29).
- **G32 (Phase 8/onboarding, vault location, A2):** onboarding defaults to `%LOCALAPPDATA%\NoaToDo`; a chosen path under a detected sync root (OneDrive env vars, Dropbox `info.json`, path-component heuristic, best effort) shows a prominent warning naming both facts: the provider keeps version history, and **killswitch/reset do not delete cloud versions**. A warning, never a block.
- **G33 (Phase 8, dev legacy data, A3):** the first `create_vault()` secure-deletes the old `data/tasks.db` including `-journal`/`-wal`/`-shm` (overwrite then unlink, same path as the `.bak` cleanup in N11.3 (c), never a bare `os.remove`), plus a one-time notice about the honest SSD forensic limit (wear leveling).
- **G34 (Phase 9, release hardening, A4/A6):** the frozen release build hard-ignores `NOATODO_DEBUG` (build constant) and sets `AreDevToolsEnabled=false`, `AreBrowserAcceleratorKeysEnabled=false` (kills the Ctrl+P plaintext-PDF export past G21) and `AreDefaultContextMenusEnabled=false`. **`text_select=False` is now set explicitly in `create_window` (done 2026-07-16, `main.py`);** the former unintended PyWebView default is a deliberate, commented decision now. The regression test comes with the Phase 9 test list (no test setup yet). The rest of G34 (a)/(c) stays Phase 9. Input-field copy stays an open, honestly documented channel (B.10.3 item 8).
- **G27 extension (Phase 9, frontend integrity, A5):** the exe signature does not cover `index.html`/`app.js`/`style.css`; embed the frontend assets in the signed binary or verify each asset hash against an embedded manifest at startup, and refuse to start with a clear message on any mismatch (hardens against silent K4 persistence, never sold as full K4 protection).
- **Window-title rule (B.4, A7, no gate):** the native window title is constantly "NoaToDo" and never contains user content (no list names, task text, or counters, in no mode incl. mini mode); same for taskbar tooltip and jumplists.

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

**Error hygiene (gate G29, implemented 2026-07-17):** the frontend only ever sees a **code plus a static English text** from the canonical error-code table in Bauplan B.2 (`not_found`, `invalid`, `locked`, `passphrase`, `rate_limited`, `vault`, `canceled`, `busy`, `memory`, `internal`), never `str(exc)`, never paths, tracebacks, SQL fragments, task text, passphrase or keys. `ERROR_MESSAGES`/`_err()` in `api.py` hold the catalog; the `@bridge` decorator maps `KeyError` -> `not_found`, `MemoryError` -> `memory`, everything else -> `internal` plus a 4-hex `ref`. Details go into the **redacted in-memory ring buffer** `Api._errors` (deque, last 50 entries, `_redact()` replaces paths by `<path>` and caps at 200 chars, never bridge arguments), viewable in the status modal ("Recent errors", collapsed, copy button via the hardened G23 clipboard path, bridge method `copy_errors()`) and cleared on `lock()`/`panic()`/`killswitch()`/`quit_app()` (Phase 8 moves that into `teardown()`). Frontend: `handleError(res)` in `app.js` is the single error sink; toast only for `not_found` (then a silent `refreshState()`), `invalid`, `busy` and `internal` (with ref); `locked` and `canceled` are deliberately silent. Logging policy: **no persistent logfile in the release** (no `FileHandler`, no `basicConfig(filename=...)`, no traceback file); verbose diagnostics only behind `NOATODO_DEBUG`, and even then never passphrase/keys/task text; the release-build check is Phase 9.

**PyWebView introspection rule:** PyWebView recursively scans all public attributes of the `js_api` object to build the JS bridge. Any attribute that is not a plain method (e.g. the `Window` object stored in `api._window`) must have a `_` prefix; otherwise PyWebView descends into it and may call `evaluate_js` before the window is ready, causing "Main window failed to start". All private state in `Api` uses `_` prefix for this reason.

**Navigation lockdown (gate G12, implemented 2026-07-17):** `_wire_navigation_guard()` in `main.py` attaches a `NavigationStarting` handler to the WebView2 control (`window.native.browser.webview`) that cancels every navigation except `about:` and `file:` URIs inside the app's own `frontend/` dir; `webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False` makes `window.open` go through `load_url` (and thus the same guard) instead of the system browser. The app is purely local and never navigates elsewhere; do not loosen this.

**WinForms thread safety:** `set_mini` runs in PyWebView's API worker thread. All native window mutations (size, position, `TopMost`, `FormBorderStyle`) must be dispatched to the WinForms UI thread via `form.Invoke(Action(work))`. Direct calls from the worker thread cause the message loop to deadlock.

The same applies to `on_start` and the `_on_setting_change` / `_on_frame_changed` callbacks in `main.py`: they also run on a worker thread. Setting `window.native.Icon` (in `_apply_window_icon`) directly from there deadlocked against the UI thread while it was still initializing the WebView2 control (`edgechromium.py:__init__`), so the window never appeared (intermittently white, "not responding", or nothing, depending on timing; root cause found 2026-06-13 via thread stack dump). Fix: all startup window operations (icon, DWM titlebar theme, `SetWindowPos`) are dispatched through `_run_on_ui_thread(window, work)`, which uses `window.native.BeginInvoke(Action(work))` (async, non-blocking) after the window handle exists. Never call WinForms members on `window.native` directly from a worker thread; route them through `_run_on_ui_thread`.

**`db.edit_task` SQL:** builds a dynamic SET clause from a whitelisted `allowed` set (`{"text", "done"}` since the N11.1.3 meta removal). The f-string in the query is safe because only those whitelisted column names can appear. This is an intentional tradeoff and not a SQL injection risk.

## Critical constraints

**Dual-layer encryption (mandatory, both layers always present in Phase 8+):**
- Layer 1, SQLCipher (AES-256): the package is **`sqlcipher3-wheels`** (imported as `import sqlcipher3`), not `sqlite3`, `sqlcipher3-binary` has no Windows wheels, `sqlcipher3-wheels` provides them with an identical API. Immediately after `connect()`, set `PRAGMA key = ?` with the derived `aes_key`, then `PRAGMA foreign_keys = ON`.
- Layer 2, ChaCha20-Poly1305 (outer wrapper, `cryptography` package): the permanent file on disk is `data/tasks.db.enc` = ChaCha20-Poly1305(SQLCipher blob). On unlock: unwrap -> write SQLCipher working copy to `%TEMP%` (restricted permissions) -> open with `aes_key`. On lock/quit/panic: re-wrap to `tasks.db.enc` -> securely delete the working copy -> discard keys from RAM. Wrap hardening per G16/V1 (2026-07-15): the full `.enc` header goes into the AEAD as `associated_data`, the fresh `.tmp` is test-decrypted **before** the `.bak` rotation (so two bad write cycles cannot destroy both generations), and free disk space is checked before each wrap (on shortage the old state stays untouched, error code `vault`).
- Both keys (`aes_key`, `chacha_key`) live only in RAM while unlocked; never written to disk.

**Passphrase / key derivation (gate G15, N11.3):** User passphrase bound to the DPAPI pepper first, then Argon2id -> one 32-byte master secret -> HKDF-SHA256 with separate `info` labels -> `aes_key` and `chacha_key` (domain separation, not raw slices). **Pepper binding (V2a, decided 2026-07-15):** `argon2-cffi` does not expose Argon2's keyed `secret` parameter, so the pepper cannot go in that way; instead `ikm = HKDF-Extract(salt=pepper, ikm=passphrase_utf8)` (by definition `HMAC-SHA256(key=pepper, msg=passphrase_utf8)`, 32 bytes) runs before Argon2id, and Argon2id derives the master secret from `ikm` + the header salt. The construction is versioned via the G16 header format version. **Fixed Argon2id parameters (U17/N11.4.3, decided 2026-07-15, pro security): type Argon2id, version 0x13, `memory_cost=262144` KiB (256 MiB), `time_cost=3`, `parallelism=4`, `hash_len=32`, 16-byte per-vault salt.** 256 MiB, not 512, on purpose: availability counts as a security goal (a pepper-bound vault must not lock itself out on a RAM-tight machine), and the offline attacker is stopped primarily by the DPAPI pepper, not the memory cost. These params live in the G16 `.enc` header (authenticated as AEAD `associated_data`, V1) and are validated against an accepted range (64 to 512 MiB, else the header counts as unreadable -> `vault`, no Argon2 run) before allocation, which blocks a header-inflation DoS. They are raised to the current target only on passphrase change (N11.3 (d)). A `MemoryError` during derivation (in `unlock`/`create_vault`/`change_passphrase`) is caught before the `@bridge` `internal` catch-all and returned as the dedicated error code **`memory`** ("Not enough memory. Close other apps and try again."): never surfaced as wrong passphrase, never crashes, and it does NOT advance the rate-limit ladder (a memory shortage is not a guess). Concrete derivation (U18, so two implementations agree bit-for-bit): `HKDF-SHA256(ikm=master_secret, salt=None, info=<label>, length=32)` called twice with the same master secret; the two fixed, versioned labels are `b"noatodo/aes-key/v1"` (aes_key) and `b"noatodo/chacha-key/v1"` (chacha_key). `salt=None` is deliberate (the master secret is already a uniform Argon2id key; the salt lives in Argon2id, G16 header). Store only the salt and Argon2 params; **no passphrase/verification hash is stored** (that would be an offline oracle). Unlock is verified implicitly by the ChaCha20-Poly1305 tag: the wrong passphrase makes the AEAD decryption fail. Passphrase minimum length is 12 (N11.3). Never store the passphrase or derived keys.

**DPAPI pepper:** A random 32-byte pepper (second factor of the key derivation, gate G18) is stored in the Windows Credential Manager via `keyring`, never in the DB. This is the only use of `keyring` (there are no Microsoft tokens anymore). **No pepper recovery export (N11.3):** the vault is deliberately bound to this Windows account, so losing the account (or forgetting the passphrase) means the data is unrecoverable; the only escape is the lock-screen Reset (which wipes the vault).

**No cloud / no sync:** the app is purely local. There is no external service, no Microsoft integration, and nothing ever leaves the machine.

**Frontend fonts:** JetBrains Mono and Space Grotesk must be local `.woff2` files. No external font CDN, this is a local-first app.

**CSS:** The complete `<style>` section from `Planung/weiteres/NoaToDo UI Konzept.html` is extracted verbatim into `frontend/style.css`. Do not rebuild it from scratch. The design tokens (colors, spacing, fonts) are defined there and must not be reinvented.

**Completion sound:** Checking a task off plays a short "Datenstrom" blip (`playDoneSound` in `app.js`). It is synthesized live with the Web Audio API (square-wave oscillators, no audio file), specifically so it needs no `media-src` and stays compatible with the strict CSP (`default-src 'self'`). Do not replace it with a bundled `.mp3`/`.wav` (that would require loosening the CSP). The `AudioContext` is created lazily on the first check (browsers require a user gesture before audio) and reused. The sound will become toggleable via the `sound` setting (default on, N11.6). `Code/sound-preview.html` is a standalone dev scratch file for auditioning sound variants, not part of the app and not loaded by it.

## Security rules (mandatory: all untrusted input must follow these)

Task text and list names are user-entered free text and treated as **untrusted input** (the app is local, so there is no external data source, but the defensive rules cost nothing and stay mandatory). These rules apply everywhere such values touch code:

**Escape every foreign value before it reaches `innerHTML` (anti-XSS):** The frontend runs with full `pywebview.api.*` access, an XSS is effectively RCE against the backend. `app.js` renders by building HTML strings from template literals and assigning them to `root.innerHTML` (full re-render via `render()`); it does NOT use `textContent`/`createTextNode` per node. The mandatory rule is therefore: any (potentially) foreign value interpolated into one of those template strings (task text, list name, ids) MUST be wrapped in the `esc()` helper near the top of `app.js`, which escapes `& < > " '`.
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

**Input validation (gate G20, implemented 2026-07-17):** every bridge method carries a declarative schema at its `@bridge(schema={...})` decorator (validators `v_text`/`v_id`/`v_str_list`/`v_bool`/`v_task_fields` plus `SETTINGS_SCHEMA`/`_validate_setting` in `api.py`; introspectable via `method._schema` for the Phase 9 tests; violations raise `InvalidInput` -> catalog code `invalid`). The rules: truncate task text > 4096 chars, list names > 256 chars (no more `meta` after N11.1.3); strip control characters U+0000-U+001F (except newline/tab) from stored strings; `reorder`/`reorder_lists` require `ordered_ids` to be **exactly** the list's task set (open and done together) resp. the full list set (as a set: no missing, duplicate, foreign or cross-list id), else `invalid` and nothing is written (all-or-nothing, no partial reorder), then renumber `position` 0..n-1; `move_task` validates both ids (missing -> `not_found`, target = current list -> `invalid`), **keeps `done`** and appends the task to the end of its section in the target list (highest position; the frontend sorts each section by position), then renumbers source and target 0..n-1 (U11-Entscheid, Bauplan N11.2.2); and `set_setting` only accepts whitelisted keys (`accent`, `theme`, `density`, `sidebar`, `railPinned`, `sidebarWidth`, `sound`, `autoLock`; plus `dark` transitionally until N11.6 replaces it with `theme`) **and validates the value per key (V5, 2026-07-15):** `theme`/`density`/`sidebar` against their enums, `accent` against the fixed six-value hex preset whitelist (the value lands in the DOM as a CSS variable, so the whitelist kills CSS injection via settings), `sidebarWidth` clamped to 180-520 on write (not only parsed on read), `sound` bool, `autoLock` integer from {0, 1, 5, 15, 30, 60}; `edit_task.fields` is type-checked (known fields only, `text` string, `done` bool). Preferred shape: a declarative schema per bridge method at the `@bridge` decorator so Phase 9 can test the rules directly. Export filename hardening (G21) additionally replaces the Windows-forbidden characters `< > : " / \ | ? *` and `..` sequences with `_` and caps the name at about 120 chars before the reserved-device-name check (V6, applies to `export_list` and `export_all`).

## Lock policy (B.8)

The app is always fully locked or fully unlocked. Lock triggers (passphrase required on return):
- Lock button / `Ctrl+L`
- Panic (mouse only via the rail button; deliberately no keyboard shortcut, N5)
- App restart (always starts locked)
- Auto-lock after inactivity (configurable via the `autoLock` setting, default 15 min, `0` = never; N11.4). **"Inactivity" is defined in N11.4.2:** activity = input events in the app window's DOM (mouse/keyboard/wheel/scroll), NOT global system idle and NOT bridge calls in general. The frontend reports it throttled (leading edge, then at most every 30 s) via `activity_ping()`, which only stamps `last_activity` on the backend's monotonic clock. The backend timer is the **sole, fail-safe** authority: if pings stop (frontend hangs/crashes/XSS-killed), the app locks; the frontend can only defer the lock, never prevent it. **Only** `activity_ping` counts as activity (no other bridge call, so a background poll like `get_wifi_signal()` does not keep the app awake); it is NOT in `ALLOWED_WHEN_LOCKED`, so while locked it returns `locked` and does not touch the timer.

**No lock on:** window minimize, focus switch to another app, window resize/move, **Windows session lock (Win+L)**. Win+L does nothing for NoaToDo (N11.8.4): there is no `WTSRegisterSessionNotification` / `WM_WTSSESSION_CHANGE` / `WTS_SESSION_LOCK` hook and none may be added. The auto-lock is the only reliable lock; its background timer (monotonic clock, own thread) keeps running while the PC is locked, so the app is guaranteed locked when the user comes back after the timeout.

**Auto-lock while a native dialog is open (N11.11.5, U5 decision 2026-07-13):** the export save dialog and the onboarding folder dialog are the only modal native windows; tearing the main window down under one of them hangs or crashes the app. The fix is **not** "postpone the lock" (that would let anyone suppress the auto-lock forever by leaving `Ctrl+E`'s dialog open, threat class K3, and would let a returning dialog write a plaintext export while locked). The rule is to **split the teardown sequence**: on `autolock` with a dialog open, steps 1 to 7 of N11.11.2 run immediately (freeze the bridge, flush the write-back, clear the clipboard, close the DB, **zero the keys**) and the frontend renders the lock screen via `evaluate_js` (pure DOM, safe under a modal dialog); only the native steps 9 to 11 (tear down the view, wipe `PROFILE_DIR`) wait, and the sequence **closes the dialog itself** instead of waiting for it. A dialog returning after a lock has its result voided: no file is written, the export buffer is zeroed, the method returns `{"error": "locked"}`. Every other exit (lock button, `Ctrl+L`, panic, killswitch, reset, quit, window X) cancels the dialog at once and does not defer. All `create_file_dialog` calls go through one `_native_dialog()` context manager in `api.py` (flag released in `finally`, at most one dialog at a time, a second one returns the new `busy` error code); an open dialog is **not** activity and does not reset the auto-lock timer.

**Unlock, reset, rate-limit (Phase 8 target, N11.3/N11.4):** first run lets the user choose the vault file location (path stored in an unencrypted config, N11.3) and set a passphrase (min 12 chars, prominent "no recovery" warning). A forgotten passphrase has no recovery; the lock screen offers a **Reset** (killswitch-style confirm, then type `RESET`) that wipes the vault and restarts full onboarding (choose location + new passphrase). Passphrase is changeable in Settings. Wrong-passphrase rate-limit: 2 s after each attempt, 3 free tries, then an escalating lockout ladder 10 s / 30 s / 1 min / 5 min / 15 min / 30 min / 1 h / 5 h / 10 h (each stage allows 2 tries before advancing).

**Rate-limit state is persisted (N11.4.1, U6 decision 2026-07-13):** the ladder must survive a restart, otherwise the lock screen's own off button resets it in two clicks. `{fails, stage, next_try_at, locked_at, duration}` live in `config.json` (unencrypted, outside the vault, which is closed while locked; full schema in N11.15.1, Plananalyse U2 resolved). Only a successful `unlock()` clears it (and `reset_vault()`, which deletes everything anyway). **Persist before verify (pro-security):** a failed attempt is counted and `config.json` is written **atomically before** Argon2id/AEAD even run and before any response goes back, so killing the process mid-check can't dodge the count the way the off button did; every non-success outcome (wrong, crash, kill, power loss) leaves the raised state. Stage/`duration`/`next_try_at` derive from `fails` through **one** deterministic function (identical live and on restart); on a `fails`/`stage` mismatch the higher value wins. Two clocks, deliberately: `time.monotonic()` within a session (immune to clock tampering), UTC wall-clock timestamps across restarts; within a session the remaining lockout is `max(monotonic, wall-clock)`, never the shorter; if `now < locked_at` (clock turned back) or the values contradict each other, the current lockout **restarts in full**, never shortens. Honest scope (threat model K3): the ladder only slows the casual on-device guesser. Whoever can copy `tasks.db.enc` guesses offline, where no ladder exists (only Argon2id cost + DPAPI pepper stand there), and whoever has file access can delete `config.json` to reset the ladder. Never sell it as protection against K1.

**Onboarding and vault management (N11.13, U1 decision 2026-07-13):** boot is **three-valued**, not two: `get_boot_state()` returns `onboarding | locked | unlocked` and is the first and only call the frontend makes before rendering anything (the switch is N11.8.2: only the existence of `tasks.db.enc` at the path from `config.json` decides). `get_state()` stays two-valued on purpose so G13's "locked reveals nothing" rule stays sharp. Onboarding is a boot state, not a modal (no `Esc`, no way past creating the vault): three screens (location incl. cloud-path warning per G32, passphrase with the loss warning as mandatory text plus an active "I understand" checkbox, then done and unlocked with an empty list view). The loss warning must name **both** facts: forgotten passphrase = data gone, and the vault is bound to this Windows account (other PC or fresh profile = data gone even with the right passphrase). `config.json` schema (U2) and the passphrase-change details incl. the `.bak` generation (U8) are now both resolved (U2 in N11.15, 2026-07-15; U8 in N11.3 a-d): the change re-encrypts or securely deletes the `.bak` so nothing stays readable with the **old** passphrase, keeps the pepper, and lifts the Argon2 params to the G8 target (KDF-upgrade path), verified by a fixed Phase-9 crypto test.

**Shutdown/lock sequence (N11.11, gate G35, S5 decision 2026-07-13):** there is exactly **one** routine, `teardown(reason)` in `security.py`, and every exit runs through it (lock button, `Ctrl+L`, auto-lock, lock-screen off button, panic Finish, killswitch, reset, native window X, `atexit`). A second hand-written exit path is a gate violation. Order (N11.11.2, itself security-relevant): idempotency guard, resolve open native dialogs (every exit except auto-lock cancels the dialog outright; auto-lock still runs steps 1 to 7 immediately and defers only the native steps 9 to 11, see N11.11.5 above), freeze input (G13), **cancel the G17 debounce timer and persist pending changes synchronously** (skipped for killswitch/reset; on failure the sequence aborts into the N6 error screen rather than losing data; the G17 write-back debounces ~3 s after the last change but has a hard cap: **it writes at least every 30 s even under continuous edits**, so sustained typing cannot defer the write-back indefinitely, U20), **clear the clipboard if it still holds app content** (G23/V7), close the DB, zero the keys and discard the last-deleted-list undo buffer (G25, N11.2.1, so a locked app holds no deleted-task plaintext), only then delete files and the DPAPI pepper (killswitch/reset, U21), wipe `PROFILE_DIR` (G14; `LOCK_PROFILE_DIR` is never wiped), **restore the radio state last** (exit paths only, never on lock, N11.5/N11.10), release the mutex, exit. Steps after the flush are best effort: a failing step is skipped, never blocks the following ones.

## Bridge API (`pywebview.api.*`)

All frontend<->backend communication goes through these methods on the `Api` class in `backend/api.py`. Each returns a JSON-serializable value (or `{ "error": "code", "message": "..." }` on failure; the **canonical error-code table lives in Bauplan B.2**, see "Error hygiene" above, and a code that has no row there must not reach the frontend). Methods marked (stub) return placeholder values and will be replaced in later phases.

| Method | Args | Returns |
|---|---|---|
| `get_boot_state()` | (keine) | `{ state: 'onboarding'\|'locked'\|'unlocked', vault_path }` (planned, N11.13: the boot switch, first and only call before the frontend renders anything; allowed while locked) |
| `get_state()` | (keine) | `{ lists, settings, online, locked }` (only after unlock; locked it returns just `{ locked: true }`, G13) |
| `get_lists()` | (keine) | `[{ id, name, open:[task], done:[task] }]` |
| `add_list(name)` | str | `{ id, name, ... }` |
| `rename_list(id, name)` | str, str | `{ ok }` |
| `delete_list(id)` | str | `{ ok }` |
| `add_task(list_id, text)` | str, str | `{ ...task }` (no meta field, N11.1.3) |
| `toggle_task(id)` | str | `{ id, done }` |
| `edit_task(id, fields)` | str, obj | `{ ...task }` (text only, no meta, N11.1.3) |
| `delete_task(id)` | str | `{ ok }` |
| `reorder(list_id, ordered_ids)` | str, [str] | `{ ok }` (task order within a list) |
| `reorder_lists(ordered_ids)` | [str] | `{ ok }` (planned, N11.2: sidebar list order) |
| `move_task(id, target_list_id)` | str, str | `{ ...task }` (planned, N11.2: move task to another list) |
| `export_list(id, format)` | str, `'md'`\|`'txt'` | `{ filename, content }` (N11: JSON dropped) |
| `export_all(format)` | `'md'`\|`'txt'` | `{ filename, content }` (planned, N11.2: all lists in one file) |
| `copy_task(id)` | str | `{ ok, clears_in }` (hardened backend clipboard copy of ONE task) |
| `copy_errors()` | (keine) | `{ ok, clears_in }` (copies the redacted G29 error ring buffer via the same hardened G23 clipboard path; status modal "Recent errors" copy button) |
| `set_setting(key, value)` | str, * | `{ ok }` |
| `set_mini(flag)` | bool | `{ mini }` |
| `get_status()` | (keine) | `{ db, encryption, runtime }` |
| `set_online(flag)` | bool | `{ online }` today (local flag); N11.5 target `{ online, partial }`: real Windows airplane-mode toggle (all radios), answers only after completion with the verified real state, offline aggregates security-first (`online:true` while any radio stays on), partial success raises a toast, U15 |
| `get_wifi_signal()` | (keine) | `{ connected, percent, level }` (level 0-3, real WLAN strength via `netsh wlan show interfaces`; cosmetic, drives the rail WiFi icon; N11.5 polls every 10 s only while online + window visible + unlocked, paused otherwise, never counts as auto-lock activity, U15) |
| `activity_ping()` | (keine) | `{ ok }` (planned, N11.4.2: resets the auto-lock timer; frontend-throttled, leading edge then at most every 30 s; only stamps `last_activity` on the monotonic backend clock, takes no timestamp, cannot disable the timer; **not** in `ALLOWED_WHEN_LOCKED`, returns `locked` while locked; no other bridge call counts as activity) |
| `choose_vault_dir()` | (keine) | `{ path, has_vault }` or `{ error: 'canceled' }` (planned, N11.13: native folder dialog, checks writability, warns on cloud paths per G32; `has_vault:true` if the folder already holds a `tasks.db.enc` so onboarding offers "open this vault" instead of "create new" per N11.15.6; allowed while locked) |
| `create_vault(path, passphrase)` | str, str | `{ ok }` (planned, N11.13: pepper + salt + Argon2 params, empty DB, writes `tasks.db.enc` and the path into `config.json`; app is unlocked afterwards; **refuses with `invalid` if a `tasks.db.enc` already exists at `path`, an existing vault is never overwritten, N11.15.6**; allowed while locked) |
| `change_passphrase(old, new)` | str, str | `{ ok }` (planned, N11.13: Settings only, **not** in the locked allowlist; fresh salt + nonce, pepper stays; the `.bak` generation is re-encrypted with the new key (preferred, keeps the G16 crash backup) or removed via the secure-delete path so nothing stays readable with the old passphrase, and the Argon2 params are lifted to the G8 target = the KDF-upgrade path, N11.3 a-d, U8 resolved) |
| `reset_vault()` | (keine) | `{ ok }` (planned, N11.13: forgotten-passphrase exit; runs `teardown(reason='reset')`, deletes vault + `.bak` + metadata + pepper, then restarts onboarding; allowed while locked) |
| `lock()` | (keine) | `{ locked: true }` (frontend-only, gate G13 not enforced; the frontend clears the workspace and goes offline before calling it, N10) |
| `unlock(passphrase)` | str | today a placeholder returning `{ ok }`. **Phase 8 target (N6, resolves U7):** `{ ok:true }` on success, else the canonical B.2 codes, decided **before** the costly Argon2 by inspecting the unencrypted container header: missing file -> `vault` (never silent onboarding, that is only `get_boot_state()`), unreadable header (magic/version/salt/params/nonce) -> `vault` (N6 damaged screen + `.bak` offer), well-formed header but failing AEAD tag -> `passphrase` (+ `retry_in`), running lockout ladder -> `rate_limited` (+ `retry_in`). Only `passphrase` advances the N11.4 ladder; a `.bak` restore is a full unlock attempt under the same ladder and overwrites the primary only after it verifies; after `DAMAGE_HINT_AFTER = 5` consecutive `passphrase` results the lock screen adds a neutral "maybe damaged, try a backup?" hint. Frontend re-fetches `get_state()` after success |
| `panic()` | (keine) | `{ locked: true }` (frontend-only; flow ends in the end screen with Finish/Killswitch, N10) |
| `killswitch()` | (keine) | `{ ok }` (REALLY and irreversibly wipes all DB content, rewrites default settings + `seeded` marker; only reachable from the panic end screen) |
| `quit_app()` | (keine) | `{ ok }` (closes the app window via `BeginInvoke` on the UI thread; lock-screen off button, panic Finish, killswitch end) |

Backend -> frontend events (via `window.evaluate_js`): `window.noa.onLocked()`.

## SQLite schema (2 main tables + settings)

`lists(id, name, position, created_at, updated_at)`.  
`tasks(id, list_id, text, done, position, created_at, updated_at)` (the `meta` column was removed 2026-07-17 per N11.1.3, a task is only `text` + `done`; `_drop_legacy_columns()` migrates old dev DBs). **Position invariant (Bauplan B.1, U13 decision 2026-07-15, implemented 2026-07-17):** `position` is kept **per section**, i.e. `open` (`done=0`) and `done` (`done=1`) each have their own 0..n sequence within a list. Checking a task off appends it to the **end of `done`** (`MAX(position) + 1` among that list's done tasks); reopening appends it to the **end of `open`**; a new task appends to the end of `open` (`MAX+1` only among `done=0`); `reorder` takes the list's full task set (open + done, N11.2.2) and renumbers 0..n-1 per section; each section is ordered by `(position, created_at)`. The frontend cache mirrors this (checked task is push-ed to the end of `done`).  
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

Bauplan B.5 is the **single source of truth** for shortcuts (fully re-derived from the real `onKeyGlobal` on 2026-07-13, resolving Plananalyse W6). Whoever changes or adds a shortcut updates the code, Bauplan B.5, the shortcuts modal (`?`), and this table in the same change.

| Action | Key |
|---|---|
| New task | `Enter` (in new-task field) |
| New task in open list | `Ctrl+N` (toggles the bottom new-task field, second press closes it; needs an open list) |
| New list | `Ctrl+Shift+N` (toggles the new-list field, second press closes it) |
| Toggle sidebar | `Ctrl+B` |
| Focus mode | `F` (needs an open list; exit always works) |
| Switch list | `Ctrl+ArrowUp` / `Ctrl+ArrowDown` (sidebar open and a list open; stops at the ends, no wrap-around) |
| Open list 1-9 | `Ctrl+1` bis `Ctrl+9` (opens the n-th sidebar list, 1 = topmost; same key again toggles it closed; only when the sidebar is open, a list open with the sidebar closed does not count) |
| Lock app | `Ctrl+L` |
| Export | `Ctrl+E` (today: exports the currently open list directly; Phase 7 target per N11.2: opens the two-step export pill; with no open list the "current list" scope option is greyed out, only "all lists" is selectable, N11.2.3) |
| Toggle theme | `Ctrl+J` (from `auto`: override to the opposite of the shown theme; from a fixed theme: the other fixed theme; back to `auto` only via the Settings segment) |
| Online/offline | `G` |
| Shortcut help | `?` |
| Close all | `Esc` (closes menus/modals/inputs, clears selection and focus mode; in mini mode it exits mini; closes the panic panel but never the running/finished wipe screen; also works while typing) |

Deliberately WITHOUT a shortcut (per B.5, do not add one): the panic flow (rail button only, two-stage arming; decided 2026-07-13, Bauplan N5, the former `Ctrl+Shift+!` idea is dropped for good), copy (rail button only, gate G23, no `Ctrl+C` app shortcut), and mini mode (rail button only; `Esc` exits it). Mouse gestures (click = select, double-click = inline edit, drag = reorder) are documented in the shortcuts modal.

Letter hotkeys (`F`, `G`, `?`) must not fire while focus is inside an input or textarea; the exceptions are `Esc` and the `Ctrl+N`/`Ctrl+Shift+N` toggles (so the second press can close the freshly opened field). Both call `e.preventDefault()` so the triggering letter does not land in the freshly focused input (and to suppress the browser's default new-window action). While the app is locked, all shortcuts are disabled; any printable key instead focuses the lock-screen password input (the character itself is then inserted normally).

## Key dependencies

`pywebview`, `sqlcipher3-wheels` (import `sqlcipher3`), `cryptography`, `argon2-cffi`, `keyring` (only for the DPAPI pepper, gate G18). See `Code/requirements.txt`.

**Planned for the real airplane-mode toggle (N11.5, resolves U14; not yet in `requirements.txt`):** the modular PyWinRT packages `winrt-runtime`, `winrt-Windows.Devices.Radios`, `winrt-Windows.Devices.Enumeration`, `winrt-Windows.Foundation` (smaller surface than the `winsdk` bundle, which stays only a fallback). `set_online` will enumerate radios via `Radio.GetRadiosAsync()`, switch each WiFi/Bluetooth/MobileBroadband radio with `SetStateAsync`, and read the state back; there is no switchable airplane-mode flag in the public API, only individual radios. Denied `RequestAccessAsync` degrades visibly (tooltip "no radio access", no radio touched, state unchanged). All new packages must be pinned in `requirements.lock.txt` under gate G11.

**Python version is pinned to 3.11.x (gate G11, Plananalyse U25):** the interpreter is treated as a pinned dependency, not just the packages. `sqlcipher3-wheels` ships wheels only for specific CPython versions, and the Phase 9 `.exe` must be built against exactly this interpreter. Today's setup runs on Microsoft-Store Python 3.11; the release build (Phase 9) runs under 3.11.x as well. Do not build or target another Python minor version without updating G11 in the Bauplan first.
