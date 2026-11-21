<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Credits & licences

[Home](Home.md) › Credits & licences

**Contents:** [Author](#author) · [This project's licence](#this-projects-licence) · [Data and sound](#data-and-sound) ·
[Included here](#included-here) · [Used, not included](#used-not-included) · [Trademarks](#trademarks)

## Author

Created by **ChaoticSPARTAN1**. Under GPLv3 section 7(b), redistributions and modified versions must keep this
attribution in the README credits and in any About or credits screen ([ADDITIONAL-TERMS.md](../ADDITIONAL-TERMS.md)).

## This project's licence

**GPL-3.0-or-later** ([LICENSE](../LICENSE)) for everything written for Chromavision: the PC tools, the docs, the
build scripts and the icons. [ADDITIONAL-TERMS.md](../ADDITIONAL-TERMS.md) adds the attribution term (7(b)) and the
marking of modified versions (7(c)), as in Jellymatic. The console code is part of Jellymatic, under Jellymatic's
licence and additional terms.

## Data and sound

| What | From | Licence or terms |
|---|---|---|
| Weather observations, forecasts, alerts, radar pictures | US National Weather Service (`api.weather.gov`, its map server) | US Government work, public domain. Not for safety decisions. Fetched by the console; nothing is stored here |
| Place look-up table used by Chromatic Manager | US Census Bureau, 2024 Gazetteer files (ZIP Code Tabulation Areas and places) | US Government work, public domain. Bundled with Jellymatic, not here |
| Channel data (channels, feeds, streams, blocklist) | [iptv-org](https://github.com/iptv-org) (`iptv-org/iptv`, `iptv-org/api`) | The Unlicense. Read at run time by `make_channel_list.py`; nothing of it is stored here. **Each stream belongs to its broadcaster**; pay-TV re-streams are left out on purpose |
| Announcer lines of Local Weather | Made with Piper (`OHF-Voice/piper1-gpl`) and its voice `en_US-norman-medium` (rhasspy/piper-voices) | Piper is GPL-3.0 and is not included. The Norman voice is listed as public domain, trained from scratch on public-domain LibriVox recordings. The wording is the project's own. The clips are in Jellymatic's start-up menu |
| Music loop and alert tone | Written in code for this project | Part of Jellymatic (GPL-3.0-or-later) |
| Retro look | Original art, colours and fonts of this project | No third-party weather-channel name, logo, artwork, music or data is used |

## Included here

| Part | Where | Licence |
|---|---|---|
| Press Start 2P font (CodeMan38) | `docs/fonts/` | SIL OFL 1.1, [LICENSES/OFL-1.1-PressStart2P.txt](../LICENSES/OFL-1.1-PressStart2P.txt) |
| Silkscreen font (The Silkscreen Project Authors) | `docs/fonts/` | SIL OFL 1.1, [LICENSES/OFL-1.1-Silkscreen.txt](../LICENSES/OFL-1.1-Silkscreen.txt) |

## Used, not included

| Tool | Licence |
|---|---|
| Jellyfin server (its Live TV and FFmpeg-based conversion) | GPL-2.0; the Jellyfin logo is CC BY-SA 4.0. Used through its public web API; no Jellyfin code is here |
| Python | PSF licence |
| Jellymatic (the start-up menu and Chromatic Manager) | GPL-3.0-or-later with its additional terms |

## Trademarks

ModRetro and Chromatic are trademarks of ModRetro, Inc. Analogue and Pocket are trademarks of Analogue. Jellyfin
is a trademark of its owners. Channel names and logos belong to their owners. They are used only to say what Chromavision works with. Chromavision is an
independent project, not affiliated with, endorsed or supported by any of them, by iptv-org or by the US National
Weather Service.
