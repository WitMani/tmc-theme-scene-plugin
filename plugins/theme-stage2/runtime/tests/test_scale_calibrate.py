import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as h
from scene_size import normalize_scene, check_run, digest
from scale_calibrate import calibrate_asset, calibrate_all, contact_sheet


def body(width, height, color=(200, 40, 40, 255), pad=(13, 7)):
    """RGBA sprite whose visible body is width x height, surrounded by transparent slack."""
    im = Image.new('RGBA', (width + 2 * pad[0], height + 2 * pad[1]), (0, 0, 0, 0))
    im.paste(Image.new('RGBA', (width, height), color), pad)
    return im


def visible(path, axis):
    with Image.open(path) as im:
        box = im.getchannel('A').point(lambda v: 255 if v > 16 else 0).getbbox()
    return box[2] - box[0] if axis == 'width' else box[3] - box[1]


class ScaleCalibrateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.png'
        Image.new('RGB', (64, 64), 'green').save(self.source)
        self.run = self.root / 'run'
        inventory = {'items': [
            {'id': 'background', 'name': 'terrain', 'category': 'background', 'identity_brief': 'Test terrain'},
            {'id': 'person', 'name': 'goose', 'category': 'character', 'identity_brief': 'Test goose'},
            {'id': 'boat', 'name': 'boat', 'category': 'vehicle', 'identity_brief': 'Test boat'}]}
        m = h.prepare(self.source, inventory, self.run)
        m.pop('scene_plan_contract', None)  # scene handoff is gated in its own suite
        h.write_json(self.run / 'manifest.json', m)
        bg = self.root / 'bg.png'
        normalize_scene(self.source, bg)
        h.register(self.run, 'background', bg)
        self.person_raw = self.root / 'person.png'
        body(90, 333).save(self.person_raw)  # far from 128 tall, odd ratio
        self.boat_raw = self.root / 'boat.png'
        body(1000, 300, (40, 90, 200, 255)).save(self.boat_raw)
        h.register(self.run, 'person', self.person_raw)
        h.register(self.run, 'boat', self.boat_raw)
        self.plan = {'H_px': 128, 'alpha_threshold': 16, 'items': [
            {'id': 'person', 'primary_axis': 'height', 'target_H': 1.0},
            {'id': 'boat', 'primary_axis': 'width', 'target_H': 4.5}]}
        h.write_json(self.run / 'scale-plan.json', self.plan)

    def manifest(self):
        return h.read_json(self.run / 'manifest.json')

    def test_calibrate_all_hits_plan_registers_and_binds_review(self):
        result = calibrate_all(self.run)
        self.assertEqual(set(result['calibrated']), {'person', 'boat'})
        self.assertEqual(result['skipped_without_candidate'], [])
        m = self.manifest()
        person = next(i for i in m['items'] if i['id'] == 'person')
        boat = next(i for i in m['items'] if i['id'] == 'boat')
        self.assertEqual(visible(self.run / person['artifact']['file'], 'height'), 128)
        self.assertEqual(visible(self.run / boat['artifact']['file'], 'width'), 576)
        # uniform scaling: the boat keeps its 1000:300 body ratio
        with Image.open(self.run / boat['artifact']['file']) as im:
            box = im.getchannel('A').point(lambda v: 255 if v > 16 else 0).getbbox()
        self.assertAlmostEqual((box[3] - box[1]) / (box[2] - box[0]), 0.3, delta=0.01)
        self.assertEqual(person['artifact']['origin'], 'scale calibration to plan; not art-style approval')
        self.assertTrue(any(r.startswith('calibrated/person/') for r in person['processing_records']))
        # previous candidate is preserved in history, raw file untouched
        self.assertEqual(person['artifact_history'][-1]['sha256'], digest(self.person_raw))
        with Image.open(self.person_raw) as im:
            self.assertEqual(im.size, (90 + 26, 333 + 14))
        review = h.read_json(self.run / 'scale-review.json')
        self.assertEqual(review['plan_sha256'], digest(self.run / 'scale-plan.json'))
        self.assertEqual(review['status'], 'unreviewed')
        entries = {x['id']: x for x in review['items']}
        self.assertEqual(entries['person']['sha256'], person['artifact']['sha256'])
        self.assertEqual(entries['person']['status'], 'unreviewed')
        self.assertEqual(entries['boat']['target_px'], 576)
        self.assertEqual(entries['boat']['actual_px'], 576)
        # the automatic measurement is not a visual approval: validate stays blocked
        errors = check_run(self.run, self.manifest())
        self.assertTrue(any('incomplete' in e for e in errors), errors)
        # executor signs off; the run passes the size gate with no further changes
        review.update(status='pass', reviewer='tester', observation='Synthetic gate test only')
        for entry in review['items']:
            entry.update(status='pass', observation='Synthetic gate test only')
        h.write_json(self.run / 'scale-review.json', review)
        self.assertEqual(check_run(self.run, self.manifest()), [])
        self.assertEqual(h.validate(self.run)['errors'], [])

    def test_recalibration_is_idempotent_and_voids_old_approval(self):
        first = calibrate_asset(self.run, 'person')
        review = h.read_json(self.run / 'scale-review.json')
        review.update(status='pass', reviewer='tester', observation='ok')
        review['items'][0].update(status='pass', observation='ok')
        h.write_json(self.run / 'scale-review.json', review)
        again = calibrate_asset(self.run, 'person')
        # source is now the calibrated artifact itself; the body is already at target so the
        # result is a new deterministic file, and any prior approval is reset
        self.assertEqual(again['actual_px'], 128)
        review = h.read_json(self.run / 'scale-review.json')
        self.assertEqual(review['status'], 'unreviewed')
        self.assertEqual(review['items'][0]['status'], 'unreviewed')
        # same source + same plan reuses the same output path and hash
        repeat = calibrate_asset(self.run, 'person', image=self.person_raw)
        self.assertEqual(repeat['artifact']['file'], first['artifact']['file'])
        self.assertEqual(repeat['artifact']['sha256'], first['artifact']['sha256'])

    def test_plan_change_resets_review_binding(self):
        calibrate_all(self.run)
        review = h.read_json(self.run / 'scale-review.json')
        review.update(status='pass', reviewer='tester', observation='ok')
        for entry in review['items']:
            entry.update(status='pass', observation='ok')
        h.write_json(self.run / 'scale-review.json', review)
        self.plan['items'][1]['target_H'] = 5.0
        h.write_json(self.run / 'scale-plan.json', self.plan)
        calibrate_asset(self.run, 'boat', image=self.boat_raw)
        review = h.read_json(self.run / 'scale-review.json')
        self.assertEqual(review['plan_sha256'], digest(self.run / 'scale-plan.json'))
        self.assertEqual(review['status'], 'unreviewed')
        self.assertTrue(all(x['status'] == 'unreviewed' for x in review['items']))
        boat = next(i for i in self.manifest()['items'] if i['id'] == 'boat')
        self.assertEqual(visible(self.run / boat['artifact']['file'], 'width'), 640)

    def test_rejections(self):
        with self.assertRaises(ValueError):
            calibrate_asset(self.run, 'background')
        flat = self.root / 'flat.png'
        Image.new('RGB', (40, 40), 'red').save(flat)
        with self.assertRaisesRegex(ValueError, 'real alpha'):
            calibrate_asset(self.run, 'person', image=flat)
        empty = self.root / 'empty.png'
        Image.new('RGBA', (40, 40), (0, 0, 0, 0)).save(empty)
        with self.assertRaisesRegex(ValueError, 'visible pixels'):
            calibrate_asset(self.run, 'person', image=empty)
        self.plan['items'].pop()
        h.write_json(self.run / 'scale-plan.json', self.plan)
        with self.assertRaisesRegex(ValueError, 'not in scale-plan'):
            calibrate_asset(self.run, 'boat')
        with self.assertRaisesRegex(ValueError, 'cover each'):
            calibrate_all(self.run)
        (self.run / 'scale-plan.json').unlink()
        with self.assertRaisesRegex(ValueError, 'missing'):
            calibrate_asset(self.run, 'person')

    def test_cli_and_contact_sheet(self):
        self.assertEqual(h.main(['calibrate', '--run', str(self.run), '--all']), 0)
        self.assertEqual(h.main(['calibrate', '--run', str(self.run)]), 2)
        self.assertEqual(h.main(['calibrate', '--run', str(self.run), '--id', 'person', '--all']), 2)
        out = self.root / 'scale-contact.png'
        self.assertEqual(h.main(['scale-contact', '--run', str(self.run), '--out', str(out)]), 0)
        with Image.open(out) as im:
            self.assertGreaterEqual(im.width, 576 + 16)
        self.assertEqual(h.main(['scale-contact', '--run', str(self.run), '--out', str(out)]), 2)
        with self.assertRaises(ValueError):
            contact_sheet(self.run, out)


if __name__ == '__main__':
    unittest.main()
