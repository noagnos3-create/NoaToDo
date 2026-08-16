# Threat model

This document says **who** NoaToDo defends against, and just as importantly, who it
does not. It is a condensed English translation of the binding German
specification the app was built from. Where the two differ, the German original
is the authority; if you find a difference, that is a bug worth reporting.

## Why this document exists

For a long time the specification defined countermeasures without ever naming an
opponent. That had three measurable consequences:

1. A promise was made that could not be kept unconditionally (the pepper claim,
   see below).
2. Fake countermeasures appeared against threats that no application in this
   position can address. One of them, screenshot protection, actively broke the
   app on some GPU and driver combinations while never defending against the real
   threat, which is a phone camera. It was removed.
3. The panic end screen claimed a wipe that had not happened, and nowhere was it
   written down why that was supposed to be acceptable.

**The rule since then:** every security measure has to name the attacker class it
addresses. A measure without a class is not security, it is theatre, and it does
not get built.

## What is protected

The protected assets are **the content of your tasks** (task text, list names) and
**the fact and pattern of your usage** (metadata).

Explicitly **not** protected assets:

- The existence of the app on your machine. It is visible, and that is intended.
- The program itself and its source code. Security here rests on the passphrase,
  the pepper and the encryption, never on hiding how any of it works. That is
  Kerckhoffs's principle, and it is the reason this repository can be public
  without weakening anything.

The app is purely local. There is no server, no account, no sync and no inbound
network channel, which removes entire attacker classes (server breach,
man-in-the-middle, account takeover) rather than defending against them. What
remains is local and enumerable.

## Attacker classes

| Class | Who or what | What actually helps | What remains, honestly |
|:--|:--|:--|:--|
| **K1** | **Someone who has the file or the disk.** Laptop stolen, SSD removed, `tasks.db.enc` copied. Has the file, not the running system. | Dual-layer encryption, Argon2id cost, HKDF domain separation, a container format with a fresh nonce per write, the DPAPI pepper, and no verification hash on disk | An offline guessing attack against the passphrase, **if** the attacker also obtains the pepper. Without the pepper, hopeless by current standards. See the conditioned promise below. |
| **K2** | **Forensics on a powered-off device.** An authority, a data recovery service, the buyer of your used SSD. Looks for remains outside the vault. | An encrypted working copy instead of a plaintext temp file, wiping the WebView profile, the killswitch as a real file deletion, deletion of development-era leftovers | **Without full-disk encryption this class wins.** SSD wear levelling makes secure overwriting unreliable, and remains in the pagefile, the hibernation file and crash dumps can survive. |
| **K3** | **Someone with brief physical access** to a running or locked machine. A flatmate, a colleague, a border check with the device in hand. Has minutes, not days. | The lock enforced in the backend as an allowlist, the inactivity auto-lock, a rate limit ladder that persists across restarts and resists clock tampering, locking on every start, the panic button, no plaintext in the window title, no DevTools in a release | If the app is **unlocked** and you walk away, everything is open. Only the auto-lock helps, default 15 minutes. A photo of the screen cannot be prevented. The ladder slows only this class. |
| **K4** | **Malware in your own Windows account.** An infostealer, a trojan, a remote access tool. Runs **with the same rights as the app**. | None that work. Hardening (CSP, `esc()`, the lock allowlist, clipboard hygiene, the frontend hash manifest, release hardening) raises the bar and prevents **silent persistence**, not access. | **An explicit non-goal, see below.** |
| **K5** | **Someone reverse-engineering the binary.** Looks for backdoors, static keys, weak derivation. | Binary hardening exists, but above all: **there is no secret in the code.** | Nothing harmful. Whoever fully understands the code is not one step closer to the data. That is the design. |
| **K6** | **Coercion.** Someone with authority or force demands that you open the app or name the passphrase. | The panic flow (clear the screen, wipe screen, end screen), the killswitch as a real and irreversible deletion, the reset on the lock screen | Against an attacker who waits and watches, no software helps. The panic flow buys seconds and covers the screen. It is not plausible deniability, which this app deliberately does not offer. |

