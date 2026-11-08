"""Native Linux regression tests for the *outer* console and terminal loss.

Only fake servers in temporary folders are started. Each test owns its outer
PTY and records process identities before signaling anything during cleanup.
Run on Mint with: python3 scripts/test_console_lifecycle.py
"""
import errno
import json
import os
from pathlib import Path
import select
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

RECORDER = Path(__file__).with_name('run_logged_server.py').resolve()
NATIVE = sys.platform == 'linux' and shutil.which('script') is not None

FAKE_SERVER = '''import json,os,pathlib,signal,sys
def identity(pid):
    fields=pathlib.Path(f"/proc/{pid}/stat").read_text().rsplit(")",1)[1].split()
    return {"pid":pid,"start":fields[19]}
mode=sys.argv[2]
if mode=="ignore-term":
    signal.signal(signal.SIGTERM,signal.SIG_IGN)
    # Closing script's inner PTY can itself deliver HUP. Ignore that too so
    # these cases actually exercise the owned-child cleanup/PDEATHSIG path.
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
identities={"server":identity(os.getpid()),"script":identity(os.getppid())}
destination=pathlib.Path(sys.argv[1])
temporary=destination.with_suffix(".writing")
temporary.write_text(json.dumps(identities))
temporary.replace(destination)
print("FAKE_STDOUT_READY",flush=True)
print("FAKE_STDERR_READY",file=sys.stderr,flush=True)
print("FAKE_TTY="+str(os.isatty(0) and os.isatty(1)),flush=True)
if mode=="interactive":
    value=sys.stdin.readline().strip()
    print("FAKE_INPUT="+value,flush=True)
    sys.exit(7)
while True:
    signal.pause()
'''


def process_identity(pid):
    """Linux start ticks distinguish this test's process from a reused PID."""
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return {'pid': pid, 'start': fields[19], 'state': fields[0]}
    except (OSError, ValueError, IndexError):
        return None


def same_live_process(identity):
    current = process_identity(identity['pid'])
    return bool(current and current['start'] == identity['start'] and current['state'] != 'Z')


