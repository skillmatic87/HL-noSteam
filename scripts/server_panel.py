#!/usr/bin/env python3
"""Loopback-only offline CS 1.5 panel: file access and local HLDS lifecycle."""
import argparse
import base64
import ctypes
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parents[1]
FILES = {
    'cstrike/server.cfg', 'cstrike/addons/yapb/conf/yapb.cfg',
    'cstrike/addons/amxmodx/configs/SND-LIST.CFG',
    'cstrike/addons/amxmodx/configs/mapmanager.cfg', 'cstrike/mapcycle.txt',
    'cstrike/addons/amxmodx/configs/maps.ini', 'cstrike/addons/statsme/statsme.cfg',
    'cstrike/motd.txt', 'settings.local.json', 'Start-CS15.cmd', 'Start-CS15.sh',
}
ADMIN_USERS = 'cstrike/addons/amxmodx/configs/users.ini'
ADMIN_AMXX = 'cstrike/addons/amxmodx/configs/amxx.cfg'
ADMIN_FILES = ('cstrike/server.cfg', 'cstrike/addons/yapb/conf/yapb.cfg', ADMIN_USERS,
               'settings.local.json', 'ADMIN.local.txt')
USER_LINE = re.compile(rb'^([ \t]*)"([^"\r\n]*)"([ \t]+)"([^"\r\n]*)"([ \t]+)"([a-zA-Z]*)"([ \t]+)"([a-zA-Z]*)"([ \t]*(?:;[^\r\n]*)?)(\r\n|\n|\r)?$')


def display_name(raw):
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('latin1')


def user_entries(raw):
    entries, protected = [], 0
    for index, line in enumerate(raw.splitlines(keepends=True)):
        match = USER_LINE.match(line)
        if not match:
            if line.strip() and not line.lstrip().startswith((b';', b'//')):
                protected += 1
            continue
        access, flags = match[6].decode('ascii'), match[8].decode('ascii')
        if any(flag in flags.lower() for flag in 'bcd') or not set(access.lower()) - {'z'}:
            protected += 1
            continue
        entries.append(dict(id='line-' + str(index), name=display_name(match[2]), access=access,
                            flags=flags, passwordSet=bool(match[4]), index=index, match=match))
    return entries, protected


