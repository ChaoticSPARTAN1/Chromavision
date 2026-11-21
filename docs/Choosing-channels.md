<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Choosing channels

[Home](Home.md) › Choosing channels

**Contents:** [Where the channels come from](#where-the-channels-come-from) · [The rules](#the-rules) ·
[Options](#options) · [Examples](#examples) · [Whose channels are these?](#whose-channels-are-these)

## Where the channels come from

[iptv-org](https://github.com/iptv-org/iptv) keeps a public, community-made index of free TV streams, with an open
data set ([iptv-org/api](https://github.com/iptv-org/api)): channels, their feeds and languages, stream addresses,
labels such as "Geo-blocked", and a blocklist of channels removed after a rights claim. iptv-org hosts no video.

`tools/make_channel_list.py` reads that data and writes **your own** list. Lists are personal: the tool writes
into your private folder and refuses to write inside this repository, and no list is ever published here.

## The rules

Every channel in your list passed all of these:

| Rule | Why |
|---|---|
| In the **groups** you chose (iptv-org categories such as `weather`, `animation`, `classic`, `news`) and **countries** (default: US) | You decide what you get |
| Not closed, not marked adult, not on iptv-org's **blocklist** | Removed channels and rights claims stay out |
| The feed's **language** is the one you chose (default: English); no language data means left out | A channel with another language mixed into its only sound track is no fun on a handheld |
| Not labelled **Geo-blocked** | It would not play at your home anyway |
| Not labelled **Not 24/7** (unless `--keep-not-24-7`) | Fewer "No signal" screens |
| Not served from a **bare IP address** | A common sign of a re-stream |
| A plain web address with no spaces, line breaks or control characters | Third-party data cannot add lines to your list; names and headers are cleaned the same way |
| Not a **pay-TV brand** (cable and premium networks) | Their entries in public lists are re-streams by third parties: **never offered**, even if asked for by name |
| Not reached through a **third-party redirect** (unless `--allow-redirects`) | The address belongs to someone in between, not the broadcaster; whether you may watch such platform channels outside the platform's own apps is your call |
| Your own `--exclude` and `--include` patterns | Fine-tuning |

When a channel has several copies, the **smallest picture** is kept: the console shows at most 160 × 120, so your
server has less to convert.

## Options

| Option | Does |
|---|---|
| `--list-groups` | Prints the groups and how many channels each would give with your other options |
| `--group NAME` (repeat) / `--all-groups` | What to take (adult groups are never taken) |
| `--country XX` (repeat) | Two-letter country codes; default `US` |
| `--language xxx` | Three-letter language code; default `eng` |
| `--keep-not-24-7`, `--allow-redirects` | Relax those two rules |
| `--include PATTERN`, `--exclude PATTERN` (repeat) | Keep only / leave out names matching a pattern (not case-sensitive) |
| `--pick` | Shows the numbered list and asks which to keep (`1-5,8,12`) |
| `--max N` | Keep at most N channels |
| `--show` | Prints the kept names |
| `--out FILE` | Write somewhere else (never inside the repository) |
| `--source DIR` | Read the four iptv-org data files from a folder instead of the internet |

The tool prints counts of what was kept and why the rest was left out; it never prints stream addresses.

## Examples

```
py -3 tools\make_channel_list.py --group weather --group animation --show
py -3 tools\make_channel_list.py --group classic --group comedy --exclude "late night" --pick
py -3 tools\make_channel_list.py --group news --max 10
```

## Whose channels are these?

Each stream belongs to its broadcaster. The list data is public domain (The Unlicense), but that says nothing about
the rights to each stream. Chromavision lists only free channels offered to the public, leaves pay-TV re-streams out
on purpose, keeps the adverts in, and records nothing. Links break often (some channels are gone the next day): build
the list again now and then.

Next: [Using TV](Using-TV.md)
