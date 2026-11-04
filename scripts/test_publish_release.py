"""Release correction tests; GitHub operations use disposable in-memory fixtures."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import publish_release as publisher


class ReleaseCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.request = dict(tag='v1.0.0', title='Version 1.0.0', prerelease=False,
                            replaces=dict(tag='v0.1.0-rc.1', id=123))
        self.asset_names = ['HL-noSteam-Windows-v1.0.0.zip', 'HL-noSteam-Linux-v1.0.0.zip',
                            'SHA256SUMS.txt', 'RELEASE-NOTES.md']
        self.assets = []
        for name in self.asset_names:
            asset = self.root / name
            asset.write_bytes(('new ' + name).encode())
            self.assets.append(asset)
        self.old_zips = ['HL-noSteam-Windows-v0.1.0-rc.1.zip', 'HL-noSteam-Linux-v0.1.0-rc.1.zip']
        self.remote = {name: ('old ' + name).encode() for name in self.old_zips + self.asset_names[2:]}
        self.release = dict(id=123, tag_name='v0.1.0-rc.1', prerelease=True, immutable=False,
                            assets=[dict(name=name) for name in self.remote])
        self.calls = []

    def tearDown(self):
        self.temporary.cleanup()

    def fake_gh(self, *args):
        self.calls.append(args)
        if args[1] == 'upload':
            for name in args[3:]:
                if not name.startswith('--'):
                    self.remote[Path(name).name] = Path(name).read_bytes()
        elif args[1] == 'download':
            (Path(args[6]) / args[4]).write_bytes(self.remote[args[4]])
        elif args[1] == 'delete-asset':
            del self.remote[args[3]]
        return b''

    def promote(self):
        with patch.object(publisher, 'gh', side_effect=self.fake_gh):
            publisher.promote(self.request, 'a' * 40, self.assets, self.assets[-1], [self.release])

    def test_replaces_old_zips_only_after_all_new_files_verified(self):
        self.promote()
        self.assertEqual(set(self.remote), set(self.asset_names))
        for asset in self.assets:
            self.assertEqual(self.remote[asset.name], asset.read_bytes())
        deletion = next(index for index, args in enumerate(self.calls) if args[1] == 'delete-asset')
        verified = [args[4] for args in self.calls[:deletion] if args[1] == 'download' and args[2] == 'v1.0.0']
        self.assertEqual(set(verified), set(self.asset_names))
        edit = next(args for args in self.calls if args[1] == 'edit')
        self.assertIn('--prerelease=false', edit)
        self.assertIn('--latest', edit)

    def test_invalid_remote_zip_aborts_before_edit_or_deletion(self):
        self.remote[self.asset_names[0]] = b'corrupt'
        self.release['assets'].append(dict(name=self.asset_names[0]))
        with self.assertRaises(ValueError):
            self.promote()
        self.assertFalse(any(args[1] in ('edit', 'delete-asset') for args in self.calls))

    def test_immutable_changed_or_unexpected_release_is_untouched(self):
        initial = copy.deepcopy(self.release)
        for update in (dict(immutable=True), dict(id=999), dict(assets=[dict(name='someone-elses-file.zip')])):
            self.release = {**copy.deepcopy(initial), **update}
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.promote()
            self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
