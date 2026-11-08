"""Recorder and legacy-launcher safety checks using disposable server folders."""
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import run_logged_server as recorder


class ConsoleRecording(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="CS15 LAN's server ")
        self.root = Path(self.temp.name).resolve()
        self.launcher = self.root / 'Start-CS15.sh'
        self.original = ('#!/usr/bin/env bash\nset -euo pipefail\n'
            'cd -- "$(dirname -- "${BASH_SOURCE[0]}")"\n'
            'export LD_LIBRARY_PATH="$PWD${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
            'exec ./hlds -game cstrike +ip 127.0.0.1 +map de_dust2 "$@"\n').encode()
        self.launcher.write_bytes(self.original)
        (self.root / 'cstrike').mkdir()
        (self.root / 'cstrike/server.cfg').write_bytes(b'private fixture settings')

    def tearDown(self):
        self.temp.cleanup()

    def test_launcher_upgrade_is_backed_up_idempotent_and_preserves_command_and_settings(self):
        recorder.ensure_launcher_logging(self.root, self.launcher)
        text = self.launcher.read_text()
        preamble = recorder.recording_preamble()
        self.assertEqual(text.replace(preamble, '').encode(), self.original)
        self.assertLess(text.index(recorder.MARKER), text.index('export LD_LIBRARY_PATH'))
        self.assertEqual((self.root / 'cstrike/server.cfg').read_bytes(), b'private fixture settings')
        backups = list((self.root / '_configurator/recording-backups').iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / 'Start-CS15.sh').read_bytes(), self.original)
        self.assertEqual((self.root / 'run_logged_server.py').read_bytes(), Path(recorder.__file__).read_bytes())
        recorder.ensure_launcher_logging(self.root, self.launcher)
        self.assertEqual(self.launcher.read_text(), text)
        self.assertEqual(list((self.root / '_configurator/recording-backups').iterdir()), backups)

    def test_unsupported_launcher_is_never_changed(self):
        self.launcher.write_bytes(b'#!/bin/sh\necho custom launcher\n')
        with self.assertRaises(ValueError):
            recorder.ensure_launcher_logging(self.root, self.launcher)
        self.assertFalse((self.root / 'run_logged_server.py').exists())

    def test_failed_launcher_install_restores_previous_helper_and_launcher(self):
        old_helper = b'previous helper'
        (self.root / 'run_logged_server.py').write_bytes(old_helper)
        real = recorder.replace_file
        def fail(path, data, mode):
            if path == self.launcher:
                raise OSError('simulated read-only launcher')
            return real(path, data, mode)
        with patch.object(recorder, 'replace_file', side_effect=fail), self.assertRaises(OSError):
            recorder.ensure_launcher_logging(self.root, self.launcher)
        self.assertEqual(self.launcher.read_bytes(), self.original)
        self.assertEqual((self.root / 'run_logged_server.py').read_bytes(), old_helper)

    def test_unique_logs_are_never_truncated_and_record_nonzero_exit(self):
        first = recorder.new_log_file(self.root)
        first.write_bytes(b'previous crash\n')
        command = [str(self.root / 'hlds'), '+rcon_password', 'do-not-log-this-secret']
        process = Mock()
        process.wait.return_value = 255
        with patch.object(recorder.shutil, 'which', return_value='/usr/bin/script'), \
                patch.object(recorder.subprocess, 'Popen', return_value=process) as start:
            self.assertEqual(recorder.run_recorded(self.root, command), 255)
        self.assertEqual(first.read_bytes(), b'previous crash\n')
        logs = sorted((self.root / 'logs/console').glob('*.log'))
        self.assertEqual(len(logs), 2)
        latest = next(path for path in logs if path != first)
        text = latest.read_text()
        self.assertIn('CS15_SESSION_START', text)
        self.assertIn('exit_code=255', text)
        self.assertNotIn('do-not-log-this-secret', text)
        arguments = start.call_args.args[0]
        shell = arguments[arguments.index('-c') + 1]
        self.assertNotIn('do-not-log-this-secret', shell)
        self.assertEqual(shlex.split(shell), ['exec', sys.executable, str(Path(recorder.__file__).resolve()), '--child'])
        self.assertEqual(json.loads(start.call_args.kwargs['env'][recorder.COMMAND]), command)
        self.assertTrue(set(('-q', '-f', '-e', '-a')) <= set(arguments))
        self.assertNotIn('stdin', start.call_args.kwargs)
        self.assertNotIn('stdout', start.call_args.kwargs)
        self.assertNotIn('start_new_session', start.call_args.kwargs)

    def test_signal_status_is_recorded(self):
        process = Mock()
        process.wait.return_value = -signal.SIGTERM
        with patch.object(recorder.shutil, 'which', return_value='/usr/bin/script'), \
                patch.object(recorder.subprocess, 'Popen', return_value=process):
            self.assertEqual(recorder.run_recorded(self.root, ['fake-hlds']), 128 + signal.SIGTERM)
        text = next((self.root / 'logs/console').glob('*.log')).read_text()
        self.assertIn('exit_code=143', text)

    def test_termination_is_forwarded_and_recorded_before_return(self):
        process = Mock()
        process.poll.return_value = None
        def wait():
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            return 0
        process.wait.side_effect = wait
        with patch.object(recorder.shutil, 'which', return_value='/usr/bin/script'), \
                patch.object(recorder.subprocess, 'Popen', return_value=process):
            self.assertEqual(recorder.run_recorded(self.root, ['fake-hlds']), 143)
        process.send_signal.assert_called_once_with(signal.SIGTERM)
        text = next((self.root / 'logs/console').glob('*.log')).read_text()
        self.assertIn('signal=15', text)

    def test_termination_during_spawn_is_not_swallowed(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.return_value = 0
        def spawn(*args, **kwargs):
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            return process
        with patch.object(recorder.shutil, 'which', return_value='/usr/bin/script'), \
                patch.object(recorder.subprocess, 'Popen', side_effect=spawn):
            self.assertEqual(recorder.run_recorded(self.root, ['fake-hlds']), 143)
        process.send_signal.assert_called_once_with(signal.SIGTERM)
        process.wait.assert_called_once()
        self.assertIn('CS15_SESSION_END', next((self.root / 'logs/console').glob('*.log')).read_text())

    def test_missing_recorder_and_invalid_log_prevent_server_launch(self):
        with patch.object(recorder.shutil, 'which', return_value=None), \
                patch.object(recorder.subprocess, 'Popen') as start:
            with self.assertRaisesRegex(ValueError, 'util-linux'):
                recorder.run_recorded(self.root, ['fake-hlds'])
            start.assert_not_called()
        with patch.object(recorder.shutil, 'which', return_value='/bin/script'), \
                patch.object(recorder.subprocess, 'Popen') as start:
            with self.assertRaises(ValueError):
                recorder.run_recorded(self.root, ['fake-hlds'], self.root / 'outside.log')
            start.assert_not_called()

    @unittest.skipUnless(os.name == 'posix', 'POSIX file permissions')
    def test_logs_are_private(self):
        log = recorder.new_log_file(self.root)
        self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(log.parent.stat().st_mode), 0o700)


