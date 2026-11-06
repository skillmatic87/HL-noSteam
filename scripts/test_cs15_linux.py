"""Offline safety tests and optional real-archive assembly validation."""
import argparse
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch
import zipfile

import install_cs15_linux as installer


class InstallerTests(unittest.TestCase):
    def test_names_cannot_inject_configuration(self):
        for value in ('', '   ', 'a";quit', 'hello\nquit', 'a\\b', 'x' * 32):
            with self.subTest(value=value), self.assertRaises(ValueError):
                installer.validate_setting('AdminName', value)
        self.assertEqual(installer.validate_setting('AdminName', 'LAN Admin'), 'LAN Admin')

    def test_integer_and_score_choices(self):
        for key, (low, high) in installer.RANGES.items():
            for value in (low - 1, high + 1, True, 1.5, None):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    installer.validate_setting(key, value)
            self.assertEqual(installer.validate_setting(key, str(high)), high)
        with self.assertRaises(ValueError):
            installer.validate_setting('RankScore', 'unapproved')

    def test_server_names_have_their_own_length_limit(self):
        names = ('oldsk00l CS1.5 amx,sounds, statsme, vote',
                 'oldsk00l CS1.5 sounds statsme vote',
                 'oldschool CS15 statsme sounds vote', 's' * 63)
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(installer.validate_setting('ServerName', name), name)
        with self.assertRaisesRegex(ValueError, '64 characters entered; maximum is 63'):
            installer.validate_setting('ServerName', 's' * 64)
        for name in ('', '   ', 'name;quit', 'name"', 'name\\path', 'name\nquit'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                installer.validate_setting('ServerName', name)

    def test_paths_cannot_escape(self):
        for value in ('../escape', '/etc/passwd', 'a/../../escape', 'C:/escape', '..\\escape', 'a\x00b'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                installer.safe_path(Path('/safe/root'), value)

    def test_zip_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as stream:
                stream.writestr('../escape.txt', 'bad')
            with self.assertRaises(ValueError):
                installer.extract(archive, root / 'out')
            self.assertFalse((root / 'escape.txt').exists())

    def test_zip_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'link.zip'
            with zipfile.ZipFile(archive, 'w') as stream:
                member = zipfile.ZipInfo('link')
                member.external_attr = 0o120777 << 16
                stream.writestr(member, '/outside')
            with self.assertRaises(ValueError):
                installer.extract(archive, root / 'out')

    def test_corrupt_cache_never_downloads_or_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / 'test.zip'
            payload.write_bytes(b'keep these bytes')
            with patch.object(installer.urllib.request, 'urlopen') as network:
                with self.assertRaises(ValueError):
                    installer.download({'file': 'test.zip', 'sha256': '0' * 64}, root)
                network.assert_not_called()
            self.assertEqual(payload.read_bytes(), b'keep these bytes')

    def test_existing_server_is_not_modified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sentinel = root / 'operator-data.txt'
            sentinel.write_text('preserve')
            with patch.object(installer, 'download', return_value=Path('unused')):
                with self.assertRaises(FileExistsError):
                    installer.assemble(root, root, {}, '192.168.1.10')
            self.assertEqual(sentinel.read_text(), 'preserve')

    def test_linux_manifest_keeps_shared_versions(self):
        entries = installer.components()
        self.assertNotIn('unpacker', entries)
        self.assertEqual(entries['server']['file'], 'hlds_l_3110_full.tar.gz')
        for entry in entries.values():
            self.assertRegex(entry['sha256'], r'^[0-9a-f]{64}$')
            self.assertTrue(entry['url'].startswith('https://'))
        self.assertEqual(entries['statsme']['file'], 'statsme-2.7-cstrike.zip')

    def test_missing_native_library_stops_setup(self):
        missing = subprocess.CompletedProcess([], 0, 'libstdc++.so.6 => not found\n', '')
        with patch.object(installer.subprocess, 'run', return_value=missing):
            with self.assertRaisesRegex(ValueError, 'Missing or incompatible'):
                installer.check_libraries(Path('/server'), ['hlds'])

    def test_wad_names_match_case_sensitive_map_references(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory)
            originals = {'cstrike.WAD': b'WAD3-textures', 'cs_assault.WAD': b'WAD3-assault',
                         'tswad.WAD': b'WAD3-oilrig', 'itsItaly.wad': b'WAD3-italy',
                         'prodigy.wad': b'WAD3-prodigy'}
            for name, data in originals.items():
                (game / name).write_bytes(data)
            bsp = game / 'de_prodigy.bsp'
            bsp.write_bytes(b'original map bytes')
            installer.normalize_wad_names(game)
            # Path.exists() on Windows would hide this Linux-only regression.
            actual_names = {entry.name for entry in game.iterdir()}
            for name, data in originals.items():
                self.assertIn(name.lower(), actual_names)
                self.assertEqual((game / name.lower()).read_bytes(), data)
                if name != name.lower():
                    self.assertNotIn(name, actual_names)
            self.assertEqual(bsp.read_bytes(), b'original map bytes')
            installer.normalize_wad_names(game)
            self.assertEqual({entry.name for entry in game.iterdir()}, actual_names)


def integration(cache, compiler):
    """Use real, already verified archives; never start the server on Windows."""
    import datetime
    settings = {'ServerName': 'Linux assembly test', 'AdminName': 'AssemblyAdmin',
                'MapMinutes': 30, 'FriendlyFire': 0, 'BotTarget': 2, 'BotDifficulty': 2,
                'SoundCooldown': 5, 'SoundQuota': 20, 'RankBots': 1, 'RankScore': 'KillsMinusDeaths'}
    target = installer.ROOT / 'runtime' / ('linux-assembly-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    # Test credentials are generated locally and excluded from Git.
    installer.assemble(target, cache.resolve(), settings, '192.168.1.10', compiler.resolve() if compiler else None)
    game = target / 'cstrike'
    assert len(list((game / 'maps').glob('*.bsp'))) == 39
    wad_names = {entry.name for entry in game.iterdir() if entry.suffix.lower() == '.wad'}
    assert all(name == name.lower() for name in wad_names)
    assert {'cstrike.wad', 'cs_assault.wad', 'tswad.wad', 'itsitaly.wad'} <= wad_names
    assert not (target / '.install-incomplete').exists()
    assert '+maxplayers 32' in (target / 'Start-CS15.sh').read_text()
    assert 'gamedll_linux "addons/metamod/dlls/metamod.so"' in (game / 'liblist.gam').read_text()
    assert 'mapm_start_vote_before_end 5' in (game / 'addons/amxmodx/configs/mapmanager.cfg').read_text()
    assert all(line.startswith('linux ') for line in (game / 'addons/metamod/plugins.ini').read_text().splitlines())
    manifest = installer.read_json(installer.ROOT / 'content/pack.json')
    sound_config = (game / 'addons/amxmodx/configs/SND-LIST.CFG').read_text()
    for item in manifest['sounds']:
        assert (game / item['path']).is_file(), item['path']
        assert f"{item['keyword']}; {item['path']}" in sound_config
    assert f"SND_JOIN; {manifest['joinSound']}" in sound_config
    for relative in ('cstrike/motd.txt', 'cstrike/addons/yapb/conf/lang/en_chat.cfg'):
        assert (target / relative).read_bytes() == (installer.ROOT / 'content/files' / relative).read_bytes()
    for item in manifest['maps']:
        assert (game / f"maps/{item['name']}.bsp").is_file()
        assert (game / f"addons/yapb/data/graph/{item['name']}.graph").is_file()
    for name in ('mapmanager', 'sank_sounds'):
        assert (game / f'addons/amxmodx/plugins/{name}.amxx').stat().st_size > 1000
    print(f'PASS: native archive assembly, both plugins compiled, 39 maps, {14 + len(manifest["sounds"])} sound triggers.\n{target}')
    print('This verifies assembly and platform-independent Pawn bytecode; Linux runtime remains untested.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integration-cache', type=Path)
    parser.add_argument('--compiler', type=Path, help='Optional AMXX 1.8.1 host compiler for assembly testing')
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InstallerTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.integration_cache:
        integration(args.integration_cache, args.compiler)
