#!/usr/bin/env python3
"""Assemble a new native CS 1.5 LAN server from checksum-pinned archives."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RANGES = {'MapMinutes': (6, 180), 'FriendlyFire': (0, 1), 'BotTarget': (0, 32),
          'BotDifficulty': (0, 4), 'SoundCooldown': (0, 300),
          'SoundQuota': (1, 1000), 'RankBots': (0, 1)}
CLASSIC_SOUNDS = ('dominating doublekill firstblood godlike headshot humiliation '
                  'killingspree monsterkill multikill perfect prepare rampage '
                  'ultrakill unstoppable').split()
PLUGINS = ('admin admincmd adminhelp multilingual menufront cmdmenu plmenu mapsmenu '
           'pluginmenu adminchat antiflood adminvote pausecfg mapmanager sank_sounds').split()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_text(path, text, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='ascii', newline='\n')
    path.chmod(mode)


def safe_path(root, name):
    """Never permit absolute paths, traversal, drive names or symbolic links."""
    relative = PurePosixPath(name.replace('\\', '/'))
    if not relative.parts or relative.is_absolute() or any(
            p in ('.', '..') or ':' in p or any(ord(c) < 32 for c in p)
            for p in relative.parts):
        raise ValueError(f'Unsafe archive/content path: {name}')
    target = root.joinpath(*relative.parts)
    for parent in (target, *target.parents):
        if parent.is_symlink():
            raise ValueError(f'Links are not allowed: {parent}')
        if parent == root:
            break
    return target


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def verified_bytes(data, expected, label):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'Checksum mismatch: {label}')
    return data


def download(entry, cache):
    target = safe_path(cache, entry['file'])
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        temporary = target.with_name(target.name + '.' + secrets.token_hex(6) + '.partial')
        print(f"Downloading {entry['file']}", flush=True)
        try:
            request = urllib.request.Request(entry['url'], headers={'User-Agent': 'HL-noSteam/1.0'})
            with urllib.request.urlopen(request, timeout=180) as response, temporary.open('xb') as output:
                shutil.copyfileobj(response, output)
            if digest(temporary) != entry['sha256']:
                raise ValueError(f"Downloaded checksum mismatch: {entry['file']}")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    if not target.is_file() or digest(target) != entry['sha256']:
        raise ValueError(f'Cached checksum mismatch; move this file aside and retry: {target}')
    return target


def extract(archive_path, destination):
    """Extract regular files/directories only; keep executable bits, never ownership."""
    destination.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                target = safe_path(destination, member.filename)
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ValueError(f'Archive link rejected: {member.filename}')
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, target.open('wb') as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(0o755 if mode & 0o111 else 0o644)
    else:
        with tarfile.open(archive_path) as archive:
            for member in archive:
                target = safe_path(destination, member.name)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as source, target.open('wb') as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(0o755 if member.mode & 0o111 else 0o644)
                else:
                    raise ValueError(f'Archive link/device rejected: {member.name}')


def components():
    shared = {e['id']: e for e in read_json(ROOT / 'scripts/components.json')['components']}
    shared.pop('unpacker')
    shared.update({e['id']: e for e in read_json(ROOT / 'scripts/components-linux.json')['components']})
    return shared


def validate_setting(name, value):
    if name in ('ServerName', 'AdminName'):
        if not isinstance(value, str) or not value.strip() or not re.fullmatch(r'[\x20-\x7e]{1,31}', value) or any(c in value for c in '";\\'):
            raise ValueError(f'{name}: use 1-31 printable ASCII characters without quotes, semicolons or backslashes.')
        return value
    if name == 'RankScore':
        if value not in ('Kills', 'KillsMinusDeaths'):
            raise ValueError('RankScore: choose Kills or KillsMinusDeaths.')
        return value
    low, high = RANGES[name]
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]+', str(value)) or not low <= int(value) <= high:
        raise ValueError(f'{name}: enter an integer from {low} to {high}.')
    return int(value)


def get_settings(path):
    prompts = {
        'ServerName': 'Server name', 'MapMinutes': 'Map duration in minutes (6-180)',
        'FriendlyFire': 'Enable Friendly Fire? (yes/no)',
        'BotTarget': 'Fill with bots to this total player count (0-32; 0 disables bots)',
        'BotDifficulty': 'Bot difficulty (0 new, 1 easy, 2 medium, 3 hard, 4 expert)',
        'SoundCooldown': 'Seconds between chat sounds (0-300)',
        'SoundQuota': 'Sound triggers per player per map (1-1000)',
        'RankBots': 'Include bots in the ranking? (yes/no)',
        'RankScore': 'Ranking score (Kills or KillsMinusDeaths)',
        'AdminName': 'Administrator player name (exact spelling)'}
    if path:
        supplied = read_json(path)
        return {key: validate_setting(key, supplied.get(key)) for key in prompts}
    print('Ranking is stored by player name. Reusing a name reuses its ranking.')
    result = {}
    for name, prompt in prompts.items():
        while True:
            value = input(prompt + ': ').strip()
            try:
                if name in ('FriendlyFire', 'RankBots'):
                    answers = {'yes': 1, 'y': 1, 'no': 0, 'n': 0}
                    if value.lower() not in answers:
                        raise ValueError('Please answer yes/y or no/n.')
                    value = answers[value.lower()]
                result[name] = validate_setting(name, value)
                break
            except ValueError as error:
                print(error)
    return result


def lan_address(value):
    if not value:
        routes = json.loads(subprocess.check_output(['ip', '-j', '-4', 'route', 'show', 'default'], text=True))
        devices = {r['dev'] for r in routes if 'dev' in r}
        if len(devices) != 1:
            raise ValueError('Cannot select a LAN adapter unambiguously. Supply --bind-address <LAN-IPv4>.')
        records = json.loads(subprocess.check_output(['ip', '-j', '-4', 'addr', 'show', 'dev', devices.pop()], text=True))
        addresses = [a['local'] for r in records for a in r['addr_info'] if a['scope'] == 'global']
        if len(addresses) != 1:
            raise ValueError('Cannot select a LAN address unambiguously. Supply --bind-address <LAN-IPv4>.')
        value = addresses[0]
    address = ipaddress.IPv4Address(value)
    if address.is_loopback or address.is_link_local or address.is_multicast or address.is_unspecified or address.is_reserved:
        raise ValueError('Use an assigned LAN IPv4 address.')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((str(address), 0))
    return str(address)


def replace_cvars(path, values):
    text = path.read_text(encoding='latin1')
    for key, value in values.items():
        text, count = re.subn(r'(?m)^' + re.escape(key) + r'\s+[^\r\n]*', lambda _: key + ' ' + value, text)
        if not count:
            raise ValueError(f'Missing upstream setting {key}: {path}')
    write_text(path, text.replace('\r\n', '\n'))


def single_root(path):
    roots = list(path.iterdir())
    if len(roots) != 1 or not roots[0].is_dir():
        raise ValueError(f'Unexpected source archive layout: {path}')
    return roots[0]


def check_libraries(server, paths):
    """Check native dynamic dependencies on Linux before compilation/startup."""
    environment = os.environ.copy()
    environment['LD_LIBRARY_PATH'] = str(server) + ':' + environment.get('LD_LIBRARY_PATH', '')
    failures = []
    for relative in paths:
        path = server / relative
        run = subprocess.run(['ldd', str(path)], env=environment, capture_output=True, text=True)
        if run.returncode or 'not found' in run.stdout + run.stderr:
            failures.append(f'{relative}:\n{run.stdout}{run.stderr}')
    if failures:
        raise ValueError('Missing or incompatible 32-bit Linux libraries. See docs/LINUX-MINT.md.\n' + '\n'.join(failures))


def compile_plugins(server, compiler=None):
    work = server / '_setup'
    amxx = server / 'cstrike/addons/amxmodx'
    map_root = single_root(work / 'mapmanager')
    sank_root = single_root(work / 'sank')
    source = (map_root / 'mapmanager.sma').read_text(encoding='utf-8-sig')
    event = 'register_event("HLTV", "Event_NewRound", "a", "1=0", "2=0");'
    if source.count(event) != 1 or '#define VERSION "2.5.61"' not in source:
        raise ValueError('Unexpected Map Manager source.')
    source = source.replace(event, 'register_logevent("Event_NewRound", 2, "0=World triggered", "1=Round_Start");')
    source = source.replace('#define VERSION "2.5.61"', '#define VERSION "2.5.61-cs15"')
    adapted = map_root / 'mapmanager_cs15.sma'
    adapted.write_text(source, encoding='utf-8', newline='\n')
    compiler = compiler or amxx / 'scripting/amxxpc'
    compiler.chmod(0o755)
    for source_path, name in ((adapted, 'mapmanager'), (sank_root / 'sank_sounds.sma', 'sank_sounds')):
        output = amxx / f'plugins/{name}.amxx'
        run = subprocess.run([str(compiler), str(source_path), '-i' + str(amxx / 'scripting/include'),
                              '-i' + str(map_root / 'include'), '-o' + str(output)],
                             cwd=compiler.parent, capture_output=True, text=True, errors='replace')
        write_text(work / f'{name}-compile.txt', run.stdout + run.stderr)
        if run.returncode or re.search(r'error [0-9]|Compilation aborted|compile failed', run.stdout + run.stderr, re.I) or not output.is_file():
            raise ValueError(f'Plugin compilation failed. See {work / (name + "-compile.txt")}')
        shutil.copy2(source_path, amxx / 'scripting' / source_path.name)
    dictionary = (map_root / 'mapmanager.txt').read_text(encoding='utf-8-sig')
    english = re.search(r'(?ms)^\[en\]\s*\n(.*?)(?=^\[|\Z)', dictionary)
    if not english:
        raise ValueError('English Map Manager dictionary missing.')
    write_text(amxx / 'data/lang/mapmanager.txt', '[en]\n' + english[1])
    map_config = (map_root / 'mapmanager.cfg').read_text(encoding='utf-8-sig')
    # Upstream contains non-ASCII comments; retain English-compatible bytes.
    write_text(amxx / 'configs/mapmanager.cfg', map_config.encode('ascii', 'replace').decode('ascii'))
    replace_cvars(amxx / 'configs/mapmanager.cfg', {'mapm_start_vote_before_end': '5'})


def install_content(server, cache):
    """Fresh installations only; operator updates continue to use their platform's updater."""
    manifest = read_json(ROOT / 'content/pack.json')
    managed = []

    def put(entry, data):
        verified_bytes(data, entry['sha256'], entry['target'])
        target = safe_path(server, entry['target'])
        if target.exists() and target.read_bytes() != data:
            if entry.get('preserveExisting'):
                return
            raise ValueError(f'Content would overwrite a different file: {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        managed.append({'path': entry['target'], 'sha256': entry['sha256']})

    for entry in manifest['localFiles']:
        put(entry, safe_path(ROOT / 'content', entry['source']).read_bytes())
    for package in manifest['packages']:
        path = download(package, cache)
        if package['kind'] == 'raw':
            if len(package['files']) != 1:
                raise ValueError('A raw package must supply exactly one file.')
            put(package['files'][0], path.read_bytes())
        elif package['kind'] == 'zip':
            with zipfile.ZipFile(path) as archive:
                for entry in package['files']:
                    matches = [m for m in archive.infolist() if m.filename.replace('\\', '/') == entry['source']]
                    if len(matches) != 1 or matches[0].file_size > 64 * 1024 * 1024:
                        raise ValueError(f"Missing, duplicate or oversized member: {entry['source']}")
                    put(entry, archive.read(matches[0]))
        else:
            raise ValueError(f"Unknown package kind: {package['kind']}")
    for relative in ('cstrike/mapcycle.txt', 'cstrike/addons/amxmodx/configs/maps.ini'):
        path = server / relative
        lines = path.read_text(encoding='ascii').rstrip() + '\n'
        for item in manifest['maps']:
            name, capacity = item['name'], item['maxPlayers']
            lines += f'{name} 0 {capacity}\n' if relative.endswith('maps.ini') else f'{name} "\\minplayers\\0\\maxplayers\\{capacity}"\n'
        write_text(path, lines)
    path = server / 'cstrike/addons/amxmodx/configs/SND-LIST.CFG'
    lines = path.read_text(encoding='ascii')
    lines += ''.join(f"{s['keyword']}; {s['path']}\n" for s in manifest['sounds'])
    write_text(path, lines)
    write_text(server / '_content/installed.json', json.dumps({'schemaVersion': 1, 'id': manifest['id'], 'files': managed}, indent=2) + '\n')


def assemble(server, cache, settings, address, compiler=None):
    entries = components()
    archives = {key: download(entry, cache) for key, entry in entries.items()}
    # Existence is checked again atomically, after downloads, before any server writes.
    server.mkdir(mode=0o700, parents=True, exist_ok=False)
    write_text(server / '.install-incomplete', 'Setup is incomplete. Do not start this installation.\n')
    work = server / '_setup'
    for key in ('server', 'cs15', 'metamod', 'amxx', 'statsme', 'statsmeSource', 'sank', 'mapmanager', 'bots', 'sounds'):
        print(f'Extracting {key}', flush=True)
        extract(archives[key], work / key)
    shutil.copytree(work / 'server/hlds_l', server, dirs_exist_ok=True)
    shutil.copyfile(server / 'EULA.TXT', server / 'SERVER-LICENSE.txt')
    shutil.copytree(single_root(work / 'cs15') / 'cstrike', server / 'cstrike')
    game = server / 'cstrike'
    for key in ('metamod', 'amxx', 'statsme', 'bots'):
        shutil.copytree(work / key / 'addons', game / 'addons', dirs_exist_ok=True)
    shutil.copytree(work / 'sounds/sound', game / 'sound', dirs_exist_ok=True)
    for key in ('graphTundra', 'graphVegas'):
        shutil.copyfile(archives[key], game / 'addons/yapb/data/graph' / entries[key]['file'])
    for key in ('graphLicense', 'graphCredits', 'graphReadme'):
        shutil.copyfile(archives[key], work / entries[key]['file'])
    required = ('hlds', 'engine_i386.so', 'cstrike/dlls/cs_i386.so',
                'cstrike/addons/metamod/dlls/metamod.so',
                'cstrike/addons/statsme/dlls/sm_cstrike_mm_i386.so',
                'cstrike/addons/amxmodx/dlls/amxmodx_mm_i386.so',
                'cstrike/addons/yapb/bin/yapb.so')
    for relative in required:
        if (server / relative).read_bytes()[:5] != b'\x7fELF\x01':
            raise ValueError(f'Expected 32-bit Linux ELF: {relative}')
    if sys.platform == 'linux':
        check_libraries(server, (*required, 'cstrike/addons/amxmodx/scripting/amxxpc',
                                'cstrike/addons/amxmodx/scripting/amxxpc32.so',
                                'cstrike/addons/amxmodx/modules/engine_amxx_i386.so'))
    compile_plugins(server, compiler)
    amxx = game / 'addons/amxmodx'
    write_text(amxx / 'configs/plugins.ini', ''.join(p + '.amxx\n' for p in PLUGINS))
    write_text(game / 'addons/metamod/plugins.ini',
               'linux addons/amxmodx/dlls/amxmodx_mm_i386.so\n'
               'linux addons/statsme/dlls/sm_cstrike_mm_i386.so\n'
               'linux addons/yapb/bin/yapb.so\n')
    liblist = (game / 'liblist.gam').read_text(encoding='ascii')
    liblist, count = re.subn(r'(?m)^gamedll_linux\s+"[^"]+"', 'gamedll_linux "addons/metamod/dlls/metamod.so"', liblist)
    if count != 1:
        raise ValueError('Expected one gamedll_linux entry.')
    write_text(game / 'liblist.gam', liblist)
    replace_cvars(amxx / 'configs/amxx.cfg', {'amx_client_languages': '0'})
    with (amxx / 'configs/amxx.cfg').open('a', encoding='ascii') as stream:
        stream.write('\namx_language en\n')
    maps = sorted(p.stem for p in (game / 'maps').glob('*.bsp'))
    if len(maps) != 26:
        raise ValueError('Expected 26 original maps.')
    for name in maps:
        if not (game / f'addons/yapb/data/graph/{name}.graph').is_file():
            raise ValueError(f'Bot navigation missing: {name}')
    for path in (game / 'mapcycle.txt', amxx / 'configs/maps.ini'):
        write_text(path, '\n'.join(maps) + '\n')
    admin_password, rcon_password = secrets.token_hex(16), secrets.token_hex(16)
    write_text(server / 'settings.local.json', json.dumps(settings, indent=2) + '\n')
    write_text(game / 'server.cfg', f'hostname "{settings["ServerName"]}"\nsv_lan 1\nsv_allowdownload 1\n'
               f'rcon_password "{rcon_password}"\nmp_timelimit {settings["MapMinutes"]}\n'
               f'mp_friendlyfire {settings["FriendlyFire"]}\nmp_maxrounds 0\nmp_winlimit 0\nlog on\n')
    write_text(amxx / 'configs/users.ini', f'"{settings["AdminName"]}" "{admin_password}" "abcdefghijklmnopqrstu" "a"\n')
    write_text(server / 'ADMIN.local.txt', f'Private administrator instructions. Do not publish.\n'
               f'Player name: {settings["AdminName"]}\nBefore connecting, enter in your client console:\n'
               f'setinfo _pw "{admin_password}"\nAfter connecting: amxmodmenu\nRCON password: {rcon_password}\n')
    score = '{rk.kills}' if settings['RankScore'] == 'Kills' else '{{rk.kills}-{rk.deaths}}'
    replace_cvars(game / 'addons/statsme/statsme.cfg', {'sm_menupassword': '""', 'sm_storebyauth': '0',
                  'sm_resetrank': '0', 'sm_rankbots': str(settings['RankBots']), 'sm_rankscore': '"' + score + '"'})
    replace_cvars(game / 'addons/yapb/conf/yapb.cfg', {'yb_quota': str(settings['BotTarget']),
                  'yb_quota_mode': '"fill"', 'yb_difficulty': str(settings['BotDifficulty'])})
    write_text(amxx / 'configs/SND-LIST.CFG', f'SND_MAX; {settings["SoundQuota"]}\nSND_MAX_DUR; 180.0\n'
               f'SND_WARN; {max(1, settings["SoundQuota"] - 3)}\nSND_JOIN;\nSND_EXIT;\n'
               f'SND_DELAY; {settings["SoundCooldown"]}\nSND_MODE; 15\nSND_OBEY_DUR; 7\n'
               'EXACT_MATCH; 1\nADMINS_ONLY; 0\nDISPLAY_KEYWORDS; 1\nFREEZE_TIME_CON; 0\n' +
               ''.join(f'{s}; sound/misc/{s}.wav\n' for s in CLASSIC_SOUNDS))
    install_content(server, cache)
    write_text(server / 'COMPONENTS-linux.json', json.dumps({'schemaVersion': 1, 'components': list(entries.values())}, indent=2) + '\n')
    # A direct exec preserves argument boundaries and lets Ctrl+C reach the server.
    write_text(server / 'Start-CS15.sh', '#!/usr/bin/env bash\nset -euo pipefail\n'
               'cd -- "$(dirname -- "${BASH_SOURCE[0]}")"\n'
               'if [[ -e .install-incomplete ]]; then echo "Installation is incomplete." >&2; exit 1; fi\n'
               'if (( EUID == 0 )); then echo "Run the server as a regular user." >&2; exit 1; fi\n'
               'export LD_LIBRARY_PATH="$PWD${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
               f'exec ./hlds -game cstrike -nomaster -insecure -noipx -port 27015 +ip {address} '
               '+sv_lan 1 +maxplayers 32 +map de_dust2 "$@"\n', 0o700)
    (server / 'hlds').chmod(0o755)
    (server / '.install-incomplete').unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=ROOT / 'CS15Server-Linux')
    parser.add_argument('--cache-directory', type=Path, default=ROOT / 'downloads/linux')
    parser.add_argument('--settings', type=Path, help='Private JSON using the Windows installer setting names')
    parser.add_argument('--bind-address', help='Assigned LAN IPv4; otherwise use the sole default-route adapter')
    args = parser.parse_args()
    if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'i386', 'i686'):
        parser.error('Run on x86 Linux Mint/Ubuntu; ARM and Windows are not supported by this installer.')
    if os.geteuid() == 0:
        parser.error('Run setup as a regular user, without sudo.')
    if not Path('/lib/ld-linux.so.2').exists() or not shutil.which('ldd'):
        parser.error('32-bit Linux support is missing. Follow the dependency commands in docs/LINUX-MINT.md first.')
    os.umask(0o077)
    destination = args.destination.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        parser.error('Destination already exists. Choose a new directory; existing servers are never overwritten.')
    address = lan_address(args.bind_address)
    settings = get_settings(args.settings)
    assemble(destination, args.cache_directory.expanduser().absolute(), settings, address)
    print(f'Installed: {destination}\nStart: bash "{destination / "Start-CS15.sh"}"\n'
          f'Connect: {address}:27015\nPrivate credentials: {destination / "ADMIN.local.txt"}\n'
          'Mint runtime and human-client acceptance checks are still required; see docs/LINUX-MINT.md.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, EOFError, subprocess.SubprocessError) as error:
        print(f'Setup stopped: {error}', file=sys.stderr)
        sys.exit(1)
