# Bundled fonts

These files are **third-party software** and are not covered by NoaToDo's GPL
license. Both typefaces are licensed under the **SIL Open Font License,
version 1.1**, whose full text ships next to them in this folder, including each
project's own copyright line as required.

| Font | Copyright | License text |
|:--|:--|:--|
| [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) | Copyright 2020 The JetBrains Mono Project Authors | [OFL-JetBrainsMono.txt](OFL-JetBrainsMono.txt) |
| [Space Grotesk](https://github.com/floriankarsten/space-grotesk) | Copyright 2020 The Space Grotesk Project Authors | [OFL-SpaceGrotesk.txt](OFL-SpaceGrotesk.txt) |

## Which file is which

The `.woff2` files carry the opaque names they were delivered with. They are
unmodified language subsets, so the mapping is not guessable from the filename
and is recorded here instead. It is derived from the 36 `@font-face` blocks in
`../style.css`, which remain the authoritative source.

| File | Family |
|:--|:--|
| `1597fbbb-d254-4f3c-957c-27988c22b911.woff2` | JetBrains Mono |
| `34178017-bdf9-4b07-b1cd-5abbbaaee8ef.woff2` | JetBrains Mono |
| `672604d8-2bb2-47e7-8259-515881a69869.woff2` | JetBrains Mono |
| `8d777a0a-8a6a-4e16-a22b-973d6c1f552f.woff2` | JetBrains Mono |
| `9393c2fb-e5c4-4349-95a4-ca44f32ca4cb.woff2` | JetBrains Mono |
| `c379cb29-6d43-4d54-b3ef-fcfb3a83246a.woff2` | JetBrains Mono |
| `b923439a-9b7c-4bc1-ae51-27b1f66d181f.woff2` | Space Grotesk |
| `dabb4d03-8efe-4c63-b22e-f79ee5d7212b.woff2` | Space Grotesk |
| `ed3d7172-4317-48b3-8c7d-2b08617ea4a3.woff2` | Space Grotesk |

## Why they are here at all

NoaToDo loads no font from a network location, because it makes no network
requests at all. Bundling the files locally is what makes that claim true rather
than aspirational. The same reasoning applies to the completion sound, which is
synthesised at runtime instead of shipped as an audio file.

## If you change anything here

The OFL permits redistribution and bundling, including inside the compiled
executable, on one condition that is easy to break by accident: the license text
and the copyright notice must travel with the fonts. Do not delete the two
`OFL-*.txt` files, and do not replace them with NoaToDo's own license.

Renaming or subsetting the files is allowed, but then update `../style.css` and
this table in the same change. The build hashes every file in this folder into
the integrity manifest, so a rename that misses the CSS turns into a startup
failure rather than a silent one.
