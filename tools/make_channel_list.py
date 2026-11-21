# SPDX-License-Identifier: GPL-3.0-or-later
# Additional terms: ADDITIONAL-TERMS.md
"""Build YOUR channel list (an .m3u file for a Jellyfin Live TV tuner) from the public iptv-org data.

You choose the groups (iptv-org categories such as weather, animation, classic, news), the country and
the language; the tool keeps only entries that pass every rule below and writes the list to your private
folder, never into this repository. Channel lists are personal choices and stay on your own machines.

    py -3 tools/make_channel_list.py --list-groups                       what groups exist, with counts
    py -3 tools/make_channel_list.py --group weather --group animation   build the list
    py -3 tools/make_channel_list.py --group news --pick                 choose single channels by number
    py -3 tools/make_channel_list.py --group classic --show              also print the kept channel names

Rules (every entry must pass all of them):
- the channel is in the chosen groups and countries (default country: US), not closed, not marked
  adult, and not on iptv-org's blocklist (channels removed after a rights claim);
- its feed's language is the chosen one (default: English); entries with no language data are left out;
- not labelled [Geo-blocked]; not labelled [Not 24/7] unless --keep-not-24-7;
- not served from a bare IP address (a common sign of a re-stream);
- not a pay-TV brand (cable and premium networks re-streamed by third parties): never offered, even if
  asked for by name;
- not reached through a third-party redirect host unless --allow-redirects (some free platform channels
  are listed that way; whether you may watch them outside the platform's own apps is your call);
- your own --exclude patterns, then your --include patterns when given.
One stream is kept per channel feed, the smallest listed picture size first (the Chromatic shows at most
160x120, so the server has less to convert).

The data (channels, feeds, streams, blocklist) is read from https://iptv-org.github.io/api/ (The
Unlicense); --source DIR reads the same four .json files from a folder instead (offline, tests). iptv-org
hosts no video: each stream belongs to its broadcaster. Prints counts only, unless --show or --pick.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jellyfin_admin as ja  # noqa: E402  (only for the private folder and path checks)

APP = 'Chromavision'
REPO = Path(__file__).resolve().parents[1]
API = 'https://iptv-org.github.io/api/'
FILES = ('channels.json', 'feeds.json', 'streams.json', 'blocklist.json')
LIMIT = 256 * 1024 * 1024

# Cable and premium networks. Their entries in public lists are re-streams by third parties, so they are
# never offered, whatever the options. (Official free channels of the same owners have other names.)
PAY_TV = re.compile(
    r'\b(Cartoon\s*Network|Cartoonito|Boomerang|Disney|Nick\s*Jr|Nicktoons|TeenNick|Nickelodeon|MTV|Starz|HBO|'
    r'Showtime|Cinemax|Epix|MGM\+|ESPN|Fox\s*Sports|FS1|FS2|NFL\s*Network|NBA\s*TV|NHL\s*Network|MLB\s*Network|'
    r'The\s*Weather\s*Channel|Discovery|Animal\s*Planet|TLC|AMC|FXX?|Adult\s*Swim|Toonami|Comedy\s*Central|'
    r'Paramount\s*Network|BET|CNN|HLN|TNT|TBS|truTV|USA\s*Network|Syfy|Bravo|Hallmark|Lifetime|A&E|History|'
    r'National\s*Geographic|Nat\s*Geo|Food\s*Network|HGTV|Travel\s*Channel|Sky\s*\w+|DAZN|beIN)\b', re.I)
# Hosts that only redirect to someone else's stream (not the broadcaster's own service).
REDIRECT_HOSTS = {'jmp2.uk'}
QUALITY = re.compile(r'(\d{3,4})p')


def fetch(name, source=None):
    if source:
        return json.loads((Path(source) / name).read_text(encoding='utf-8'))
    request = urllib.request.Request(API + name, headers={'User-Agent': 'chromavision-list-builder/1.0'})
    with urllib.request.urlopen(request, timeout=180) as reply:
        return json.loads(reply.read(LIMIT))


def bare_ip(url):
    try:
        ipaddress.ip_address(urlsplit(url).hostname or '')
        return True
    except ValueError:
        return False


def height(stream):
    match = QUALITY.search(str(stream.get('quality') or ''))
    return int(match.group(1)) if match else 10_000


UNSAFE = re.compile(r'[\x00-\x20\x7f-\x9f"<>\\^`{|}]')   # whitespace, control characters and characters no address holds


def clean(text):
    """A name or header value from third-party data, safe on one line of the list: no control characters."""
    return re.sub(r'[",\x00-\x1f\x7f-\x9f]+', ' ', str(text or '')).strip()


def safe_url(url):
    """A stream address is written only when it is one plain http(s) address: no whitespace or control characters
    (which could add lines to the list), no quotes."""
    return url.startswith(('http://', 'https://')) and not UNSAFE.search(url) and len(url) <= 2048


def build(data, groups, countries, language='eng', keep_not_247=False, allow_redirects=False,
          include=(), exclude=(), all_groups=False):
    """(kept entries, counts of what was dropped and why). An entry: dict with id, name, group, stream."""
    channels = {c['id']: c for c in data['channels.json']}
    blocked = {b.get('channel') for b in data['blocklist.json']}
    feeds = {(f.get('channel'), f.get('id')): f for f in data['feeds.json']}
    main_feed = {f.get('channel'): f for f in data['feeds.json'] if f.get('is_main')}
    groups = {g.lower() for g in groups}
    countries = {c.upper() for c in countries}
    include = [re.compile(p, re.I) for p in include]
    exclude = [re.compile(p, re.I) for p in exclude]
    dropped, best = Counter(), {}
    for stream in data['streams.json']:
        channel = channels.get(stream.get('channel') or '')
        if not channel:
            continue          # a stream iptv-org cannot tie to a channel: no country, group or language to check
        cats = {c.lower() for c in channel.get('categories') or []}
        if countries and str(channel.get('country', '')).upper() not in countries:
            continue
        if 'xxx' in cats or channel.get('is_nsfw'):
            dropped['adult'] += 1
            continue
        if not all_groups and not cats & groups:
            continue
        name = clean(stream.get('title') or channel.get('name'))
        labels = {str(x).lower() for x in stream.get('labels') or []}
        feed = feeds.get((channel['id'], stream.get('feed'))) or main_feed.get(channel['id']) or {}
        url = str(stream.get('url') or '').strip()
        host = (urlsplit(url).hostname or '').lower()
        if channel.get('closed') or channel['id'] in blocked:
            dropped['closed or on the blocklist'] += 1
        elif language and language not in (feed.get('languages') or []):
            dropped['other language or no language data'] += 1
        elif 'geo-blocked' in labels:
            dropped['geo-blocked'] += 1
        elif 'not 24/7' in labels and not keep_not_247:
            dropped['not 24/7'] += 1
        elif not safe_url(url):
            dropped['unsafe or malformed address'] += 1
        elif bare_ip(url):
            dropped['bare IP address or not a web address'] += 1
        elif PAY_TV.search(name) or PAY_TV.search(str(channel.get('name') or '')):
            dropped['pay-TV brand (never offered)'] += 1
        elif host in REDIRECT_HOSTS and not allow_redirects:
            dropped['third-party redirect'] += 1
        elif any(p.search(name) for p in exclude) or (include and not any(p.search(name) for p in include)):
            dropped['your include/exclude patterns'] += 1
        else:
            key = (channel['id'], stream.get('feed') or (feed.get('id') or ''))
            entry = {'id': f'{key[0]}@{key[1]}' if key[1] else key[0], 'name': name,
                     'group': sorted(cats & groups)[0] if cats & groups else (sorted(cats)[0] if cats else 'other'),
                     'stream': stream}
            if key not in best or height(stream) < height(best[key]['stream']):
                if key in best:
                    dropped['larger copy of a kept channel'] += 1
                best[key] = entry
            else:
                dropped['larger copy of a kept channel'] += 1
    kept = sorted(best.values(), key=lambda e: (e['group'], e['name'].lower()))
    return kept, dropped


def m3u(entries):
    lines = ['#EXTM3U']
    entries = [e for e in entries if safe_url(str(e['stream'].get('url') or '').strip())]   # again, in case
    for number, entry in enumerate(entries, 1):
        group = clean(entry['group']).title()
        lines.append(f'#EXTINF:-1 tvg-id="{clean(entry["id"])}" tvg-chno="{number}" group-title="{group}",{entry["name"]}')
        stream = entry['stream']
        if stream.get('referrer'):
            lines.append('#EXTVLCOPT:http-referrer=' + clean(stream['referrer']))
        if stream.get('user_agent'):
            lines.append('#EXTVLCOPT:http-user-agent=' + clean(stream['user_agent']))
        lines.append(str(stream['url']).strip())
    return '\n'.join(lines) + '\n'


def pick(entries, ask=input):
    for number, entry in enumerate(entries, 1):
        print(f'{number:4}  [{entry["group"]}] {entry["name"]}')
    answer = ask('Numbers to keep (for example 1-5,8,12; Enter keeps all): ').strip()
    if not answer:
        return entries
    chosen = set()
    for part in answer.split(','):
        part = part.strip()
        if re.fullmatch(r'\d+-\d+', part):
            a, b = (int(x) for x in part.split('-'))
            chosen.update(range(min(a, b), max(a, b) + 1))
        elif part.isdigit():
            chosen.add(int(part))
        elif part:
            raise ValueError('Use numbers, ranges like 3-7 and commas only.')
    return [e for n, e in enumerate(entries, 1) if n in chosen]


def main(argv=None):
    parser = argparse.ArgumentParser(description='Build your own Chromavision channel list from iptv-org data.')
    parser.add_argument('--group', action='append', default=[], help='an iptv-org category, for example weather (repeat it)')
    parser.add_argument('--all-groups', action='store_true', help='every group except adult ones')
    parser.add_argument('--country', action='append', default=[], help='two-letter country code (repeat it; default US)')
    parser.add_argument('--language', default='eng', help='three-letter language code (default eng)')
    parser.add_argument('--keep-not-24-7', action='store_true', help='keep channels labelled [Not 24/7]')
    parser.add_argument('--allow-redirects', action='store_true', help='keep channels reached through a third-party redirect')
    parser.add_argument('--include', action='append', default=[], help='keep only names matching this pattern (repeat it)')
    parser.add_argument('--exclude', action='append', default=[], help='leave out names matching this pattern (repeat it)')
    parser.add_argument('--max', type=int, default=0, help='keep at most this many channels')
    parser.add_argument('--pick', action='store_true', help='choose single channels by number')
    parser.add_argument('--show', action='store_true', help='print the names of the kept channels')
    parser.add_argument('--list-groups', action='store_true', help='print the groups and how many channels each would give')
    parser.add_argument('--out', help='where to write the list (default: channels.m3u in your private folder)')
    parser.add_argument('--source', help='read channels/feeds/streams/blocklist .json from this folder (offline)')
    args = parser.parse_args(argv)
    countries = args.country or ['US']
    out = Path(args.out) if args.out else ja.private_home(APP) / 'channels.m3u'
    if ja.inside(out, REPO):
        print('FAIL the list would be written inside the repository folder. Channel lists are personal and stay '
              'out of Git: choose a folder outside it (the default is your private folder).')
        return 2
    if not (args.group or args.all_groups or args.list_groups):
        print('Choose at least one --group (see --list-groups), or --all-groups.')
        return 2
    try:
        data = {name: fetch(name, args.source) for name in FILES}
    except (OSError, ValueError):
        print('FAIL the iptv-org data could not be read (no internet, or the address changed); nothing was written')
        return 1
    if args.list_groups:
        kept, _ = build(data, [], countries, args.language, args.keep_not_24_7, args.allow_redirects,
                        args.include, args.exclude, all_groups=True)
        channels = {c['id']: c for c in data['channels.json']}
        counts = Counter(cat for e in kept for cat in channels[e['id'].split('@')[0]].get('categories') or [])
        for group, count in sorted(counts.items()):
            print(f'{group:16} {count}')
        return 0
    kept, dropped = build(data, args.group, countries, args.language, args.keep_not_24_7, args.allow_redirects,
                          args.include, args.exclude, args.all_groups)
    if args.pick:
        try:
            kept = pick(kept)
        except (ValueError, EOFError) as error:
            print(f'FAIL {error}' if isinstance(error, ValueError) else 'FAIL nothing chosen; nothing was written')
            return 2
    if args.max > 0:
        kept = kept[:args.max]
    if args.show and not args.pick:
        for entry in kept:
            print(f'  [{entry["group"]}] {entry["name"]}')
    for reason, count in sorted(dropped.items()):
        print(f'INFO left out ({reason}): {count}')
    if not kept:
        print('FAIL no channel passed the rules; nothing was written')
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(m3u(kept), encoding='utf-8', newline='\n')
    groups = Counter(e['group'] for e in kept)
    print(f'PASS channels written: {len(kept)} (' + ', '.join(f'{g} {n}' for g, n in sorted(groups.items())) + ')')
    print('INFO the list is in your private folder' if not args.out else 'INFO the list was written where you asked')
    print('INFO next: put it where your Jellyfin server can read it (docs/Live-TV-setup.md)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
