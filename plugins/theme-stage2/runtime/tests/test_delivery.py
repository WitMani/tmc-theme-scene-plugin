import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

spec = importlib.util.spec_from_file_location('delivery', Path(__file__).resolve().parents[2] / 'scripts/deliver.py')
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)


class DeliveryTests(unittest.TestCase):
    def test_review_states_and_missing_image_do_not_block_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / 'run'
            run.mkdir()
            image = run / 'good.png'
            Image.new('RGBA', (8, 8), (1, 2, 3, 255)).save(image)
            manifest = {'items': [
                {'id': 'good', 'category': 'background', 'artifact': {
                    'file': 'good.png', 'sha256': delivery.harness.file_hash(image)}},
                {'id': 'missing', 'category': 'background', 'artifact': None}]}
            (run / 'manifest.json').write_text(json.dumps(manifest))
            for state in ('blocked', 'needs_review', 'accepted'):
                with self.subTest(state=state), patch.object(delivery.harness, 'validate', return_value={'state': state}):
                    result = delivery.deliver(run, root / state)
                    self.assertEqual(result['state'], 'delivered')
                    self.assertEqual(len(result['files']), 1)
                    self.assertEqual(len(result['missing']), 1)
                    self.assertEqual(result['audit']['state'], state)
                    self.assertEqual(Path(result['files'][0]).read_bytes(), image.read_bytes())
                    self.assertTrue(all(p.suffix == '.png' for p in (root / state).rglob('*') if p.is_file()))
            self.assertEqual(len(list((run / 'export-records').glob('delivery-*.json'))), 3)


if __name__ == '__main__':
    unittest.main()