@unittest.skipUnless(sys.platform == 'linux' and shutil.which('script'), 'Native Linux util-linux PTY')
class NativeConsoleRecording(unittest.TestCase):
    def test_package_and_installed_launchers_each_create_exactly_one_recording(self):
        package = Path(__file__).resolve().parents[1]
        for direct in (False, True):
            with self.subTest(installed_direct=direct), tempfile.TemporaryDirectory(prefix='CS15 launcher ') as directory:
                root = Path(directory)
                launcher = root / 'Start-CS15.sh'
                launcher.write_text('#!/usr/bin/env bash\ncd -- "$(dirname -- "${BASH_SOURCE[0]}")"\n'
                    'exec ./hlds -game cstrike "$@"\n')
                fake = root / 'hlds'
                fake.write_text('#!/bin/sh\necho stdout-ready\necho stderr-ready >&2\nexit 7\n')
                fake.chmod(0o700)
                if direct:
                    recorder.ensure_launcher_logging(root, launcher)
                    command = ['bash', root.name + '/Start-CS15.sh']
                else:
                    command = ['bash', str(package / 'start-server.sh'), str(root)]
                result = subprocess.run(command, cwd=root.parent, capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 7, result.stderr)
                logs = list((root / 'logs/console').glob('*.log'))
                self.assertEqual(len(logs), 1)
                text = logs[0].read_text()
                self.assertEqual(text.count('CS15_SESSION_START'), 1)
                self.assertIn('stdout-ready', text)
                self.assertIn('stderr-ready', text)
                self.assertIn('exit_code=7', text)

    def test_real_pty_flushes_both_streams_and_retains_nonzero_exit(self):
        with tempfile.TemporaryDirectory(prefix='CS15 native recording ') as directory:
            root = Path(directory)
            fake = root / 'fake.py'
            fake.write_text('import sys,time,os\nprint("stdout-ready",flush=True)\n'
                'print("stderr-ready",file=sys.stderr,flush=True)\n'
                'print("tty="+str(os.isatty(0)),flush=True)\ntime.sleep(1)\nsys.exit(7)\n')
            process = subprocess.Popen([sys.executable, recorder.__file__, '--server', str(root),
                '--', sys.executable, str(fake)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                logs = list((root / 'logs/console').glob('*.log'))
                if logs and 'stdout-ready' in logs[0].read_text(errors='replace'):
                    break
                time.sleep(0.05)
            self.assertTrue(logs)
            process.communicate(timeout=10)
            self.assertEqual(process.returncode, 7)
            text = logs[0].read_text(errors='replace')
            self.assertIn('stdout-ready', text)
            self.assertIn('stderr-ready', text)
            self.assertIn('tty=True', text)
            self.assertIn('exit_code=7', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
