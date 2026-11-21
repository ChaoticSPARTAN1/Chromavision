# SPDX-License-Identifier: GPL-3.0-or-later
# Additional terms: ADDITIONAL-TERMS.md
"""make_channel_list.py on made-up iptv-org data (offline: --source). Every rule is exercised:
groups, country, language, geo-blocked, not 24/7, bare IP, blocklist, closed, adult, pay-TV brands,
third-party redirects, include/exclude, the smallest copy of a feed, referrer/user-agent lines, names
that would break the file, and that the list is never written inside the repository.

    py -3 tools/tests/test_make_channel_list.py
"""
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import make_channel_list as tool  # noqa: E402

failures = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok:
        failures.append(what)


def channel(ident, name, cats, country='US', **extra):
    return dict({'id': ident, 'name': name, 'categories': cats, 'country': country, 'is_nsfw': False, 'closed': None}, **extra)


DATA = {
    'channels.json': [
        channel('SunnyWeather.us', 'Sunny Weather', ['weather']),
        channel('ToonTime.us', 'Toon Time', ['animation', 'kids']),
        channel('RetroToons.us', 'Retro Toons', ['animation']),
        channel('Spanish.us', 'Canal Uno', ['animation']),
        channel('NoLang.us', 'Mystery Toons', ['animation']),
        channel('Geo.us', 'Locked Toons', ['animation']),
        channel('Part.us', 'Weekend Toons', ['animation']),
        channel('Bare.us', 'Pirate Toons', ['animation']),
        channel('Gone.us', 'Old Toons', ['animation'], closed='2020-01-01'),
        channel('Claimed.us', 'Claimed Toons', ['animation']),
        channel('Adult.us', 'Late Toons', ['animation'], is_nsfw=True),
        channel('Pay.us', 'Cartoon Network East', ['animation']),
        channel('Platform.us', 'Platform Toons', ['animation']),
        channel('Quoted.us', 'Toons "Plus", More', ['animation']),
        channel('News.us', 'Daily News', ['news']),
        channel('UK.uk', 'British Toons', ['animation'], country='UK'),
        channel('Inject.us', 'Sneaky Toons', ['animation']),
        channel('Ctrl.us', 'Bell\x07Toons', ['animation']),
    ],
    'feeds.json': [{'channel': c, 'id': 'SD', 'is_main': True, 'languages': ['eng']}
                   for c in ('SunnyWeather.us', 'ToonTime.us', 'RetroToons.us', 'Geo.us', 'Part.us', 'Bare.us', 'Gone.us',
                             'Claimed.us', 'Adult.us', 'Pay.us', 'Platform.us', 'Quoted.us', 'News.us', 'UK.uk',
                             'Inject.us', 'Ctrl.us')]
                  + [{'channel': 'Spanish.us', 'id': 'SD', 'is_main': True, 'languages': ['spa']},
                     {'channel': 'NoLang.us', 'id': 'SD', 'is_main': True, 'languages': []}],
    'streams.json': [
        {'channel': 'SunnyWeather.us', 'feed': 'SD', 'title': 'Sunny Weather', 'url': 'https://cdn.sunny.example/live.m3u8', 'quality': '720p', 'labels': []},
        {'channel': 'ToonTime.us', 'feed': 'SD', 'title': 'Toon Time', 'url': 'https://cdn.toon.example/big.m3u8', 'quality': '1080p', 'labels': []},
        {'channel': 'ToonTime.us', 'feed': 'SD', 'title': 'Toon Time', 'url': 'https://cdn.toon.example/small.m3u8', 'quality': '360p',
         'labels': [], 'referrer': 'https://toon.example/', 'user_agent': 'Mozilla/5.0'},
        {'channel': 'RetroToons.us', 'feed': 'SD', 'title': 'Retro Toons', 'url': 'https://retro.example/a.m3u8', 'quality': None, 'labels': []},
        {'channel': 'Spanish.us', 'feed': 'SD', 'title': 'Canal Uno', 'url': 'https://uno.example/a.m3u8', 'labels': []},
        {'channel': 'NoLang.us', 'feed': 'SD', 'title': 'Mystery Toons', 'url': 'https://m.example/a.m3u8', 'labels': []},
        {'channel': 'Geo.us', 'feed': 'SD', 'title': 'Locked Toons', 'url': 'https://g.example/a.m3u8', 'labels': ['Geo-blocked']},
        {'channel': 'Part.us', 'feed': 'SD', 'title': 'Weekend Toons', 'url': 'https://p.example/a.m3u8', 'labels': ['Not 24/7']},
        {'channel': 'Bare.us', 'feed': 'SD', 'title': 'Pirate Toons', 'url': 'http://203.0.113.9:8080/live.m3u8', 'labels': []},
        {'channel': 'Gone.us', 'feed': 'SD', 'title': 'Old Toons', 'url': 'https://old.example/a.m3u8', 'labels': []},
        {'channel': 'Claimed.us', 'feed': 'SD', 'title': 'Claimed Toons', 'url': 'https://c.example/a.m3u8', 'labels': []},
        {'channel': 'Adult.us', 'feed': 'SD', 'title': 'Late Toons', 'url': 'https://late.example/a.m3u8', 'labels': []},
        {'channel': 'Pay.us', 'feed': 'SD', 'title': 'Cartoon Network East', 'url': 'https://pay.example/a.m3u8', 'labels': []},
        {'channel': 'Platform.us', 'feed': 'SD', 'title': 'Platform Toons', 'url': 'https://jmp2.uk/abc', 'labels': []},
        {'channel': 'Quoted.us', 'feed': 'SD', 'title': 'Toons "Plus", More', 'url': 'https://q.example/a.m3u8', 'labels': []},
        {'channel': 'News.us', 'feed': 'SD', 'title': 'Daily News', 'url': 'https://news.example/a.m3u8', 'labels': []},
        {'channel': 'UK.uk', 'feed': 'SD', 'title': 'British Toons', 'url': 'https://uk.example/a.m3u8', 'labels': []},
        {'channel': 'Inject.us', 'feed': 'SD', 'title': 'Sneaky Toons',
         'url': 'https://sneaky.example/a.m3u8\r\n#EXTINF:-1,Injected\r\nhttps://evil.example/x.m3u8', 'labels': []},
        {'channel': 'Ctrl.us', 'feed': 'SD', 'title': 'Bell\x07Toons\r\n#EXTINF:-1,Fake', 'url': 'https://bell.example/a.m3u8',
         'referrer': 'https://bell.example/\n#EXTINF:-1,Fake2', 'user_agent': 'UA\r\nhttp://evil.example/', 'labels': []},
    ],
    'blocklist.json': [{'channel': 'Claimed.us', 'reason': 'dmca'}],
}


