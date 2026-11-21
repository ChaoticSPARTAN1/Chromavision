# SPDX-License-Identifier: GPL-3.0-or-later
# Additional terms: ADDITIONAL-TERMS.md
"""livetv_tuner.py against the fake Jellyfin (which holds another tuner, libraries, users and sessions).

Proves, for add / remove / trial / refresh-guide / check and each failure: the other tuner is never
touched, only allow-listed requests are sent, a dry run sends no change at all, nothing private is
printed, a typed-in sign-in signs out only its own session, and (unless the delete itself fails) the
Live TV settings end identical to before. No network beyond 127.0.0.1, no device.

    py -3 tools/tests/test_livetv_tuner.py
"""
import io
import re
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import fake_jellyfin as fake  # noqa: E402
import jellyfin_admin as ja  # noqa: E402
import livetv_tuner as tool  # noqa: E402

failures = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok:
        failures.append(what)


def client_for(server, command, folder, typed=False):
    url = f'http://127.0.0.1:{server.server_port}'
    connection = ja.Connection(url, 'owner-name', 'pw-secret-9', '') if typed else ja.Connection(url, '', '', fake.SAVED_TOKEN)
    client = ja.Client(connection, tool.APP, tool.rules(command, folder))
    client.connect()
    return client, url


def private_ok(lines, url, extra=()):
    text = '\n'.join(f'{k} {t}' for k, t in lines)
    return not [s for s in fake.SECRETS + [url, 'pw-secret-9', *extra] if s in text]


def owner_tuner_untouched(state):
    return state['tuners'][0] == {'Id': 'owner1', 'Type': 'm3u', 'Url': 'http://other-tuner.invalid/channels.m3u',
                                  'FriendlyName': 'Someone Else Tuner'} and not state['unexpected']


def test_add_remove(modes, label):
    server, state = fake.start(modes)
    try:
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            client, url = client_for(server, 'add', folder)
            report = ja.Report(out=lambda s: None)
            # A dry run sends nothing that changes anything.
            dry = tool.add(client, report, '/config/chromavision/channels.m3u', apply=False, folder=folder)
            check(dry and not fake.changing(state) and not (folder / 'state.json').exists(), f'{label}: dry run sends no change')
            added = tool.add(client, report, '/config/chromavision/channels.m3u', streams=1, apply=True, wait=1,
                             sleep=lambda s: None, folder=folder)
            if 'add-refused' in modes:
                check(not added and len(state['tuners']) == 1 and not (folder / 'state.json').exists(),
                      f'{label}: a refused add leaves nothing recorded')
            else:
                new = state['tuners'][-1]
                check(added and len(state['tuners']) == 2 and new['FriendlyName'] == tool.NAME and new['TunerCount'] == 1
                      and new['AllowHWTranscoding'] is False, f'{label}: one tuner added, stream limit 1')
                check(not tool.add(client, report, '/x.m3u', apply=True, folder=folder) and len(state['tuners']) == 2,
                      f'{label}: a second add is refused')
                client_r, _ = client_for(server, 'remove', folder)
                check(tool.remove(client_r, report, apply=False, folder=folder) and len(state['tuners']) == 2,
                      f'{label}: remove dry run deletes nothing')
                removed = tool.remove(client_r, report, apply=True, folder=folder)
                if 'delete-fails' in modes:
                    check(not removed and (folder / 'state.json').exists(), f'{label}: a failed remove keeps its record')
                else:
                    check(removed and not (folder / 'state.json').exists() and len(state['tuners']) == 1,
                          f'{label}: remove deletes exactly the recorded tuner and proves the settings equal the backup')
            check(not tool.remove(client, report, apply=True, folder=folder / 'nothing'), f'{label}: remove with no record refuses')
            changed = set(fake.changing(state))
            check(changed <= {('POST', '/LiveTv/TunerHosts'), ('DELETE', '/LiveTv/TunerHosts')},
                  f'{label}: only the two tuner requests were sent ({sorted(changed)})')
            check(owner_tuner_untouched(state), f'{label}: the owner\'s own tuner was never touched')
            check(private_ok(report.lines, url, ['/config/chromavision']), f'{label}: nothing private printed')
            check(not state['logouts'], f'{label}: a saved token is never signed out')
    finally:
        server.shutdown()
        server.server_close()


