## Description

<!-- What does this PR change and why? -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation

## Testing

<!-- What did you actually run? "cd src && venv\Scripts\python.exe -m pytest"
     covers the logic. If this changes anything visible, please also say that you
     started the app and looked at it: no automated test can see a window. -->

- [ ] `pytest` passes (63 tests)
- [ ] I started the app and checked the change in the running window
- [ ] Not applicable

## Checklist

- [ ] My code follows the existing style
- [ ] Any value that reaches `innerHTML` goes through `esc()`
- [ ] Native window changes are dispatched to the WinForms UI thread
- [ ] This PR does not add a network call, a notification, or a new toast
- [ ] Security claims in the code, the UI or the docs match what the code does
- [ ] New source files carry the GPL header, as a comment above the docstring
- [ ] I agree to license my contribution under the GNU GPL v3 or later

<!-- Touching security.py, db.py, the .enc format, the lock allowlist or the CSP?
     Please open an issue first, see CONTRIBUTING.md. Found a vulnerability?
     Do not open a PR, see SECURITY.md. -->
