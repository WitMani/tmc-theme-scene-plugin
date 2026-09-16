"""Portable generation-record and alpha behavior, using synthetic images only."""
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from PIL import Image,ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import harness as h
from production import record_call,cutout_candidate
from cutout import remove_matte

class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'source.png'
        Image.new('RGB',(96,96),'#d7e5d4').save(self.source)
        self.run=self.root/'run'
        inventory={'items':[{'id':'sample','name':'Synthetic sample','category':'building',
                            'identity_brief':'Synthetic fixture, not real art.','source_bbox':[5,5,85,85]}]}
        h.prepare(self.source,inventory,self.run)
        # Preserve legacy tiny-image fixture semantics; new size contract has dedicated tests.
        legacy = h.read_json(self.run/'manifest.json')
        legacy.pop('scene_size_contract', None)
        legacy.pop('scene_plan_contract', None)
        h.write_json(self.run/'manifest.json', legacy)
        self.prompt=self.run/'prompts/sample.txt'
        self.raw=self.root/'synthetic-generated.png'
        im=Image.new('RGB',(96,96),'#ff00ff')
        ImageDraw.Draw(im).rectangle((23,24,73,75),fill=(70,140,190));im.save(self.raw)

    def call(self,inputs=None,image=None):
        return record_call(self.run,'sample',image or self.raw,self.prompt,
                           inputs or [self.run/'input/source.png'],tool='synthetic_test_fixture')

    def test_record_is_idempotent_and_preserves_actual_prompt(self):
        first=self.call();again=self.call()
        self.assertTrue(again['idempotent'])
        self.assertEqual(first['record_key'],again['record_key'])
        self.assertEqual((self.run/first['actual_prompt_file']).read_bytes(),self.prompt.read_bytes())
        self.assertEqual(h.read_json(self.run/'manifest.json')['actual_generation_calls'],1)

    def test_original_source_alias_is_traced_by_content(self):
        record=self.call(inputs=[self.source])
        self.assertEqual(record['inputs'][0]['actual_input_path'],str(self.source))
        self.assertEqual(record['inputs'][0]['resolved_input_path'],str(self.source.resolve()))
        self.assertEqual(record['inputs'][0]['file'],'input/source.png')

    def test_unrelated_reference_is_rejected_without_recording(self):
        other=self.root/'other-scene.png';Image.new('RGB',(96,96),'red').save(other)
        with self.assertRaises(ValueError):self.call(inputs=[other])
        self.assertNotIn('actual_generation_calls',h.read_json(self.run/'manifest.json'))

    def test_correction_can_use_own_recorded_and_processed_derivatives(self):
        first=self.call()
        cut=cutout_candidate(self.run,'sample',self.run/first['raw_file'])
        second=self.root/'second-tool-output.png';Image.open(self.raw).save(second)
        record=self.call(inputs=[self.run/cut['artifact']['file']],image=second)
        self.assertEqual(record['attempt'],2)
        self.assertEqual(h.read_json(self.run/'manifest.json')['actual_generation_calls'],2)

    def test_cutout_produces_real_alpha_without_approving_style(self):
        self.call();result=cutout_candidate(self.run,'sample',self.raw)
        path=self.run/result['artifact']['file'];im=Image.open(path)
        self.assertEqual(im.mode,'RGBA');self.assertEqual(im.getchannel('A').getextrema(),(0,255))
        self.assertEqual(im.getpixel((im.width//2,im.height//2))[:3],(70,140,190))
        self.assertTrue(result['visual_review_required'])
        self.assertEqual(h.validate(self.run)['state'],'needs_review')

    def test_native_alpha_is_preserved_byte_for_byte(self):
        native=self.root/'native.png';im=Image.new('RGBA',(50,50))
        ImageDraw.Draw(im).ellipse((10,10,40,40),fill=(200,120,50,255));im.save(native)
        result=cutout_candidate(self.run,'sample',native)
        self.assertEqual((self.run/result['artifact']['file']).read_bytes(),native.read_bytes())

    def test_auto_does_not_key_a_gray_checkerboard(self):
        a=np.indices((96,96)).sum(axis=0)//6%2
        image=Image.fromarray(np.repeat(np.where(a[...,None],150,210).astype(np.uint8),3,axis=2))
        with self.assertRaises(ValueError):remove_matte(image)

    def test_empty_matte_is_rejected(self):
        with self.assertRaises(ValueError):remove_matte(Image.new('RGB',(96,96),'#ff00ff'))

    def test_explicit_alternate_matte_preserves_white_subject(self):
        im=Image.new('RGB',(96,96),'#00ff00');ImageDraw.Draw(im).rectangle((22,22,74,74),fill='white')
        out,_=remove_matte(im,matte='#00ff00')
        self.assertEqual(out.getchannel('A').getextrema(),(0,255))
        self.assertEqual(out.getpixel((out.width//2,out.height//2)),(255,255,255,255))

    def test_shadowed_matte_option_removes_tinted_opening(self):
        im=Image.open(self.raw);ImageDraw.Draw(im).rectangle((39,38,57,59),fill=(205,95,195))
        out,stats=remove_matte(im,shadowed_matte=True)
        box=stats['raw_visible_bbox'];x=48-box[0]+stats['padding'];y=48-box[1]+stats['padding']
        self.assertEqual(out.getpixel((x,y))[3],0)

if __name__=='__main__':unittest.main()