def test_trial(modes, label):
    server, state = fake.start(modes)
    try:
        with tempfile.TemporaryDirectory() as folder:
            client, url = client_for(server, 'trial', Path(folder))
            report = ja.Report(out=lambda s: None)
            tool.trial(client, report, list_url='https://list.invalid/three.m3u', sleep=lambda s: None,
                       wait_channels=1, play_seconds=0.2)
            fails = [t for k, t in report.lines if k == 'FAIL']
            passes = [t for k, t in report.lines if k == 'PASS']
            identical = any('identical to "before"' in t for t in passes)
            if not modes:
                check(not fails and identical and any('plays in the Chromatic format' in t for t in passes),
                      f'{label}: plays, deletes the test tuner, settings identical')
            elif 'delete-fails' in modes:
                check(any('DIFFER' in f for f in fails) and any('manual undo' in t for _, t in report.lines),
                      f'{label}: says so and gives the manual undo')
            else:
                check(bool(fails) and identical and len(state['tuners']) == 1, f'{label}: fails cleanly, settings identical')
            check(not state['open'], f'{label}: no live stream left open')
            allowed = [('POST', r'/LiveTv/TunerHosts'), ('DELETE', r'/LiveTv/TunerHosts'), ('POST', r'/Items/new\d/PlaybackInfo'),
                       ('POST', r'/LiveStreams/Close'), ('DELETE', r'/Videos/ActiveEncodings')]
            check(all(any(m == a and re.fullmatch(p, path) for a, p in allowed) for m, path in fake.changing(state)),
                  f'{label}: only the trial\'s requests were sent')
            check(owner_tuner_untouched(state), f'{label}: the owner\'s own tuner was never touched')
            check(private_ok(report.lines, url, ['list.invalid']), f'{label}: nothing private printed')
            # A request outside the allow-list is refused before it is sent.
            for method, path in (('POST', '/Library/Refresh'), ('DELETE', '/Devices'), ('POST', '/Sessions/Logout/All'),
                                 ('POST', '/System/Restart'), ('DELETE', '/LiveTv/ListingProviders'), ('POST', '/Items/own1/PlaybackInfo')):
                try:
                    client.send(method, path)
                    refused = False
                except ja.ClientError:
                    refused = True
                check(refused and (method, path) not in fake.changing(state), f'{label}: {method} {path} refused unsent')
    finally:
        server.shutdown()
        server.server_close()


def test_typed_sign_in_and_check():
    server, state = fake.start()
    try:
        with tempfile.TemporaryDirectory() as folder:
            client, url = client_for(server, 'check', Path(folder), typed=True)
            report = ja.Report(out=lambda s: None)
            import os
            os.environ['CHROMAVISION_HOME'] = folder
            ok = tool.check(client, report)
            check(ok and not fake.changing(state)[1:], 'check: reads only (after the sign-in)')
            check(client.sign_out_own_session() and state['logouts'] == [fake.OWN_TOKEN],
                  'a typed-in sign-in signs out its own session only')
            check(not client.sign_out_own_session(), 'it signs out at most once')
            check(private_ok(report.lines, url), 'check: nothing private printed')
            check(client.device_id.startswith('chromavision-setup-') and len(client.device_id) > 25,
                  'a fresh device id per run (no other device can be replaced)')
    finally:
        server.shutdown()
        server.server_close()


