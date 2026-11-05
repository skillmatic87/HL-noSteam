"""Offline update/rollback tests; never operate on an installed game server."""
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'Update.sh').read_text(encoding='utf-8').split("<<'CS15_UPDATE_PYTHON'\n", 1)[1].rsplit('\nCS15_UPDATE_PYTHON', 1)[0]
updater = types.ModuleType('package_updater')
exec(compile(SOURCE, 'Update.sh (embedded Python)', 'exec'), updater.__dict__)
COMMIT = 'a' * 40


def snapshot(extra=None):
    files = {name: b'package data\n' for name in updater.REQUIRED}
    files['VERSION'] = b'1.0.1\n'
    files.update(extra or {})
    return files


def archive(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as stream:
        for name, data in files.items():
            if isinstance(name, zipfile.ZipInfo):
                stream.writestr(name, data)
            else:
                # ZipInfo normally rewrites Windows separators on Windows.
                member = zipfile.ZipInfo('placeholder')
                member.filename = f'HL-noSteam-{COMMIT}/{name}'
                stream.writestr(member, data)
    return buffer.getvalue()


class PackageUpdates(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='CS15 ZIP package ')
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_first_update_preserves_server_secrets_maps_runtime_and_unknown_files(self):
        protected = {'CS15Server-Linux/cstrike/server.cfg': b'rcon_password "private"\n',
            'CS15Server-Linux/cstrike/addons/amxmodx/configs/users.ini': b'private admin',
            'CS15Server-Linux/cstrike/maps/my_map.bsp': b'personal map',
            'CS15Server-Linux/cstrike/cstrike.WAD': b'original wad',
            'CS15Server-Linux/_configurator/server-console.log': b'log',
            'settings.local.json': b'{"private": true}', 'notes.txt': b'my notes',
            'scripts/notes.local.txt': b'private script notes'}
        for relative, data in protected.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        # Even unexpected archive payloads must not be installed as server data.
        files, version = updater.read_snapshot(archive(snapshot({p: b'wrong' for p in protected})), COMMIT)
        backup, count = updater.apply_snapshot(self.root, files, version, COMMIT)
        self.assertTrue(backup.is_dir())
        self.assertGreater(count, 0)
        for relative, data in protected.items():
            self.assertEqual((self.root / relative).read_bytes(), data, relative)
        self.assertEqual(json.loads((self.root / updater.STATE).read_text())['commit'], COMMIT)
        self.assertFalse((self.root / updater.JOURNAL).exists())

    def test_repeat_update_is_noop_but_repairs_changed_package_files(self):
        files = snapshot()
        updater.apply_snapshot(self.root, files, '1.0.1', COMMIT)
        self.assertEqual(updater.apply_snapshot(self.root, files, '1.0.1', COMMIT), (None, 0))
        (self.root / 'scripts/server_panel.py').write_bytes(b'local edit')
        backup, count = updater.apply_snapshot(self.root, files, '1.0.1', COMMIT)
        self.assertEqual(count, 1)
        self.assertEqual((backup / 'files/scripts/server_panel.py').read_bytes(), b'local edit')
        self.assertEqual((self.root / 'scripts/server_panel.py').read_bytes(), files['scripts/server_panel.py'])

    def test_archive_traversal_and_invalid_roots_are_rejected_even_if_ignored(self):
        for name in ('../escape', '/absolute', 'docs/../bad', 'docs\\bad', 'C:/bad', 'docs//bad'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                updater.read_snapshot(archive(snapshot({name: b'bad'})), COMMIT)
        with self.assertRaises(ValueError):
            updater.read_snapshot(archive(snapshot()), 'b' * 40)

    def test_archive_symlink_and_case_duplicates_are_rejected(self):
        member = zipfile.ZipInfo(f'HL-noSteam-{COMMIT}/ignored-link')
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaises(ValueError):
            updater.read_snapshot(archive(snapshot({member: b'/elsewhere'})), COMMIT)
        with self.assertRaises(ValueError):
            updater.read_snapshot(archive(snapshot({'version': b'duplicate'})), COMMIT)

    def test_archive_file_directory_conflicts_are_rejected_in_either_order(self):
        for extra in ({'docs': b'file', 'docs/update.md': b'child'},
                      {'docs/update.md': b'child', 'docs': b'file'},
                      {'docs': b'file', 'docs/': b''}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                updater.read_snapshot(archive(snapshot(extra)), COMMIT)

    def test_incomplete_invalid_version_and_oversized_packages_are_rejected(self):
        with self.assertRaises(ValueError):
            updater.read_snapshot(archive({'VERSION': b'1.0.1\n'}), COMMIT)
        with self.assertRaises(ValueError):
            updater.read_snapshot(archive(snapshot({'VERSION': b'latest'})), COMMIT)
        with patch.object(updater, 'MAX_UNPACKED', 10), self.assertRaises(ValueError):
            updater.read_snapshot(archive(snapshot()), COMMIT)

    def test_destination_file_parent_fails_before_any_package_write(self):
        (self.root / 'scripts').write_bytes(b'not a directory')
        with self.assertRaises(ValueError):
            updater.apply_snapshot(self.root, snapshot(), '1.0.1', COMMIT)
        self.assertEqual(list(self.root.iterdir()), [self.root / 'scripts'])

    def test_destination_symlink_is_rejected_before_writes(self):
        external = self.root / 'external'
        external.mkdir()
        try:
            (self.root / 'scripts').symlink_to(external, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink permission unavailable on this host')
        with self.assertRaises(ValueError):
            updater.apply_snapshot(self.root, snapshot(), '1.0.1', COMMIT)
        self.assertEqual(list(external.iterdir()), [])
        self.assertFalse((self.root / 'VERSION').exists())

    def test_link_guard_on_hosts_without_symlink_permission(self):
        with patch.object(Path, 'is_symlink', lambda path: path == self.root / 'scripts'):
            with self.assertRaisesRegex(ValueError, 'link'):
                updater.apply_snapshot(self.root, snapshot(), '1.0.1', COMMIT)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_write_failure_restores_old_files_and_removes_new_files(self):
        old = {'README.md': b'old readme', 'VERSION': b'1.0.0\n'}
        for name, data in old.items():
            (self.root / name).write_bytes(data)
        real = updater.atomic_write
        failed = False
        def fail_once(path, data, mode):
            nonlocal failed
            if path.name == 'VERSION' and not failed:
                failed = True
                raise OSError('simulated disk error')
            return real(path, data, mode)
        with patch.object(updater, 'atomic_write', side_effect=fail_once), self.assertRaises(OSError):
            updater.apply_snapshot(self.root, {'README.md': b'new', 'scripts/new.py': b'new', 'VERSION': b'1.0.1\n'}, '1.0.1', COMMIT)
        for name, data in old.items():
            self.assertEqual((self.root / name).read_bytes(), data)
        self.assertFalse((self.root / 'scripts/new.py').exists())
        self.assertFalse((self.root / updater.STATE).exists())
        self.assertFalse((self.root / updater.JOURNAL).exists())

    def test_next_run_restores_an_interrupted_transaction(self):
        (self.root / 'README.md').write_bytes(b'old readme')
        real = updater.atomic_write
        def interrupted(path, data, mode):
            if path.name == 'VERSION':
                raise KeyboardInterrupt()
            return real(path, data, mode)
        with patch.object(updater, 'atomic_write', side_effect=interrupted), \
                patch.object(updater, 'recover_interrupted', side_effect=RuntimeError('process killed')), \
                self.assertRaisesRegex(RuntimeError, 'process killed'):
            updater.apply_snapshot(self.root, {'README.md': b'new', 'VERSION': b'1.0.1\n'}, '1.0.1', COMMIT)
        self.assertEqual((self.root / 'README.md').read_bytes(), b'new')
        self.assertTrue((self.root / updater.JOURNAL).exists())
        updater.recover_interrupted(self.root)
        self.assertEqual((self.root / 'README.md').read_bytes(), b'old readme')
        self.assertFalse((self.root / 'VERSION').exists())
        self.assertFalse((self.root / updater.JOURNAL).exists())

    def test_tampered_recovery_cannot_target_installed_server(self):
        (self.root / updater.JOURNAL).write_text(json.dumps({'backup': '20261105-120000-abcdef12',
            'files': ['CS15Server-Linux/cstrike/server.cfg'], 'newFiles': ['CS15Server-Linux/cstrike/server.cfg']}))
        with self.assertRaises(ValueError):
            updater.recover_interrupted(self.root)

    def interrupted_receipt(self):
        identifier = '20261105-120000-abcdef12'
        saved = self.root / '.update-backups' / identifier / 'files'
        saved.mkdir(parents=True)
        for name in ('README.md', 'VERSION'):
            (self.root / name).write_bytes(b'new')
            (saved / name).write_bytes(b'old')
        (self.root / updater.JOURNAL).write_text(json.dumps({'backup': identifier,
            'files': ['README.md', 'VERSION'], 'newFiles': []}))
        return saved

    def test_recovery_failure_retains_journal_and_can_be_retried(self):
        self.interrupted_receipt()
        real = updater.atomic_write
        def fail(path, data, mode):
            if path.name == 'README.md':
                raise OSError('recovery disk error')
            return real(path, data, mode)
        with patch.object(updater, 'atomic_write', side_effect=fail), self.assertRaises(OSError):
            updater.recover_interrupted(self.root)
        self.assertTrue((self.root / updater.JOURNAL).exists())
        updater.recover_interrupted(self.root)
        self.assertFalse((self.root / updater.JOURNAL).exists())
        self.assertEqual((self.root / 'README.md').read_bytes(), b'old')
        self.assertEqual((self.root / 'VERSION').read_bytes(), b'old')

    def test_missing_backup_prevents_any_recovery_writes(self):
        saved = self.interrupted_receipt()
        (saved / 'VERSION').unlink()
        with self.assertRaises(OSError):
            updater.recover_interrupted(self.root)
        self.assertEqual((self.root / 'README.md').read_bytes(), b'new')
        self.assertEqual((self.root / 'VERSION').read_bytes(), b'new')
        self.assertTrue((self.root / updater.JOURNAL).exists())

    def test_download_failure_and_oversize_do_not_write_package_files(self):
        with patch.object(updater.urllib.request, 'urlopen', side_effect=OSError('offline')):
            with self.assertRaises(OSError):
                updater.request_bytes('https://example.test', 5)
        with patch.object(updater.urllib.request, 'urlopen', return_value=io.BytesIO(b'123456')):
            with self.assertRaises(ValueError):
                updater.request_bytes('https://example.test', 5)
        self.assertEqual(list(self.root.iterdir()), [])

    def run_main(self, *arguments):
        # Exercise the Linux orchestration; real flock is a Mint acceptance check.
        fake_fcntl = types.SimpleNamespace(LOCK_EX=2, LOCK_NB=4, flock=lambda *args: None)
        with patch.object(updater.sys, 'argv', ['Update.sh', str(self.root), *arguments]), \
                patch.object(updater.sys, 'platform', 'linux'), \
                patch.dict('sys.modules', {'fcntl': fake_fcntl}), \
                patch.object(updater, 'refuse_running'):
            updater.main()

    def seed_package(self):
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/server_panel.py').write_bytes(b'old helper')
        (self.root / 'Setup-Linux.sh').write_bytes(b'old setup')

    def test_main_check_only_does_not_replace_package_files(self):
        self.seed_package()
        with patch.object(updater, 'latest_commit', return_value=COMMIT), \
                patch.object(updater, 'request_bytes', return_value=archive(snapshot())) as download:
            self.run_main('--check')
        self.assertEqual((self.root / 'scripts/server_panel.py').read_bytes(), b'old helper')
        self.assertFalse((self.root / updater.STATE).exists())
        self.assertFalse((self.root / '.update-backups').exists())
        self.assertEqual(download.call_args.args[0], f'https://codeload.github.com/{updater.REPOSITORY}/zip/{COMMIT}')

    def test_main_update_uses_exact_snapshot_and_local_version_needs_no_network(self):
        self.seed_package()
        with patch.object(updater, 'latest_commit', return_value=COMMIT), \
                patch.object(updater, 'request_bytes', return_value=archive(snapshot())):
            self.run_main()
        self.assertEqual((self.root / 'VERSION').read_text().strip(), '1.0.1')
        with patch.object(updater, 'request_bytes', side_effect=AssertionError('unexpected network')):
            self.run_main('--version')

    def test_main_rejects_git_checkout_and_parallel_updater(self):
        self.seed_package()
        (self.root / '.git').mkdir()
        with self.assertRaisesRegex(ValueError, 'Git checkout'):
            self.run_main()
        (self.root / '.git').rmdir()
        busy = types.SimpleNamespace(LOCK_EX=2, LOCK_NB=4,
            flock=lambda *args: (_ for _ in ()).throw(BlockingIOError()))
        with patch.object(updater.sys, 'argv', ['Update.sh', str(self.root)]), \
                patch.object(updater.sys, 'platform', 'linux'), \
                patch.dict('sys.modules', {'fcntl': busy}), \
                patch.object(updater, 'latest_commit', side_effect=AssertionError('unexpected network')):
            with self.assertRaisesRegex(ValueError, 'already running'):
                updater.main()

    @unittest.skipUnless(os.name == 'posix', 'POSIX executable permissions')
    def test_new_shell_entry_points_are_executable(self):
        updater.apply_snapshot(self.root, snapshot(), '1.0.1', COMMIT)
        self.assertTrue((self.root / 'Update.sh').stat().st_mode & stat.S_IXUSR)


if __name__ == '__main__':
    unittest.main(verbosity=2)
