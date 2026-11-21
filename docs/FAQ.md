<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# FAQ

[Home](Home.md) › FAQ

**Is this made by ModRetro, Analogue, Jellyfin, iptv-org or the National Weather Service?** No. Chromavision is an independent
project, not affiliated with any of them.

**Does it cost anything?** No. It is free software (GPL-3.0-or-later), and it needs no account, key or subscription.

**Do I need a Jellyfin server?** Not for Local Weather. For live channels, yes: the console cannot decode the
channels' own video, so your server converts the one you watch.

**Do I need the PC while I watch?** No. The PC is for setting things up and undoing them.

**Does it change my Jellyfin server?** Only if you add the Live TV tuner: one tuner, nothing else, with a backup, a
dry run and proof afterwards ([Server safety](Server-safety.md)). It never signs out your other devices.

**Is it legal?** Chromavision lists only free channels that their broadcasters offer to the public, never pay-TV
re-streams, and records nothing. The streams belong to their broadcasters, and some platforms' terms limit their
free channels to their own apps: that choice (`--allow-redirects`) is yours. The weather data is public domain.

**Why does a channel say "No signal"?** Free channels come and go, and some run only part of the day. Build your
list again now and then.

**Does TV write to my watch history?** No. Channels send no playback reports.

**Can I use it outside the US?** Local Weather: no, it uses the US National Weather Service. Live TV: the list
builder takes `--country` and `--language`, but only US channels in English were tried.

**Does it work on the Analogue Pocket?** Not in this version: TV and Local Weather are on the Chromatic only. The
Pocket link still works as before from the Jellyfin row.

**Why is the picture small and soft?** The console's screen is 160 × 144; channels arrive at up to 160 × 120 and
about 400 kbit/s, which is what its Wi-Fi and decoder manage.

**Is the weather accurate?** It is the National Weather Service's own data, but shown for fun, refreshed only while
the channel is on screen, and shortened to fit: never use it for safety decisions.

**Who made the music and the voice?** The music and alert tone are written in code for this project. The announcer
lines were made with Piper's "Norman" voice, trained only on public-domain recordings
([Credits & licences](Credits-and-licences.md)).

Next: [Building and testing](Building-and-testing.md)
