# SPDX-License-Identifier: GPL-3.0-or-later
# Additional terms: ADDITIONAL-TERMS.md
"""A fake Jellyfin server for the tools' tests (127.0.0.1 only, standard library only).

It already holds things that belong to someone else and must never be touched: another tuner, a guide
source, four libraries, other users' devices and sessions. It records every request (method, path, the
token used) so the tests can prove what was and was not sent. Requests it does not know are recorded in
state['unexpected'] and answered 400.

Modes (a set of words): 'add-refused', 'delete-fails', 'no-channels', 'bad-stream', 'not-admin',
'folder-hidden', 'library-add-refused', 'library-delete-fails', 'no-videos', 'live' (PlaybackInfo returns
a live stream id).
"""
from __future__ import annotations

import json
import struct
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SECRETS = ['TOKEN-saved-abc123', 'TEMP-own-session-77', 'Someone Else Tuner', 'http://other-tuner.invalid/channels.m3u',
           'Kitchen TV', 'owner-name', '/srv/private/media', 'family-movies', 'living-room-tv']
SAVED_TOKEN = 'TOKEN-saved-abc123'
OWN_TOKEN = 'TEMP-own-session-77'


def avi(good=True, pictures=30):
    width, height = (160, 90) if good else (1920, 1080)
    avih = b'avih' + struct.pack('<I', 56) + struct.pack('<14I', 66666, 0, 0, 0, 0, 0, 2, 0, width, height, 0, 0, 0, 0)
    video = b'strh' + struct.pack('<I', 8) + b'vids' + (b'MJPG' if good else b'H264')
    audio = (b'strh' + struct.pack('<I', 8) + b'auds\0\0\0\0' + b'strf' + struct.pack('<I', 16) +
             struct.pack('<HHIIHH', 0x11 if good else 0x55, 1, 16000, 8000, 1024, 4))
    frames = b''.join(b'00dc' + struct.pack('<I', 4) + b'\xff\xd8\xff\xd9' for _ in range(pictures))
    body = b'AVI ' + b'LIST' + struct.pack('<I', 4) + b'hdrl' + avih + video + audio + b'LIST' + struct.pack('<I', 4) + b'movi' + frames
    return b'RIFF' + struct.pack('<I', len(body)) + body


