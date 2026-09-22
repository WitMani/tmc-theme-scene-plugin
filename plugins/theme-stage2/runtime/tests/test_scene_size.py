import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as h
from scene_size import CONTRACT, normalize_scene, check_run, digest

class SceneSizeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'source.png'
        Image.new('RGB', (64, 64), 'green').save(self.source)

    def test_resampling_and_non_square_and_overwrite(self):
        output = self.root/'background.png'
        info = normalize_scene(self.source, output)
        with Image.open(output) as im: self.assertEqual(im.size, (4096, 4096))
        self.assertTrue(info['resampled'])
        self.assertFalse(info['native_4096'])
        with Image.open(self.source) as im: self.assertEqual(im.size, (64, 64))
        with self.assertRaises(ValueError): normalize_scene(self.source, output)
        Image.new('RGB', (32, 64)).save(self.root/'wide.png')
        with self.assertRaises(ValueError): normalize_scene(self.root/'wide.png', self.root/'bad.png')

    def test_new_run_gate_dimensions_scale_and_stale_review(self):
        from test_scene_handoff import make_fixture
        run, visual, scene = make_fixture(self.root/'full')
        m = h.read_json(run/'manifest.json')
        self.assertEqual(m['scene_size_contract'], CONTRACT)
        self.assertEqual(check_run(run,m), [])
        review = h.read_json(run/'size-review.json')
        review['items'][0]['sha256'] = 'stale'
        h.write_json(run/'size-review.json',review)
        self.assertTrue(check_run(run,m))
        review['items'][0]['sha256'] = m['items'][0]['artifact']['sha256']
        h.write_json(run/'size-review.json',review)
        plan = h.read_json(run/'scale-plan.json')
        plan['items'][0]['target_H'] = 10
        h.write_json(run/'scale-plan.json',plan)
        self.assertTrue(check_run(run,m))
