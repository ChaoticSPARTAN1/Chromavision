# SPDX-License-Identifier: GPL-3.0-or-later
# Additional terms: ADDITIONAL-TERMS.md
"""A small, careful Jellyfin client for the PC set-up tools (Python standard library only).

The same file is used by Chromavision and ChromaTube. What it guarantees:

- **Allow-listed changes.** GET requests are free. Every other request must match the calling tool's
  allow-list (method, path pattern and, where given, a check of the query and body), or it is refused
  before anything is sent. The only exceptions are this run's own sign-in and the sign-out of this run's
  own session.
- **Your other devices are never signed out.** A typed-in sign-in uses a new device id made for this
  run, so it cannot replace the token of any other device. At the end the tool signs out that one
  session (POST /Sessions/Logout with its own token). It never uses user-wide sign-outs, device
  deletion or API-key calls.
- **Nothing private is printed.** Messages never contain a server address, user name, token, path or
  id. Passwords are read with getpass, kept in memory for one run and never saved, logged or put on a
  command line.
- **No surprises on the wire.** No proxy is taken from the environment and redirects are refused, so a
  token can only ever go to the address you configured.

Where your own files go (never inside the repository): see private_home().
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from getpass import getpass
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit

SIGN_IN = '/Users/AuthenticateByName'
SIGN_OUT = '/Sessions/Logout'


# ---------------------------------------------------------------- your own files
def private_home(app: str) -> Path:
    """The per-user folder for this tool's backups and state: %LOCALAPPDATA%\\<app> on Windows,
    $XDG_DATA_HOME/<app> (usually ~/.local/share/<app>) elsewhere; <APP>_HOME overrides it."""
    override = os.environ.get(app.upper() + '_HOME')
    if override:
        return Path(override)
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local') / app
    return Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share') / app.lower()


def utc_stamp() -> str:
    return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())


POSIX = os.name != 'nt'
_chmod = os.chmod


def private_dir(folder: Path) -> Path:
    """Create a folder only you can open (0700 on macOS/Linux; %LOCALAPPDATA% is per-user on Windows)."""
    folder.mkdir(parents=True, exist_ok=True)
    if POSIX:
        _chmod(folder, 0o700)
    return folder


def save_private(path: Path, value) -> None:
    """Write JSON whole or not at all (temporary file, then rename), readable by you only (0600 on macOS/Linux):
    backups can hold server paths, tuner addresses and a guide provider's sign-in."""
    private_dir(path.parent)
    temporary = path.with_name(path.name + '.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        handle.write(json.dumps(value, indent=1, sort_keys=True))
    if POSIX:
        _chmod(temporary, 0o600)
    os.replace(temporary, path)


def inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- connection settings
@dataclass(frozen=True)
class Connection:
    server_url: str = field(repr=False)
    username: str = field(default='', repr=False)
    password: str = field(default='', repr=False)
    access_token: str = field(default='', repr=False)


def validate(values: dict) -> Connection:
    if set(values) - {'server_url', 'username', 'password', 'access_token'}:
        raise ValueError('Unknown connection setting; use the keys of jellyfin-connection.example.txt.')
    url = values.get('server_url', '').strip().rstrip('/')
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme in ('http', 'https') and bool(parsed.hostname) and not parsed.username
                 and not parsed.password and not parsed.query and not parsed.fragment)
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            valid = False
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('The server address must be http:// or https:// with no user name, query or fragment in it.')
    username, password, token = values.get('username', ''), values.get('password', ''), values.get('access_token', '')
    if not token and not username:
        raise ValueError('Give a user name or an access token.')
    if token and (username or password):
        raise ValueError('Use either an access token or a user name and password, not both.')
    return Connection(url, username, password, token)


def load_connection(path: Path) -> Connection:
    """key=value lines (server_url, then username + password or access_token); '#' starts a comment line."""
    values = {}
    for number, line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, separator, value = line.partition('=')
        key = key.strip().lower()
        if not separator or key in values:
            raise ValueError(f'Malformed or repeated setting on line {number}.')
        values[key] = value
    return validate(values)


