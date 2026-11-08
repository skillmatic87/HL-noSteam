#!/usr/bin/env python3
"""Interactive Linux console recorder shared by the panel and all launchers."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

ACTIVE = 'CS15_RECORDING_ACTIVE'
COMMAND = 'CS15_RECORDED_COMMAND'
MARKER = '# cs15-console-recording-v1'


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def private_directory(path):
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise ValueError(f'Console directory is not a regular directory: {path}')
    path.mkdir(mode=0o700, exist_ok=True)
    path.chmod(0o700)


def new_log_file(server):
    directory = server / 'logs'
    private_directory(directory)
    directory = directory / 'console'
    private_directory(directory)
    name = datetime.now(timezone.utc).strftime('cs15-console-%Y%m%d-%H%M%S-') + secrets.token_hex(4) + '.log'
    path = directory / name
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    return path


def append_record(log, message):
    if log.is_symlink() or not log.is_file():
        raise ValueError(f'Console log is not a regular file: {log}')
    descriptor = os.open(log, os.O_WRONLY | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'ab') as output:
        output.write(message.encode('utf-8'))
        output.flush()
        os.fsync(output.fileno())


def replace_file(path, data, mode):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f'Recording helper destination is not a regular file: {path}')
    descriptor, temporary = tempfile.mkstemp(prefix='.cs15-recorder-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def recording_preamble():
    return (MARKER + '\n'
        'if [[ "${CS15_RECORDING_ACTIVE:-}" != 1 ]]; then\n'
        '    exec python3 "$PWD/run_logged_server.py" '
        '--server "$PWD" -- bash "$PWD/${BASH_SOURCE[0]##*/}" "$@"\n'
        'fi\n')


def ensure_launcher_logging(server, launcher):
    """Back up and upgrade only the launcher/helper, never game configuration."""
    if launcher.parent != server or launcher.is_symlink() or not launcher.is_file():
        raise ValueError('The installed launcher must be a regular file inside the server folder.')
    original = launcher.read_bytes()
    text = original.decode('utf-8-sig')
    if len(re.findall(r'^\s*exec\s+\./hlds\s+.*$', text, re.M)) != 1:
        raise ValueError('The installed launcher needs exactly one supported exec ./hlds line.')
    # Insert before the legacy library export: Python must not load server libraries.
    insertion = re.search(r'^export LD_LIBRARY_PATH=.*$|^\s*exec\s+\./hlds\s+.*$', text, re.M)
    if MARKER not in text:
        text = text[:insertion.start()] + recording_preamble() + text[insertion.start():]
    helper = server / 'run_logged_server.py'
    if helper.is_symlink() or (helper.exists() and not helper.is_file()):
        raise ValueError('The installed recording helper must be a regular file.')
    source = Path(__file__).read_bytes()
    updated = text.encode('utf-8')
    changes = [(launcher, updated, original, stat.S_IMODE(launcher.stat().st_mode))]
    old_helper = helper.read_bytes() if helper.exists() else None
    changes.append((helper, source, old_helper, 0o700))
    changes = [item for item in changes if item[1] != item[2]]
    if not changes:
        return
    directory = server / '_configurator'
    private_directory(directory)
    directory = directory / 'recording-backups'
    private_directory(directory)
    backup = directory / (datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-') + secrets.token_hex(4))
    private_directory(backup)
    for target, data, old, mode in changes:
        if old is not None:
            replace_file(backup / target.name, old, mode)
    # Install the helper first. A killed migration leaves either the old launcher
    # or a launcher whose helper is already present; repeating this is safe.
    changes.sort(key=lambda item: item[0] == launcher)
    applied = []
    try:
        for target, data, old, mode in changes:
            replace_file(target, data, mode)
            applied.append((target, old, mode))
    except BaseException:
        for target, old, mode in reversed(applied):
            if old is None:
                target.unlink(missing_ok=True)
            else:
                replace_file(target, old, mode)
        raise


def run_recorded(server, command, log=None):
    recorder = shutil.which('script')
    if not recorder:
        raise ValueError('Console recording requires util-linux: sudo apt install util-linux')
    if not command:
        raise ValueError('No server command supplied.')
    log = log or new_log_file(server)
    if log.parent != server / 'logs' / 'console' or log.is_symlink() or not log.is_file():
        raise ValueError('The console log must be a regular file in this server\'s logs/console folder.')
    append_record(log, f'\nCS15_SESSION_START time={stamp()}\n')
    print(f'Console recording: {log}', flush=True)
    environment = os.environ.copy()
    environment['SHELL'] = '/bin/sh'
    environment[COMMAND] = json.dumps(command)
    # Keep arguments out of script's COMMAND header (they can contain passwords).
    child = 'exec ' + shlex.join([sys.executable, str(Path(__file__).resolve()), '--child'])
    arguments = [recorder, '-q', '-f', '-e', '-a', '-c', child, str(log)]
    received = []
    previous = {}
    process = None
    def forward(number, frame):
        received.append(number)
        if process is not None and process.poll() is None:
            process.send_signal(number)
    try:
        for number in (signal.SIGTERM, signal.SIGINT, getattr(signal, 'SIGHUP', signal.SIGTERM)):
            if number not in previous:
                previous[number] = signal.signal(number, forward)
        # Inherit the visible terminal. No PIPEs or separate process group here.
        process = subprocess.Popen(arguments, cwd=server, env=environment)
        if received and process.poll() is None:
            process.send_signal(received[-1])
        code = process.wait()
        status = 128 - code if code < 0 else code
        if received and status == 0:
            status = 128 + received[-1]
        append_record(log, f'\nCS15_SESSION_END time={stamp()} exit_code={status}' +
                      (f' signal={received[-1]}' if received else '') + '\n')
        print(f'Server stopped: exit_code={status}; log: {log}', flush=True)
        return status
    except OSError as error:
        append_record(log, f'\nCS15_RECORDER_ERROR time={stamp()} {error}\n')
        raise
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def main():
    if sys.argv[1:] == ['--child']:
        command = json.loads(os.environ.pop(COMMAND))
        if not isinstance(command, list) or not command or not all(isinstance(a, str) for a in command):
            raise ValueError('Invalid recorded server command.')
        os.environ[ACTIVE] = '1'
        os.environ['LD_LIBRARY_PATH'] = str(Path.cwd()) + (
            ':' + os.environ['LD_LIBRARY_PATH'] if os.environ.get('LD_LIBRARY_PATH') else '')
        os.execvpe(command[0], command, os.environ)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', required=True, type=Path)
    parser.add_argument('--log-file', type=Path)
    parser.add_argument('--launcher', type=Path, help='Back up and enable recording for this installed launcher')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    server = args.server.expanduser().resolve()
    if not server.is_dir() or (server / '.install-incomplete').exists():
        raise ValueError('Server folder is missing or installation is incomplete.')
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if args.launcher:
        launcher = args.launcher.expanduser().resolve()
        ensure_launcher_logging(server, launcher)
        command = ['bash', str(launcher), *command]
    return run_recorded(server, command, args.log_file)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(f'Server recording failed: {error}', file=sys.stderr)
        sys.exit(1)