def start(modes=()):
    modes = set(modes)
    admin = 'not-admin' not in modes
    user = {'Id': 'a' * 32, 'Name': 'owner-name',
            'Policy': {'IsAdministrator': admin, 'EnableLiveTvAccess': True, 'EnableVideoPlaybackTranscoding': True}}
    state = {
        'tuners': [{'Id': 'owner1', 'Type': 'm3u', 'Url': 'http://other-tuner.invalid/channels.m3u', 'FriendlyName': 'Someone Else Tuner'}],
        'guides': [{'Id': 'g1', 'Type': 'xmltv'}],
        'libraries': [{'Name': 'family-movies', 'ItemId': 'lib1', 'CollectionType': 'movies',
                       'Locations': ['/srv/private/media/movies'], 'LibraryOptions': {'EnableRealtimeMonitor': True}},
                      {'Name': 'Shows', 'ItemId': 'lib2', 'CollectionType': 'tvshows', 'Locations': ['/srv/private/media/tv'],
                       'LibraryOptions': {}, 'RefreshProgress': 12}],
        'folders': {'/config/chromavision': ['channels.m3u'], '/config': ['chromavision', 'ChromaTube'],
                    '/config/ChromaTube': ['Maker Channel', 'Another Channel']},
        'polls': 0, 'open': set(), 'seen': [], 'unexpected': [], 'logouts': [], 'refreshed': [], 'task_runs': 0,
        'library_scans': 0,
    }
    if 'folder-hidden' in modes:
        state['folders'] = {'/config': []}

    def channels():
        items = [{'Id': f'own{i}', 'Name': 'Kitchen TV'} for i in range(10)]
        if len(state['tuners']) > 1 and 'no-channels' not in modes:
            state['polls'] += 1
            if state['polls'] > 2:   # a slow refresh
                items += [{'Id': f'new{i}'} for i in range(3)]
        return {'Items': items, 'TotalRecordCount': len(items)}

    def library_items(parent):
        mine = next((f for f in state['libraries'] if f.get('ItemId') == parent), None)
        if not mine or mine['Name'] != 'ChromaTube' or 'no-videos' in modes:
            return {'Items': [], 'TotalRecordCount': 0}
        items = [{'Id': f'vid{i}', 'Type': 'Episode', 'Name': f'video {i}'} for i in range(3)]
        return {'Items': items, 'TotalRecordCount': len(items)}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, value=None, raw=None):
            body = raw if raw is not None else (json.dumps(value).encode() if value is not None else b'')
            self.send_response(code)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def handle_any(self, method):
            path, _, raw_query = self.path.partition('?')
            query = dict(urllib.parse.parse_qsl(raw_query))
            body = self.rfile.read(int(self.headers.get('Content-Length', 0) or 0))
            token = self.headers.get('X-Emby-Token', '')
            state['seen'].append((method, path, token))
            if path == '/System/Info/Public':
                return self.reply(200, {'Version': '10.11.3'})
            if (method, path) == ('POST', '/Users/AuthenticateByName'):
                return self.reply(200, {'AccessToken': OWN_TOKEN, 'User': user})
            if token not in (SAVED_TOKEN, OWN_TOKEN):
                return self.reply(401)
            if method == 'GET':
                if path == '/Users/Me':
                    return self.reply(200, user)
                if path == '/System/Configuration/livetv':
                    return self.reply(200 if admin else 403, {'TunerHosts': state['tuners'], 'ListingProviders': state['guides'],
                                                              'Other': 1})
                if path == '/LiveTv/Channels':
                    return self.reply(200, channels())
                if path == '/Sessions':
                    return self.reply(200, [{'DeviceId': 'living-room-tv', 'TranscodingInfo': {}}])
                if path.startswith('/Videos/') and path.endswith('/stream.avi'):
                    item = path.split('/')[2]
                    if item.startswith('new') and query.get('liveStreamId') not in state['open']:
                        state['unexpected'].append(('stream without an opened live stream', item))
                        return self.reply(400)
                    return self.reply(200, raw=avi('bad-stream' not in modes))
                if path == '/Environment/DirectoryContents':
                    if not admin:
                        return self.reply(403)
                    names = state['folders'].get(query.get('path', '').rstrip('/'))
                    if names is None:
                        return self.reply(404)
                    return self.reply(200, [{'Name': n, 'Path': query['path'].rstrip('/') + '/' + n,
                                             'Type': 'File' if '.' in n else 'Directory'} for n in names])
                if path == '/Library/VirtualFolders':
                    return self.reply(200, state['libraries'])
                if path == '/Items':
                    return self.reply(200, library_items(query.get('parentId')))
                if path == '/ScheduledTasks':
                    return self.reply(200, [{'Key': 'RefreshGuide', 'Id': 'task0guide1', 'State': 'Idle',
                                             'Triggers': [{'Type': 'IntervalTrigger'}], 'LastExecutionResult': {'Status': 'Completed'}},
                                            {'Key': 'RefreshLibrary', 'Id': 'task0library', 'State': 'Idle', 'Triggers': []}])
                simple = {'/Users': [user, {'Id': 'b' * 32}], '/Devices': {'Items': [{'Id': 'living-room-tv'}, {'Id': 'phone'}]},
                          '/Plugins': [{'Id': 'p1', 'Version': '1', 'Status': 'Active'}],
                          '/System/Configuration/encoding': {'HardwareAccelerationType': 'none'}}
                return self.reply(200, simple[path]) if path in simple else self.reply(404)
            if (method, path) == ('POST', '/Sessions/Logout'):
                state['logouts'].append(token)
                return self.reply(204)
            if (method, path) == ('POST', '/LiveTv/TunerHosts'):
                if 'add-refused' in modes:
                    return self.reply(500)
                info = dict(json.loads(body), Id=f'test{len(state["tuners"])}')
                state['tuners'].append(info)
                return self.reply(200, info)
            if (method, path) == ('DELETE', '/LiveTv/TunerHosts'):
                if query.get('id') == 'owner1':
                    state['unexpected'].append(('DELETE owner tuner',))
                    return self.reply(400)
                if 'delete-fails' in modes:
                    return self.reply(500)
                state['tuners'] = [t for t in state['tuners'] if t['Id'] != query.get('id')]
                return self.reply(204)
            if method == 'POST' and path == '/ScheduledTasks/Running/task0guide1':
                state['task_runs'] += 1
                return self.reply(204)
            if method == 'POST' and path.endswith('/PlaybackInfo'):
                item = path.split('/')[2]
                source = {'Id': 'src-' + item}
                if item.startswith('new') or 'live' in modes:
                    state['open'].add('live1')
                    source['LiveStreamId'] = 'live1'
                return self.reply(200, {'MediaSources': [source]})
            if (method, path) == ('POST', '/LiveStreams/Close'):
                state['open'].discard(query.get('liveStreamId'))
                return self.reply(204)
            if (method, path) == ('DELETE', '/Videos/ActiveEncodings'):
                return self.reply(204)
            if (method, path) == ('POST', '/Library/VirtualFolders'):
                if 'library-add-refused' in modes:
                    return self.reply(500)
                options = json.loads(body or b'{}').get('LibraryOptions') or {}
                paths = [p.get('Path') for p in options.get('PathInfos') or []]
                state['libraries'].append({'Name': query.get('name'), 'ItemId': 'lib-new', 'CollectionType': query.get('collectionType'),
                                           'Locations': paths, 'LibraryOptions': options})
                if query.get('refreshLibrary') == 'true':
                    state['library_scans'] += 1
                return self.reply(204)
            if (method, path) == ('DELETE', '/Library/VirtualFolders'):
                if 'library-delete-fails' in modes:
                    return self.reply(500)
                state['libraries'] = [f for f in state['libraries'] if f['Name'] != query.get('name')]
                return self.reply(204)
            if method == 'POST' and path.startswith('/Items/') and path.endswith('/Refresh'):
                state['refreshed'].append(path.split('/')[2])
                return self.reply(204)
            state['unexpected'].append((method, path))
            return self.reply(400)

        def do_GET(self):
            self.handle_any('GET')

        def do_POST(self):
            self.handle_any('POST')

        def do_DELETE(self):
            self.handle_any('DELETE')

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, state


def changing(state):
    """Every request that was not a read, without the token."""
    return [(m, p) for m, p, _ in state['seen'] if m != 'GET']