def test_refresh_guide():
    server, state = fake.start()
    try:
        client, _ = client_for(server, 'refresh-guide', Path('.'))
        report = ja.Report(out=lambda s: None)
        tool.refresh_guide(client, report, sleep=lambda s: None, wait=1)
        check(state['task_runs'] == 1 and fake.changing(state) == [('POST', '/ScheduledTasks/Running/task0guide1')],
              'refresh-guide starts only the Refresh Guide task')
    finally:
        server.shutdown()
        server.server_close()


def test_manager_tuner():
    """A tuner added by Chromatic Manager (older name, its record in Jellymatic's folder) is ours too."""
    import json
    import os
    server, state = fake.start()
    saved = dict(os.environ)
    try:
        with tempfile.TemporaryDirectory() as jm, tempfile.TemporaryDirectory() as cv:
            os.environ['JELLYMATIC_HOME'], os.environ['CHROMAVISION_HOME'] = jm, cv
            state['tuners'].append({'Id': 'mgr1', 'Type': 'm3u', 'Url': '/config/x.m3u', 'FriendlyName': tool.OLDER_NAME})
            client, _ = client_for(server, 'add', None)
            report = ja.Report(out=lambda s: None)
            before = {'TunerHosts': [state['tuners'][0]], 'ListingProviders': state['guides'], 'Other': 1}
            check(not tool.add(client, report, '/config/chromavision/channels.m3u', apply=True) and len(state['tuners']) == 2,
                  'a tuner with the older Manager name is never doubled')
            folder = Path(jm) / 'livetv-backups'
            folder.mkdir()
            (folder / 'before-add-x.json').write_text(json.dumps({'livetv': before, 'fingerprint': {}}), encoding='utf-8')
            (folder / 'state.json').write_text(json.dumps({'tuner_id': 'mgr1', 'backup': 'before-add-x.json'}), encoding='utf-8')
            client_r, _ = client_for(server, 'remove', None)
            removed = tool.remove(client_r, report, apply=True)
            check(removed and [t['Id'] for t in state['tuners']] == ['owner1'] and not (folder / 'state.json').exists(),
                  "Chromatic Manager's recorded tuner is removed by its record, nothing else")
            check(owner_tuner_untouched(state), 'the owner\'s own tuner was never touched (Manager record)')
    finally:
        os.environ.clear()
        os.environ.update(saved)
        server.shutdown()
        server.server_close()


def test_command_line():
    out = io.StringIO()
    with redirect_stdout(out):
        codes = [tool.main(['trial']), tool.main(['trial', '--yes']), tool.main(['refresh-guide']), tool.main(['add']),
                 tool.main(['add', '--list-url', 'http://plain.invalid/x.m3u']),
                 tool.main(['add', '--list-url', 'https://user@x.invalid/x.m3u']),
                 tool.main(['add', '--server-path', '/x.m3u', '--streams', '5'])]
    check(codes == [2] * 7, 'the command line refuses: changes without --yes, a trial without your own filtered list, '
          'bad list addresses, a stream limit above 2')


if __name__ == '__main__':
    import os
    with tempfile.TemporaryDirectory(prefix='chromavision-test-') as home:
        os.environ['CHROMAVISION_HOME'] = home     # never the real private folders
        os.environ['JELLYMATIC_HOME'] = os.path.join(home, 'jellymatic')
        test_add_remove(set(), 'add/remove')
        test_add_remove({'add-refused'}, 'add refused')
        test_add_remove({'delete-fails'}, 'delete fails')
        test_trial(set(), 'trial')
        test_trial({'no-channels'}, 'trial, no channels')
        test_trial({'bad-stream'}, 'trial, wrong format')
        test_trial({'add-refused'}, 'trial, add refused')
        test_trial({'delete-fails'}, 'trial, delete fails')
        test_typed_sign_in_and_check()
        test_refresh_guide()
        test_manager_tuner()
        test_command_line()
    print('PASS' if not failures else f'FAIL: {len(failures)} check(s) failed')
    sys.exit(1 if failures else 0)
