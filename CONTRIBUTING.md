<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Contributing to Chromavision

Pull requests, bug fixes and bug reports are welcome. This is a hobby project: there is no guarantee of a response
or a fix, but every report is read when time allows.

## Reporting a bug

Open an issue with what you did, what you expected and what happened; the start-up menu version (its credits screen
or Chromatic Manager), the Jellyfin server version, and the tool's PASS/FAIL lines (they hold no private details).
Never post server addresses, tokens, your channel list or your weather location. Security problems:
[SECURITY.md](SECURITY.md). Problems with the console's TV row or Local Weather screens belong to
[Jellymatic](https://github.com/ChaoticSPARTAN1/Jellymatic).

## Pull requests

- Keep the server rules ([docs/Server-safety.md](docs/Server-safety.md)): add-only, backup, dry run, proof,
  allow-listed requests, nothing private printed, never sign out another session or device.
- Never add channel lists, stream addresses, logos or recordings to the repository.
- Run the tests (`tools/tests/`, `scripts/test_docs_html.py`) and say which ones you ran. Tests must never contact a
  real server or device.
- After editing any documentation page, run `py -3 scripts\build_docs_html.py` and `py -3 scripts\build_docs_pdf.py`;
  `scripts\test_docs_html.py` checks the results.
- Plain words in anything a user reads.
- By contributing you agree that your contribution is licensed under GPL-3.0-or-later with the additional terms in
  [ADDITIONAL-TERMS.md](ADDITIONAL-TERMS.md).
