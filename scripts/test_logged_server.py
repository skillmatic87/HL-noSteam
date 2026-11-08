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
        def wait(*args, **kwargs):
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

    def test_lost_terminal_uses_scripts_supported_termination_signal(self):
        # Windows has no SIGHUP; use the POSIX number to exercise the mapping.
        for during_spawn in (False, True):
            with self.subTest(during_spawn=during_spawn), patch.object(recorder.signal, 'SIGHUP', 1, create=True), \
                    patch.object(recorder.signal, 'signal', wraps=signal.signal) as register:
                handlers = {}
                def install(number, handler):
                    previous = handlers.get(number, signal.SIG_DFL)
                    handlers[number] = handler
                    return previous
                register.side_effect = install
                process = Mock()
                process.poll.return_value = None
                process.wait.side_effect = lambda *args, **kwargs: (handlers[1](1, None) if not during_spawn else None) or 0
                def spawn(*args, **kwargs):
                    if during_spawn:
                        handlers[1](1, None)
                    return process
                with patch.object(recorder.shutil, 'which', return_value='/usr/bin/script'), \
                        patch.object(recorder.subprocess, 'Popen', side_effect=spawn):
                    self.assertEqual(recorder.run_recorded(self.root, ['fake-hlds']), 129)
                process.send_signal.assert_called_once_with(signal.SIGTERM)


    def test_missing_recorder_and_invalid_log_prevent_server_launch(self):
        with patch.object(recorder.shutil, 'which', return_value=None), \
                patch.object(recorder.subprocess, 'Popen') as start:
            with self.assertRaisesRegex(ValueError, 'util-linux'):
                recorder.run_recorded(self.root, ['fake-hlds'])
            start.assert_not_called()

    def test_child_identity_is_checked_after_parent_death_protection_is_armed(self):
        for expected_parent, succeeds in ((1234, True), (4321, False)):
            with self.subTest(parent=expected_parent):
                control = self.root / 'parent-control'
                control.write_bytes(b'1234\n')
                libc = Mock()
                libc.prctl.return_value = 0
                with patch.object(recorder.sys, 'platform', 'linux'), \
                        patch.object(recorder.signal, 'SIGKILL', 9, create=True), \
                        patch.object(recorder.ctypes, 'CDLL', return_value=libc), \
                        patch.object(recorder.os, 'getppid', return_value=expected_parent):
                    if succeeds:
                        recorder.protect_child_parent(control)
                        self.assertFalse(control.exists())
                    else:
                        with self.assertRaisesRegex(ValueError, 'parent exited'):
                            recorder.protect_child_parent(control)
                libc.prctl.assert_called_once_with(1, 9, 0, 0, 0)

    def test_malformed_parent_record_prevents_server_execution(self):
        control = self.root / 'parent-control'
        for record in (b'0\n', b'not-a-pid\n', b'1234', b'1234\nextra'):
            control.write_bytes(record)
            with self.subTest(record=record), patch.object(recorder.ctypes, 'CDLL') as libc:
                with self.assertRaises(ValueError):
                    recorder.protect_child_parent(control)
                libc.assert_not_called()

    def test_termination_deadline_escalates_only_the_owned_recorder(self):
        process = Mock(pid=1234)
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('script', 0.25), 0]
        def spawn(*args, **kwargs):
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            return process
        with patch.object(recorder.shutil, 'which', return_value='/usr/bin/script'), \
                patch.object(recorder.subprocess, 'Popen', side_effect=spawn), \
                patch.object(recorder.time, 'monotonic', side_effect=[0, 6]):
            self.assertEqual(recorder.run_recorded(self.root, ['fake-hlds']), 143)
        process.kill.assert_called_once()
        self.assertEqual(list((self.root / 'logs/console').glob('.recorder-parent-*')), [])
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
