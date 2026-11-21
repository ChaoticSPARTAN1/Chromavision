<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Server safety

[Home](Home.md) › Server safety

**Contents:** [The rules](#the-rules) · [Keep Jellyfin private](#keep-jellyfin-private) ·
[Sign-ins](#sign-ins) · [Exactly what can be sent](#exactly-what-can-be-sent) · [Side effects](#side-effects)

## The rules

| Rule | How the tools keep it |
|---|---|
| **Add-only** | One tuner, nothing else. No library, user, device, plugin, scheduled task, guide source or conversion setting is ever written. |
| **Backup first** | Before any change: the whole Live TV configuration and a fingerprint of libraries, users, devices, plugins, task triggers and conversion settings are saved in your private folder. The backups can hold tuner addresses and a guide provider's sign-in (for example a listings service user and password hash), so they are written readable by you only (folder 0700, files 0600 on macOS/Linux; `%LOCALAPPDATA%` is per-user on Windows). Never share them. |
| **Dry run first** | `add` and `remove` without `--yes` only read, then show exactly what would be sent. |
| **Proof after** | After `add`: exactly one new tuner and every other Live TV setting identical; the fingerprint unchanged. After `remove`: the Live TV configuration equal to the backup. Anything else is a **FAIL** with the manual undo. |
| **Tagged** | The tuner is named "Chromavision Live TV (added by Chromavision tools)" (Chromatic Manager uses the same name; its older "Chromatic TV (added by Chromatic Manager)" counts too, so a tuner is never added twice); its id is recorded, and `remove` deletes only that id, from this tool's record or Chromatic Manager's. |
| **Cannot overload the server** | The tuner's stream limit is 1 (or 2): a further channel is refused by the server instead of starting another conversion. The console asks for at most 400 kbit/s, 160 × 120, 15 pictures a second, one stream. |
| **Cleans up** | The console closes every channel it opened (stop conversion, then close the live stream). Jellyfin itself ends a conversion about 10 seconds after its viewer has gone. |
| **No plugins, no restarts** | Live TV is built into Jellyfin; adding a tuner takes effect at once. |
| **Nothing private printed** | The tools print PASS / FAIL / INFO and counts: never an address, path, name, token or id. |

## Keep Jellyfin private

- **Do not expose Jellyfin to the internet** for Chromavision: no port forward on your router, no public reverse
  proxy. The console and the PC tools need it on your home network only.
- Allow Jellyfin's port (8096) on the server's firewall for your **private** network only.
- Keep the server up to date with Jellyfin's own releases.

## Sign-ins

- **The console uses a normal user**, not an administrator, with Live TV allowed, signed in with Quick Connect (its
  own revocable sign-in; your password never goes to the console).
- **The administrator is used only on the PC, only for set-up**: `--ask-admin` asks for the name and password, keeps
  them in memory for that one run, signs in as a new device made for that run (so no other device's sign-in can be
  replaced) and signs that one session out at the end. Nothing is saved.
- **Your other devices and sessions are never signed out.** The tools never use "sign out everywhere", device
  deletion or API-key calls.

## Exactly what can be sent

Every request that could change something is checked against a short allow-list before it is sent; anything else is
refused unsent:

| Command | Changing requests it may send |
|---|---|
| `check`, `status` | none (read-only) |
| `add --yes` | `POST /LiveTv/TunerHosts`, only for a tuner with Chromavision's name |
| `remove --yes` | `DELETE /LiveTv/TunerHosts?id=`, only the recorded id |
| `refresh-guide --yes` | `POST /ScheduledTasks/Running/{id}`, only Jellyfin's own Refresh Guide task |
| `trial --yes` | add and delete its own test tuner (reading a list you built with the same rules as the main list); open, stop and close one of its test channels |
| any, with `--ask-admin` | its own sign-in, and the sign-out of that one session |

The tests in `tools/tests/` run every command against a fake server that holds someone else's tuner, libraries,
users and sessions, and check that nothing else is ever sent or printed.

## Side effects

- While the tuner is there, its channels show under **Live TV** in your other Jellyfin apps too, for users allowed
  Live TV.
- After the tuner is added (and after `refresh-guide`), Jellyfin refreshes its channel list once in the background.
- Each watched channel is one conversion on the server and one stream from the internet.
- Jellyfin's activity log keeps its own lines about these changes.

Next: [Undo everything](Undo-everything.md)
