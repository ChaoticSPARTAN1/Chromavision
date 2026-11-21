# Third-party notices

## Included in this repository

| Component | Files here | Licence | Licence text |
|---|---|---|---|
| Press Start 2P (CodeMan38) | `docs/fonts/heading-PressStart2P-Regular.ttf` | SIL OFL 1.1 | [LICENSES/OFL-1.1-PressStart2P.txt](LICENSES/OFL-1.1-PressStart2P.txt) |
| Silkscreen (The Silkscreen Project Authors) | `docs/fonts/body-Silkscreen-Regular.ttf` | SIL OFL 1.1 | [LICENSES/OFL-1.1-Silkscreen.txt](LICENSES/OFL-1.1-Silkscreen.txt) |

Everything else here is Chromavision's own (GPL-3.0-or-later with [ADDITIONAL-TERMS.md](ADDITIONAL-TERMS.md)).

## Data read at run time (not included)

| Source | Used by | Licence or terms |
|---|---|---|
| iptv-org: [iptv-org/iptv](https://github.com/iptv-org/iptv) and [iptv-org/api](https://github.com/iptv-org/api) (channels, feeds, streams, blocklist) | `tools/make_channel_list.py`, on your PC; `livetv_tuner.py trial` reads a small list you built with `make_channel_list.py` | [The Unlicense](https://github.com/iptv-org/iptv/blob/master/LICENSE). The list data is public domain; **the rights to each stream belong to its broadcaster**. iptv-org hosts no video. Pay-TV re-streams are never offered by the tools |
| US National Weather Service: `api.weather.gov` and its map server | the console's Local Weather channel (code in Jellymatic) | US Government work, public domain ([weather.gov/disclaimer](https://www.weather.gov/disclaimer)). Asked with a plain program name, nothing personal. Not for safety decisions |
| `pool.ntp.org` | the console's clock while Local Weather is on screen | Public time service |

## In Jellymatic's start-up menu (not included here)

The console side of Chromavision is built into Jellymatic's start-up menu, which carries these and their notices:

| Component | Licence |
|---|---|
| Local Weather announcer lines, made with [Piper](https://github.com/OHF-Voice/piper1-gpl) (GPL-3.0; the tool is not distributed, only the five short clips it spoke) and its voice `en_US-norman-medium` from [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) | The voice's model card lists it as public domain, trained from scratch on public-domain LibriVox recordings. The wording is the project's own |
| Music loop and alert tone | Written in code for the project (GPL-3.0-or-later, Jellymatic) |
| Place look-up table for the weather location (Chromatic Manager) | US Census Bureau 2024 Gazetteer files, US Government work, public domain |
| ESP-IDF, Mbed TLS, the root certificate bundle and the other firmware components | Apache-2.0, MPL-2.0 and others; see Jellymatic's THIRD-PARTY-NOTICES.md |

## Used through its public interface (not included)

| Component | Licence |
|---|---|
| Jellyfin server, its Live TV feature and its FFmpeg-based conversion | GPL-2.0 (server); the Jellyfin logo is CC BY-SA 4.0. Chromavision contains no Jellyfin code and does not show the Jellyfin logo |
| Python | PSF licence |
