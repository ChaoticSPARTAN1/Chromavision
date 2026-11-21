<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Troubleshooting

[Home](Home.md) › Troubleshooting

**Contents:** [Local Weather](#local-weather) · [Live TV on the console](#live-tv-on-the-console) · [The PC tools](#the-pc-tools)

## Local Weather

| Problem | Try |
|---|---|
| **Wi-Fi isn't set up yet** | Local Weather needs Wi-Fi: press **Select** to add your network on the console, or use Chromatic Manager |
| Pages show `--` and **UPDATING** for a long time | The console needs internet access through your Wi-Fi. Wait a minute; leave and open the channel again |
| The clock shows `--:--` | The time service did not answer yet; it is set from the first weather reply too |
| The wrong place | Chromatic Manager › Settings › Weather location; an older start-up menu (before 1.6.3) ignores your place |
| No radar or map pages | They come from the built-in Orlando area or a location pack: make your place's area pages (Settings › Weather location › Make the area pages); without one the Rain Outlook page takes their place |
| An imported pack is not used | It is for another place, or damaged: the console checks every pack and then shows the place without the map and radar pages. Make the pages again |
| No sound | Sound needs Jellymatic's console chip image 18.40 or 18.41 |
| The TV row is missing | It is hidden: Other firmware › Show hidden apps, or Chromatic Manager › Settings › Apps; or the start-up menu is older than 1.6 |
| TV opens the weather but no channel list | That is "Local Weather only": choose "Local Weather and your Jellyfin server's Live TV channels" in Settings › Apps |

## Live TV on the console

| Problem | Try |
|---|---|
| **No Live TV channels yet** | The server has no channels for this user: add the tuner (Settings › Live TV channels, or [Live TV set-up](Live-TV-setup.md)) and allow Live TV for the console's user |
| Only the weather row, "Try again" and a reason | The server is off or unreachable, or Live TV failed: press **Select** to find the server or sign in again |
| No channels under the weather row | Is the tuner there (`livetv_tuner.py status`)? Run `refresh-guide --yes`. Does the console's user have **Allow Live TV access**? |
| **No signal** on many channels | Free channels come and go. Build your list again; try `livetv_tuner.py trial --yes` to see that your server converts live channels at all |
| **No signal** after a few seconds every time | The stream limit is reached (another screen is watching a channel from this tuner), or the server cannot convert: check Dashboard › Playback › Transcoding and the server's log |
| **The server did not answer** | Live channels can take a while to open on a slow server; try again; check the server's load |
| Pictures stop but sound goes on | Some channels do this; after 20 seconds the console says No signal and returns to the list |
| A channel with the wrong language | Leave it out with `--exclude` and build the list again |

## The PC tools

| Message | Means |
|---|---|
| `FAIL no saved Jellyfin settings found` | Use `--ask-admin`, or save `jellyfin-connection.txt` (see `jellyfin-connection.example.txt`) |
| `FAIL the Jellyfin sign-in was not accepted` | Wrong name or password, or the account is disabled. Nothing was changed |
| `Live TV settings not readable` | The sign-in is not an administrator: use `--ask-admin` with an administrator |
| `the server does not list the channel list file at that path` | The path is the one your PC sees, not the server's, or the folder is not mounted into the Jellyfin container ([Live TV set-up](Live-TV-setup.md#4-put-the-list-where-the-server-can-read-it)) |
| `the Chromavision tuner is already there` | Remove it first (`remove --yes`) if you want to change its stream limit; to change channels just replace the file |
| `FAIL ... settings differ` | Something else changed the Live TV settings meanwhile. The line says what to check; the backup is in your private folder |
| `FAIL the list would be written inside the repository folder` | Choose a folder outside the repository (lists stay out of Git) |

Next: [FAQ](FAQ.md)
