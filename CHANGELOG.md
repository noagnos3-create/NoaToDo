# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/).

The version number is visible inside the app, in the status dialog, together with
the build date and the commit the binary was built from.

## [Unreleased]

Nothing yet.

## [1.0.0] - 2026-08-16

The first release. Everything below is new, so this entry describes the app
rather than a diff against a predecessor.

### Added

**Tasks and lists**
- Lists and tasks with drag-and-drop ordering, inline editing on double-click,
  and separate ordering for open and completed tasks.
- Moving a task to another list by dragging it onto a sidebar entry or through a
  right-click menu.
- Undo for a deleted list, held in memory for a few seconds, discarded on lock.
- Export of the current list or of all lists to Markdown or plain text through a
  native save dialog, with a setting for whether completed tasks are included.
- A hardened single-task clipboard copy that is excluded from the Windows
  clipboard history and from cloud clipboard sync, and clears itself after
  60 seconds.

**Security**
- Dual-layer encryption at rest: ChaCha20-Poly1305 around a SQLCipher AES-256
  database, in a versioned container whose header is authenticated as associated
  data.
- Argon2id key derivation (256 MiB, 3 iterations, 4 lanes) with a random 32-byte
  DPAPI pepper from the Windows Credential Manager mixed in before the hash, and
  HKDF-SHA256 domain separation into two independent keys.
- A working copy that is itself SQLCipher-encrypted, never plaintext, securely
  deleted on every lock.
- A lock screen on every start, on `Ctrl+L`, and after a configurable inactivity
  timeout enforced by a fail-safe backend timer.
- The lock enforced in the backend as an explicit allowlist, so a locked app
  answers almost every bridge call with `locked` and reveals nothing.
- A persisted rate limit ladder for wrong passphrases that survives restarts and
  is written before the check runs.
- A panic flow that clears the screen and switches the radios off, ending in a
  screen with an honest label and a two-stage killswitch that really deletes
  everything.
- A reset path on the lock screen for a forgotten passphrase.
- Passphrase change from the settings, which re-encrypts the backup generation so
  nothing stays readable with the old passphrase.
- One single teardown sequence that every exit path runs through, including the
  window close button, with key zeroing, clipboard clearing and profile wiping.

**Interface**
- A design that also applies to the native windows: dark DWM title bars, the app
  grid, self-drawn pill controls, and a curtain that makes window handovers
  seamless.
- A welcome screen on start, an unlock animation on the lock ring, and a power
  button that arms itself over a ring sweep instead of quitting on the first
  click.
- Theme that follows the Windows light and dark setting live, six accent colours,
  two density settings, a resizable sidebar, focus mode and mini mode.
- A completion sound synthesised in the Web Audio API, so no audio file and no
  loosened Content Security Policy.
- A status dialog that reports the real state and says "unknown" where it cannot
  read something, instead of claiming anything.

**Windows integration**
- A real airplane mode that switches the actual WiFi, Bluetooth and mobile
  radios, reads the state back, reports refusals honestly, mirrors external
  changes, and restores the pre-app state on exit.
- Single-instance protection, a per-user mutex namespace, and a first-start
  cleanup of paths left behind by earlier development builds.

**Build and release**
- A single-file `NoaToDo.exe` built with PyInstaller at optimisation level 2,
  with the icon and version resource embedded and no UPX.
- A startup integrity check of every frontend file against a hash manifest
  embedded in the binary, refusing to start on any mismatch.
- Release hardening: no DevTools, no browser accelerator keys, no default context
  menu, and a debug switch that is a build constant rather than an environment
  variable.
- An honest message and a clean exit when the WebView2 runtime is missing,
  instead of a blank window.
- Hash-pinned dependencies and a pinned CPython version, enforced by the build
  script.
- 63 tests covering the database layer, input validation, the lock allowlist, the
  cryptography, the rate limit ladder, the teardown sequence and a set of release
  checks.

### Not included, deliberately

No cloud, no sync, no account, no telemetry, no update check, no notifications,
no full-text search, no due dates, no reminders, no recovery for a forgotten
passphrase, and no screenshot protection. The reasoning for each is in
[docs/threat-model.md](docs/threat-model.md) and in the README.

### Known limitations of this release

- The executable is **not code-signed**. Windows SmartScreen warns on first run,
  and a tampered binary cannot be detected by signature. Verify the published
  SHA-256 checksum, or build it yourself.
- Builds are not bit-for-bit reproducible.
- The Microsoft Edge WebView2 runtime is assumed to be present and is not
  bundled.
- Windows only, by construction.

### History

This is the first published version, but not the first commit. The repository
carries the full development history from June 2026 onwards, phase by phase, in
German commit messages.
