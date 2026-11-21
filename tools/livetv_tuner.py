# SPDX-License-Identifier: GPL-3.0-or-later
# Additional terms: ADDITIONAL-TERMS.md
"""Add, check and remove the ONE Live TV tuner Chromavision uses on your Jellyfin server.

    py -3 tools/livetv_tuner.py check                       read-only: is the server ready? (changes nothing)
    py -3 tools/livetv_tuner.py add --server-path PATH      dry run: shows exactly what would be added
    py -3 tools/livetv_tuner.py add --server-path PATH --yes     adds the tuner
    py -3 tools/livetv_tuner.py trial --server-path PATH --yes   adds a temporary test tuner reading a small list
                                                            you built (make_channel_list.py), plays one channel
                                                            in the Chromatic's format, deletes the tuner
    py -3 tools/livetv_tuner.py status                      read-only
    py -3 tools/livetv_tuner.py refresh-guide --yes         runs Jellyfin's own "Refresh Guide" task once
    py -3 tools/livetv_tuner.py remove                      dry run
    py -3 tools/livetv_tuner.py remove --yes                deletes exactly the tuner "add" recorded

Where the channel list comes from (add): --server-path is the list file as the SERVER sees it (for
example /config/chromavision/channels.m3u inside a Jellyfin container); the tool first checks, read-only,
that the server lists that file. --list-url is a plain public https address of a list instead.

Sign-in: by default the saved Jellyfin settings (this tool's folder, then Jellymatic's). Adding a tuner
needs an administrator: --ask-admin asks for an administrator's name and password for this one run (kept
in memory only, never saved; that run's own session is signed out at the end). Use a normal,
non-administrator account on the console itself.

Safety (docs/Server-safety.md): add-only; a backup of the Live TV settings and a fingerprint of libraries,
users, devices, plugins, task triggers and conversion settings are saved first; after the change the
tool proves nothing else changed; remove deletes only the recorded id and proves the Live TV settings
equal the backup. The tuner has a stream limit (1 by default, at most 2). Only these changing requests
can ever be sent, everything else is refused unsent:
    POST   /LiveTv/TunerHosts                 only a tuner named as below
    DELETE /LiveTv/TunerHosts?id=             only the id this tool created and recorded
    POST   /ScheduledTasks/Running/{id}       only Jellyfin's own Refresh Guide task (refresh-guide)
    POST   /Items/{id}/PlaybackInfo, POST /LiveStreams/Close, DELETE /Videos/ActiveEncodings
                                              (trial only: open, close and stop one test channel)
It prints PASS / FAIL / INFO lines and counts only: never an address, path, name, token or id.

Chromatic Manager (start-up menu 1.6.5 or newer, Settings > Live TV channels) adds the same tuner under the same name and keeps
its record with the same keys; its older name "Chromatic TV (added by Chromatic Manager)" counts too. So neither tool
adds a second tuner, and either one's remove works (this tool reads the Manager's record when it has none of its own).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jellyfin_admin as ja  # noqa: E402

APP = 'Chromavision'
NAME = 'Chromavision Live TV (added by Chromavision tools)'
TRIAL_NAME = 'Chromavision test (removed automatically)'
MAX_STREAMS = 2
# Chromatic Manager (start-up menu 1.6.5 or newer) adds the same tuner under the same name; an older Manager used this one.
# Both count as "ours": never added twice, shown by status, removable by their recorded id.
OLDER_NAME = 'Chromatic TV (added by Chromatic Manager)'
NAMES = (NAME, OLDER_NAME)


def state_dir():
    return ja.private_home(APP) / 'livetv'


def manager_dir():
    """Where Chromatic Manager keeps its Live TV record (the same keys as this tool's)."""
    return ja.private_home('Jellymatic') / 'livetv-backups'


def record_dir(folder=None):
    """The folder holding the tuner record: this tool's, else Chromatic Manager's, else this tool's (none yet)."""
    if folder is not None:
        return folder
    for candidate in (state_dir(), manager_dir()):
        if (candidate / 'state.json').exists():
            return candidate
    return state_dir()


# ---------------------------------------------------------------- reading
def tuners(client):
    value, status = ja.read(client, '/System/Configuration/livetv')
    return (value, value.get('TunerHosts') or []) if status == 'ok' and isinstance(value, dict) else (None, None)


def channel_ids(client):
    value, status = ja.read(client, '/LiveTv/Channels', {'userId': client.user_id, 'limit': 2000, 'enableUserData': 'false',
                                                         'enableImages': 'false'})
    return {str(c.get('Id')) for c in (value or {}).get('Items') or []} if status == 'ok' else None


def without(config, ident):
    return dict(config, TunerHosts=[x for x in config.get('TunerHosts') or [] if str(x.get('Id')) != ident])


def wait_for(check, seconds, step=3.0, sleep=time.sleep):
    deadline = time.monotonic() + seconds
    while True:
        value = check()
        if value or time.monotonic() >= deadline:
            return value
        sleep(step)


def tuner_body(name, url, streams):
    return {'Type': 'm3u', 'Url': url, 'FriendlyName': name, 'TunerCount': streams, 'AllowHWTranscoding': False,
            'AllowStreamSharing': True, 'EnableStreamLooping': False, 'ImportFavoritesOnly': False, 'IgnoreDts': True}


def check_list_url(url):
    """A public https list address with nothing that could carry a sign-in."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return (parts.scheme == 'https' and bool(parts.hostname) and not parts.username and not parts.password
            and not parts.query and not parts.fragment and '@' not in url)


# ---------------------------------------------------------------- check (read-only)
def check(client, report, save=True):
    version = ja.server_version(client)
    report('PASS' if version and version >= (10, 9) else 'FAIL', 'server version is 10.9 or newer')
    report('INFO', 'this sign-in is an administrator: ' + ('yes' if client.is_admin else 'no'))
    report('PASS' if client.policy.get('EnableLiveTvAccess') else 'FAIL', 'this user may watch Live TV')
    report('PASS' if client.policy.get('EnableVideoPlaybackTranscoding') else 'FAIL', 'this user may have video converted')
    before, found = tuners(client)
    if before is None:
        report('FAIL' if client.is_admin else 'INFO', 'Live TV settings not readable; an administrator sign-in is needed (--ask-admin)')
    else:
        guides = before.get('ListingProviders') or []
        report('PASS', f'Live TV settings readable; tuners now: {len(found)}, guide sources now: {len(guides)}')
        report('INFO', 'the Chromavision tuner is already there: ' + ('yes' if any(t.get('FriendlyName') in NAMES for t in found) else 'no'))
    channels = channel_ids(client)
    if channels is not None:
        report('INFO', f'Live TV channels this user sees now: {len(channels)}')
    print_, shown = ja.fingerprint(client)
    report('INFO', 'server set-up: ' + ', '.join(shown))
    if save and before is not None:
        ja.save_private(state_dir() / f'check-{ja.utc_stamp()}.json', {'livetv': before, 'fingerprint': print_})
        report('PASS', 'Live TV settings and fingerprint saved in your private folder')
    report('INFO', 'nothing on the server was changed by this check')
    return not report.failed


# ---------------------------------------------------------------- add
def add(client, report, list_url, streams=1, apply=False, wait=600, sleep=time.sleep, folder=None, shown_list='a list'):
    known = record_dir(folder) / 'state.json'
    folder = folder or state_dir()
    record = folder / 'state.json'
    before, found = tuners(client)
    if before is None:
        report('FAIL', 'Live TV settings not readable (an administrator sign-in is needed); nothing was changed')
        return False
    if known.exists() or record.exists() or any(t.get('FriendlyName') in NAMES for t in found):
        report('FAIL', 'the Chromavision tuner is already there; nothing was changed (remove it first to change it)')
        return False
    body = tuner_body(NAME, list_url, streams)
    report('INFO', f'would add ONE tuner: type m3u, name "{NAME}", {shown_list}, at most {streams} stream(s) at once, '
                   'no hardware conversion; nothing else')
    report('INFO', f'the server has now: {len(found)} tuner(s), {len(before.get("ListingProviders") or [])} guide source(s)')
    if not apply:
        report('INFO', 'dry run: nothing was sent. Run again with --yes to add it')
        return True
    print_, _ = ja.fingerprint(client)
    channels = channel_ids(client) or set()
    stamp = ja.utc_stamp()
    backup = folder / f'before-add-{stamp}.json'
    ja.save_private(backup, {'taken_utc': stamp, 'livetv': before, 'fingerprint': print_, 'channels': len(channels)})
    report('PASS', 'backup of the Live TV settings and the server fingerprint saved in your private folder')
    try:
        client.send('POST', '/LiveTv/TunerHosts', payload=body)
    except ja.ClientError:
        pass  # judged by what the server now holds
    after, now = tuners(client)
    old = {str(t.get('Id')) for t in found}
    fresh = [t for t in now or [] if str(t.get('Id')) not in old]
    if len(fresh) != 1 or fresh[0].get('FriendlyName') != NAME:
        report('FAIL', 'the tuner was not added cleanly' if not fresh else 'unexpected tuner change: check Dashboard > Live TV')
        return False
    ident = str(fresh[0].get('Id'))
    ja.save_private(record, {'tuner_id': ident, 'backup': backup.name, 'added_utc': stamp})
    same = ja.canonical(without(after, ident)) == ja.canonical(before)
    report('PASS' if same else 'FAIL', 'tuner added; every other Live TV setting is unchanged' if same
           else 'tuner added, but other Live TV settings changed: check Dashboard > Live TV')
    new = wait_for(lambda: (channel_ids(client) or set()) - channels, wait, sleep=sleep)
    report('PASS' if new else 'INFO', f'new channels listed: {len(new or ())}' if new
           else 'no new channels yet; Jellyfin lists them after its guide refresh (refresh-guide --yes)')
    after_print, _ = ja.fingerprint(client)
    unchanged = after_print == print_
    report('PASS' if unchanged else 'FAIL', 'libraries, users, devices, plugins, tasks and conversion settings unchanged'
           if unchanged else 'the server fingerprint differs from before')
    return same and unchanged


# ---------------------------------------------------------------- remove
def remove(client, report, apply=False, folder=None):
    folder = record_dir(folder)
    record = folder / 'state.json'
    if not record.exists():
        report('FAIL', 'no Chromavision tuner is recorded on this PC; nothing was changed '
                       '(to remove one by hand: Dashboard > Live TV > delete the tuner with that name)')
        return False
    state = json.loads(record.read_text(encoding='utf-8'))
    saved = json.loads((folder / state['backup']).read_text(encoding='utf-8'))
    _, found = tuners(client)
    ours = [t for t in found or [] if str(t.get('Id')) == state['tuner_id'] and t.get('FriendlyName') in NAMES]
    report('INFO', 'would delete ONE tuner: the recorded Chromavision tuner' + ('' if ours else ' (it is no longer on the server)'))
    if not apply:
        report('INFO', 'dry run: nothing was sent. Run again with --yes to remove it')
        return True
    if ours:
        try:
            client.send('DELETE', '/LiveTv/TunerHosts', {'id': state['tuner_id']})
        except ja.ClientError:
            pass
    after, _ = tuners(client)
    same = after is not None and ja.canonical(after) == ja.canonical(saved['livetv'])
    report('PASS' if same else 'FAIL', 'tuner removed; the Live TV settings are identical to before it was added' if same
           else 'the Live TV settings differ from before it was added: check Dashboard > Live TV')
    print_, _ = ja.fingerprint(client)
    report('PASS' if print_ == saved['fingerprint'] else 'INFO',
           'libraries, users, devices, plugins, tasks and conversion settings unchanged' if print_ == saved['fingerprint']
           else 'the server fingerprint differs from the day the tuner was added (devices or plugins may have changed since)')
    if same:
        record.unlink()
        report('INFO', 'its channels leave the list at the next guide refresh (refresh-guide --yes)')
    return same


# ---------------------------------------------------------------- status and guide refresh
def status(client, report, folder=None):
    folder = record_dir(folder)
    _, found = tuners(client)
    report('INFO', f'tuners: {len(found or [])}; Chromavision tuner present: '
                   f'{"yes" if any(t.get("FriendlyName") in NAMES for t in found or []) else "no"}; '
                   f'recorded on this PC: {"yes" if (folder / "state.json").exists() else "no"}')
    channels = channel_ids(client)
    report('INFO', f'channels listed: {len(channels) if channels is not None else "not readable"}')
    return True


def guide_task(client):
    tasks, status_ = ja.read(client, '/ScheduledTasks')
    return next((t for t in tasks or [] if t.get('Key') == 'RefreshGuide'), None) if status_ == 'ok' else None


def refresh_guide(client, report, sleep=time.sleep, wait=600):
    task = guide_task(client)
    if not task or not re.fullmatch(r'[A-Za-z0-9]{8,64}', str(task.get('Id', ''))):
        report('FAIL', 'the guide refresh task was not found')
        return False
    client.allowed.append(('POST', re.escape('/ScheduledTasks/Running/' + task['Id']), None))
    if task.get('State') == 'Idle':
        try:
            client.send('POST', '/ScheduledTasks/Running/' + task['Id'])
        except ja.ClientError:
            report('FAIL', 'the server refused to start the guide refresh')
            return False
        report('PASS', 'guide refresh started')
    else:
        report('INFO', 'the guide refresh was already running')
    deadline = time.monotonic() + wait
    sleep(3)
    while time.monotonic() < deadline:
        task = guide_task(client)
        if task and task.get('State') == 'Idle':
            break
        sleep(5)
    result = ((task or {}).get('LastExecutionResult') or {}).get('Status', 'unknown')
    report('INFO', f'guide refresh finished: {"yes" if (task or {}).get("State") == "Idle" else "not yet"}; result: {result}')
    return True


# ---------------------------------------------------------------- trial: add, play, delete, compare
def trial(client, report, list_url, sleep=time.sleep, wait_channels=240, play_seconds=20):
    """list_url: a list built by make_channel_list.py (so it passed the same rules as the main list), as the server
    sees it, or a plain https address of one."""
    before, found = tuners(client)
    if before is None:
        report('FAIL', 'Live TV settings not readable (an administrator sign-in is needed); nothing was changed')
        return False
    if any(t.get('FriendlyName') == TRIAL_NAME for t in found):
        report('FAIL', 'a test tuner from an earlier run is still there; delete it in Dashboard > Live TV first')
        return False
    print_before, _ = ja.fingerprint(client)
    channels_before = channel_ids(client)
    if channels_before is None:
        report('FAIL', 'channels not readable; nothing was changed')
        return False
    report('PASS', f'"before" read: {len(found)} tuner(s), {len(channels_before)} channel(s)')
    created = None
    try:
        try:
            reply = client.send('POST', '/LiveTv/TunerHosts', payload=tuner_body(TRIAL_NAME, list_url, 1))
        except ja.ClientError:
            reply = None
        _, now = tuners(client)
        old = {str(t.get('Id')) for t in found}
        fresh = [t for t in now or [] if str(t.get('Id')) not in old]
        if len(fresh) == 1 and fresh[0].get('FriendlyName') == TRIAL_NAME:
            created = str(fresh[0].get('Id'))
        if not created:
            report('FAIL', 'the test tuner was not added' if not fresh else 'unexpected tuner change')
            if reply and reply.get('Id') and not fresh:
                created = str(reply['Id'])
            raise ja.ClientError('add failed')
        report('PASS', 'test tuner added (one stream at most)')
        new = wait_for(lambda: (channel_ids(client) or set()) - channels_before, wait_channels, sleep=sleep)
        if not new:
            report('FAIL', f'no new channels after {wait_channels} s')
            raise ja.ClientError('no channels')
        sleep(5)
        new = sorted((channel_ids(client) or set()) - channels_before)
        report('PASS', f'{len(new)} new channel(s) appeared')
        played = False
        for attempt, channel in enumerate(new[:4], 1):
            report('INFO', f'trying channel {attempt}')
            client.allowed.append(('POST', re.escape(f'/Items/{channel}/PlaybackInfo'), None))
            if ja.play_like_the_console(client, channel, report, seconds=play_seconds, bitrate=400000):
                played = True
                break
            sleep(3)
        report('PASS' if played else 'FAIL', 'a live channel plays in the Chromatic format (MJPEG up to 160x120, '
               'IMA ADPCM 16 kHz, first data within 15 s)' if played else 'no tried channel played in the Chromatic format')
    except ja.ClientError:
        pass
    finally:
        _, now = tuners(client)
        old = {str(t.get('Id')) for t in found}
        ours = [str(t.get('Id')) for t in now or [] if t.get('FriendlyName') == TRIAL_NAME and str(t.get('Id')) not in old]
        for ident in ours or ([created] if created else []):
            client.allowed.append(('DELETE', r'/LiveTv/TunerHosts', lambda q, p, i=ident: q.get('id') == i))
            try:
                client.send('DELETE', '/LiveTv/TunerHosts', {'id': ident})
            except ja.ClientError:
                pass
        after, _ = tuners(client)
        same = after is not None and ja.canonical(after) == ja.canonical(before)
        report('PASS' if same else 'FAIL', 'test tuner deleted; the Live TV settings are identical to "before"' if same
               else 'the Live TV settings DIFFER from "before"')
        print_after, _ = ja.fingerprint(client)
        report('PASS' if print_after == print_before else 'FAIL', 'libraries, users, devices, plugins, tasks and conversion '
               'settings unchanged' if print_after == print_before else 'the server fingerprint DIFFERS from "before"')
        if not same:
            report('INFO', f'manual undo: Jellyfin Dashboard > Live TV > delete the tuner "{TRIAL_NAME}"')
        else:
            report('INFO', 'the test channels leave the list at the next guide refresh (refresh-guide --yes)')
    return not report.failed


# ---------------------------------------------------------------- command line
def rules(command, folder=None):
    """The changing requests each command may send (see the module text)."""
    if command == 'add':
        return [('POST', r'/LiveTv/TunerHosts', lambda q, p: (p or {}).get('FriendlyName') == NAME)]
    if command == 'remove':
        def recorded(query, payload):
            record = record_dir(folder) / 'state.json'
            return record.exists() and query.get('id') == json.loads(record.read_text(encoding='utf-8')).get('tuner_id')
        return [('DELETE', r'/LiveTv/TunerHosts', recorded)]
    if command == 'trial':
        return [('POST', r'/LiveTv/TunerHosts', lambda q, p: (p or {}).get('FriendlyName') == TRIAL_NAME),
                ('POST', r'/LiveStreams/Close', None), ('DELETE', r'/Videos/ActiveEncodings', None)]
    return []   # check, status: read-only; refresh-guide adds its one task id after reading it


def main(argv=None):
    parser = argparse.ArgumentParser(description='The one Chromavision Live TV tuner on your Jellyfin server.')
    parser.add_argument('command', choices=['check', 'add', 'remove', 'status', 'refresh-guide', 'trial'])
    parser.add_argument('--server-path', help='add, trial: the channel list file as the Jellyfin server sees it')
    parser.add_argument('--list-url', help='add, trial: a plain https address of a channel list instead')
    parser.add_argument('--streams', type=int, default=1, help='add: channels that may play at once (1 or 2; default 1)')
    parser.add_argument('--yes', action='store_true', help='really change the server (otherwise: a dry run)')
    parser.add_argument('--ask-admin', action='store_true', help='type an administrator sign-in for this run only')
    parser.add_argument('--connection', help='a saved connection file other than the default ones')
    args = parser.parse_args(argv)
    report = ja.Report()
    if args.command in ('refresh-guide', 'trial') and not args.yes:
        print(f'"{args.command}" changes the server. It runs only with --yes.')
        return 2
    if args.command in ('add', 'trial'):
        if bool(args.server_path) == bool(args.list_url):
            print(f'{args.command} needs exactly one of --server-path or --list-url (a list made by make_channel_list.py).')
            return 2
        if args.list_url and not check_list_url(args.list_url):
            print('--list-url must be a plain https address (no user name, query or fragment).')
            return 2
        if not 1 <= args.streams <= MAX_STREAMS:
            print(f'--streams must be 1 or {MAX_STREAMS}: the stream limit keeps the server from being overloaded.')
            return 2
    client = ja.open_client(APP, args, rules(args.command), report)
    if client is None:
        return 1
    try:
        if args.command == 'check':
            ok = check(client, report)
        elif args.command == 'status':
            ok = status(client, report)
        elif args.command == 'refresh-guide':
            ok = refresh_guide(client, report)
        elif args.command == 'remove':
            ok = remove(client, report, apply=args.yes)
        else:
            if args.server_path:
                seen = ja.server_sees_file(client, args.server_path)
                if seen != 'yes':
                    report('FAIL', 'the server does not list the channel list file at that path' if seen == 'no' else
                           'the server would not list that folder (an administrator sign-in is needed, or the path is wrong)')
                    report('INFO', 'nothing was changed. See docs/Live-TV-setup.md, "Put the list where the server can read it"')
                    return 1
                report('PASS', 'the server can see the channel list file')
                url, shown = args.server_path, 'a list file the server can read'
            else:
                url, shown = args.list_url, 'a public https list'
            ok = (trial(client, report, url) if args.command == 'trial'
                  else add(client, report, url, args.streams, apply=args.yes, shown_list=shown))
    finally:
        if client.sign_out_own_session():
            report('INFO', "this run's own sign-in was signed out (no other device or session was touched)")
    return 0 if ok and not report.failed else 1


if __name__ == '__main__':
    raise SystemExit(main())
