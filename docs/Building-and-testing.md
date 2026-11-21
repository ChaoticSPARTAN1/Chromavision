<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Building and testing

[Home](Home.md) › Building and testing

**Contents:** [Where the code is](#where-the-code-is) · [Tests](#tests) · [Documentation](#documentation) ·
[Rules for changes](#rules-for-changes)

## Where the code is

| What | Where |
|---|---|
| PC tools | `tools/` here: `make_channel_list.py`, `livetv_tuner.py`, and `jellyfin_admin.py`, the small careful Jellyfin client they share with ChromaTube's tools |
| The TV row, the channel list and tuning on the console | Jellymatic: `chromatic/jellyfin/` (the Jellyfin app in its TV mode) and `chromatic/launcher/` |
| The Local Weather channel (pages, data reader, radar decoder, sound, location record) | Jellymatic: `chromatic/weather/` and `chromatic/launcher/main/` |
| The weather location setting, location packs and the Apps switches | Jellymatic: Chromatic Manager (`scripts/`); by hand, `scripts/make_location_pack.py` makes a `.pjlp` location pack |
| The TV icons | `art/` here (original pixel art; Jellymatic carries the same pixels in its launcher) |

The console code lives in [Jellymatic](https://github.com/ChaoticSPARTAN1/Jellymatic) because there is one start-up
menu image to build, install and review. Build it from there (Jellymatic's "Building from source").

## Tests

Standard library only; no device, no internet (the fake Jellyfin server listens on 127.0.0.1):

```
py -3 tools\tests\test_livetv_tuner.py
py -3 tools\tests\test_make_channel_list.py
py -3 tools\tests\test_private_files.py
py -3 scripts\test_docs_html.py
```

`test_livetv_tuner.py` runs every command against a fake server that already holds someone else's tuner, guide
source, libraries, users and sessions, with failures injected (add refused, delete fails, no channels, wrong stream
format). It checks that only allow-listed requests are sent, nothing else is touched, nothing private is printed and
only the run's own session is ever signed out. `test_make_channel_list.py` checks every list rule on made-up data,
that no line can be injected from third-party names or addresses, and that a list is never written inside the
repository. `test_private_files.py` checks that backups are user-only on macOS/Linux.

## Documentation

After editing any page: `py -3 scripts\build_docs_html.py` (writes `Open-Documentation.html` and `docs/index.html`
for GitHub Pages), then `py -3 scripts\build_docs_pdf.py` (the PDF guide; needs Chrome or Edge), then
`py -3 scripts\test_docs_html.py`. GitHub Pages: Settings › Pages, branch `main`, folder `/docs`.

## Rules for changes

- Keep the server rules of [Server safety](Server-safety.md): add-only, backup, dry run, proof, allow-listed
  requests, nothing private printed, never sign out another session.
- No channel lists, stream addresses, logos, recordings or anything personal in the repository.
- Plain words in anything a user reads.

Next: [Credits & licences](Credits-and-licences.md)
