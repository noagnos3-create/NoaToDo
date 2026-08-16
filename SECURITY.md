# Security Policy

## Reporting a vulnerability

**Please report security issues privately, not as a public issue.**

Two ways, either is fine:

- GitHub's private vulnerability reporting: the **Security** tab of this repository, then **Report a vulnerability**.
- Email: noagnos3@gmail.com

This project is maintained by one person in their spare time. Expect a first reply within seven days. Please allow 90 days before disclosing publicly, and let me know if you intend to publish sooner, so I can prioritise accordingly.

If you want to encrypt your report, say so in a first short message and we will arrange a key.

## What I consider in scope

- Anything that puts task text, list names or the passphrase outside the vault: on disk, in the clipboard, in a log, in a crash artifact, in a window title, or on the network.
- Anything that runs code inside the WebView. This is the sharpest edge in the app: the frontend has full access to `pywebview.api.*`, so cross-site scripting is effectively remote code execution against the backend, including the killswitch.
- Anything that bypasses the lock: reaching a bridge method that is not in the locked allowlist, defeating the inactivity timer, or getting past the rate limit ladder.
- Mistakes in the cryptography: the key derivation, the domain separation, the `.enc` container format, nonce or salt handling, the AEAD usage, or the backup rotation.
- Anything that leaves plaintext behind where the app claims it does not: the working copy, the WebView profile, the legacy cleanup, the teardown sequence.
- **Dishonest claims.** If the app, this README or the status dialog states something the code does not actually do, that is a bug in this project even when nothing is technically broken. Honest security claims are a hard rule here, not a nicety, and a false claim erodes exactly the thing the app is asking users to rely on.

## What is out of scope

These are documented non-goals, not oversights. Each one is argued in the [threat model](docs/threat-model.md), and a report that simply demonstrates one of them will be closed with a pointer to that document.

- **Malware or code execution in the same Windows user account.** Anything running as you can read the DPAPI pepper, hook the keyboard, read unlocked process memory or replace `app.js`. No application can defend against an attacker inside its own security context, including one that claims it can. Hardening that makes *silent persistence* harder is in scope; a report that boils down to "if I can already run code as the user, I win" is not.
- **A compromised or hostile Windows installation**, including an administrator attacker, kernel-level malware, or a manipulated WebView2 runtime.
- **Optical and physical channels:** a photo of the screen, shoulder surfing, a camera in the room, a hardware keylogger, evil-maid or DMA attacks on a running machine. The screen shows plaintext, that is the purpose of the app.
- **Data recovery after a forgotten passphrase or a lost Windows account.** There is none, deliberately. That is part of the protection, not a missing feature.
- **The export feature writing plaintext.** That is what an export is.
- **The missing code signature.** It is known and documented. A certificate is a cost question, not an oversight.
- **Retention by a third party.** If the vault file is placed in a cloud sync folder, the provider keeps versions, and neither the killswitch nor the reset can delete those. The app warns about this during setup; it cannot prevent it.
- **The rate limit ladder being resettable by deleting `config.json`.** Known and stated: the ladder slows a person at the keyboard, nothing else.

## Supported versions

Only the latest release. There are no backports and no long-term branches.

If a relevant vulnerability appears in a pinned dependency (`cryptography`, `pywebview`, `sqlcipher3-wheels` and the like), a rebuild is published even without any functional change. The browser part is covered automatically by the evergreen WebView2 runtime, which Windows keeps up to date.

## What the app does not do to you

Worth stating in a security file, because it is checkable rather than promised: NoaToDo makes **no outbound network connections at all**. There is no HTTP client anywhere in the codebase, no telemetry, no crash reporting, no update check. The only external commands it runs are `netsh wlan show interfaces` for the WiFi signal strength icon and a WMI query for the BitLocker status. Both are local, and both are visible in the source.
