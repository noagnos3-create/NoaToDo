# Contributing to NoaToDo

Thank you for your interest. Bug reports, questions and pull requests are all welcome.

## How to contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes and commit them with a clear message
4. Run the tests (`cd src` then `venv\Scripts\python.exe -m pytest`)
5. Push to your fork and open a pull request

## Guidelines

- Keep pull requests focused on a single change.
- Write clear commit messages.
- Test your changes before submitting, and say in the pull request what you actually ran.
- Follow the existing code style.
- Verify user interface changes by running the app. There is no automated test that can see a window.

## Three things that are specific to this project

### 1. Language

The code is commented in German, the user interface and the documentation are in English. That split is deliberate and it is not going to be reversed: the German comments carry the reasoning behind the security decisions, and a bulk translation would flatten exactly the part that has the value.

So:

- **User interface strings, documentation, issue titles and commit messages: English.**
- **Code comments and docstrings: German is the existing convention.** German is preferred for new comments, English is accepted. Nobody is turned away over this.
- Please do not open a pull request that translates existing comments in bulk.

Issues and discussions in German are fine too. English reaches more people, that is all.

### 2. Security-relevant code needs an issue first

Please open an issue before writing code that touches any of these:

- `src/backend/security.py` (key derivation, the vault session, the rate limit ladder, the teardown sequence)
- `src/backend/db.py` (schema, SQLCipher handling)
- the `.enc` container format or anything about how keys are derived, separated or zeroed
- the backend lock allowlist in `src/backend/api.py`
- the Content Security Policy in `src/frontend/index.html`

This is not gatekeeping, it is about wasted effort. These parts follow a written specification with reasoning attached, and a change that looks like an obvious improvement often collides with a decision that was made deliberately and argued at length. An issue costs you ten minutes and can save you a weekend.

The same applies in reverse: if you think one of those decisions is wrong, an issue is exactly the right place to say so. Several of them exist precisely because an earlier version was challenged.

### 3. There is a specification, and it is not in this repository

NoaToDo was built from a detailed German-language build plan (the "Bauplan") that defines the data model, the bridge contract between frontend and backend, the design tokens, the keyboard shortcuts, the threat model and a set of numbered security gates. It stays on the maintainer's machine and is not published.

What this means for you in practice:

- You do not need it to fix a bug or to improve the interface.
- Some comments in the code refer to it by label (`G13`, `N11.5`, `B.8.4`, `U3` and so on). Those are stable identifiers for decisions, not dead references. If one blocks your understanding, ask in the issue and it will be quoted.
- The essential parts have been extracted into English: [docs/architecture.md](docs/architecture.md) and [docs/threat-model.md](docs/threat-model.md). Start there.

## Things that will not be merged

Stated up front so nobody spends an evening on them:

- **Any form of network access.** No telemetry, no crash reporting, no update check, no font CDN, no analytics. The claim "this app makes no outbound connection" is verifiable today and is supposed to stay that way.
- **Notifications**, in-app or Windows toasts. The app has exactly one toast, for undoing a deleted list, and that is the whole budget.
- **Screenshot protection.** It existed, it broke rendering on some GPU and driver combinations, and it never defended against a phone camera. It is documented as removed and stays removed.
- **A weaker default**, such as an option to disable encryption, to store the passphrase, or to add a recovery backdoor.
- **Security claims that overstate what the code does.** If a change makes the app safer, say so precisely. If it only raises the bar, say that instead.

## Reporting security issues

Not here, and not as a public issue. See [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the **GNU General Public License, version 3 or any later version**, the same license as the rest of the project. See [LICENSE](LICENSE).

There is no contributor license agreement to sign and no copyright assignment. You keep the copyright on what you write.

If you add a new source file, give it the same header the existing files carry (the short GPL notice with the copyright line, as a comment above the module docstring, never inside it). The two font license files under `src/frontend/fonts/` are third-party texts and must stay exactly as they are.