def connection_files(app: str, explicit=None):
    """Where a saved connection is looked for, in order: --connection, this tool's folder, Jellymatic's."""
    if explicit:
        return [Path(explicit)]
    return [private_home(app) / 'jellyfin-connection.txt', private_home('Jellymatic') / 'jellyfin-connection.txt']


def find_connection(app: str, explicit=None):
    for path in connection_files(app, explicit):
        if path.is_file():
            return load_connection(path)
    return None


def ask_connection(saved=None) -> Connection:
    """An administrator sign-in for this one run: typed, kept in memory, never saved."""
    url = saved.server_url if saved else input('Jellyfin server address (for example http://your-server:8096): ').strip()
    user = input('Jellyfin administrator user name: ').strip()
    return validate({'server_url': url, 'username': user, 'password': getpass('Password (not shown, not saved): ')})


# ---------------------------------------------------------------- the client
class ClientError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ClientError('The server redirected a request. Use its final address in your settings.')


def item_id(value) -> str:
    value = str(value or '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value):
        raise ClientError('Unexpected item identifier from the server.')
    return value


class Client:
    """allowed: list of (method, path regex) or (method, path regex, check(query, payload) -> bool)."""

    def __init__(self, connection: Connection, app: str, allowed=(), opener=None):
        self._connection = connection
        self._token = connection.access_token
        self._own_session = False
        self.app = app
        self.user_id = ''
        self.policy = {}
        self.allowed = [tuple(rule) + ((None,) if len(rule) == 2 else ()) for rule in allowed]
        self.device_id = f'{app.lower()}-setup-{secrets.token_hex(8)}'
        self._http = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirects())

    # -- plumbing
    def _headers(self, extra=None):
        headers = {'Accept': 'application/json',
                   'Authorization': f'MediaBrowser Client="{self.app} setup tools", Device="PC", '
                                    f'DeviceId="{self.device_id}", Version="1.0.0"'}
        if self._token:
            headers['X-Emby-Token'] = self._token
        headers.update(extra or {})
        return headers

    def permitted(self, method, path, query=None, payload=None):
        if method == 'GET':
            return True
        if method == 'POST' and path == SIGN_IN and not self._token:
            return True
        for rule_method, pattern, check in self.allowed:
            if rule_method == method and re.fullmatch(pattern, path) and (check is None or check(query or {}, payload)):
                return True
        return False

    def open(self, method, path, query=None, payload=None, headers=None, timeout=30):
        if not path.startswith('/') or path.startswith('//'):
            raise ClientError('Invalid API path.')
        if not self.permitted(method, path, query, payload):
            raise ClientError('Refusing a request this tool is not allowed to send.')
        url = self._connection.server_url + path + ('?' + urllib.parse.urlencode(query) if query else '')
        data = None
        extra = dict(headers or {})
        if payload is not None:
            data = json.dumps(payload).encode('utf-8')
            extra['Content-Type'] = 'application/json'
        elif method == 'POST':
            data = b''
        request = urllib.request.Request(url, data=data, headers=self._headers(extra), method=method)
        try:
            return self._http.open(request, timeout=timeout)
        except ClientError:
            raise
        except urllib.error.HTTPError as error:
            error.close()
            raise ClientError(f'The server refused the request (HTTP {error.code}).', error.code) from None
        except (OSError, ValueError):
            raise ClientError('The server could not be reached.') from None

    def json(self, path, query=None):
        with self.open('GET', path, query) as response:
            try:
                return json.load(response)
            except (ValueError, OSError):
                raise ClientError('The server sent a reply that is not JSON.') from None

    def send(self, method, path, query=None, payload=None, timeout=60):
        """One allow-listed change. Returns the parsed reply, or None when it has no JSON body."""
        with self.open(method, path, query, payload, timeout=timeout) as response:
            body = response.read(8 * 1024 * 1024)
        try:
            return json.loads(body) if body.strip() else None
        except ValueError:
            return None

    # -- sign-in and sign-out of this run's own session only
    def connect(self):
        if self._token:
            user = self.json('/Users/Me')
        else:
            with self.open('POST', SIGN_IN, payload={'Username': self._connection.username,
                                                       'Pw': self._connection.password}) as response:
                result = json.load(response)
            self._token = str(result.get('AccessToken') or '')
            self._own_session = bool(self._token)
            user = result.get('User') or {}
        self.user_id = item_id(user.get('Id'))
        self.policy = user.get('Policy') or {}
        if not self._token:
            raise ClientError('The server did not return a sign-in.')

    @property
    def is_admin(self):
        return bool(self.policy.get('IsAdministrator'))

    def sign_out_own_session(self):
        """Signs out only the session this run created by typing a password. Never raises."""
        if not (self._own_session and self._token):
            return False
        try:
            request = urllib.request.Request(self._connection.server_url + SIGN_OUT, data=b'',
                                             headers=self._headers(), method='POST')
            self._http.open(request, timeout=15).close()
            return True
        except (urllib.error.HTTPError, OSError, ValueError, ClientError):
            return False
        finally:
            self._token, self._own_session = '', False