def main():
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / 'api'
        source.mkdir()
        for name, value in DATA.items():
            (source / name).write_text(json.dumps(value), encoding='utf-8')
        data = {name: tool.fetch(name, source) for name in tool.FILES}

        kept, dropped = tool.build(data, ['animation', 'weather'], ['US'])
        names = [e['name'] for e in kept]
        check(names == ['Bell Toons #EXTINF:-1 Fake', 'Retro Toons', 'Toon Time', 'Toons  Plus  More', 'Sunny Weather'],
              f'kept exactly the good ones: {names}')
        check(dropped['unsafe or malformed address'] == 1, 'an address with line breaks or spaces is never written')
        check(dropped['other language or no language data'] == 2, 'other language and no language data left out')
        check(dropped['geo-blocked'] == 1 and dropped['not 24/7'] == 1, 'geo-blocked and not 24/7 left out')
        check(dropped['bare IP address or not a web address'] == 1, 'a bare IP stream is left out')
        check(dropped['closed or on the blocklist'] == 2 and dropped['adult'] == 1, 'closed, blocklisted and adult left out')
        check(dropped['pay-TV brand (never offered)'] == 1, 'a pay-TV brand is never offered')
        check(dropped['third-party redirect'] == 1, 'a third-party redirect is left out by default')
        toon = next(e for e in kept if e['name'] == 'Toon Time')
        check(toon['stream']['url'].endswith('small.m3u8') and dropped['larger copy of a kept channel'] == 1,
              'the smallest copy of a feed is kept')
        check('British Toons' not in names and 'Daily News' not in names, 'other countries and other groups are not taken')

        more, _ = tool.build(data, ['animation'], ['US'], keep_not_247=True, allow_redirects=True)
        more_names = {e['name'] for e in more}
        check({'Weekend Toons', 'Platform Toons'} <= more_names and 'Cartoon Network East' not in more_names,
              'options keep not-24/7 and redirects, but never a pay-TV brand')
        only, _ = tool.build(data, ['animation'], ['US'], include=['retro'])
        check([e['name'] for e in only] == ['Retro Toons'], '--include keeps only matching names')
        less, _ = tool.build(data, ['animation'], ['US'], exclude=['retro'])
        check('Retro Toons' not in {e['name'] for e in less}, '--exclude leaves matching names out')

        text = tool.m3u(kept)
        lines = text.splitlines()
        check(lines[0] == '#EXTM3U' and sum(line.startswith('#EXTINF') for line in lines) == 5 and len(lines) == 1 + 5 * 2 + 4,
              'a valid m3u with five channels, one line per field')
        urls = [line for line in lines if not line.startswith('#')]
        check('Injected' not in text and not any(ord(c) < 32 for c in text.replace('\n', ''))
              and all(line.startswith(('#EXTM3U', '#EXTINF:-1 tvg-id=', '#EXTVLCOPT:http-')) for line in lines if line.startswith('#'))
              and len(urls) == 5 and all(u.startswith('https://') and ' ' not in u for u in urls),
              'no line can be injected from third-party names, addresses, referrers or user agents')
        check('#EXTVLCOPT:http-referrer=https://toon.example/' in lines and '#EXTVLCOPT:http-user-agent=Mozilla/5.0' in lines,
              'referrer and user-agent lines are kept')
        check(all(line.count('"') % 2 == 0 for line in lines if line.startswith('#EXTINF')), 'names cannot break the file')

        picked = tool.pick(kept, ask=lambda prompt: '2, 4-5')
        check([e['name'] for e in picked] == ['Retro Toons', 'Toons  Plus  More', 'Sunny Weather'], '--pick takes numbers and ranges')

        out = io.StringIO()
        with redirect_stdout(out):
            inside = tool.main(['--group', 'animation', '--source', str(source), '--out', str(tool.REPO / 'channels.m3u')])
            outside = tool.main(['--group', 'animation', '--source', str(source), '--out', str(Path(folder) / 'mine.m3u')])
            none = tool.main(['--source', str(source), '--out', str(Path(folder) / 'none.m3u')])
        check(inside == 2 and not (tool.REPO / 'channels.m3u').exists(), 'never writes a list inside the repository')
        check(outside == 0 and (Path(folder) / 'mine.m3u').is_file(), 'writes the list outside the repository')
        check(none == 2, 'refuses without a group')
        check('https://' not in out.getvalue(), 'prints counts, not stream addresses')
    print('PASS' if not failures else f'FAIL: {len(failures)} check(s) failed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
