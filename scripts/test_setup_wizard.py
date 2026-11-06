"""Interactive setup, private input and credential persistence regression tests."""
import contextlib
import inspect
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings

import install_cs15_linux as installer


class SetupWizardTests(unittest.TestCase):
    def recommended(self):
        answers = ['LAN fixture', 'j', 'n', 'y', 'ja', 'YES', 'y', 'j', 'n', 'y', 'TestAdmin']
        with patch('builtins.input', side_effect=answers), contextlib.redirect_stdout(io.StringIO()):
            return installer.get_settings(None)

    def test_recommended_flow_and_numbered_questions(self):
        answers = ['LAN fixture', 'j', 'n', 'y', 'ja', 'YES', 'y', 'j', 'n', 'y', 'TestAdmin']
        with patch('builtins.input', side_effect=answers) as reader, contextlib.redirect_stdout(io.StringIO()):
            settings = installer.get_settings(None)
        self.assertEqual([int(call.args[0].split('.')[0]) for call in reader.call_args_list], list(range(1, 12)))
        self.assertEqual(settings, dict(ServerName='LAN fixture', MapMinutes=20, FriendlyFire=0,
                         BotTarget=16, BotDifficulty=2, SoundCooldown=3, SoundQuota=100,
                         RankBots=0, RankScore='KillsMinusDeaths', AdminName='TestAdmin'))

    def test_disabled_bots_skip_followups(self):
        with patch('builtins.input', side_effect=['LAN', 'y', 'n', 'n', 'y', 'y', 'n', 'n', 'Admin']) as reader, contextlib.redirect_stdout(io.StringIO()):
            settings = installer.get_settings(None)
        self.assertEqual([int(call.args[0].split('.')[0]) for call in reader.call_args_list], [1, 2, 3, 4, 7, 8, 9, 10, 11])
        self.assertEqual((settings['BotTarget'], settings['BotDifficulty'], settings['RankScore']), (0, 2, 'Kills'))

    def test_custom_values_and_rejected_boundaries(self):
        answers = ['LAN', 'n', '5', '180', 'j', 'j', 'n', '0', '32', 'n', '4', 'n', '0', 'n', '1000', 'j', 'n', 'Admin']
        with patch('builtins.input', side_effect=answers), contextlib.redirect_stdout(io.StringIO()):
            settings = installer.get_settings(None)
        for key, value in dict(MapMinutes=180, BotTarget=32, BotDifficulty=4, SoundCooldown=0, SoundQuota=1000).items():
            self.assertEqual(settings[key], value)

    def test_yes_no_aliases_and_empty_retry(self):
        for token in ('y', 'yes', 'j', 'ja', ' Y ', 'JA'):
            with self.subTest(token=token), patch('builtins.input', return_value=token):
                self.assertEqual(installer.ask_yes_no('Question?'), 1)
        for token in ('n', 'no', 'nein', ' N ', 'NEIN'):
            with self.subTest(token=token), patch('builtins.input', return_value=token):
                self.assertEqual(installer.ask_yes_no('Question?'), 0)
        with patch('builtins.input', side_effect=['', 'true', '1', 'y']) as reader, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.ask_yes_no('Question?'), 1)
            self.assertEqual(reader.call_count, 4)

    def test_password_confirmation_is_exact_and_never_echoed(self):
        output = io.StringIO()
        with patch.object(installer.getpass, 'getpass', side_effect=['bad space', 'Match$&', 'match$&', 'Match$&', 'Match$&']) as reader, contextlib.redirect_stdout(output):
            self.assertEqual(installer.read_password('12. AMX password'), 'Match$&')
        self.assertEqual(reader.call_count, 5)
        self.assertNotIn('Match$&', output.getvalue())
        self.assertNotIn('bad space', output.getvalue())

    def test_three_private_questions_are_ordered(self):
        with patch.object(installer.getpass, 'getpass', side_effect=['Amx$&', 'Amx$&', 'Yb$1', 'Yb$1', 'Rcon$$', 'Rcon$$']) as reader:
            credentials = installer.read_credentials()
        self.assertEqual(set(credentials), set(installer.CREDENTIAL_FIELDS))
        self.assertEqual([call.args[0] for call in reader.call_args_list],
                         ['12. AMX password: ', 'Confirm password: ', '13. YaPB password: ',
                          'Confirm password: ', '14. RCON password: ', 'Confirm password: '])

    def test_password_reader_refuses_echo_fallback_and_eof(self):
        def fallback(*args):
            warnings.warn('Echo fallback', installer.getpass.GetPassWarning)
            self.fail('The echoed fallback was allowed to continue.')
        with patch.object(installer.getpass, 'getpass', side_effect=fallback), self.assertRaisesRegex(ValueError, 'private terminal'):
            installer.private_input('Password')
        with patch.object(installer.getpass, 'getpass', side_effect=EOFError), self.assertRaises(ValueError):
            installer.private_input('Password')

    def test_credential_boundaries_and_automatic_generation(self):
        for value in ('x', 'x' * 31, "A$&$1$$'!%"):
            self.assertEqual(installer.validate_password(value), value)
        for value in ('', ' ', 'bad space', 'x' * 32, 'bad"', 'bad;', 'bad\\', 'bad\n', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                installer.validate_password(value)
        generated = installer.validate_credentials(None)
        self.assertEqual(len(set(generated.values())), 3)
        for value in generated.values():
            self.assertEqual(len(value), 30)
            installer.validate_password(value)

    def test_public_json_keeps_its_ten_fields_and_needs_no_input(self):
        settings = self.recommended()
        settings['AmxPassword'] = 'DO-NOT-COPY-PRIVATE-JSON'
        settings.update(BotTarget=0, BotDifficulty=4)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_text(json.dumps(settings))
            with patch('builtins.input', side_effect=AssertionError('Unattended setup prompted')), patch.object(installer.getpass, 'getpass', side_effect=AssertionError('Unattended password prompt')):
                public = installer.get_settings(path)
        self.assertEqual(set(public), set(installer.PUBLIC_FIELDS))
        self.assertEqual((public['BotTarget'], public['BotDifficulty']), (0, 4))
        self.assertNotIn('DO-NOT-COPY', json.dumps(public))

    def test_all_private_outputs_preserve_literal_values(self):
        settings = {**self.recommended(), 'RconPassword': 'DO-NOT-COPY-PRIVATE-JSON'}
        credentials = dict(AmxPassword='Amx$&$1$$', YbPassword="Yb$&$1$$'T", RconPassword='Rcon%&$1')
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()) as output:
            server = Path(directory)
            bot_file = server / 'cstrike/addons/yapb/conf/yapb.cfg'
            bot_file.parent.mkdir(parents=True)
            bot_file.write_text('yb_password ""\nyb_password_key "_ybpw"\nyb_quota 0\n')
            installer.write_access_settings(server, settings, credentials)
            public = json.loads((server / 'settings.local.json').read_text())
            self.assertEqual(set(public), set(installer.PUBLIC_FIELDS))
            for value in credentials.values():
                self.assertNotIn(value, json.dumps(public))
                self.assertNotIn(value, output.getvalue())
            self.assertIn('"' + credentials['AmxPassword'] + '"', (server / 'cstrike/addons/amxmodx/configs/users.ini').read_text())
            self.assertIn('yb_password "' + credentials['YbPassword'] + '"', bot_file.read_text())
            self.assertIn('rcon_password "' + credentials['RconPassword'] + '"', (server / 'cstrike/server.cfg').read_text())
            self.assertIn('setinfo _ybpw "' + credentials['YbPassword'] + '"', (server / 'ADMIN.local.txt').read_text())

    def test_invalid_credentials_fail_before_files_or_network(self):
        settings = self.recommended()
        with tempfile.TemporaryDirectory() as directory, patch.object(installer, 'download') as download:
            server = Path(directory) / 'server'
            with self.assertRaises(ValueError):
                installer.assemble(server, Path(directory), settings, '192.168.1.10', credentials={'AmxPassword': 'partial'})
            self.assertFalse(server.exists())
            download.assert_not_called()
        bound = inspect.signature(installer.assemble).bind('server', 'cache', settings, 'address', 'compiler')
        self.assertEqual(bound.arguments['compiler'], 'compiler')
        self.assertNotIn('credentials', bound.arguments)

    def test_duplicate_access_cvars_fail_before_private_files(self):
        with tempfile.TemporaryDirectory() as directory:
            server = Path(directory)
            path = server / 'cstrike/addons/yapb/conf/yapb.cfg'
            path.parent.mkdir(parents=True)
            path.write_text('yb_password "one"\nyb_password "two"\n')
            with self.assertRaises(ValueError):
                installer.write_access_settings(server, self.recommended(), installer.validate_credentials(None))
            self.assertFalse((server / 'settings.local.json').exists())
            self.assertFalse((server / 'ADMIN.local.txt').exists())


if __name__ == '__main__':
    unittest.main()
