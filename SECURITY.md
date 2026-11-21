<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Security

## Reporting a vulnerability

Please report security problems **privately**, not in a public issue: use GitHub's **Security › Report a
vulnerability** (private vulnerability reporting) on this repository. Describe the problem, how to reproduce it and
what it affects (the PC tools, the Jellyfin server, the console). There is no guarantee of a response time; reports are
handled as time allows. Problems in the console code belong to [Jellymatic](https://github.com/ChaoticSPARTAN1/Jellymatic).

## Never post publicly

- Jellyfin server addresses, user names, user IDs, tokens, device IDs, Quick Connect codes
- Your channel list, server paths, your weather location or ZIP code
- The files in your private folder (`%LOCALAPPDATA%\Chromavision`): backups, the tuner record, your list
- Logs or screenshots that show any of the above

## What Chromavision does to protect you

- The tools print counts and PASS/FAIL lines only, never addresses, paths, names, tokens or ids.
- An administrator sign-in is typed for one run (`--ask-admin`), kept in memory, never saved, and that run's own
  session is signed out at the end. No other session or device is ever signed out.
- Every request that could change the server is checked against a short allow-list before it is sent.
- No redirect is followed and no proxy is taken from the environment, so a token only ever goes to your server.
- Channel lists are written outside the repository; `.gitignore` keeps `*.m3u` and private files out of Git.
- Keep Jellyfin on your home network: Chromavision never needs it to be reachable from the internet.