def password_value(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 31 or re.search(r'[^\x21-\x7e]|[";\\]', value):
        fail('New passwords must use 1-31 basic characters without spaces, quotes, semicolons or backslashes.')
    return value.encode('ascii')


def admin_name(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 31 or value != value.strip() or re.search(r'[^\x20-\x7e]|[";\\]', value):
        fail('Admin names must use 1-31 basic characters without quotes, semicolons or backslashes.')
    return value.encode('ascii')


def private_cvar(raw, name, default=b''):
    pattern = rb'^[ \t]*' + re.escape(name.encode()) + rb'[ \t]+(?:"([^"\r\n]*)"|([^\s;]+))[^\r\n]*'
    matches = list(re.finditer(pattern, raw, re.M))
    if len(matches) > 1:
        fail('Multiple active credential settings were found. Resolve them before editing access.')
    if not matches:
        return default
    return matches[0][1] if matches[0][1] is not None else matches[0][2]


def patch_private_cvar(raw, name, value):
    private_cvar(raw, name)
    pattern = rb'^([ \t]*' + re.escape(name.encode()) + rb'[ \t]+)(?:"[^"\r\n]*"|[^\s;]+)([^\r\n]*)'
    if re.search(pattern, raw, re.M):
        return re.sub(pattern, lambda match: match[1] + b'"' + value + b'"' + match[2], raw, flags=re.M)
    newline = b'\r\n' if b'\r\n' in raw else b'\n'
    return raw + (newline if raw and not raw.endswith((b'\r', b'\n')) else b'') + name.encode() + b' "' + value + b'"' + newline


class PanelError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def fail(message, status=400):
    raise PanelError(message, status)


def atomic_write(path, data):
    """Replace a file only after the complete temporary copy has been flushed."""
    previous_mode = path.stat().st_mode if path.exists() else None
    descriptor, temporary = tempfile.mkstemp(prefix='.cs15-write-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if previous_mode is not None:
            os.chmod(temporary, previous_mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def windows_arguments(line):
    function = ctypes.windll.shell32.CommandLineToArgvW
    function.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    function.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    pointer = function(line, ctypes.byref(count))
    if not pointer:
        fail('Die Windows-Startargumente konnten nicht gelesen werden.')
    try:
        return [pointer[index] for index in range(count.value)]
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(pointer)


def local_ipv4_addresses():
    """Enumerate assigned Linux addresses; a hostname may resolve only to lo."""
    if not sys.platform.startswith('linux'):
        return {item[4][0] for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
    try:
        result = subprocess.run(['ip', '-j', '-4', 'address', 'show'],
                                capture_output=True, text=True, check=True, timeout=3)
        records = json.loads(result.stdout)
        if not isinstance(records, list):
            raise ValueError('Expected an interface list.')
        addresses = set()
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get('addr_info', []), list):
                raise ValueError('Invalid interface record.')
            for info in record.get('addr_info', []):
                if not isinstance(info, dict):
                    raise ValueError('Invalid address record.')
                if info.get('family') == 'inet':
                    value = info.get('local')
                    if not isinstance(value, str):
                        raise ValueError('Missing IPv4 address.')
                    addresses.add(str(ipaddress.IPv4Address(value)))
        return addresses
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        fail('Could not read assigned IPv4 addresses. Check that iproute2 is installed and run ip -j -4 address show.')


class Panel:
    def __init__(self, root=None):
        self.root = None
        self.generation = secrets.token_hex(16)
        self.token = secrets.token_urlsafe(32)
        self.instance = secrets.token_hex(12)
        self.lock = threading.RLock()
        self.process = None
        self.lease = None
        self.lease_until = 0
        self.admin_revision_key = secrets.token_bytes(32)
        if root:
            self.open(root)

    def path(self, relative):
        if self.root is None:
            fail('Zuerst einen installierten Serverordner auswählen.')
        if not isinstance(relative, str) or len(relative) > 300 or '\\' in relative or re.search(r'[<>:"|?*\x00-\x1f]', relative):
            fail('Ungültiger relativer Dateipfad.')
        parts = relative.split('/') if relative else []
        if any(part in ('', '.', '..') for part in parts) or PurePosixPath(relative).is_absolute():
            fail('Der Dateipfad verlässt den Serverordner.')
        candidate = self.root.joinpath(*parts)
        for ancestor in [candidate, *candidate.parents]:
            if ancestor == self.root.parent:
                break
            if ancestor.is_symlink() or getattr(ancestor, 'is_junction', lambda: False)():
                fail('Verknüpfte Dateipfade werden nicht bearbeitet.')
        if not candidate.resolve().is_relative_to(self.root):
            fail('Der Dateipfad verlässt den Serverordner.')
        return candidate

    def allowed(self, relative, write=False):
        if relative in FILES:
            return True
        match = re.fullmatch(r'_configurator/backups/[A-Za-z0-9.-]+/(.+)', relative)
        if match:
            member = match[1]
            return member in ('restore.json', 'README.txt') or (member.startswith('files/') and member[6:] in FILES)
        return not write and (relative == '.install-incomplete' or relative.startswith('cstrike/sound/'))

    def open(self, directory):
        with self.lock:
            if self.editing():
                fail('Eine Konfiguration wird gerade gespeichert. Danach den Ordner wechseln.', 409)
            if self.process and self.process.poll() is None:
                fail('Zuerst den vom Panel gestarteten Server beenden.', 409)
            root = Path(directory).expanduser().resolve()
            if not root.is_dir() or not (root / 'cstrike/server.cfg').is_file():
                fail('Wähle den installierten Serverordner mit cstrike/server.cfg.')
            launchers = [name for name in ('Start-CS15.cmd', 'Start-CS15.sh') if (root / name).is_file()]
            if len(launchers) != 1 or not any((root / name).is_file() for name in ('hlds.exe', 'hlds')):
                fail('Im Serverordner fehlen eine eindeutige Startdatei oder HLDS.')
            if (root / '.install-incomplete').exists():
                fail('Die Serverinstallation ist noch nicht abgeschlossen.')
            self.root = root
            self.generation = secrets.token_hex(16)
            return self.info()

    def info(self):
        return dict(root=str(self.root) if self.root else '', name=self.root.name if self.root else '',
                    generation=self.generation, platform='windows' if os.name == 'nt' else 'linux')

    def arguments(self):
        launcher = self.path('Start-CS15.cmd' if os.name == 'nt' else 'Start-CS15.sh')
        if not launcher.is_file():
            fail('Die Startdatei passt nicht zum Betriebssystem dieses PCs.')
        text = launcher.read_text(encoding='utf-8-sig')
        pattern = r'^\s*hlds(?:\.exe)?\s+.*$' if os.name == 'nt' else r'^\s*exec\s+\./hlds\s+.*$'
        lines = re.findall(pattern, text, re.M | re.I)
        if len(lines) != 1:
            fail('Die Startdatei braucht genau eine unterstützte HLDS-Startzeile.')
        if os.name == 'nt':
            arguments = windows_arguments(lines[0].strip())
        else:
            arguments = shlex.split(lines[0].strip())[1:]
            arguments = [argument for argument in arguments if argument != '$@']
        if '-game' not in arguments or arguments[arguments.index('-game') + 1:arguments.index('-game') + 2] != ['cstrike']:
            fail('Die Startdatei muss -game cstrike verwenden.')
        return [str(self.path('hlds.exe' if os.name == 'nt' else 'hlds')), *arguments[1:]]

    def endpoint(self):
        args = self.arguments()
        def value(key, default):
            return args[args.index(key) + 1] if key in args and args.index(key) + 1 < len(args) else default
        address = value('+ip', '127.0.0.1')
        if address == '0.0.0.0':
            address = '127.0.0.1'
        try:
            ip = ipaddress.IPv4Address(address)
            if ip.is_multicast or address == '255.255.255.255':
                fail('Die Startdatei verweist nicht auf eine IPv4-Adresse dieses PCs.')
            if not ip.is_loopback and address not in local_ipv4_addresses():
                fail('Die Startdatei verweist nicht auf eine IPv4-Adresse dieses PCs.')
            port = int(value('-port', '27015'))
            if not 1 <= port <= 65535:
                raise ValueError()
        except ValueError:
            fail('Ungültige lokale Serveradresse oder Portnummer in der Startdatei.')
        return address, port

    def probe(self):
        if self.root is None:
            return None
        endpoint = self.endpoint()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
                udp.settimeout(.18)
                udp.connect(endpoint)
                udp.send(b'\xff\xff\xff\xffdetails\0')
                reply = udp.recv(8192)
            if not reply.startswith(b'\xff\xff\xff\xffm'):
                return None
            fields = reply[5:].split(b'\0', 5)
            if len(fields) != 6 or len(fields[5]) < 3:
                return None
            return dict(name=fields[1].decode('latin1'), map=fields[2].decode('ascii', 'replace'),
                        players=fields[5][0], maxPlayers=fields[5][1])
        except (OSError, TimeoutError):
            return None

    def status(self):
        with self.lock:
            managed = bool(self.process and self.process.poll() is None)
            details = self.probe()
            return dict(running=managed or details is not None, managed=managed, responding=details is not None,
                        editing=self.editing(),
                        details=details, endpoint='%s:%s' % self.endpoint() if self.root else '',
                        exitCode=self.process.poll() if self.process else None)

    def ensure_stopped(self):
        if self.process and self.process.poll() is None or self.probe() is not None:
            fail('Der Server läuft. Vor dem Speichern zuerst im Panel beenden.', 409)

    def _admin_snapshot(self):
        for name in (*ADMIN_FILES, ADMIN_AMXX):
            if self.path(name).is_file() and self.path(name).stat().st_size > 2 * 1024 * 1024:
                fail('An access file is too large to edit.')
        return {name: self.path(name).read_bytes() if self.path(name).is_file() else None
                for name in (*ADMIN_FILES, ADMIN_AMXX)}

    def _admin_revision(self, files):
        digest = hmac.new(self.admin_revision_key, self.generation.encode(), hashlib.sha256)
        for name, raw in files.items():
            digest.update(name.encode() + b'\0' + (b'missing' if raw is None else hashlib.sha256(raw).digest()))
        return digest.hexdigest()

    def admin_info(self):
        with self.lock:
            files = self._admin_snapshot()
            entries, protected = user_entries(files[ADMIN_USERS] or b'')
            amx_key = private_cvar(files[ADMIN_AMXX] or b'', 'amx_password_field', b'_pw')
            yb_key = private_cvar(files[ADMIN_FILES[1]] or b'', 'yb_password_key', b'_ybpw')
            for key in (amx_key, yb_key):
                if not re.fullmatch(rb'[a-zA-Z_][a-zA-Z0-9_]{0,30}', key):
                    fail('The configured login key cannot be displayed as a client command.')
            return dict(generation=self.generation, revision=self._admin_revision(files),
                        accounts=[{key: entry[key] for key in ('id', 'name', 'access', 'flags', 'passwordSet')} for entry in entries],
                        protectedRules=protected, rconSet=bool(private_cvar(files[ADMIN_FILES[0]] or b'', 'rcon_password')),
                        ybSet=bool(private_cvar(files[ADMIN_FILES[1]] or b'', 'yb_password')),
                        amxKey=amx_key.decode(), ybKey=yb_key.decode())

    def _admin_commit(self, before, changes):
        """Back up all private changes, then atomically write with CAS checks."""
        changes = {name: raw for name, raw in changes.items() if raw != before[name]}
        if not changes:
            return dict(changed=False, files=[], backup=None)
        identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-access-' + secrets.token_hex(4)
        relative = '_configurator/backups/' + identifier
        backup = self.path(relative)
        records = []
        for name, after in changes.items():
            previous = before[name]
            if previous is not None:
                saved = self.path(relative + '/files/' + name)
                saved.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(saved, previous)
                if saved.read_bytes() != previous:
                    fail('The access backup could not be verified.')
            records.append(dict(path=name, existed=previous is not None,
                                beforeSHA256=None if previous is None else hashlib.sha256(previous).hexdigest(),
                                installedSHA256=hashlib.sha256(after).hexdigest()))
        backup.mkdir(parents=True, exist_ok=True)
        atomic_write(backup / 'admin-restore.json', json.dumps(dict(schemaVersion=1, kind='admin-access',
                     server=str(self.root), files=records), indent=2).encode())
        atomic_write(backup / 'README.txt', b'Private administrator access backup. Stop HLDS before restoring.\nRestore through the Administration section or copy files/ back to the matching paths.\nKeep this directory private: it contains previous credentials.\n')
        written = []
        try:
            for name, after in changes.items():
                current = self.path(name).read_bytes() if self.path(name).is_file() else None
                if current != before[name]:
                    fail('Access files changed during saving. Reload administration and try again.', 409)
                self.path(name).parent.mkdir(parents=True, exist_ok=True)
                written.append(name)
                atomic_write(self.path(name), after)
        except Exception:
            conflicts = []
            for name in reversed(written):
                try:
                    current = self.path(name).read_bytes() if self.path(name).is_file() else None
                    if current != changes[name]:
                        if current != before[name]:
                            conflicts.append(name)
                        continue
                    if before[name] is None:
                        self.path(name).unlink()
                    else:
                        atomic_write(self.path(name), before[name])
                except OSError:
                    conflicts.append(name)
            if conflicts:
                fail('Access saving failed. Restore the private access backup manually before continuing.', 409)
            raise
        return dict(changed=True, files=list(changes), backup=relative)

    def save_admin(self, data):
        with self.lock:
            self.ensure_stopped()
            if self.editing():
                fail('Another configuration save is in progress.', 409)
            before = self._admin_snapshot()
            if data.get('generation') != self.generation or not hmac.compare_digest(str(data.get('revision', '')), self._admin_revision(before)):
                fail('Access settings changed. Reload administration before saving.', 409)
            entries, _ = user_entries(before[ADMIN_USERS] or b'')
            updates = data.get('accounts')
            if not isinstance(updates, list) or len(updates) > max(64, len(entries)):
                fail('Invalid administrator list.')
            existing = {entry['id']: entry for entry in entries}
            supplied = [entry.get('id') for entry in updates if isinstance(entry, dict) and entry.get('id') is not None]
            if len(supplied) != len(existing) or len(set(supplied)) != len(supplied) or set(supplied) != set(existing):
                fail('The administrator list is incomplete or stale. Reload it before saving.')
            lines = (before[ADMIN_USERS] or b'').splitlines(keepends=True)
            additions, final_names, renamed = [], [], {}
            for update in updates:
                if not isinstance(update, dict) or not isinstance(update.get('password', ''), str):
                    fail('Invalid administrator entry.')
                entry = existing.get(update.get('id'))
                name = update.get('name')
                if entry and name == entry['name']:
                    name_bytes = entry['match'][2]
                else:
                    name_bytes = admin_name(name)
                final_names.append(name.casefold())
                password = password_value(update['password']) if update.get('password') else None
                if entry:
                    match = entry['match']
                    flags = match[8].replace(b'e', b'').replace(b'E', b'') if password is not None else match[8]
                    line = match[1] + b'"' + name_bytes + b'"' + match[3] + b'"' + (password if password is not None else match[4]) + b'"' + match[5] + b'"' + match[6] + b'"' + match[7] + b'"' + flags + b'"' + match[9] + (match[10] or b'')
                    lines[entry['index']] = line
                    renamed[entry['name']] = dict(name=name, password=password)
                else:
                    if password is None:
                        fail('A new administrator needs a password.')
                    additions.append(b'"' + name_bytes + b'" "' + password + b'" "abcdefghijklmnopqrstu" "a"')
            if len(set(final_names)) != len(final_names) and any(update.get('id') is None or update.get('name') != existing[update['id']]['name'] for update in updates):
                fail('Administrator names must be unique.')
            newline = b'\r\n' if b'\r\n' in (before[ADMIN_USERS] or b'') else b'\n'
            users = b''.join(lines)
            if additions:
                users += (newline if users and not users.endswith((b'\r', b'\n')) else b'') + newline.join(additions) + newline
            changes = {ADMIN_USERS: users}
            rcon = data.get('rconPassword', '')
            yb = data.get('ybPassword', '')
            if not isinstance(rcon, str) or not isinstance(yb, str):
                fail('Invalid password value.')
            if rcon:
                if before[ADMIN_FILES[0]] is None:
                    fail('The server configuration is missing.')
                changes[ADMIN_FILES[0]] = patch_private_cvar(before[ADMIN_FILES[0]], 'rcon_password', password_value(rcon))
            if yb:
                if before[ADMIN_FILES[1]] is None:
                    fail('The YaPB configuration is missing.')
                changes[ADMIN_FILES[1]] = patch_private_cvar(before[ADMIN_FILES[1]], 'yb_password', password_value(yb))
            # Synchronize the installer's primary operator name and private note.
            settings = json.loads((before['settings.local.json'] or b'{}').decode('utf-8-sig'))
            owner = settings.get('AdminName')
            if owner in renamed and renamed[owner]['name'] != owner and before['settings.local.json'] is not None:
                settings['AdminName'] = renamed[owner]['name']
                changes['settings.local.json'] = (json.dumps(settings, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
            note = before['ADMIN.local.txt']
            if note is not None:
                if owner in renamed:
                    target = renamed[owner]
                    if target['name'] != owner:
                        note = re.sub(rb'(?m)^(Player name: )[^\r\n]*', lambda m: m[1] + target['name'].encode('ascii'), note)
                    if target['password'] is not None:
                        amx_key = private_cvar(before[ADMIN_AMXX] or b'', 'amx_password_field', b'_pw')
                        note = re.sub(rb'(?m)^(setinfo ' + re.escape(amx_key) + rb' )"[^"\r\n]*"', lambda m: m[1] + b'"' + target['password'] + b'"', note)
                if rcon:
                    note = re.sub(rb'(?m)^((?:Server-console RCON password|RCON password): )[^\r\n]*', lambda m: m[1] + rcon.encode('ascii'), note)
                changes['ADMIN.local.txt'] = note
            return self._admin_commit(before, changes)

    def restore_admin(self, data):
        with self.lock:
            self.ensure_stopped()
            if self.editing() or data.get('generation') != self.generation:
                fail('Server selection changed or another save is in progress.', 409)
            relative = data.get('backup', '')
            if not re.fullmatch(r'_configurator/backups/[A-Za-z0-9.-]+-access-[a-f0-9]+', relative):
                fail('Invalid access backup.')
            document = json.loads(self.path(relative + '/admin-restore.json').read_bytes())
            if document.get('kind') != 'admin-access' or document.get('schemaVersion') != 1 or document.get('server') != str(self.root):
                fail('This access backup belongs to a different server.')
            records = document.get('files')
            if not isinstance(records, list) or not records or len({r['path'] for r in records}) != len(records):
                fail('Invalid access backup.')
            changes, before = {}, self._admin_snapshot()
            for record in records:
                name = record['path']
                if type(record.get('existed')) is not bool or not re.fullmatch('[a-f0-9]{64}', str(record.get('installedSHA256', ''))):
                    fail('Invalid access backup.')
                if name not in ADMIN_FILES or before[name] is None or hashlib.sha256(before[name]).hexdigest() != record['installedSHA256']:
                    fail('Access files changed since this backup. Restore was cancelled.', 409)
                if not record['existed']:
                    changes[name] = None
                else:
                    saved = self.path(relative + '/files/' + name)
                    if saved.stat().st_size > 2 * 1024 * 1024:
                        fail('Invalid access backup.')
                    changes[name] = saved.read_bytes()
                    if hashlib.sha256(changes[name]).hexdigest() != record.get('beforeSHA256'):
                        fail('The access backup could not be verified.')
            written = []
            try:
                for name, raw in changes.items():
                    if self.path(name).read_bytes() != before[name]:
                        fail('Access files changed during restoring.', 409)
                    written.append(name)
                    if raw is None:
                        self.path(name).unlink()
                    else:
                        atomic_write(self.path(name), raw)
            except Exception:
                for name in reversed(written):
                    current = self.path(name).read_bytes() if self.path(name).exists() else None
                    if current == changes[name]:
                        atomic_write(self.path(name), before[name])
                raise
            return dict(restored=True, files=list(changes))

    def editing(self):
        return self.lease is not None and time.monotonic() < self.lease_until

    def begin_edit(self, generation):
        with self.lock:
            if generation != self.generation or self.editing():
                fail('Serverauswahl geändert oder eine andere Speicherung läuft.', 409)
            self.ensure_stopped()
            self.lease = secrets.token_hex(16)
            self.lease_until = time.monotonic() + 120
            return dict(lease=self.lease)

    def end_edit(self, lease):
        with self.lock:
            if lease == self.lease:
                self.lease = None
            return dict(ok=True)

    def fs(self, op, relative, generation, data=None, lease=None):
        with self.lock:
            if generation != self.generation:
                fail('Der ausgewählte Serverordner hat sich geändert. Seite neu laden.', 409)
            path = self.path(relative)
            if op == 'kind':
                if not path.exists():
                    return dict(missing=True)
                return dict(kind='directory' if path.is_dir() else 'file')
            if op == 'entries':
                if relative != 'cstrike/maps':
                    fail('Nur das installierte Map-Verzeichnis wird aufgelistet.')
                return dict(entries=[[p.name, 'file'] for p in path.iterdir() if p.is_file() and p.suffix.lower() == '.bsp'])
            if op == 'read':
                if not self.allowed(relative):
                    fail('Diese Datei gehört nicht zum Konfigurator.', 403)
                if not path.is_file():
                    return dict(missing=True)
                if path.stat().st_size > 16 * 1024 * 1024:
                    fail('Die Datei ist zu groß.')
                return dict(data=base64.b64encode(path.read_bytes()).decode('ascii'))
            self.ensure_stopped()
            if self.editing():
                if lease != self.lease:
                    fail('Eine andere Panel-Sitzung speichert gerade.', 409)
                self.lease_until = time.monotonic() + 120
            if op == 'mkdir':
                if not re.fullmatch(r'_configurator(?:/backups(?:/[A-Za-z0-9.-]+(?:/files(?:/(?:cstrike|addons|yapb|amxmodx|configs|conf|lang|statsme))*)?)?)?', relative):
                    # Require the directory to be an ancestor of a permitted backup file.
                    prefix = relative + '/'
                    allowed_parent = relative.startswith('_configurator/backups/') and any(
                        ('_configurator/backups/' + relative.split('/')[2] + '/files/' + name).startswith(prefix)
                        for name in FILES)
                    if not allowed_parent:
                        fail('Nicht freigegebenes Backup-Verzeichnis.', 403)
                path.mkdir(exist_ok=True)
                return dict(ok=True)
            if op not in ('touch', 'write', 'remove') or not self.allowed(relative, write=True):
                fail('Diese Datei darf vom Panel nicht geändert werden.', 403)
            if op == 'touch':
                if not path.exists():
                    path.touch(exist_ok=False)
            elif op == 'remove':
                path.unlink()
            else:
                try:
                    payload = base64.b64decode(data, validate=True)
                except (ValueError, TypeError):
                    fail('Ungültige Dateidaten.')
                if len(payload) > 2 * 1024 * 1024:
                    fail('Die Konfigurationsdatei ist zu groß.')
                atomic_write(path, payload)
            return dict(ok=True)

    def start(self):
        with self.lock:
            if self.editing():
                fail('Zuerst die laufende Speicherung abschließen.', 409)
            self.ensure_stopped()
            command = self.arguments()
            self.endpoint()  # Never start an incorrectly bound local server.
            log = self.path('_configurator/server-console.log')
            log.parent.mkdir(exist_ok=True)
            environment = os.environ.copy()
            if os.name != 'nt':
                environment['LD_LIBRARY_PATH'] = str(self.root) + (':' + environment['LD_LIBRARY_PATH'] if environment.get('LD_LIBRARY_PATH') else '')
            if os.name == 'nt':
                # Legacy Windows HLDS needs actual console input handles. A
                # windowless process with redirected stdin exits after startup.
                startup = subprocess.STARTUPINFO()
                startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow = subprocess.SW_HIDE
                self.process = subprocess.Popen(command, cwd=self.root, env=environment,
                                                creationflags=subprocess.CREATE_NEW_CONSOLE,
                                                startupinfo=startup)
            else:
                with log.open('ab') as output:
                    self.process = subprocess.Popen(command, cwd=self.root, env=environment, stdin=subprocess.DEVNULL,
                                                    stdout=output, stderr=subprocess.STDOUT)
            return dict(started=True, pid=self.process.pid)

    def stop(self):
        with self.lock:
            if not self.status()['running']:
                return dict(stopped=True)
            config = self.path('cstrike/server.cfg').read_text(encoding='utf-8-sig')
            passwords = re.findall(r'^[ \t]*rcon_password[ \t]+"([^"\r\n]+)"[ \t]*(?://[^\r\n]*)?\r?$', config, re.M)
            if len(passwords) != 1 or re.search(r'[^\x20-\x7e]', passwords[0]):
                fail('Für reguläres Beenden wird ein eindeutiges lokales RCON-Passwort benötigt.')
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
                    udp.settimeout(1.2)
                    udp.connect(self.endpoint())
                    udp.send(b'\xff\xff\xff\xffchallenge rcon\0')
                    reply = udp.recv(8192)
                    match = re.search(rb'challenge rcon ([0-9]+)', reply)
                    if not match:
                        fail('Der Server hat keine gültige RCON-Challenge geliefert.')
                    udp.send(b'\xff\xff\xff\xffrcon ' + match[1] + b' "' + passwords[0].encode('ascii') + b'" quit\0')
                    try:
                        answer = udp.recv(8192)
                        if b'Bad rcon_password' in answer or b'Bad challenge' in answer:
                            fail('Der Server hat die lokalen RCON-Daten abgelehnt.')
                    except socket.timeout:
                        pass  # Shutdown can close the endpoint before replying.
            except OSError:
                fail('Der Server antwortet noch nicht auf RCON. Gleich erneut versuchen.', 409)
            for _ in range(40):
                if not self.status()['running']:
                    return dict(stopped=True)
                time.sleep(.15)
            fail('Der Server läuft noch. Es wurde kein Prozess zwangsweise beendet.', 409)


class PanelHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, panel):
        self.panel = panel
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # No credentials, paths or API payloads in access logs.

    def send(self, value, status=200, content_type='application/json; charset=utf-8'):
        payload = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def guard(self, authenticated=True):
        host = '127.0.0.1:%d' % self.server.server_port
        if self.headers.get('Host') != host or self.headers.get('Origin', 'http://' + host) != 'http://' + host:
            fail('Dieses Panel akzeptiert nur seinen lokalen Ursprung.', 403)
        if authenticated and not hmac.compare_digest(self.headers.get('X-CS15-Token', ''), self.server.panel.token):
            fail('Panel-Sitzung ungültig. Seite über den lokalen Starter neu öffnen.', 403)

    def do_GET(self):
        try:
            self.guard(authenticated=self.path not in ('/', '/health'))
            panel = self.server.panel
            if self.path == '/':
                html = (PROJECT / 'Configure-Server.html').read_text(encoding='utf-8')
                boot = '<script>window.CS15Panel=' + json.dumps({'token': panel.token}).replace('<', '\\u003c') + ';</script>'
                self.send(html.replace('<script>', boot + '\n<script>', 1).encode('utf-8'), content_type='text/html; charset=utf-8')
            elif self.path == '/health':
                self.send(dict(app='CS15-Local-Panel', instance=panel.instance))
            elif self.path == '/api/info':
                self.send(panel.info())
            elif self.path == '/api/status':
                self.send(panel.status())
            elif self.path == '/api/admin':
                self.send(panel.admin_info())
            else:
                self.send({'error': 'Nicht gefunden.'}, 404)
        except PanelError as error:
            self.send({'error': str(error)}, error.status)
        except Exception:
            self.send({'error': 'Der lokale Status konnte nicht gelesen werden.'}, 500)

    def do_POST(self):
        try:
            self.guard()
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                fail('JSON-Anfrage erforderlich.', 415)
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4 * 1024 * 1024:
                fail('Ungültige Anfragegröße.', 413)
            data = json.loads(self.rfile.read(length))
            panel = self.server.panel
            if self.path == '/api/open':
                self.send(panel.open(data['path']))
            elif self.path == '/api/fs':
                self.send(panel.fs(data['op'], data['path'], data['generation'], data.get('data'), data.get('lease')))
            elif self.path == '/api/begin-edit':
                self.send(panel.begin_edit(data['generation']))
            elif self.path == '/api/end-edit':
                self.send(panel.end_edit(data.get('lease')))
            elif self.path == '/api/admin/save':
                self.send(panel.save_admin(data))
            elif self.path == '/api/admin/restore':
                self.send(panel.restore_admin(data))
            elif self.path in ('/api/start', '/api/stop'):
                if data.get('generation') != panel.generation:
                    fail('Serverauswahl geändert. Seite neu laden.', 409)
                self.send(panel.start() if self.path.endswith('start') else panel.stop())
            elif self.path == '/api/pick-folder':
                environment = os.environ.copy()
                environment['CS15_PICKER_INITIAL'] = str(panel.root or PROJECT)
                environment['PYTHONIOENCODING'] = 'utf-8'
                language = self.headers.get('Accept-Language', 'en').split(',')[0].split('-')[0]
                environment['CS15_PICKER_TITLE'] = 'CS 1.5 Serverordner auswählen' if language == 'de' else 'Choose CS 1.5 server folder'
                code = 'import os,tkinter as t;from tkinter import filedialog;r=t.Tk();r.withdraw();r.attributes("-topmost",True);p=filedialog.askdirectory(title=os.environ["CS15_PICKER_TITLE"],initialdir=os.environ["CS15_PICKER_INITIAL"]);print(p);r.destroy()'
                result = subprocess.run([sys.executable, '-c', code], env=environment, capture_output=True, encoding='utf-8',
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                if result.returncode:
                    fail('Ordnerauswahl nicht verfügbar. Den vollständigen Pfad im Panel eintragen.')
                self.send(dict(path=result.stdout.strip()))
            else:
                self.send({'error': 'Nicht gefunden.'}, 404)
        except PanelError as error:
            self.send({'error': str(error)}, error.status)
        except (ValueError, KeyError, TypeError):
            self.send({'error': 'Ungültige Panel-Anfrage.'}, 400)
        except OSError:
            self.send({'error': 'Dateizugriff fehlgeschlagen. Pfad, Schreibrechte und freie Speicherkapazität prüfen.'}, 409)
        except Exception:
            self.send({'error': 'Der lokale Vorgang ist fehlgeschlagen.'}, 500)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path)
    parser.add_argument('--state-file', type=Path)
    parser.add_argument('--open-browser', action='store_true')
    parser.add_argument('--browser', type=Path)
    args = parser.parse_args()
    panel = Panel(args.server)
    http = PanelHTTPServer(('127.0.0.1', 0), panel)
    url = 'http://127.0.0.1:%d/' % http.server_port
    if args.state_file:
        args.state_file.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(args.state_file, json.dumps(dict(url=url, pid=os.getpid(), instance=panel.instance)).encode())
    print('CS 1.5 local panel: ' + url, flush=True)
    if args.open_browser:
        if args.browser:
            subprocess.Popen([str(args.browser), url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            webbrowser.open(url)
    try:
        http.serve_forever()
    finally:
        http.server_close()
        if args.state_file and args.state_file.exists():
            try:
                if json.loads(args.state_file.read_text())['instance'] == panel.instance:
                    args.state_file.unlink()
            except (OSError, ValueError, KeyError):
                pass


if __name__ == '__main__':
    main()
