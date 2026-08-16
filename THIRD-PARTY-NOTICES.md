# Third-Party Notices

NoaToDo itself is licensed under GPL-3.0-or-later, see [LICENSE](LICENSE). The
components listed here are **not** NoaToDo, they are other people's work that the
app builds on and, in the case of the released executable, redistributes.

Why this file exists: when you run NoaToDo from source, `pip` installs every
dependency on your machine and each one arrives with its own license text next to
it. The single-file `NoaToDo.exe` is a different kind of delivery. It carries
compiled copies of all of them inside one binary, without their license files. The
only metadata folder that travels along belongs to `keyring`, and it is there
because `keyring` finds its backend through entry points, not because it settles
anything about licensing.

Almost every license below (MIT, BSD, Apache-2.0, zlib, PSF, OFL) permits that
bundling without asking for anything in return except one thing: the license text
and the copyright notice have to travel with the redistribution. This file is how
they travel. It is part of the repository and is published with every release, and
it belongs next to the `.exe` in the release assets.

## Python packages in the executable

Every package pinned in [`src/requirements.lock.txt`](src/requirements.lock.txt)
ends up in the binary. The license identifiers below are the ones each project
declares in its own package metadata for exactly the pinned version.

| Package | Version | License | Project |
|:--|:--|:--|:--|
| argon2-cffi | 25.1.0 | MIT | [hynek/argon2-cffi](https://github.com/hynek/argon2-cffi) |
| argon2-cffi-bindings | 25.1.0 | MIT | [hynek/argon2-cffi-bindings](https://github.com/hynek/argon2-cffi-bindings) |
| backports.tarfile | 1.2.0 | MIT | [jaraco/backports.tarfile](https://github.com/jaraco/backports.tarfile) |
| bottle | 0.13.4 | MIT | [bottlepy/bottle](https://github.com/bottlepy/bottle) |
| cffi | 2.0.0 | MIT | [python-cffi/cffi](https://github.com/python-cffi/cffi) |
| clr_loader | 0.3.1 | MIT | [pythonnet/clr-loader](https://github.com/pythonnet/clr-loader) |
| cryptography | 48.0.0 | Apache-2.0 OR BSD-3-Clause | [pyca/cryptography](https://github.com/pyca/cryptography) |
| importlib_metadata | 9.0.0 | Apache-2.0 | [python/importlib_metadata](https://github.com/python/importlib_metadata) |
| jaraco.classes | 3.4.0 | MIT | [jaraco/jaraco.classes](https://github.com/jaraco/jaraco.classes) |
| jaraco.context | 6.1.2 | MIT | [jaraco/jaraco.context](https://github.com/jaraco/jaraco.context) |
| jaraco.functools | 4.5.0 | MIT | [jaraco/jaraco.functools](https://github.com/jaraco/jaraco.functools) |
| keyring | 25.7.0 | MIT | [jaraco/keyring](https://github.com/jaraco/keyring) |
| more-itertools | 11.1.0 | MIT | [more-itertools/more-itertools](https://github.com/more-itertools/more-itertools) |
| proxy_tools | 0.1.0 | MIT | [jtushman/proxy_tools](https://github.com/jtushman/proxy_tools) |
| pycparser | 3.0 | BSD-3-Clause | [eliben/pycparser](https://github.com/eliben/pycparser) |
| pythonnet | 3.1.0 | MIT | [pythonnet/pythonnet](https://github.com/pythonnet/pythonnet) |
| pywebview | 5.3.2 | BSD-3-Clause | [r0x0r/pywebview](https://github.com/r0x0r/pywebview) |
| pywin32-ctypes | 0.2.3 | BSD-3-Clause | [enthought/pywin32-ctypes](https://github.com/enthought/pywin32-ctypes) |
| sqlcipher3-wheels | 0.5.7 | zlib | [laggykiller/sqlcipher3](https://github.com/laggykiller/sqlcipher3) |
| typing_extensions | 4.15.0 | PSF-2.0 | [python/typing_extensions](https://github.com/python/typing_extensions) |
| winrt-runtime | 3.2.1 | MIT | [pywinrt/pywinrt](https://github.com/pywinrt/pywinrt) |
| winrt-Windows.Devices.Enumeration | 3.2.1 | MIT | [pywinrt/pywinrt](https://github.com/pywinrt/pywinrt) |
| winrt-Windows.Devices.Radios | 3.2.1 | MIT | [pywinrt/pywinrt](https://github.com/pywinrt/pywinrt) |
| winrt-Windows.Foundation | 3.2.1 | MIT | [pywinrt/pywinrt](https://github.com/pywinrt/pywinrt) |
| winrt-Windows.Foundation.Collections | 3.2.1 | MIT | [pywinrt/pywinrt](https://github.com/pywinrt/pywinrt) |
| zipp | 4.1.0 | MIT | [jaraco/zipp](https://github.com/jaraco/zipp) |

The full license text of each package sits in its own distribution. After
installing the dependencies you can read every one of them locally:

```
src\venv\Lib\site-packages\*.dist-info\licenses\
```

`sqlcipher3-wheels` carries the license of the `pysqlite3` code it forked:
Copyright (c) 2004 to 2007 Gerhard Häring, under the zlib/libpng license.

## Native code inside those packages

Three of the packages above are not pure Python. They contain compiled libraries
that are written by other projects again, and those end up in the executable too.

| Component | Where it comes from | License |
|:--|:--|:--|
| **SQLCipher** (the AES-256 layer of the vault) | statically linked into the `sqlcipher3` extension module | BSD-3-Clause, Copyright (c) ZETETIC LLC |
| **SQLite** (SQLCipher is a fork of it) | same extension module | Public domain |
| **OpenSSL** (`libcrypto`, the cipher primitives under SQLCipher) | statically linked into the `sqlcipher3` extension module, built through Conan by the wheel project | Apache-2.0 |
| **OpenSSL** (the primitives under `cryptography`) | statically linked into the `cryptography` Rust binding | Apache-2.0 |
| **phc-winner-argon2** (the Argon2 reference implementation) | compiled into `argon2-cffi-bindings` | CC0-1.0 OR Apache-2.0 |
| **ClrLoader.dll** (starts the .NET runtime for `pythonnet`) | shipped inside `clr_loader` | MIT, Copyright (c) 2019 to 2026 Benedikt Reinartz |

This is worth stating plainly rather than hiding in a table: **the two encryption
layers of this app are other people's cryptography.** NoaToDo chooses the
parameters, derives the keys and holds the format together, but the ciphers
themselves are SQLCipher, OpenSSL and the Argon2 reference implementation. That is
the intended arrangement. An app that shipped its own AES would be a worse app.

## The Python runtime and the PyInstaller bootloader

The executable is built with PyInstaller in one-file mode, which means it also
contains a complete Python:

- **CPython 3.11.9** with the parts of its standard library that the app imports,
  under the [Python Software Foundation License Version 2](https://docs.python.org/3/license.html).
  The version is pinned, see the header of `src/requirements.lock.hashes.txt`.
- **The PyInstaller bootloader**, the small program that unpacks and starts the
  bundle. PyInstaller is GPL-2.0-or-later **with the bootloader exception**, which
  explicitly allows the bootloader to be shipped inside binaries under any license.
  NoaToDo is GPL-3.0-or-later, so this would be fine even without the exception.

PyInstaller itself is a build tool and is not otherwise part of the binary. The
spec file excludes it, along with `pytest` and `PIL`.

## Fonts

Both typefaces are bundled as local `.woff2` files, in the repository and inside
the executable, because the app makes no network requests and therefore cannot
fetch a font from a CDN.

| Font | Copyright | License |
|:--|:--|:--|
| [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) | Copyright 2020 The JetBrains Mono Project Authors | SIL Open Font License 1.1, [full text](src/frontend/fonts/OFL-JetBrainsMono.txt) |
| [Space Grotesk](https://github.com/floriankarsten/space-grotesk) | Copyright 2020 The Space Grotesk Project Authors | SIL Open Font License 1.1, [full text](src/frontend/fonts/OFL-SpaceGrotesk.txt) |

The files are unmodified language subsets. Which file belongs to which family is
recorded in [`src/frontend/fonts/README.md`](src/frontend/fonts/README.md), because
the delivered filenames do not say so.

## Components that are used but not redistributed

These are Microsoft components that the app talks to on your machine. NoaToDo does
not ship them and does not license them to you.

- **Microsoft Edge WebView2 runtime.** The app renders its interface in it and
  assumes it is present, which it is on current Windows installations. It is
  covered by Microsoft's own terms.
- **The .NET runtime**, reached through `pythonnet` for the native lock window and
  the app-themed message dialogs.
- **The Windows APIs** behind the radio control, the Credential Manager and the
  BitLocker status query.

## Development tools

Not in the executable, listed for completeness because they are pinned in
[`src/requirements-dev.txt`](src/requirements-dev.txt): `pytest` (MIT),
`pyinstaller` (GPL-2.0-or-later with the bootloader exception, see above) and
`pillow` (MIT-CMU), the last of which only generates the application icon from the
logo.

## Keeping this file honest

A notices file that drifts from the lock file is worse than none, because it
claims a completeness it no longer has. So: **whoever changes a version or adds a
dependency in `src/requirements.lock.txt` updates this file in the same commit.**
The check is a comparison of two lists, and the pinned-package table above is
meant to be read against the lock file line by line.

If you want to verify the licenses yourself rather than trust this table, install
the dependencies and read the metadata that came with them:

```
src\venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock.hashes.txt
src\venv\Scripts\python.exe -c "from importlib.metadata import distributions; [print(d.metadata['Name'], d.version, d.metadata['License-Expression'] or d.metadata['License']) for d in sorted(distributions(), key=lambda d: d.metadata['Name'].lower())]"
```
