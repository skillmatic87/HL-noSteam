"""Offline local-panel request, filesystem and shutdown regression tests."""
import base64
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import Mock, patch
from types import SimpleNamespace

import server_panel as module


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / 'cstrike').mkdir()
        (self.root / 'cstrike/server.cfg').write_text('hostname "Fixture"\nrcon_password "fixture-only"\n')
        self.launcher = 'Start-CS15.cmd' if os.name == 'nt' else 'Start-CS15.sh'
        (self.root / ('hlds.exe' if os.name == 'nt' else 'hlds')).touch()
        command = 'hlds.exe' if os.name == 'nt' else 'exec ./hlds'
        (self.root / self.launcher).write_text(command + ' -console -game cstrike -port 27987 +ip 127.0.0.1 +maxplayers 32 +map de_dust2\n')
        self.panel = module.Panel(self.root)
        self.http = module.PanelHTTPServer(('127.0.0.1', 0), self.panel)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:%d' % self.http.server_port

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.temporary.cleanup()

    def request(self, route, body=None, token=True, headers=None):
        selected = {'X-CS15-Token': self.panel.token} if token else {}
        if body is not None:
            selected['Content-Type'] = 'application/json'
        selected.update(headers or {})
        request = urllib.request.Request(self.url + route, data=None if body is None else json.dumps(body).encode(), headers=selected)
        try:
            with urllib.request.urlopen(request, timeout=4) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            error.close()
            raise

    def test_page_uses_local_helper_without_native_file_handles(self):
        html = self.request('/', token=False).decode()
        self.assertIn('window.CS15Panel=', html)
        self.assertIn("connect-src 'self'", html)
        self.assertNotIn('await window.showDirectoryPicker', html)

    def linux_interfaces(self):
        return SimpleNamespace(stdout=json.dumps([
            {'ifname': 'lo', 'addr_info': [{'family': 'inet', 'local': '127.0.0.1'}]},
            {'ifname': 'enp0s31f6', 'addr_info': [
                {'family': 'inet', 'local': '192.168.178.31'},
                {'family': 'inet', 'local': '192.168.178.32'}]},
            {'ifname': 'wlp2s0', 'addr_info': [{'family': 'inet', 'local': '10.0.0.7'}]}
        ]))

    def endpoint_arguments(self, address):
        return ['hlds', '-game', 'cstrike', '-port', '27015', '+ip', address]

    def test_linux_assigned_addresses_do_not_depend_on_hostname(self):
        with patch.object(module.sys, 'platform', 'linux'), \
                patch.object(module.subprocess, 'run', return_value=self.linux_interfaces()) as interfaces, \
                patch.object(module.socket, 'getaddrinfo', return_value=[
                    (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.1.1', 0))]) as resolver:
            for address in ('192.168.178.31', '192.168.178.32', '10.0.0.7'):
                with self.subTest(address=address), patch.object(self.panel, 'arguments', return_value=self.endpoint_arguments(address)):
                    self.assertEqual(self.panel.endpoint(), (address, 27015))
            resolver.assert_not_called()
            self.assertEqual(interfaces.call_args.args[0], ['ip', '-j', '-4', 'address', 'show'])
            self.assertEqual(interfaces.call_args.kwargs['timeout'], 3)

    def test_linux_remote_broadcast_and_multicast_endpoints_are_rejected(self):
        with patch.object(module.sys, 'platform', 'linux'), \
                patch.object(module.subprocess, 'run', return_value=self.linux_interfaces()):
            for address in ('192.168.178.99', '192.168.178.255', '224.0.0.1', '255.255.255.255', '300.0.0.1'):
                with self.subTest(address=address), patch.object(self.panel, 'arguments', return_value=self.endpoint_arguments(address)):
                    with self.assertRaises(module.PanelError):
                        self.panel.endpoint()

    def test_linux_interface_lookup_failures_are_actionable_and_fail_closed(self):
        failures = [FileNotFoundError('ip'), subprocess.TimeoutExpired('ip', 3),
                    subprocess.CalledProcessError(1, 'ip')]
        bad_json = ('not json', '{}', '[null]', '[{"addr_info": null}]',
                    '[{"addr_info": [{"family": "inet"}]}]',
                    '[{"addr_info": [{"family": "inet", "local": "not-an-ip"}]}]')
        with patch.object(module.sys, 'platform', 'linux'), \
                patch.object(self.panel, 'arguments', return_value=self.endpoint_arguments('192.168.178.31')):
            for failure in failures:
                with self.subTest(failure=type(failure).__name__), patch.object(module.subprocess, 'run', side_effect=failure):
                    with self.assertRaisesRegex(module.PanelError, 'iproute2'):
                        self.panel.endpoint()
            for data in bad_json:
                with self.subTest(data=data), patch.object(module.subprocess, 'run', return_value=SimpleNamespace(stdout=data)):
                    with self.assertRaisesRegex(module.PanelError, 'iproute2'):
                        self.panel.endpoint()

    def test_loopback_and_wildcard_need_no_interface_or_hostname_lookup(self):
        with patch.object(module.sys, 'platform', 'linux'), \
                patch.object(module.subprocess, 'run') as interfaces, \
                patch.object(module.socket, 'getaddrinfo') as resolver:
            for address in ('127.0.0.1', '127.0.1.1', '0.0.0.0'):
                with self.subTest(address=address), patch.object(self.panel, 'arguments', return_value=self.endpoint_arguments(address)):
                    self.assertEqual(self.panel.endpoint(), ('127.0.0.1' if address == '0.0.0.0' else address, 27015))
            interfaces.assert_not_called()
            resolver.assert_not_called()

    def test_linux_http_status_accepts_assigned_lan_endpoint(self):
        with patch.object(module.sys, 'platform', 'linux'), \
                patch.object(module.subprocess, 'run', return_value=self.linux_interfaces()), \
                patch.object(self.panel, 'arguments', return_value=self.endpoint_arguments('192.168.178.31')), \
                patch.object(self.panel, 'probe', return_value=None):
            response = json.loads(self.request('/api/status'))
            self.assertEqual(response['endpoint'], '192.168.178.31:27015')
            self.assertFalse(response['running'])

    def access_fixture(self):
        values = {
            module.ADMIN_USERS: b'; Private fixture\r\n"loopback" "" "abcdefghijklmnopqrstu" "de"\r\n"Alice" "old-amx" "bcdefu" "ae" ; keep rights\r\n"STEAM_0:1:123" "" "abc" "ce"\r\n',
            module.ADMIN_FILES[1]: b'// bot settings\r\nyb_password "old-bot"\r\nyb_password_key "_custombot"\r\nyb_quota "0"\r\n',
            module.ADMIN_AMXX: b'amx_password_field "_custompw"\n',
            'settings.local.json': b'{"AdminName":"Alice","BotTarget":0}\n',
            'ADMIN.local.txt': b'Player name: Alice\nsetinfo _custompw "old-amx"\nServer-console RCON password: fixture-only\nPrivate note retained\n',
        }
        for name, raw in values.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        return {name: (self.root / name).read_bytes() for name in (*module.ADMIN_FILES, module.ADMIN_AMXX)}

    def access_payload(self):
        info = json.loads(self.request('/api/admin'))
        return dict(generation=info['generation'], revision=info['revision'],
                    accounts=[dict(id=a['id'], name=a['name'], password='') for a in info['accounts']],
                    rconPassword='', ybPassword='')

    def test_access_metadata_hides_passwords_and_protects_special_rules(self):
        self.access_fixture()
        raw = self.request('/api/admin')
        info = json.loads(raw)
        for secret in (b'old-amx', b'old-bot', b'fixture-only'):
            self.assertNotIn(secret, raw)
        self.assertEqual([a['name'] for a in info['accounts']], ['Alice'])
        self.assertEqual(info['protectedRules'], 2)
        self.assertEqual((info['amxKey'], info['ybKey']), ('_custompw', '_custombot'))
        with self.assertRaises(urllib.error.HTTPError) as result:
            self.request('/api/admin', token=False)
        self.assertEqual(result.exception.code, 403)

    def test_access_noop_preserves_exact_bytes(self):
        original = self.access_fixture()
        result = json.loads(self.request('/api/admin/save', self.access_payload()))
        self.assertFalse(result['changed'])
        self.assertIsNone(result['backup'])
        for name, raw in original.items():
            self.assertEqual((self.root / name).read_bytes(), raw)

    def test_access_save_backup_and_restore_all_credentials(self):
        original = self.access_fixture()
        payload = self.access_payload()
        payload['accounts'][0].update(name='Bob', password='new-amx')
        payload.update(rconPassword='new-rcon', ybPassword='new-bot')
        result = json.loads(self.request('/api/admin/save', payload))
        users = (self.root / module.ADMIN_USERS).read_bytes()
        self.assertIn(b'"Bob" "new-amx" "bcdefu" "a" ; keep rights\r\n', users)
        self.assertIn(original[module.ADMIN_USERS].splitlines()[1], users)
        self.assertIn(original[module.ADMIN_USERS].splitlines()[3], users)
        self.assertIn(b'rcon_password "new-rcon"', (self.root / 'cstrike/server.cfg').read_bytes())
        self.assertIn(b'yb_password_key "_custombot"', (self.root / module.ADMIN_FILES[1]).read_bytes())
        self.assertEqual(json.loads((self.root / 'settings.local.json').read_bytes())['AdminName'], 'Bob')
        self.assertIn(b'setinfo _custompw "new-amx"', (self.root / 'ADMIN.local.txt').read_bytes())
        self.assertIn(b'Player name: Bob', (self.root / 'ADMIN.local.txt').read_bytes())
        for name in result['files']:
            self.assertEqual((self.root / result['backup'] / 'files' / name).read_bytes(), original[name])
        for secret in ('new-amx', 'new-rcon', 'new-bot'):
            self.assertNotIn(secret, json.dumps(result))
        with self.assertRaises(urllib.error.HTTPError):
            self.request('/api/fs', dict(op='read', path=result['backup'] + '/files/' + module.ADMIN_USERS, generation=self.panel.generation))
        self.request('/api/admin/restore', dict(generation=self.panel.generation, backup=result['backup']))
        for name, raw in original.items():
            self.assertEqual((self.root / name).read_bytes(), raw)

    def test_access_name_only_keeps_password_and_flags(self):
        self.access_fixture()
        payload = self.access_payload()
        payload['accounts'][0]['name'] = 'New name'
        self.request('/api/admin/save', payload)
        self.assertIn(b'"New name" "old-amx" "bcdefu" "ae"', (self.root / module.ADMIN_USERS).read_bytes())
        self.assertIn(b'setinfo _custompw "old-amx"', (self.root / 'ADMIN.local.txt').read_bytes())

    def test_access_new_admin_and_undo_created_users_file(self):
        self.access_fixture()
        (self.root / module.ADMIN_USERS).unlink()
        payload = self.access_payload()
        payload['accounts'].append(dict(id=None, name='Added', password='added-pass'))
        result = json.loads(self.request('/api/admin/save', payload))
        self.assertIn(b'"Added" "added-pass" "abcdefghijklmnopqrstu" "a"', (self.root / module.ADMIN_USERS).read_bytes())
        self.request('/api/admin/restore', dict(generation=self.panel.generation, backup=result['backup']))
        self.assertFalse((self.root / module.ADMIN_USERS).exists())

    def test_access_rejects_injection_duplicates_and_missing_accounts(self):
        original = self.access_fixture()
        for mutation in ('name', 'password', 'rconPassword', 'ybPassword', 'duplicate', 'missing', 'new-empty'):
            payload = self.access_payload()
            if mutation in ('name', 'password'):
                payload['accounts'][0][mutation] = 'bad"\nquit'
            elif mutation in ('rconPassword', 'ybPassword'):
                payload[mutation] = 'bad;quit'
            elif mutation == 'duplicate':
                payload['accounts'].append(dict(id=None, name='alice', password='other'))
            elif mutation == 'missing':
                payload['accounts'] = []
            else:
                payload['accounts'].append(dict(id=None, name='New', password=''))
            with self.subTest(mutation=mutation), self.assertRaises(urllib.error.HTTPError):
                self.request('/api/admin/save', payload)
        for name, raw in original.items():
            self.assertEqual((self.root / name).read_bytes(), raw)

    def test_access_stale_running_and_edit_lease_guards(self):
        self.access_fixture()
        payload = self.access_payload()
        payload['rconPassword'] = 'replacement'
        with patch.object(self.panel, 'probe', return_value={'name': 'running'}):
            with self.assertRaises(urllib.error.HTTPError) as result:
                self.request('/api/admin/save', payload)
            self.assertEqual(result.exception.code, 409)
        lease = self.panel.begin_edit(self.panel.generation)['lease']
        with self.assertRaises(urllib.error.HTTPError):
            self.request('/api/admin/save', payload)
        self.panel.end_edit(lease)
        with (self.root / 'cstrike/server.cfg').open('ab') as stream:
            stream.write(b'// external edit\n')
        with self.assertRaises(urllib.error.HTTPError) as result:
            self.request('/api/admin/save', payload)
        self.assertEqual(result.exception.code, 409)

    def test_access_restore_detects_external_changes_and_backup_corruption(self):
        self.access_fixture()
        payload = self.access_payload()
        payload['rconPassword'] = 'replacement'
        result = json.loads(self.request('/api/admin/save', payload))
        backup = dict(generation=self.panel.generation, backup=result['backup'])
        target = self.root / 'cstrike/server.cfg'
        installed = target.read_bytes()
        target.write_bytes(installed + b'// external edit\n')
        with self.assertRaises(urllib.error.HTTPError):
            self.request('/api/admin/restore', backup)
        self.assertEqual(target.read_bytes(), installed + b'// external edit\n')
        target.write_bytes(installed)
        (self.root / result['backup'] / 'files/cstrike/server.cfg').write_bytes(b'corrupt')
        with self.assertRaises(urllib.error.HTTPError):
            self.request('/api/admin/restore', backup)
        self.assertEqual(target.read_bytes(), installed)

    def test_access_partial_failure_rolls_back_written_files(self):
        original = self.access_fixture()
        payload = self.access_payload()
        payload['accounts'][0].update(name='Bob', password='new-amx')
        payload['rconPassword'] = 'new-rcon'
        real_write = module.atomic_write
        def broken_write(path, raw):
            if path == self.root / 'cstrike/server.cfg' and b'new-rcon' in raw:
                raise OSError('Fixture disk failure')
            real_write(path, raw)
        with patch.object(module, 'atomic_write', side_effect=broken_write):
            with self.assertRaises(urllib.error.HTTPError):
                self.request('/api/admin/save', payload)
        for name, raw in original.items():
            self.assertEqual((self.root / name).read_bytes(), raw)

    def test_token_and_foreign_origins_are_rejected(self):
        for kwargs in ({'token': False}, {'headers': {'Origin': 'https://example.invalid'}}, {'headers': {'Host': 'example.invalid'}}):
            with self.subTest(kwargs=kwargs), self.assertRaises(urllib.error.HTTPError) as result:
                self.request('/api/info', **kwargs)
            self.assertEqual(result.exception.code, 403)

    def test_configuration_extensions_are_read_through_the_helper(self):
        for name in ('cstrike/server.cfg', self.launcher):
            response = json.loads(self.request('/api/fs', {'op': 'read', 'path': name, 'generation': self.panel.generation}))
            self.assertEqual(base64.b64decode(response['data']), (self.root / name).read_bytes())

    def test_path_and_private_file_restrictions(self):
        for name in ('../outside', 'cstrike/../../outside', 'C:/outside', 'cstrike/addons/amxmodx/configs/users.ini'):
            with self.subTest(name=name), self.assertRaises(urllib.error.HTTPError):
                self.request('/api/fs', {'op': 'read', 'path': name, 'generation': self.panel.generation})

    def test_write_and_generation_conflicts(self):
        before = (self.root / 'cstrike/server.cfg').read_bytes()
        data = {'op': 'write', 'path': 'cstrike/server.cfg', 'generation': 'stale', 'data': base64.b64encode(b'bad').decode()}
        with self.assertRaises(urllib.error.HTTPError) as result:
            self.request('/api/fs', data)
        self.assertEqual(result.exception.code, 409)
        self.assertEqual((self.root / 'cstrike/server.cfg').read_bytes(), before)
        data.update(generation=self.panel.generation, data=base64.b64encode(before + b'// retained bytes\r\n').decode())
        self.request('/api/fs', data)
        self.assertEqual((self.root / 'cstrike/server.cfg').read_bytes(), before + b'// retained bytes\r\n')

    def test_running_managed_server_protects_configuration(self):
        self.panel.process = Mock()
        self.panel.process.poll.return_value = None
        before = (self.root / 'cstrike/server.cfg').read_bytes()
        with self.assertRaises(module.PanelError):
            self.panel.fs('write', 'cstrike/server.cfg', self.panel.generation, base64.b64encode(b'changed').decode())
        self.assertEqual((self.root / 'cstrike/server.cfg').read_bytes(), before)
        with self.assertRaises(module.PanelError):
            self.panel.open(self.root)

    def test_backup_paths_are_limited_to_managed_files(self):
        for relative in ('_configurator', '_configurator/backups', '_configurator/backups/fixture', '_configurator/backups/fixture/files', '_configurator/backups/fixture/files/cstrike'):
            self.panel.fs('mkdir', relative, self.panel.generation)
        relative = '_configurator/backups/fixture/files/cstrike/server.cfg'
        self.panel.fs('write', relative, self.panel.generation, base64.b64encode(b'backup').decode())
        self.assertEqual((self.root / relative).read_bytes(), b'backup')
        with self.assertRaises(module.PanelError):
            self.panel.fs('write', '_configurator/backups/fixture/files/users.ini', self.panel.generation, 'YQ==')

    def test_regular_shutdown_sends_only_quit(self):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(('127.0.0.1', 0))
        udp.settimeout(3)
        endpoint = udp.getsockname()
        self.panel.endpoint = lambda: endpoint
        received = []
        running = True
        def respond():
            nonlocal running
            try:
                while running:
                    request, peer = udp.recvfrom(8192)
                    if request.endswith(b'details\0'):
                        udp.sendto(b'\xff\xff\xff\xffm127.0.0.1\0Fixture\0de_dust2\0cstrike\0Counter-Strike\0\x00\x20\x2e', peer)
                    elif b'challenge rcon' in request:
                        udp.sendto(b'\xff\xff\xff\xffchallenge rcon 123\0', peer)
                    elif b'rcon 123 ' in request:
                        received.append(request)
                        udp.sendto(b'\xff\xff\xff\xfflbye\0', peer)
                        running = False
            finally:
                udp.close()
        thread = threading.Thread(target=respond, daemon=True)
        thread.start()
        self.assertEqual(self.panel.stop(), {'stopped': True})
        thread.join()
        self.assertEqual(received, [b'\xff\xff\xff\xffrcon 123 "fixture-only" quit\0'])

    def test_edit_session_prevents_start_and_other_tab_writes(self):
        lease = self.panel.begin_edit(self.panel.generation)['lease']
        with self.assertRaises(module.PanelError):
            self.panel.start()
        with self.assertRaises(module.PanelError):
            self.panel.open(self.root)
        with self.assertRaises(module.PanelError):
            self.panel.fs('write', 'cstrike/server.cfg', self.panel.generation, 'YQ==')
        self.panel.fs('write', 'cstrike/server.cfg', self.panel.generation, 'YQ==', lease)
        self.panel.end_edit(lease)
        self.assertFalse(self.panel.editing())

    def test_folder_picker_title_follows_ui_language(self):
        for language, title in (('en', 'Choose CS 1.5 server folder'), ('de', 'CS 1.5 Serverordner auswählen')):
            with self.subTest(language=language), patch.object(module.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=str(self.root))) as picker:
                result = json.loads(self.request('/api/pick-folder', {}, headers={'Accept-Language': language}))
                self.assertEqual(result['path'], str(self.root))
                self.assertEqual(picker.call_args.kwargs['env']['CS15_PICKER_TITLE'], title)


if __name__ == '__main__':
    unittest.main(verbosity=2)
