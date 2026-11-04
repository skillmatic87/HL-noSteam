"""Publish packages from tested commits; --prepare-only performs no GitHub writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'skillmatic87/HL-noSteam'


def run(*arguments):
    return subprocess.check_output(arguments, cwd=ROOT)


def gh(*arguments):
    return run('gh', *arguments, '--repo', REPOSITORY)


def archive_content_digest(archive):
    digest = hashlib.sha256()
    with zipfile.ZipFile(archive) as bundle:
        for name in sorted(bundle.namelist()):
            digest.update(name.encode() + b'\0' + hashlib.sha256(bundle.read(name)).digest())
    return digest.hexdigest()


def prepare(request):
    tag = request['tag']
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-rc\.\d+)?', tag):
        raise ValueError('Invalid release tag.')
    if type(request['prerelease']) is not bool:
        raise ValueError('The prerelease choice must be explicit.')
    if type(request.get('archiveAutoCRLF')) is not bool:
        raise ValueError('The archive line-ending format must be explicit.')
    sources = request['sources']
    if len(sources) != 2 or {source['platform'] for source in sources} != {'Windows', 'Linux'}:
        raise ValueError('Exactly one Windows source and one Linux source are required.')
    for source in sources:
        if not re.fullmatch('[a-f0-9]{40}', source['commit']) or not re.fullmatch('[a-f0-9]{64}', source['contentSHA256']):
            raise ValueError('Source commits and content checksums must be pinned.')
    output = ROOT / 'runtime/releases' / tag
    output.mkdir(parents=True, exist_ok=True)
    assets, checksums = [], []
    for source in sources:
        commit, platform = source['commit'], source['platform']
        available = subprocess.run(['git', 'cat-file', '-e', commit + '^{commit}'], cwd=ROOT,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if available.returncode:
            run('git', 'fetch', '--depth=1', 'origin', commit)
        prefix = 'HL-noSteam-' + platform + '/'
        archive = output / f'HL-noSteam-{platform}-{tag}.zip'
        # Preserve the format of the already tested ZIPs on every runner OS.
        endings = 'true' if request['archiveAutoCRLF'] else 'false'
        run('git', '-c', 'core.autocrlf=' + endings, 'archive', '--format=zip',
            '--prefix=' + prefix, '--output=' + str(archive), commit)
        if archive_content_digest(archive) != source['contentSHA256']:
            with zipfile.ZipFile(archive) as bundle:
                print('ARCHIVE_DIAGNOSTICS ' + json.dumps({name: hashlib.sha256(bundle.read(name)).hexdigest()
                                                         for name in sorted(bundle.namelist())}), flush=True)
            raise ValueError('Archive contents differ from the tested package: ' + platform)
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
            required = ('START-HERE.txt', 'Configure-Server.html', 'scripts/server_panel.py')
            required += ('Setup.cmd', 'Start-Server.cmd', 'Start-Panel.cmd') if platform == 'Windows' else ('Setup-Linux.sh', 'Start-Server.sh', 'Start-Panel.sh')
            if any(prefix + name not in names for name in required):
                raise ValueError('A package entry point is missing.')
            if any(name.endswith(('users.ini', 'ADMIN.local.txt', 'settings.local.json', '.exe', '.dll', '.so', '.pyc')) for name in names):
                raise ValueError('Private files or server binaries found in a source package.')
        checksums.append(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
        assets.append(archive)
    checksum_file = output / 'SHA256SUMS.txt'
    checksum_file.write_text(''.join(checksums), encoding='ascii', newline='\n')
    windows = next(source['commit'] for source in sources if source['platform'] == 'Windows')
    notes = run('git', 'show', windows + ':docs/RELEASE-NOTES.md').decode('utf-8')
    notes += '\n## Package sources\n\n' + '\n'.join(
        f'- {source["platform"]}: [{source["commit"][:7]}](https://github.com/{REPOSITORY}/commit/{source["commit"]})'
        for source in sources) + '\n'
    notes_file = output / 'RELEASE-NOTES.md'
    notes_file.write_text(notes, encoding='utf-8', newline='\n')
    return windows, assets + [checksum_file, notes_file], notes_file


def publish(request, target, assets, notes):
    if not os.environ.get('GH_TOKEN') or not shutil.which('gh'):
        raise RuntimeError('GitHub CLI and the workflow GH_TOKEN are required to publish.')
    releases = json.loads(run('gh', 'api', f'repos/{REPOSITORY}/releases?per_page=100'))
    release = next((entry for entry in releases if entry['tag_name'] == request['tag']), None)
    if release is not None:
        if release['target_commitish'] != target or release['prerelease'] != request['prerelease']:
            raise ValueError('An existing release has different source or prerelease settings.')
        existing = {entry['name']: entry for entry in release['assets']}
        if set(existing) - {asset.name for asset in assets}:
            raise ValueError('An existing release contains unexpected assets.')
        # Never replace a published or partially uploaded asset without verifying it.
        with tempfile.TemporaryDirectory() as directory:
            for asset in assets:
                if asset.name in existing:
                    gh('release', 'download', request['tag'], '--pattern', asset.name, '--dir', directory)
                    downloaded = Path(directory) / asset.name
                    if hashlib.sha256(downloaded.read_bytes()).digest() != hashlib.sha256(asset.read_bytes()).digest():
                        raise ValueError('An existing release asset differs: ' + asset.name)
        missing = [asset for asset in assets if asset.name not in existing]
        if not release['draft']:
            if missing:
                raise ValueError('Published release assets are incomplete; no changes made.')
            print('Already published: ' + release['html_url'])
            return
        if missing:
            gh('release', 'upload', request['tag'], *(str(asset) for asset in missing))
    else:
        command = ['release', 'create', request['tag'], *(str(asset) for asset in assets),
                   '--draft', '--target', target, '--title', request['title'], '--notes-file', str(notes)]
        if request['prerelease']:
            command.append('--prerelease')
        gh(*command)
    # Upload everything successfully before making the release public.
    gh('release', 'edit', request['tag'], '--draft=false')
    print('Published: https://github.com/' + REPOSITORY + '/releases/tag/' + request['tag'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    arguments = parser.parse_args()
    request = json.loads(arguments.request.read_text(encoding='utf-8'))
    target, assets, notes = prepare(request)
    for asset in assets:
        print('Verified: ' + asset.name)
    if not arguments.prepare_only:
        publish(request, target, assets, notes)


if __name__ == '__main__':
    main()
