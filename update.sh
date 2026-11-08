#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null || ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo 'Python 3.10 or newer is required: sudo apt install python3' >&2
    exit 1
fi
exec python3 - "$project_dir" "$@" <<'CS15_UPDATE_PYTHON'
"""Standalone updater for ZIP-extracted Linux packages (Python standard library)."""
import argparse
import datetime
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import urllib.request
import uuid
import zipfile

REPOSITORY = 'skillmatic87/HL-noSteam'
BRANCH = 'linux-mint-server'
STATE = '.package-update.json'
JOURNAL = '.update-active.json'
ROOT_FILES = frozenset({'.gitattributes', '.gitignore', 'readme.md', 'start-here.txt',
    'setup.cmd', 'setup-linux.sh', 'start-server.cmd', 'start-server.sh',
    'start-panel.cmd', 'start-panel.sh', 'configure-server.html',
    'update-content.cmd', 'update.sh', 'version'})
# Exact, previously maintained paths only. These names remain case-sensitive
# migration/recovery data; never lowercase this list or scan arbitrary files.
LEGACY_NAMES = frozenset({
    'Configure-Server.html', 'README.md', 'START-HERE.txt', 'Setup-Linux.sh',
    'Setup.cmd', 'Start-Panel.cmd', 'Start-Panel.sh', 'Start-Server.cmd',
    'Start-Server.sh', 'Update-Content.cmd', 'Update.sh', 'VERSION',
    'content/Listen.html', 'content/SOURCES.md',
    'docs/CLIENT.md', 'docs/CONFIGURATOR.md', 'docs/CONTENT.md', 'docs/DELIVERY.md',
    'docs/INSTALL.md', 'docs/LINUX-MINT.md', 'docs/OPEN-QUESTIONS.md', 'docs/PLAN.md',
    'docs/RELEASE-NOTES.md', 'docs/SETUP.md', 'docs/SOURCES.md', 'docs/TESTING.md',
    'docs/UPDATING.md', 'scripts/CS15Client.Common.ps1',
    'scripts/CS15Content.Common.ps1', 'scripts/CS15Setup.Common.ps1',
    'scripts/Configure-CS15Server.ps1', 'scripts/Get-CS15Components.ps1',
    'scripts/Get-CS15DisplayModes.ps1', 'scripts/Get-CS15LANAddress.ps1',
    'scripts/Get-CS15ServerStatus.ps1', 'scripts/Get-HalfLifeInventory.ps1',
    'scripts/Install-CS15Server.ps1', 'scripts/Invoke-CS15TestCommand.ps1',
    'scripts/New-CS15SoundPreview.ps1', 'scripts/Prepare-CS15PluginTest.ps1',
    'scripts/Read-CS15SetupInput.ps1', 'scripts/Read-CS15SetupSettings.ps1',
    'scripts/Restore-CS15Content.ps1', 'scripts/Start-CS15Client.ps1',
    'scripts/Start-CS15Panel.ps1', 'scripts/Start-CS15Server.ps1',
    'scripts/Test-CS15ClientSettings.ps1', 'scripts/Test-CS15Content.ps1',
    'scripts/Test-CS15LANAddress.ps1', 'scripts/Test-CS15PreparedSetup.ps1',
    'scripts/Test-CS15ServerNames.ps1', 'scripts/Test-CS15SetupInput.ps1',
    'scripts/Test-CS15SetupWizard.ps1', 'scripts/Update-CS15Content.ps1',
})
LEGACY_RENAMES = {name: name.lower() for name in LEGACY_NAMES}
REQUIRED = frozenset({'update.sh', 'version', 'setup-linux.sh', 'start-panel.sh',
    'scripts/server_panel.py', 'scripts/install_cs15_linux.py', 'content/pack.json'})
MAX_DOWNLOAD = 64 * 1024 * 1024
MAX_UNPACKED = 256 * 1024 * 1024


def request_bytes(url, limit):
    request = urllib.request.Request(url, headers={'User-Agent': 'CS15-Package-Updater/1.0',
        'Accept': 'application/vnd.github+json' if 'api.github.com/' in url else '*/*'})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Download exceeds the package size limit.')
    return data


def latest_commit():
    result = json.loads(request_bytes(
        f'https://api.github.com/repos/{REPOSITORY}/commits/{BRANCH}', 2 * 1024 * 1024))
    commit = result.get('sha', '')
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('GitHub returned an invalid commit ID.')
    return commit


def managed(name):
    parts = PurePosixPath(name).parts
    if any(part in {'.git', '_configurator', 'backups', 'logs', 'downloads', 'runtime'} or
           '.local.' in part or part in {'server.cfg', 'users.ini', 'csadmin.cfg'}
           for part in parts):
        return False
    return name in ROOT_FILES or name in LEGACY_RENAMES or (len(parts) > 1 and parts[0] in {'scripts', 'docs', 'content'})