## Explicit non-goals

A non-goal is not an omission. It is a commitment **not to build a fake
countermeasure** against it.

1. **Malware or code execution in the same user account (K4).** Whoever runs as
   you can read the pepper through the credential store (DPAPI decrypts for this
   account), hook the keyboard, read unlocked process memory, or replace
   `app.js`. No application in the same security context can do anything about
   that, **including one that claims it can.** The defence lives one layer down:
   a clean Windows and no malware. Measures that make persistence and silent
   observation harder remain welcome (frontend hashes against an embedded
   manifest, no DevTools in the release), but they are never *sold* as protection
   against K4.
2. **A compromised or hostile Windows.** An administrator attacker, kernel
   malware, a manipulated WebView2 runtime. Same reasoning, one level coarser.
3. **Optical and physical channels.** A photo of the screen, shoulder surfing, a
   camera in the room, a hardware keylogger, evil-maid or DMA attacks on a
   running device. The screen shows plaintext, that is the purpose of the app.
   This is why screenshot protection was rejected.
4. **Deliberate export.** The export writes plaintext files. That is intended and
   was explicitly asked for. From the moment it is saved, the file is outside the
   vault and outside this model.
5. **A forgotten passphrase or a lost Windows account.** No recovery, no backdoor
   key, no support path. That is part of the protection against K1 and K2, not a
   missing feature.
6. **Retention by third parties.** If the vault is placed in a cloud sync folder,
   the provider keeps versions, and neither the killswitch nor the reset deletes
   anything there. The app warns about this when you pick the location. It cannot
   prevent it.
7. **Plausible deniability and a hidden second vault.** Not planned. It would be
   the only real answer to K6, and in practice the file size often gives it away
   anyway. Whoever seriously fears K6 uses the killswitch.
8. **Copying from input fields.** Input fields stay selectable, which was
   accepted deliberately. Their native `Ctrl+C` lands unhardened in the Windows
   clipboard history and possibly in the cloud clipboard. The hardened path
   covers only the rail's copy button; the release hardening closes DevTools,
   `Ctrl+P` and the default context menu. The input field channel stays open, and
   it is not presented as closed.

## What you have to contribute

The promises above hold **only** under these conditions. They belong in the setup
interface and the status dialog, not only in a document, and they are stated in
both.

1. **Device encryption (BitLocker or Windows device encryption) is strongly
   recommended and effectively a prerequisite against K1 and K2.** Without it,
   the pagefile, the hibernation file and crash dumps sit in plaintext on the
   disk, development-era remains stay forensically findable, and the DPAPI pepper
   rests on the strength of your Windows sign-in password alone. The app queries
   the real BitLocker state and shows it, saying "unknown" when it cannot read it
   rather than claiming anything. Note that the query normally requires
   administrator rights, so "unknown" is the common case, not an error.
2. **A strong Windows sign-in password.** It protects the DPAPI store the pepper
   lives in.
3. **A strong, unique passphrase**, minimum length 12. It is the only factor an
   attacker with pepper access still has to guess. Argon2id makes each attempt
   expensive; it does not rescue a short or guessable passphrase.
4. **An uncompromised Windows** and no second person with administrator rights on
   the same machine. This follows from non-goals 1 and 2.

### The pepper promise, stated conditionally

An earlier version of the specification said that whoever obtains only the file
can "not guess offline at all". That is **not unconditionally true**, and the
corrected wording is binding everywhere, in the gates, in the interface and in
the documentation:

> The pepper makes an offline attack hopeless **as long as** the attacker has
> only the vault file, or the disk is encrypted with BitLocker.

The reasoning: the pepper sits DPAPI-protected in the credential store, which
means it sits **in the Windows profile on the same disk**. Whoever copies only
`tasks.db.enc` (the typical K1 case, a file carried off on a USB stick) does not
have the pepper and can do nothing offline. Whoever has the **whole disk** (a
stolen laptop, a removed SSD) and the disk is **not** encrypted can attack the
DPAPI master key offline, whose protection then rests on the Windows sign-in
password. If that falls, the pepper falls, and only the passphrase is left,
expensive through Argon2id but alone.