# ---------------------------------------------------------------- reading and comparing
def read(client: Client, path, query=None):
    """(value, status): status is 'ok', 'denied', 'missing' or 'failed'. Never raises."""
    try:
        return client.json(path, query), 'ok'
    except ClientError as error:
        return None, {401: 'denied', 403: 'denied', 404: 'missing'}.get(error.status, 'failed')


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def fingerprint(client: Client):
    """What a set-up step must never change: libraries, users, devices, plugins, task triggers and the
    conversion (encoding) settings. Values that change by themselves (last-seen times, run times,
    scan progress) are left out. Returns (fingerprint, short readable counts)."""
    result, shown = {}, []
    for name, path in (('libraries', '/Library/VirtualFolders'), ('users', '/Users'), ('devices', '/Devices'),
                       ('plugins', '/Plugins'), ('tasks', '/ScheduledTasks'),
                       ('encoding', '/System/Configuration/encoding')):
        value, status = read(client, path)
        if status != 'ok':
            result[name] = {'status': status}
            shown.append(f'{name} not readable')
            continue
        if name == 'libraries':
            value = sorted(canonical({k: v for k, v in f.items() if k not in ('RefreshStatus', 'RefreshProgress')}).decode()
                           for f in value)
        elif name == 'users':
            value = sorted(str(u.get('Id', '')) for u in value)
        elif name == 'devices':
            value = sorted(str(d.get('Id', '')) for d in (value.get('Items') or []))
        elif name == 'tasks':
            value = sorted((str(t.get('Key', '')), canonical(t.get('Triggers')).decode()) for t in value)
        elif name == 'plugins':
            value = sorted((str(p.get('Id', '')), str(p.get('Version', '')), str(p.get('Status', ''))) for p in value)
        result[name] = {'status': 'ok', 'sha256': hashlib.sha256(canonical(value)).hexdigest(),
                        'count': len(value) if isinstance(value, list) else None}
        if isinstance(value, list):
            shown.append(f'{name} {len(value)}')
    return result, shown


def server_version(client: Client):
    public, status = read(client, '/System/Info/Public')
    if status != 'ok' or not isinstance(public, dict):
        return None
    return tuple(int(p) for p in str(public.get('Version', '')).split('.')[:2] if p.isdigit())


def same_path(a: str, b: str) -> bool:
    return normal_path(a) == normal_path(b)


def normal_path(text: str):
    text = str(text or '')
    if re.match(r'^[A-Za-z]:[\\/]', text) or '\\' in text:
        return tuple(p.lower() for p in PureWindowsPath(text).parts)
    return PurePosixPath(text).parts


