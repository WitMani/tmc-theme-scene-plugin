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
        run = self.root/'run'
        inventory = {'items': [
            {'id':'background', 'name':'test terrain', 'category':'background', 'identity_brief':'Test terrain'},
            {'id':'person', 'name':'test person', 'category':'character', 'identity_brief':'Test person'}]}
        m = h.prepare(self.source, inventory, run)
        self.assertEqual(m['scene_size_contract'], CONTRACT)
        # This suite isolates the size gate; full scene handoff is tested separately.
        m.pop('scene_plan_contract', None)
        h.write_json(run/'manifest.json', m)
        self.assertEqual(h.validate(run)['state'], 'blocked')
        bg = self.root/'bg.png'
        normalize_scene(self.source, bg)
        asset = self.root/'person.png'
        Image.new('RGBA', (50, 130), (255, 0, 0, 255)).save(asset)
        h.register(run, 'background', bg)
        h.register(run, 'person', asset)
        plan = {'H_px':130, 'alpha_threshold':16, 'items':[{'id':'person','primary_axis':'height','target_H':1}]}
        h.write_json(run/'scale-plan.json', plan)
        review = {'plan_sha256':digest(run/'scale-plan.json'), 'status':'pass',
                  'observation':'Synthetic gate test only, not art approval',
                  'items':[{'id':'person','sha256':digest(asset),'status':'pass'}]}
        h.write_json(run/'scale-review.json', review)
        m = h.read_json(run/'manifest.json')
        self.assertEqual(check_run(run, m), [])
        self.assertEqual(h.validate(run)['errors'], [])
        h.register(run, 'background', self.source)
        self.assertIn('Background must be 4096x4096', h.validate(run)['errors'])
        h.register(run, 'background', bg)
        plan['items'][0]['target_H'] = 2
        h.write_json(run/'scale-plan.json', plan)
        self.assertTrue(check_run(run, h.read_json(run/'manifest.json')))
        review['plan_sha256'] = digest(run/'scale-plan.json')
        h.write_json(run/'scale-review.json', review)
        self.assertTrue(any('Visible size' in e for e in check_run(run, h.read_json(run/'manifest.json'))))
        plan['items'][0]['target_H'] = 1
        h.write_json(run/'scale-plan.json', plan)
        review['plan_sha256'] = digest(run/'scale-plan.json')
        review['items'][0]['sha256'] = 'stale'
        h.write_json(run/'scale-review.json', review)
        self.assertTrue(any('Stale' in e for e in check_run(run, h.read_json(run/'manifest.json'))))
