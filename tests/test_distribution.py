"""Distribution boundaries; no image generation or external service calls."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('theme-scene-studio', 'theme-stage2')


class DistributionTests(unittest.TestCase):
    def test_marketplace_has_separate_self_contained_plugin_entries(self):
        market = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
        self.assertEqual(market['name'], 'tmc-theme-scene')
        self.assertEqual([p['name'] for p in market['plugins']], list(NAMES))
        self.assertFalse((ROOT / '.codex-plugin').exists())
        for entry in market['plugins']:
            package = ROOT / entry['source']['path']
            self.assertEqual(package.resolve(), ROOT / 'plugins' / entry['name'])
            self.assertEqual(entry['source']['source'], 'local')
            self.assertEqual(entry['policy']['installation'], 'AVAILABLE')
            self.assertEqual(entry['policy']['authentication'], 'ON_INSTALL')
            manifest = json.loads((package / '.codex-plugin/plugin.json').read_text())
            self.assertEqual(manifest['name'], entry['name'])
            skills = package / manifest['skills']
            self.assertEqual([p.name for p in skills.iterdir() if p.is_dir()], [entry['name']])
            self.assertTrue((skills / entry['name'] / 'SKILL.md').is_file())

    def test_markdown_file_links_survive_relocation(self):
        for file in ROOT.rglob('*.md'):
            if '.git' in file.parts:
                continue
            for target in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', file.read_text()):
                if re.match(r'[a-zA-Z][\w+.-]*:', target) or target.startswith('#'):
                    continue
                path = target.split('#')[0]
                if path:
                    self.assertTrue((file.parent / path).exists(), f'{file.relative_to(ROOT)} -> {target}')

    def test_stage2_runs_without_stage1_or_repository_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            package = work / 'theme-stage2'
            shutil.copytree(ROOT / 'plugins/theme-stage2', package,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            commands = [
                [str(package / 'scripts/run.py'), 'doctor'],
                [str(package / 'scripts/run.py'), '--help'],
                ['-m', 'unittest', 'discover', '-s', str(package / 'runtime/tests'), '-v'],
            ]
            for args in commands:
                python = [sys.executable] + (['-P'] if sys.version_info >= (3, 11) else [])
                result = subprocess.run([*python, *args], cwd=work,
                                        capture_output=True, text=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertRegex(result.stderr, r'Ran [1-9][0-9]* tests')


if __name__ == '__main__':
    unittest.main()