def path_within(child: str, parent: str) -> bool:
    c, p = normal_path(child), normal_path(parent)
    return len(c) >= len(p) and c[:len(p)] == p


def server_sees_file(client: Client, server_path: str):
    """Read-only: does the server list this file in its folder? (administrator; yes / no / unknown)."""
    parent = str(PureWindowsPath(server_path).parent if '\\' in server_path else PurePosixPath(server_path).parent)
    name = PureWindowsPath(server_path).name if '\\' in server_path else PurePosixPath(server_path).name
    entries, status = read(client, '/Environment/DirectoryContents',
                           {'path': parent, 'includeFiles': 'true', 'includeDirectories': 'false'})
    if status != 'ok' or not isinstance(entries, list):
        return 'unknown'
    return 'yes' if any(e.get('Name') == name for e in entries) else 'no'


def server_folder_entries(client: Client, server_path: str):
    """Read-only: the entries the server lists in a folder, or None when it cannot list it."""
    entries, status = read(client, '/Environment/DirectoryContents',
                           {'path': server_path, 'includeFiles': 'true', 'includeDirectories': 'true'})
    return entries if status == 'ok' and isinstance(entries, list) else None


# ---------------------------------------------------------------- the Chromatic's stream format
CHROMATIC_PROFILE = {'Name': 'Chromatic check', 'MaxStreamingBitrate': 500000, 'DirectPlayProfiles': [],
                     'TranscodingProfiles': [{'Container': 'avi', 'Type': 'Video', 'VideoCodec': 'mjpeg',
                                              'AudioCodec': 'adpcm_ima_wav', 'Protocol': 'http',
                                              'Context': 'Streaming'}]}

PLAYBACK_RULES = [('POST', r'/Items/[A-Za-z0-9_-]{1,80}/PlaybackInfo'), ('POST', r'/LiveStreams/Close'),
                  ('DELETE', r'/Videos/ActiveEncodings')]


def judge_avi(data: bytes):
    """(ok, facts) for the first bytes of a stream: AVI, MJPEG <= 160x120, IMA ADPCM 16 kHz."""
    facts = {'bytes': len(data)}
    if data[:4] != b'RIFF' or data[8:12] != b'AVI ':
        return False, facts
    at = data.find(b'avih')
    if at >= 0 and len(data) >= at + 48:
        facts['width'], facts['height'] = struct.unpack_from('<II', data, at + 8 + 32)
    head = data[:data.find(b'movi')] if b'movi' in data else data[:8192]
    facts['mjpeg'] = b'MJPG' in head or b'mjpg' in head
    audio = head.find(b'auds')
    strf = head.find(b'strf', audio) if audio >= 0 else -1
    if strf >= 0 and len(head) >= strf + 16:
        tag, channels, rate = struct.unpack_from('<HHI', head, strf + 8)
        facts.update(audio_tag=tag, audio_channels=channels, audio_rate=rate)
    facts['pictures'] = len(re.findall(rb'\d\ddc....\xff\xd8', data, re.S))
    ok = (facts.get('mjpeg') and 0 < facts.get('width', 0) <= 160 and 0 < facts.get('height', 0) <= 120
          and facts.get('audio_tag') == 0x11 and facts.get('audio_rate') == 16000 and facts['pictures'] > 0)
    return bool(ok), facts


