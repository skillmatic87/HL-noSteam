"""Package path checks that also run from a source ZIP without a Git checkout."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def maintained_paths(root):
    if (root / '.git').exists() and shutil.which('git'):
        result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--cached',
                                 '--others', '--exclude-standard'], capture_output=True, check=True)
        return [name for name in result.stdout.decode('utf-8').split('\0') if name]
    paths = [path.name for path in root.iterdir() if path.is_file() and path.name != '.git']
    for directory in ('scripts', 'docs', 'content'):
        paths.extend(path.relative_to(root).as_posix() for path in (root / directory).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts)
    return paths


class PackageNames(unittest.TestCase):
    def test_all_maintained_paths_use_lowercase(self):
        paths = maintained_paths(ROOT)
        self.assertTrue(paths)
        self.assertEqual([name for name in paths if name != name.lower()], [])

    def test_public_entry_points_and_panel_references_exist(self):
        for relative in ('setup-linux.sh', 'start-server.sh', 'start-panel.sh', 'update.sh',
                         'setup.cmd', 'start-server.cmd', 'start-panel.cmd',
                         'configure-server.html', 'version', 'readme.md', 'start-here.txt'):
            self.assertTrue((ROOT / relative).is_file(), relative)
        helper = (ROOT / 'scripts/server_panel.py').read_text(encoding='utf-8')
        self.assertIn("'configure-server.html'", helper)
        for relative in ('start-panel.sh', 'start-panel.cmd'):
            text = (ROOT / relative).read_text(encoding='utf-8')
            # The Windows entry point delegates through its PowerShell script.
            target = 'server_panel.py' if relative.endswith('.sh') else 'start-cs15panel.ps1'
            self.assertIn(target, text)

    def test_pinned_payload_hashes_match_normalized_templates(self):
        manifest = json.loads((ROOT / 'content/pack.json').read_text(encoding='utf-8'))
        for entry in manifest['localFiles']:
            source = ROOT / 'content' / entry['source']
            with self.subTest(source=entry['source']):
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), entry['sha256'])

    def test_explicit_package_script_references_are_case_correct(self):
        for relative in maintained_paths(ROOT):
            path = ROOT / relative
            if (path.suffix.lower() not in ('.py', '.ps1', '.sh', '.cmd', '.html') or
                    path.name.startswith('test_') or path.name in {'update.sh', 'update.sh'}):
                continue
            text = path.read_text(encoding='utf-8-sig')
            for match in re.finditer(r'scripts[/\\]([A-Za-z0-9_.-]+\.(?:py|ps1))', text):
                script = match[1]
                with self.subTest(source=relative, target=script):
                    self.assertEqual(script, script.lower())
                    self.assertTrue((ROOT / 'scripts' / script).is_file())

    def test_installed_engine_interfaces_retain_their_required_case(self):
        # These names belong to the installed game, not the maintained ZIP paths.
        # The case migration must not globally lower upstream/runtime interfaces.
        helper = (ROOT / 'scripts/server_panel.py').read_text(encoding='utf-8')
        installer = (ROOT / 'scripts/install_cs15_linux.py').read_text(encoding='utf-8')
        self.assertIn('Start-CS15.sh', helper)
        self.assertIn('SND-LIST.CFG', helper)
        self.assertIn('SND-LIST.CFG', installer)


if __name__ == '__main__':
    unittest.main(verbosity=2)