def read_snapshot(data, commit):
    prefix = f'HL-noSteam-{commit}'
    files = {}
    seen = set()
    directories = set()
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if len(archive.infolist()) > 10000:
            raise ValueError('Too many archive entries.')
        for member in archive.infolist():
            # ZipInfo.filename can normalize backslashes on a Windows test host.
            # Validate the original name, including any NULs, on every platform.
            name = member.orig_filename
            parts = name.rstrip('/').split('/')
            if ('\\' in name or ':' in name or '\x00' in name or
                    any(p in {'', '.', '..'} for p in parts) or parts[0] != prefix):
                raise ValueError(f'Unsafe archive path: {name!r}')
            kind = stat.S_IFMT(member.external_attr >> 16)
            if kind not in (0, stat.S_IFDIR if member.is_dir() else stat.S_IFREG):
                raise ValueError(f'Unsupported archive entry: {name!r}')
            if member.flag_bits & 1:
                raise ValueError('Encrypted archive entries are not supported.')
            relative = '/'.join(parts[1:])
            key = relative.casefold()
            if any('/'.join(parts[1:i]).casefold() in seen for i in range(2, len(parts))):
                raise ValueError(f'Archive file/directory conflict: {name!r}')
            if member.is_dir():
                if key in seen:
                    raise ValueError(f'Archive file/directory conflict: {name!r}')
                directories.add(key)
                continue
            if not relative or key in seen or key in directories:
                raise ValueError(f'Duplicate archive path: {name!r}')
            seen.add(key)
            directories.update('/'.join(parts[1:i]).casefold() for i in range(2, len(parts)))
            total += member.file_size
            if total > MAX_UNPACKED:
                raise ValueError('Unpacked package exceeds the size limit.')
            if managed(relative):
                if relative != relative.lower():
                    raise ValueError(f'Package filenames must be lowercase: {relative}')
                files[relative] = archive.read(member)
    if not REQUIRED <= files.keys():
        raise ValueError('Incomplete package; required update files are missing.')
    version = files['version'].decode('ascii').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid package VERSION.')
    return files, version


def destination(root, relative):
    # Never follow a local link into a server directory or outside the package.
    path = root
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        path = path / part
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError(f'Update path is a link: {path}')
        if index < len(parts) - 1 and path.exists() and not path.is_dir():
            raise ValueError(f'Update parent is not a directory: {path}')
    if path.exists() and not path.is_file():
        raise ValueError(f'Update destination is not a regular file: {path}')
    return path


