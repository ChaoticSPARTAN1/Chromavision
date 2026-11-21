<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# What you need

[Home](Home.md) › What you need

**Contents:** [For Local Weather](#for-local-weather) · [For Live TV](#for-live-tv) · [Not needed](#not-needed)

## For Local Weather

| You need | Why | Notes |
|---|---|---|
| A **ModRetro Chromatic** with Jellymatic's start-up menu **1.6.5 or newer** | The TV row is part of it | Install and update with Chromatic Manager: [Jellymatic guide](https://chaoticspartan1.github.io/Jellymatic/). |
| The console's **Wi-Fi** set up, with internet access | The weather comes from the US National Weather Service over HTTPS | 2.4 GHz; set up on the console (Jellyfin › Select) or from Chromatic Manager. |
| A place in the **United States** | The data is the US National Weather Service's | Until you choose one the channel shows Orlando, FL. Choose yours in Chromatic Manager: **Settings › Weather location** ([Local Weather](Local-Weather.md)). |
| For sound: Jellymatic's console chip image **18.40 or 18.41** | The console plays sound through it | Without it the channel is silent. |

## For Live TV

| You need | Why | Notes |
|---|---|---|
| A **Jellyfin server 10.9 or newer** on your **home network** | It turns each channel into the small picture and sound the Chromatic plays | Keep it off the internet ([Server safety](Server-safety.md)). |
| Video conversion working on that server | Every watched channel is converted on the fly | Dashboard › Playback › Transcoding; the default settings are fine. |
| A **normal Jellyfin user for the console**, not an administrator, with **Allow Live TV access** on | The console signs in as this user | Dashboard › Users › that user › Live TV access. Approve the console's Quick Connect code while signed in as this user. |
| An **administrator** name and password, **typed once on the PC** | Only an administrator may add a tuner | Chromatic Manager and the tools ask for it for one job, keep it in memory only and sign that job's session out at the end. |
| A **PC** on the same network with **Python 3.10 or newer** | Runs the tools in `tools/` | Standard library only: nothing to install with pip. Windows, macOS or Linux. |
| A place the **server can read** your channel list file | The tuner reads the list from a file | For example Jellyfin's own configuration folder ([Live TV set-up](Live-TV-setup.md#4-put-the-list-where-the-server-can-read-it)). |
| Internet access on the server | The channels are streamed from their broadcasters | Each watched channel is one stream from the internet to your server. |

## Not needed

- No account anywhere, no API key, no paid service, no plugin and no server restart.
- No PC running while you watch: after set-up the console talks to your Jellyfin server directly.
- No channel list from anyone else: you build your own from public data, and it stays on your machines.

Next: [Local Weather](Local-Weather.md)