def play_like_the_console(client: Client, item: str, line, seconds=12.0, bitrate=500000, first_limit=15.0,
                          give_up=60.0):
    """Opens one item the way the Chromatic's TV and ChromaTube modes do (PlaybackInfo first, then
    stream.avi), reads `seconds` of it, then stops this run's own conversion and closes the live stream
    if one was opened. Prints counts only. Returns True when the stream is in the Chromatic's format and
    the first data came within first_limit seconds."""
    item = item_id(item)
    session = secrets.token_hex(16)
    live = None
    try:
        info = client.send('POST', f'/Items/{item}/PlaybackInfo', {'userId': client.user_id}, {
            'UserId': client.user_id, 'AutoOpenLiveStream': True, 'EnableDirectPlay': False,
            'EnableDirectStream': False, 'EnableTranscoding': True, 'MaxStreamingBitrate': bitrate,
            'DeviceProfile': dict(CHROMATIC_PROFILE, MaxStreamingBitrate=bitrate)})
        source = ((info or {}).get('MediaSources') or [{}])[0]
        live = source.get('LiveStreamId')
        query = {'mediaSourceId': source.get('Id') or item, 'playSessionId': session, 'deviceId': client.device_id,
                 'videoCodec': 'mjpeg', 'audioCodec': 'adpcm_ima_wav', 'audioChannels': 1, 'audioSampleRate': 16000,
                 'maxWidth': 160, 'maxHeight': 120, 'maxFramerate': 15, 'videoBitRate': bitrate}
        if live:
            query['liveStreamId'] = live
        data, started, first = b'', time.monotonic(), None
        with client.open('GET', f'/Videos/{item}/stream.avi', query, headers={'Accept': '*/*'}, timeout=give_up) as stream:
            while len(data) < 8_000_000:
                now = time.monotonic()
                if first is None and now - started > give_up:
                    break
                if first is not None and now - first > seconds:
                    break
                block = stream.read(32768)
                if not block:
                    break
                if first is None:
                    first = time.monotonic()
                data += block
        ok, facts = judge_avi(data)
        took = max(time.monotonic() - (first or started), 0.1)
        wait = f'{first - started:.1f} s' if first else 'never'
        line('INFO', f'first data after {wait}; {facts["bytes"] // 1024} KB in {took:.0f} s; picture '
                     f'{facts.get("width", "?")}x{facts.get("height", "?")}; {facts.get("pictures", 0)} pictures; '
                     f'sound {facts.get("audio_rate", "none")} Hz')
        return bool(ok and first is not None and first - started <= first_limit)
    except ClientError:
        return False
    finally:
        for method, path, query in (('DELETE', '/Videos/ActiveEncodings', {'deviceId': client.device_id, 'playSessionId': session}),
                                    ('POST', '/LiveStreams/Close', {'liveStreamId': live} if live else None)):
            if query:
                try:
                    client.send(method, path, query)
                except ClientError:
                    pass


# ---------------------------------------------------------------- printing
class Report:
    """Collects PASS / FAIL / INFO lines (generic wording only) and prints them."""

    def __init__(self, out=print):
        self.lines, self._out = [], out

    def __call__(self, kind, text):
        self.lines.append((kind, text))
        self._out(f'{kind:4} {text}')

    @property
    def failed(self):
        return any(kind == 'FAIL' for kind, _ in self.lines)


def open_client(app, args, allowed, report):
    """Signs in for one run. --ask-admin: type an administrator sign-in now (memory only). Otherwise the
    saved connection file. Returns a connected Client, or None after a FAIL line."""
    try:
        saved = find_connection(app, getattr(args, 'connection', None))
    except (OSError, ValueError):
        report('FAIL', 'the saved Jellyfin settings could not be read (see jellyfin-connection.example.txt)')
        return None
    try:
        connection = ask_connection(saved) if getattr(args, 'ask_admin', False) else saved
    except (EOFError, KeyboardInterrupt, ValueError) as error:
        report('FAIL', str(error) if isinstance(error, ValueError) else 'no sign-in typed; nothing was changed')
        return None
    if connection is None:
        report('FAIL', 'no saved Jellyfin settings found; use --ask-admin to type an administrator sign-in for this run')
        return None
    client = Client(connection, app, allowed)
    try:
        client.connect()
    except ClientError:
        report('FAIL', 'the Jellyfin sign-in was not accepted; nothing was changed')
        return None
    return client