def atomic_write(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.cs15-update-', dir=path.parent)
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


def exact_name_exists(root, relative):
    """Distinguish real case variants from aliases on a case-insensitive host."""
    current = root
    for part in PurePosixPath(relative).parts:
        if part not in {entry.name for entry in current.iterdir()}:
            return False
        current = current / part
    return True


def apply_snapshot(root, files, version, commit):
    files = dict(files)
    state_data = (json.dumps({'version': version, 'commit': commit}, indent=2) + '\n').encode()
    # Preflight every destination and read the old bytes before the first change.
    plan = []
    for relative, data in files.items():
        if not managed(relative) or relative != relative.lower():
            raise ValueError(f'Unexpected package destination: {relative}')
        target = destination(root, relative)
        old = target.read_bytes() if target.exists() else None
        if old != data:
            mode = stat.S_IMODE(target.stat().st_mode) if old is not None else (
                0o755 if relative in ROOT_FILES and relative.endswith('.sh') else 0o644)
            plan.append((relative, target, data, old, mode))
    # Delete only explicitly mapped legacy files with a replacement in this
    # snapshot. Backups/journal include deletions just like replacements.
    for relative, canonical in sorted(LEGACY_RENAMES.items()):
        if canonical not in files:
            continue
        legacy = destination(root, relative)
        if not legacy.exists():
            continue
        lower = destination(root, canonical)
        if (lower.exists() and legacy.samefile(lower) and not
                (exact_name_exists(root, relative) and exact_name_exists(root, canonical))):
            # On Windows, both spellings address the same file; unlinking the
            # old spelling would delete the newly installed lowercase file.
            continue
        plan.append((relative, legacy, None, legacy.read_bytes(), stat.S_IMODE(legacy.stat().st_mode)))
    # The success marker is the final replacement, after all legacy removals.
    state_target = destination(root, STATE)
    old_state = state_target.read_bytes() if state_target.exists() else None
    if old_state != state_data:
        plan.append((STATE, state_target, state_data, old_state,
            stat.S_IMODE(state_target.stat().st_mode) if old_state is not None else 0o644))
    if not plan:
        return None, 0
    journal = destination(root, JOURNAL)
    backup_root = root / '.update-backups'
    if (backup_root.is_symlink() or
            (hasattr(backup_root, 'is_junction') and backup_root.is_junction()) or
            (backup_root.exists() and not backup_root.is_dir())):
        raise ValueError('The update backup directory is not a regular directory.')
    backup_root.mkdir(mode=0o700, exist_ok=True)
    backup = backup_root / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
    backup.mkdir(mode=0o700)
    for relative, target, data, old, mode in plan:
        if old is not None:
            saved = backup / 'files' / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(old)
            os.chmod(saved, mode)
    receipt = {'version': version, 'commit': commit, 'backup': backup.name,
        'files': [p[0] for p in plan], 'newFiles': [p[0] for p in plan if p[3] is None],
        'removedFiles': [p[0] for p in plan if p[2] is None]}
    (backup / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    atomic_write(journal, (json.dumps(receipt) + '\n').encode(), 0o600)
    try:
        for relative, target, data, old, mode in plan:
            if data is None:
                target.unlink()
            else:
                atomic_write(target, data, mode)
        journal.unlink()
    except BaseException:
        recover_interrupted(root)
        print(f'Update cancelled; previous files restored. Backup: {backup}', file=sys.stderr)
        raise
    return backup, len(plan)


def recover_interrupted(root):
    journal = destination(root, JOURNAL)
    if not journal.exists():
        return
    receipt = json.loads(journal.read_text(encoding='utf-8'))
    identifier = receipt.get('backup', '')
    if not re.fullmatch(r'\d{8}-\d{6}-[0-9a-f]{8}', identifier):
        raise ValueError('Invalid interrupted-update backup identifier.')
    backup = root / '.update-backups' / identifier
    files = receipt.get('files', [])
    new = receipt.get('newFiles', [])
    if (not isinstance(files, list) or not files or not isinstance(new, list) or
            not all(isinstance(p, str) for p in files + new) or not set(new) <= set(files)):
        raise ValueError('Invalid interrupted-update file list.')
    recovery = []
    for relative in files:
        if (not isinstance(relative, str) or '\\' in relative or ':' in relative or
                any(p in {'', '.', '..'} for p in relative.split('/')) or
                not (managed(relative) or relative == STATE)):
            raise ValueError('Invalid interrupted-update destination.')
        target = destination(root, relative)
        saved = destination(root, f'.update-backups/{identifier}/files/{relative}')
        data = None if relative in new else saved.read_bytes()
        mode = stat.S_IMODE(saved.stat().st_mode) if data is not None else 0o644
        recovery.append((target, data, mode))
    for target, data, mode in reversed(recovery):
        if data is None:
            target.unlink(missing_ok=True)
        else:
            atomic_write(target, data, mode)
    journal.unlink()
    print(f'Restored interrupted update from: {backup}', flush=True)


def refuse_running(root):
    proc = Path('/proc')
    if not proc.exists():
        return
    for entry in proc.iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            args = (entry / 'cmdline').read_bytes().split(b'\0')
            if any(os.fsdecode(a) == str(root / 'scripts/server_panel.py') for a in args):
                raise ValueError('Close the panel helper terminal before updating.')
            if (entry / 'comm').read_text().strip() in {'hlds', 'hlds_linux'}:
                if (entry / 'cwd').resolve().is_relative_to(root):
                    raise ValueError('Stop the game server before updating.')
        except (OSError, PermissionError):
            continue


def main():
    parser = argparse.ArgumentParser(description='Update a ZIP-extracted Linux package, keeping installed servers intact.')
    parser.add_argument('folder', type=Path)
    parser.add_argument('--check', action='store_true', help='Show the available version without changing package files')
    parser.add_argument('--version', action='store_true', help='Show the locally recorded version without downloading')
    args = parser.parse_args()
    root = args.folder.resolve()
    version_path = destination(root, 'version')
    if not version_path.is_file():
        version_path = destination(root, 'VERSION')
    state_path = destination(root, STATE)
    current = version_path.read_text().strip() if version_path.is_file() else 'legacy / unversioned'
    state = json.loads(state_path.read_text()) if state_path.is_file() else {}
    print(f'Installed package: {current}; commit: {state.get("commit", "not recorded (ZIP)")}', flush=True)
    if args.version:
        return
    if sys.platform != 'linux':
        raise ValueError('Run this updater on the Linux Mint laptop.')
    if (root / '.git').exists() or (root / '.git').is_symlink():
        raise ValueError('This is a Git checkout. Use git pull --ff-only instead of the ZIP updater.')
    setup = destination(root, 'setup-linux.sh')
    old_setup = destination(root, 'Setup-Linux.sh')
    if not (setup.is_file() or old_setup.is_file()) or not (root / 'scripts/server_panel.py').is_file():
        raise ValueError('Place update.sh in the extracted package folder, beside setup-linux.sh (legacy: Setup-Linux.sh).')
    import fcntl
    lock = destination(root, '.update.lock')
    with lock.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another package update is already running.')
        if not args.check:
            refuse_running(root)
            recover_interrupted(root)
        commit = latest_commit()
        print(f'Downloading package at {commit} ...', flush=True)
        files, version = read_snapshot(request_bytes(
            f'https://codeload.github.com/{REPOSITORY}/zip/{commit}', MAX_DOWNLOAD), commit)
        print(f'Available package: {version}; commit: {commit}', flush=True)
        if args.check:
            return
        backup, count = apply_snapshot(root, files, version, commit)
        if count:
            print(f'Updated {count} package files. Backup: {backup}')
        else:
            print('Package is already up to date.')
        print('Installed game-server files and credentials were preserved. Start with: bash start-panel.sh')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        print(f'Update failed: {error}', file=sys.stderr)
        sys.exit(1)
CS15_UPDATE_PYTHON