No "not at all" without that condition.

## Why the panic end screen does not lie

The panic end screen offers two exits: **Finish** (quits, all data stays) and
**Killswitch** (really deletes). Both the wipe screen and the end screen carry
honest labels: "Clearing workspace" and "Workspace cleared".

An earlier plan called for a deliberately false outward screen ("All data
securely wiped") on the Finish path, while the data actually remained. It was
**not** built, and the reasoning belongs here rather than in a UI description:

- **In favour of the lie:** against a casual observer (K3, partly K6) a
  "securely wiped" screen would have been a deterrent and would have ended the
  situation without data loss. The user could have shown the screen and still
  pressed the killswitch later.
- **Against it, and this is what decided the matter:** against an attacker who
  keeps the disk and examines it (K1 or K2 following K6), the claim is a
  **checkable lie**. If they then find the data anyway, the user stands there as
  someone who actively deceived, which can make their situation worse. The
  deterrent value is theatre against opportunistic access and does not outweigh
  that concrete risk. Anyone in a genuine coercion scenario presses the
  **killswitch** anyway, which is a real and irreversible deletion.
- **Consequence:** the end screen says what actually happened and nothing beyond
  it. The killswitch remains the second, deliberately chosen exit for the real
  emergency, and it is not hidden.

Honest security claims therefore apply throughout this project without a single
exception.

## Which hardening addresses which class

Every measure in the app names its opponent. A measure that cannot name one does
not get built, and a rejected proposal keeps its row so the reasoning is not lost.

| Measure | Class | What it prevents |
|:--|:--|:--|
| No development key anywhere in the code | K1, K2, K5 | "Encryption" that opens with a string from the repository |
| Pinned, hash-checked dependencies | K4 (upstream) | Supply chain: a swapped library is a total compromise |
| Navigation lockdown | K4 | Exfiltration through a forced external navigation |
| The lock as a backend allowlist | K3 | A single JavaScript call that walks around the lock screen |
| Wiping the WebView2 profile | K2 | Task text in the browser cache, past both encryption layers |
| HKDF, and no verification hash on disk | K1 | An offline oracle sitting on the disk |
| Container format, fresh nonce, atomic write | K1 | Nonce reuse, and data loss on a crash |
| Debounced write-back with a hard cap | robustness | No attacker: crash safety |
| The DPAPI pepper | K1 | Offline guessing **without** disk access (conditioned, see above) |
| Single-instance guard | robustness | No attacker: corruption from two instances |
| Input validation at the bridge | K4 (hardening) | Malformed or hostile input reaching the backend |
| Export hardening | correctness | Reserved filenames, broken export structure |
| Honest status reporting | user honesty | A security display that flatters. No exception, the panic end screen included. |
| Clipboard hygiene | K2, K4 | Windows clipboard history and cloud clipboard as an outbound channel |
| Zeroing keys in RAM | K2 | Keys in a memory image, best effort |
| ~~Screenshot protection~~ | **none** | Nothing. Rejected for exactly that reason: a measure without a class. |
| Binary and frontend integrity | K5, K4 (persistence) | Tampering with the executable or the assets, not secrecy |
| A standalone encryption proof | K1, K2 | The assumption that it is encrypted, without checking |
| Error hygiene, no logfile | K3, K5 | Internals and paths in error messages and log files |
| Pagefile, hibernation and dump awareness | K2 | RAM contents reaching the disk past every layer |
| Vault location warning for cloud folders | K1 (third parties) | Version history at the cloud provider |
| Deleting development-era data | K2 | An old database readable with a key that is public |
| Release hardening | K3, K4 | DevTools, the `Ctrl+P` print export, the context menu, text selection |
| One single lock and shutdown sequence | K3 | Gaps between lock, quit, panic and the window close button |
| **This document** | all | Measures without an opponent, and promises without a condition |