@unittest.skipUnless(NATIVE, 'Requires native Linux, /proc and util-linux script')
class OuterConsoleLifecycle(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="CS15 outer console's ")
        self.root = Path(self.temporary.name)
        self.fake = self.root / 'fake_server.py'
        self.fake.write_text(FAKE_SERVER, encoding='utf-8')
        self.identities_file = self.root / 'owned-processes.json'
        self.identities = {}
        self.wrapper_pid = None
        self.wrapper_status = None
        self.master = None
        self.output = bytearray()

    def tearDown(self):
        # Only exact PID+start-time identities collected from this fixture can
        # be killed. Never use pkill, process-name searches or inherited groups.
        self.capture_inner_identities()
        for identity in reversed(list(self.identities.values())):
            if same_live_process(identity):
                try:
                    os.kill(identity['pid'], signal.SIGKILL)
                except ProcessLookupError:
                    pass
        if self.master is not None:
            os.close(self.master)
            self.master = None
        if self.wrapper_pid is not None and self.wrapper_status is None:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if self.poll_wrapper() is not None:
                    break
                time.sleep(0.05)
        self.temporary.cleanup()

    def command(self, mode):
        return [sys.executable, str(RECORDER), '--server', str(self.root),
                '--require-terminal', '--', sys.executable, str(self.fake),
                str(self.identities_file), mode]

    def start_outer_terminal(self, mode, command=None):
        import pty
        command = self.command(mode) if command is None else command
        pid, master = pty.fork()
        if pid == 0:
            try:
                # Also exercise installed launchers addressed relative to their
                # parent, which caught a previous double-directory regression.
                os.chdir(self.root.parent)
                os.execv(command[0], command)
            except BaseException:
                os._exit(127)
        self.wrapper_pid = pid
        self.master = master
        identity = process_identity(pid)
        if identity is None:
            self.fail('Recorder disappeared before its process identity could be recorded.')
        self.identities['recorder'] = identity

    def capture_inner_identities(self):
        if not self.identities_file.exists():
            return
        try:
            recorded = json.loads(self.identities_file.read_text())
        except (OSError, ValueError):
            return
        for name in ('script', 'server'):
            identity = recorded.get(name)
            if (isinstance(identity, dict) and isinstance(identity.get('pid'), int)
                    and isinstance(identity.get('start'), str)):
                self.identities[name] = identity

    def read_outer_output(self, timeout=0.05):
        if self.master is None:
            return
        ready, _, _ = select.select([self.master], [], [], timeout)
        if ready:
            try:
                self.output.extend(os.read(self.master, 65536))
            except OSError as error:
                if error.errno != errno.EIO:
                    raise

    def wait_until_ready(self):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            self.read_outer_output()
            self.capture_inner_identities()
            if b'FAKE_TTY=True' in self.output and 'server' in self.identities:
                logs = list((self.root / 'logs/console').glob('*.log'))
                if len(logs) == 1:
                    recorded = logs[0].read_text(errors='replace')
                    if all(marker in recorded for marker in
                           ('FAKE_STDOUT_READY', 'FAKE_STDERR_READY', 'FAKE_TTY=True')):
                        return
            if self.poll_wrapper() is not None:
                break
        self.fail('Fake server did not start in an interactive terminal:\n' + self.output.decode(errors='replace'))

    def poll_wrapper(self):
        if self.wrapper_status is not None or self.wrapper_pid is None:
            return self.wrapper_status
        try:
            pid, status = os.waitpid(self.wrapper_pid, os.WNOHANG)
        except ChildProcessError:
            return self.wrapper_status
        if pid:
            self.wrapper_status = status
        return self.wrapper_status

    def wait_for_all_to_stop(self):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            self.read_outer_output()
            self.poll_wrapper()
            if self.wrapper_status is not None and not any(
                    same_live_process(identity) for identity in self.identities.values()):
                return
            time.sleep(0.05)
        alive = {name: identity for name, identity in self.identities.items() if same_live_process(identity)}
        self.fail(f'Owned processes survived the terminal shutdown deadline: {alive}')

    def log_text(self):
        logs = list((self.root / 'logs/console').glob('*.log'))
        self.assertEqual(len(logs), 1, 'One recording is required for this start.')
        return logs[0].read_text(encoding='utf-8', errors='replace')

    def test_real_outer_terminal_accepts_input_and_records_nonzero_exit(self):
        self.start_outer_terminal('interactive')
        self.wait_until_ready()
        # The script -f output must already be in the log while the child waits
        # for input, rather than appearing only when its streams are closed.
        live_log = self.log_text()
        self.assertIn('FAKE_STDOUT_READY', live_log)
        self.assertIn('FAKE_STDERR_READY', live_log)
        self.assertIn('FAKE_TTY=True', live_log)
        os.write(self.master, b'lifecycle-check\n')
        self.wait_for_all_to_stop()
        self.assertEqual(os.waitstatus_to_exitcode(self.wrapper_status), 7)
        text = self.log_text()
        self.assertIn('FAKE_INPUT=lifecycle-check', text)
        self.assertIn('CS15_SESSION_END', text)
        self.assertIn('exit_code=7', text)

    def test_required_terminal_rejects_headless_start_before_child(self):
        result = subprocess.run(self.command('normal'), stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.capture_inner_identities()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.identities_file.exists(), 'Headless validation must happen before fake HLDS starts.')
        self.assertIn('terminal', self.log_text().lower())

    def test_console_also_requires_terminal_by_default(self):
        command = self.command('normal')
        command.remove('--require-terminal')
        result = subprocess.run(command, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.capture_inner_identities()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.identities_file.exists())
        self.assertIn('terminal', self.log_text().lower())

    def assert_public_launcher_has_one_recording(self, installed_direct):
        import run_logged_server
        launcher = self.root / 'Start-CS15.sh'
        launcher.write_text('#!/usr/bin/env bash\nset -euo pipefail\n'
            'cd -- "$(dirname -- "${BASH_SOURCE[0]}")"\n'
            'exec ./hlds -game cstrike +ip 127.0.0.1 "$@"\n', encoding='utf-8')
        fake_hlds = self.root / 'hlds'
        fake_hlds.write_text('#!/bin/sh\nexec ' + shlex.join([
            sys.executable, str(self.fake), str(self.identities_file), 'interactive']) + '\n',
            encoding='utf-8')
        fake_hlds.chmod(0o700)
        bash = shutil.which('bash')
        self.assertIsNotNone(bash, 'The Linux package launchers require bash.')
        if installed_direct:
            run_logged_server.ensure_launcher_logging(self.root, launcher)
            command = [bash, self.root.name + '/Start-CS15.sh']
        else:
            command = [bash, str(RECORDER.parent.parent / 'start-server.sh'), str(self.root)]
        self.start_outer_terminal('interactive', command)
        self.wait_until_ready()
        os.write(self.master, b'launcher-check\n')
        self.wait_for_all_to_stop()
        self.assertEqual(os.waitstatus_to_exitcode(self.wrapper_status), 7)
        text = self.log_text()
        self.assertEqual(text.count('CS15_SESSION_START'), 1)
        self.assertIn('FAKE_INPUT=launcher-check', text)
        self.assertIn('CS15_SESSION_END', text)
        self.assertIn('exit_code=7', text)

    def test_package_launcher_creates_one_interactive_recording(self):
        self.assert_public_launcher_has_one_recording(installed_direct=False)

    def test_relative_installed_launcher_creates_one_interactive_recording(self):
        self.assert_public_launcher_has_one_recording(installed_direct=True)

    def assert_outer_hangup_stops_owned_processes(self, mode):
        self.start_outer_terminal(mode)
        self.wait_until_ready()
        self.assertTrue(same_live_process(self.identities['server']))
        os.close(self.master)
        self.master = None
        self.wait_for_all_to_stop()
        text = self.log_text()
        self.assertIn('CS15_SESSION_END', text)
        self.assertRegex(text, r'exit_code=[1-9][0-9]*')

    def test_outer_terminal_close_stops_a_normal_server(self):
        self.assert_outer_hangup_stops_owned_processes('normal')

    def test_outer_terminal_close_stops_a_server_ignoring_sigterm(self):
        self.assert_outer_hangup_stops_owned_processes('ignore-term')

    def test_early_script_death_stops_owned_server_ignoring_sigterm(self):
        self.start_outer_terminal('ignore-term')
        self.wait_until_ready()
        script = self.identities['script']
        self.assertTrue(same_live_process(script))
        os.kill(script['pid'], signal.SIGKILL)
        self.wait_for_all_to_stop()
        text = self.log_text()
        self.assertIn('CS15_SESSION_END', text)
        self.assertRegex(text, r'exit_code=[1-9][0-9]*')


if __name__ == '__main__':
    unittest.main(verbosity=2)
