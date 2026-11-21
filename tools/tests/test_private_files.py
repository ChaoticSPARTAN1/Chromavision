# SPDX-License-Identifier: GPL-3.0-or-later
# Additional terms: ADDITIONAL-TERMS.md
"""Backups and records are written whole and readable by the user only: the folder 0700 and the file 0600 on
macOS/Linux (checked by recording the permission calls, so the test also runs on Windows), and a written file reads
back. Standard library only.

    py -3 tools/tests/test_private_files.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jellyfin_admin as ja  # noqa: E402

failures = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok:
        failures.append(what)


def main():
    calls = []
    saved = ja.POSIX, ja._chmod
    try:
        ja.POSIX = True
        ja._chmod = lambda path, mode: calls.append((Path(path).name, mode))
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'backups' / 'before-add-x.json'
            ja.save_private(target, {'livetv': {'TunerHosts': []}})
            check(json.loads(target.read_text(encoding='utf-8')) == {'livetv': {'TunerHosts': []}}, 'the backup reads back')
            check(('backups', 0o700) in calls, 'the backup folder is made user-only (0700) on macOS/Linux')
            check(('before-add-x.json.tmp', 0o600) in calls, 'the backup file is made user-only (0600) before it is put in place')
            check(not (target.parent / 'before-add-x.json.tmp').exists(), 'no temporary file is left behind')
            if os.name != 'nt':
                ja.POSIX, ja._chmod = saved
                ja.save_private(target, {'again': 1})
                check((target.stat().st_mode & 0o777) == 0o600 and (target.parent.stat().st_mode & 0o777) == 0o700,
                      'real permissions on this system: 0600 file, 0700 folder')
    finally:
        ja.POSIX, ja._chmod = saved
    print('PASS' if not failures else f'FAIL: {len(failures)} check(s) failed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
