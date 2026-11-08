"""Entry-point checks using disposable installs, never the operator server."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash') or ('C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else None)


@unittest.skipUnless(os.name == 'nt', 'Windows launcher')
class WindowsLaunchers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='CS15 package ')
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        shutil.copyfile(ROOT / 'start-server.cmd', self.root / 'start-server.cmd')
        shutil.copyfile(ROOT / 'scripts/start-cs15server.ps1', self.root / 'scripts/start-cs15server.ps1')
        self.server = self.root / 'CS15Server'
        self.server.mkdir()
        (self.server / 'hlds.exe').touch()
        (self.server / 'Start-CS15.cmd').write_text('@echo off\ncd > started.txt\nexit /b 0\n')

    def tearDown(self):
        self.temp.cleanup()

    def run_launcher(self, *arguments):
        return subprocess.run([str(self.root / 'start-server.cmd'), *arguments],
                              cwd=ROOT, input='\n', capture_output=True, text=True, timeout=10)

    def test_main_folder_starter_uses_its_own_install_from_another_cwd(self):
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path((self.server / 'started.txt').read_text().strip()), self.server)

    def test_custom_directory_and_exit_code(self):
        custom = self.root / 'custom install'
        self.server.rename(custom)
        (custom / 'Start-CS15.cmd').write_text('@echo off\ncd > started.txt\nexit /b 7\n')
        result = self.run_launcher('-ServerDirectory', str(custom))
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(Path((custom / 'started.txt').read_text().strip()), custom)

    def test_incomplete_install_is_not_started(self):
        (self.server / '.install-incomplete').touch()
        result = self.run_launcher()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('incomplete', result.stderr)
        self.assertFalse((self.server / 'started.txt').exists())

    def test_whatif_validates_without_starting(self):
        result = self.run_launcher('-WhatIf')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.server / 'started.txt').exists())


@unittest.skipUnless(BASH and Path(BASH).is_file() and (ROOT / 'start-server.sh').is_file(),
                     'Linux branch launchers and Bash are required')
class LinuxLaunchers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='CS15 package ')
        self.root = Path(self.temp.name)
        self.server = self.root / 'CS15Server-Linux'
        self.server.mkdir()
        for name in ('start-server.sh', 'start-panel.sh'):
            shutil.copyfile(ROOT / name, self.root / name)
        (self.server / 'hlds').touch()
        (self.server / 'Start-CS15.sh').write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$PWD" "$@"\n', newline='\n')
        binary = self.root / 'fake-bin'
        binary.mkdir()
        stub = binary / 'python3'
        stub.write_text('#!/usr/bin/env bash\nif [[ "$1" == "-c" ]]; then exit 0; fi\nprintf "%s\\n" "$@"\n', newline='\n')
        stub.chmod(0o755)
        self.environment = os.environ.copy()
        prefix = str(binary).replace('\\', '/')
        if os.name == 'nt':
            prefix = '/' + prefix[0].lower() + prefix[2:]
            self.environment['PATH'] = prefix + ':/usr/bin:/bin'
        else:
            self.environment['PATH'] = prefix + os.pathsep + self.environment['PATH']

    def tearDown(self):
        self.temp.cleanup()

    def run_launcher(self, name, *arguments, env=None):
        return subprocess.run([BASH, str(self.root / name), *arguments], cwd=ROOT,
                              capture_output=True, text=True, timeout=10, env=env or self.environment)

    def test_server_default_and_argument_boundaries(self):
        result = self.run_launcher('start-server.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        custom = self.root / 'custom install'
        self.server.rename(custom)
        result = self.run_launcher('start-server.sh', str(custom), '+hostname', 'A server with spaces')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[-2:], ['+hostname', 'A server with spaces'])

    def test_missing_and_incomplete_install(self):
        (self.server / '.install-incomplete').touch()
        result = self.run_launcher('start-server.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('incomplete', result.stderr)
        (self.server / '.install-incomplete').unlink()
        (self.server / 'hlds').unlink()
        result = self.run_launcher('start-server.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('setup-linux.sh', result.stderr)

    def test_panel_passes_package_and_server_paths_without_splitting(self):
        binary = self.root / 'bin'
        binary.mkdir()
        stub = binary / 'python3'
        stub.write_text('#!/usr/bin/env bash\nif [[ "$1" == "-c" ]]; then exit 0; fi\nprintf "%s\\n" "$@"\n', newline='\n')
        stub.chmod(0o755)
        env = os.environ.copy()
        # Git Bash needs a POSIX PATH, even though the subprocess starts on Windows.
        prefix = str(binary).replace('\\', '/')
        if os.name == 'nt':
            prefix = '/' + prefix[0].lower() + prefix[2:]
            env['PATH'] = prefix + ':/usr/bin:/bin'
        else:
            env['PATH'] = prefix + os.pathsep + env['PATH']
        result = self.run_launcher('start-panel.sh', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = result.stdout.splitlines()
        self.assertEqual(args[-1], '--open-browser')
        self.assertEqual(args[1], '--server')
        self.assertTrue(args[0].endswith('/scripts/server_panel.py'))
        self.assertTrue(args[2].endswith('/CS15Server-Linux'))
        result = self.run_launcher('start-panel.sh', str(self.root / 'missing'), env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not found', result.stderr)


if __name__ == '__main__':
    unittest.main()
