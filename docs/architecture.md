# Architecture

What you need to know before changing anything. This is the English extract of a
much longer German specification that is not part of this repository; the parts
that matter for reading and modifying the code are here.

Every path below is relative to `src/`, which is also the directory every command
runs from.

## The big picture

NoaToDo is one process. A Python backend and a vanilla JavaScript frontend run
together in a single native window through [PyWebView](https://pywebview.flowrl.com/),
which uses the Windows WebView2 control. No browser engine is bundled, and there
is no build step for the frontend: `index.html`, `style.css` and `app.js` are
loaded as they are.

```
+-------------------------------------------------------------+
|  NoaToDo.exe (one process)                                   |
|                                                              |
|  +--------------------------+   +-------------------------+  |
|  |  WebView2 (Chromium)     |   |  Python backend         |  |
|  |  index.html              |   |  api.py   the bridge    |  |
|  |  style.css               |<->|  db.py    SQLCipher     |  |
|  |  app.js                  |   |  security.py  vault     |  |
|  |  renders, holds no truth |   |  the source of truth    |  |
|  +--------------------------+   +-------------------------+  |
|              ^                              |                |
|              |                              v                |
|  +--------------------------+   +-------------------------+  |
|  |  Native WinForms windows |   |  tasks.db.enc           |  |
|  |  lockwindow.py           |   |  ChaCha20-Poly1305 over |  |
|  |  wintheme.py             |   |  SQLCipher AES-256      |  |
|  +--------------------------+   +-------------------------+  |
+-------------------------------------------------------------+
```

**The backend is the source of truth.** The frontend holds a cache and nothing
more. After every mutating action it applies the backend's answer to its state
and re-renders. If the two ever disagree, the frontend is wrong.

## Boot: three states, not two

`main.py` runs a loop rather than a single startup. `get_boot_state()` is the
first and only call the frontend makes before it renders anything, and it returns
one of three states:

- `onboarding`: there is no config, or no vault file at the path the config
  names. Setup runs as a boot state, not as a modal, so there is no way to press
  `Esc` past creating a vault.
- `locked`: a vault exists. The **native** lock window opens, not the WebView.
- `unlocked`: the session is open, the WebView main window runs.

The loop alternates between the native lock window and the WebView main window,
and wipes the WebView profile directory after each window teardown. The lock
screen is a native WinForms window because a spike proved that PyWebView cannot
run two WebView2 profiles in one process; that fallback is binding, and there is
no second profile directory anywhere.

`get_state()` deliberately stays two-valued. While locked it returns nothing but
`{ locked: true }`, so "locked reveals nothing" stays a sharp rule.

## The bridge

Every call from the frontend to the backend goes through public methods on the
`Api` class in `backend/api.py`, reachable as `pywebview.api.<name>()`.

### The `@bridge` decorator

Every public method carries it, and it does four things:

1. **Enforces the lock.** While locked, only an explicit allowlist is reachable:
   `unlock`, `quit_app`, `killswitch`, `get_state`, `get_boot_state`,
   `choose_vault_dir`, `create_vault`, `reset_vault`. Everything else returns
   `{"error": "locked"}`. It is an allowlist, not "everything except X": a newly
   added method is denied by default and has to be permitted deliberately.
2. **Validates input** against a declarative schema passed at the decorator, so
   the rules are introspectable and directly testable.
3. **Maps exceptions to a fixed catalogue.** `KeyError` becomes `not_found`,
   `MemoryError` becomes `memory`, anything else becomes `internal` plus a
   four-hex reference.
4. **Keeps error details out of the frontend**, see below.

### Error hygiene

The frontend only ever sees a **code plus a static English message** from a
canonical table: `not_found`, `invalid`, `locked`, `passphrase`, `rate_limited`,
`vault`, `canceled`, `busy`, `memory`, `internal`. Never `str(exc)`, never a
path, a traceback, an SQL fragment, task text, a passphrase or a key. A code with
no row in that table must not reach the frontend.

Details go into a redacted in-memory ring buffer (the last 50 entries, paths
replaced, capped at 200 characters, never bridge arguments), visible in the
status dialog and cleared on every teardown. There is **no persistent log file in
the release**: no file handler, no traceback file. Verbose diagnostics exist only
behind an environment variable, and that variable is hard-disabled in a frozen
build.

`handleError(res)` in `app.js` is the single error sink on the other side.

### The methods

| Method | Returns |
|:--|:--|
| `get_boot_state()` | `{ state, vault_path, resumed }` |
| `get_state()` | `{ lists, settings, online, locked, system_theme }`, or just `{ locked: true }` |
| `get_lists()` | `[{ id, name, open: [task], done: [task] }]` |
| `add_list`, `rename_list`, `delete_list`, `undo_delete_list` | list operations |
| `add_task`, `toggle_task`, `edit_task`, `delete_task` | task operations |
| `reorder(list_id, ordered_ids)`, `reorder_lists(ordered_ids)` | ordering |
| `move_task(id, target_list_id)` | move between lists, keeps `done` |
| `export_list(id, format)`, `export_all(format)` | `md` or `txt`, shows the save dialog |
| `copy_task(id)`, `copy_errors()` | hardened clipboard path |
| `set_setting(key, value)`, `set_mini(flag)` | settings and window mode |
| `get_status()` | everything the status dialog shows |
| `set_online(flag)`, `get_wifi_signal()` | the real radios |
| `activity_ping()` | stamps the auto-lock clock, nothing else |
| `choose_vault_dir()`, `create_vault(path, passphrase)`, `open_existing_vault(path)` | setup |
| `unlock(passphrase)`, `lock()`, `change_passphrase(old, new)`, `reset_vault()` | session |
| `panic()`, `killswitch()`, `quit_app()` | exits |

Backend to frontend events, sent through `evaluate_js`: `window.noa.onLocked()`,
`window.noa.onNetChange(online)`, `window.noa.onSystemTheme(dark)`.

### Input validation

Task text is truncated above 4096 characters, list names above 256. Control
characters are stripped. A reorder must name **exactly** the target set, as a set:
no missing, duplicate, foreign or cross-list id, otherwise nothing is written at
all. `set_setting` accepts only whitelisted keys **and** validates the value per
key: enums against their values, the accent colour against a fixed list of six
hex presets (the value lands in the DOM as a CSS variable, so the whitelist is
what stops CSS injection through settings), the sidebar width clamped on write,
the auto-lock interval against a fixed set of minute values.

## The frontend

`app.js` holds one in-memory state object and rebuilds the **entire** DOM on every
render:

```js
root.innerHTML = /* one big template string */;
```

There is no per-node diffing. Two consequences that trip people up:

**Interaction is delegated, never attached.** Clickable elements carry a
`data-act="..."` attribute (often with `data-id`), and one central handler
dispatches on it. Adding an interaction means emitting a `data-act` in the
template and adding a `case` to that dispatcher. Listeners attached after a
render would be gone at the next one.

**Every foreign value must go through `esc()`.**

```js
`<span class="t-text">${esc(t.text)}</span>`   // correct
`<span class="t-text">${t.text}</span>`         // forbidden
```

This is the sharpest rule in the codebase. The frontend has full access to
`pywebview.api.*`, so an XSS is effectively remote code execution against the
backend, including the killswitch. The Content Security Policy in `index.html`
(`script-src 'self'`, no `unsafe-inline` for scripts) is defence in depth, not a
substitute.

A few renders deliberately bypass `render()` and touch the DOM in place, because
a full re-render would restart animations or tear a running progress bar apart:
the welcome screen fade, the theme switch from an OS event, the two-stage
killswitch button, and the panic progress screen. If you touch those, keep them
in place.

## Data model

Two tables plus settings:

- `lists(id, name, position, created_at, updated_at)`
- `tasks(id, list_id, text, done, position, created_at, updated_at)`
- `settings(key, value)`, all values stored as strings

A task is text plus a done flag. There is no metadata column, no due date, and
none of those are coming back.

**The position invariant:** `position` is kept **per section**. Open tasks
(`done=0`) and completed tasks (`done=1`) each have their own 0..n sequence
inside a list. Checking a task off appends it to the end of the completed
section, reopening appends it to the end of the open section, a new task appends
to the end of open. A reorder takes the list's full task set and renumbers each
section 0..n-1. Each section is ordered by `(position, created_at)`. The frontend
cache mirrors exactly this.

All SQL uses `?` placeholders. The one f-string, in `edit_task`, builds a SET
clause from a whitelisted column set and is safe by construction.

Settings keys: `accent`, `theme`, `density`, `sidebar`, `railPinned`,
`sidebarWidth`, `sound`, `autoLock`, `exportDone`. Ids are `'l' + uuid` for lists
and `'t' + uuid` for tasks.

## Security architecture

`backend/security.py` holds the whole session lifecycle. The shape you need to
know:

- **At rest** there is exactly one artifact: `tasks.db.enc` at the user-chosen
  path, plus a `.bak` generation. It is ChaCha20-Poly1305 over a SQLCipher
  AES-256 image. The container header (magic, format version, KDF parameters,
  salt, nonce) goes into the AEAD as associated data, so it cannot be altered
  unnoticed. Parameters are validated against an accepted range **before**
  allocation, which blocks a header-inflation denial of service.
- **On unlock** the outer layer is removed into a working copy under
  `%LOCALAPPDATA%\NoaToDo\work`, which is itself SQLCipher-encrypted. Never
  plaintext, never `%TEMP%`. Snapshots use `VACUUM INTO`, because the SQLCipher
  binding exposes no in-memory serialisation.
- **While unlocked** a debounced write-back runs about three seconds after the
  last change, with a hard cap of thirty seconds, so continuous typing cannot
  postpone it indefinitely.
- **On the way out** exactly one routine, `teardown(reason)`, runs, and **every**
  exit path goes through it: the lock button, the shortcut, the auto-lock, the
  lock screen's power button, panic finish, the killswitch, the reset, the window
  close button, and the interpreter exit hook. A second hand-written exit path is
  a defect. Its order is itself security-relevant: resolve open native dialogs,
  freeze the bridge, cancel the debounce and flush synchronously, clear the
  clipboard if it still holds app content, close the database, zero the keys and
  drop the undo buffer, then delete files, wipe the WebView profile, restore the
  radio state, release the mutex, exit. Everything after the flush is best
  effort: a failing step is skipped, never blocking the next one.

Two subtleties worth knowing before you touch this:

**Auto-lock is fail-safe by design.** The frontend reports activity through
`activity_ping()`, throttled, and that call does nothing but stamp a monotonic
clock in the backend. The backend timer is the sole authority. A hung, crashed or
compromised frontend can **delay** the lock, never prevent it. No other bridge
call counts as activity, so a background poll cannot keep the app awake.

**A native dialog open during an auto-lock does not postpone it.** Otherwise
anyone could suppress the lock forever by leaving a save dialog open. Instead the
sequence splits: the non-native steps run immediately, including zeroing the
keys, the frontend renders the lock screen through `evaluate_js`, and only the
native teardown waits. A dialog that returns afterwards has its result voided: no
file is written and the method returns `locked`.

## Native windows

No window NoaToDo opens may look like plain Windows. `wintheme.py` is the single
implementation of that look: the design tokens copied from `style.css`, the DWM
dark title bar, the app backdrop with its grid, and self-drawn antialiased pill
controls (buttons, inputs, links, labels) plus the themed message window.

`lockwindow.py` builds the lock screen on top of it, and also owns the
**curtain**: a maximised, app-designed window that is raised **before** the old
window closes and taken down only once the next one has painted. Without it the
screen goes briefly empty during a handover, which reads as the app minimising.
The curtain runs on its own UI thread with its own message loop, because the main
thread is blocked during a handover.

Honest limits of the native look, which are documented rather than quietly
worked around: Windows' own file and folder dialogs stay Windows-looking, the
three caption buttons are drawn by Windows, and the app fonts exist only as
`.woff2`, which GDI+ cannot load, so native windows fall back to the same CSS
chain's last stage.

## Threading rules

This is where the app has historically deadlocked, so it is worth stating
plainly.

PyWebView runs bridge methods on an API worker thread. `on_start` and the setting
and frame callbacks also run on a worker thread. **All** native window mutations
(size, position, always-on-top, border style, icon, title bar theme) must be
dispatched to the WinForms UI thread. Calling them directly from a worker thread
deadlocks the message loop, and the window then either never appears, appears
white, or reports "not responding" depending on timing.

Use the existing helpers rather than calling `window.native` members directly.

One more PyWebView-specific rule: it recursively scans all **public** attributes
of the API object to build the JavaScript bridge. Any attribute that is not a
plain method, and any method that must not become a bridge call, needs a leading
underscore. Otherwise PyWebView descends into it and may call into the window
before it is ready. All private state and all internal helpers in `Api` carry the
underscore for this reason.

## Build

`buildinfo.py` is the one source for everything that differs between "started
from the source tree" and "frozen executable": the version, the optional build
stamp, whether this is a release, whether debug is allowed (hard `False` when
frozen, so an environment variable cannot open a DevTools console with full
bridge access), and path resolution. A one-file build unpacks its assets into a
fresh temporary directory per start, so `__file__`-relative asset paths are wrong
there. Every access to a bundled file goes through `resource_path()`. Do not add
a second asset path helper and do not add a second debug switch.

`integrity.py` hashes every frontend file at build time into a manifest that is
embedded in the binary, and re-checks them at startup. On any mismatch the app
shows a message and **exits without starting**. There is deliberately no
"continue anyway" button, because a manipulated `app.js` has full bridge access
and can read the passphrase straight out of the lock screen. Without an embedded
manifest, a normal development start, the check is a no-op; otherwise every
frontend edit would cry wolf.

`tools/build_exe.py` is the single build entry point. It refuses to run on
anything but CPython 3.11.x, writes the build stamp, writes the version resource,
runs PyInstaller, and **deletes the stamp again** in a `finally`, because a
leftover stamp would make the next development start fail its own integrity
check.

## Things that will surprise you

- **The WebView2 cache is purged on every startup.** The fixed profile directory
  otherwise serves a stale frontend for hours, because Chromium applies heuristic
  freshness to files with no cache headers. This is not an optimisation
  opportunity.
- **Private mode is off on purpose**, replaced by one fixed user-private profile
  directory plus a single-instance mutex. The old per-start temporary profile
  piled up dozens of leftovers on hard exits and made startup take over a minute.
  Do not turn private mode back on.
- **Navigation is locked down.** Everything except the app's own files and
  loopback is cancelled. PyWebView 5 serves the frontend over a local HTTP server
  in every mode, not only in debug, which is why loopback is allowed
  unconditionally rather than behind the debug flag. Remote targets, the actual
  exfiltration vector, are still refused.
- **There is exactly one toast**, for undoing a deleted list. Every other
  confirmation and every error toast was removed deliberately. Do not add one.
- **`Win+L` does nothing** for NoaToDo. There is no session-change hook and none
  may be added. The auto-lock is the reliable lock, and its timer keeps running
  while the PC is locked.
- **The window title is constantly "NoaToDo"** and never carries user content, in
  any mode. The same goes for the taskbar tooltip.
