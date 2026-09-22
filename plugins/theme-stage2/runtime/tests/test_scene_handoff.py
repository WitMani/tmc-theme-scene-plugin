"""Synthetic workflow evidence only; these fixtures are not real art approvals."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as h
from scene_contract import validate_plan, validate_bundle, sha, write, read
from scene_handoff import bind_plan, infrastructure_template, export_handoff

def make_fixture(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    source = root/'source.png'
    im = Image.new('RGB', (4096,4096), '#1BFF1B')
    ImageDraw.Draw(im).rectangle((0,3500,4095,4095), fill='#808080')
    im.save(source)
    definitions = [('house','building','building',2,3,[]),
                   ('person','character','person',3,1,[]),
                   ('train','vehicle','rail_vehicle',1,1,['rail'])]
    plan = {'schema':'scene-plan.v1','source_sha256':sha(source),'canvas':[4096,4096], 'H_px':130,
            'density':{'intent':'Separated synthetic objects','basis':'test fixture'},
            'goals':[{'id':'town','description':'Synthetic house and train composition'}],
            'infrastructure':[{'kind':'rail','description':'Continuous southern rail strip'}],
            'assets':[{'id':iid,'count':count,'critical':iid=='house','class':cls,
                       'role':'distractor','zones':['rail'] if cls=='rail_vehicle' else ['grass'],
                       'requires':deps,'count_basis':{'mode':'authored','reason':'Synthetic fixture count'}}
                      for iid,cat,cls,count,height,deps in definitions]}
    inventory = {'scene_plan':plan, 'items':[
        {'id':iid,'name':iid,'category':cat,'identity_brief':'Synthetic '+iid}
        for iid,cat,cls,count,height,deps in definitions] +
        [{'id':'background','name':'test background','category':'background','identity_brief':'Synthetic terrain'}]}
    run = root/'run'
    h.prepare(source, inventory, run)
    h.register(run, 'background', source)
    scale_items, reviews = [], []
    for iid,cat,cls,count,height,deps in definitions:
        height_px = round(height*130)
        image = Image.new('RGBA', (224,height_px+24))
        ImageDraw.Draw(image).rectangle((12,12,211,11+height_px), fill=(150,90,30,255))
        path = root/(iid+'.png')
        image.save(path)
        h.register(run, iid, path)
        scale_items.append({'id':iid,'primary_axis':'height','target_H':height})
        reviews.append({'id':iid,'sha256':sha(path),'status':'pass'})
    write(run/'scale-plan.json', {'H_px':130,'alpha_threshold':16,'items':scale_items})
    write(run/'scale-review.json', {'plan_sha256':sha(run/'scale-plan.json'),'status':'pass',
        'observation':'SYNTHETIC TEST ONLY','items':reviews})
    infra = infrastructure_template(run)
    infra['reviewer'] = 'SYNTHETIC TEST ONLY'
    for row in infra['checks']: row.update(result='pass', observation='Synthetic southern strip')
    write(run/'infrastructure-review.json', infra)
    review = h.review_template(run)
    for item in review['items']:
        item['reviewer'] = 'SYNTHETIC TEST ONLY'
        for check in item['checks']: check.update(result='pass',observation='Synthetic validation fixture')
    return run, review, plan

class SceneHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run, self.review, self.plan = make_fixture(self.root)

    def test_accepted_export_has_exact_count_package_and_images_only_delivery(self):
        result = h.export(self.run, self.review, self.root/'delivery')
        self.assertEqual(result['state'],'accepted')
        self.assertTrue(all(p.suffix=='.png' for p in (self.root/'delivery').rglob('*') if p.is_file()))
        root,bundle,plan = validate_bundle(result['layout_handoff'])
        self.assertEqual({a['id']:a['count'] for a in plan['assets']}, {'house':2,'person':3,'train':1})
        self.assertEqual(bundle['status'],'art_accepted_layout_pending')
        self.assertIn('Railway tracks are functional', (self.run/'prompts/background.txt').read_text())

    def test_absent_or_failed_infrastructure_and_stale_background_block(self):
        path = self.run/'infrastructure-review.json'
        original = read(path)
        review = copy.deepcopy(original)
        review['checks'][0]['result'] = 'fail'
        write(path, review)
        self.assertEqual(export_handoff(self.run,self.review,self.root/'bad')['state'],'blocked')
        self.assertFalse((self.root/'bad').exists())
        review = copy.deepcopy(original)
        review['background_sha256'] = '0'*64
        write(path, review)
        self.assertEqual(h.validate(self.run,self.review)['state'],'blocked')
        path.unlink()
        self.assertEqual(h.validate(self.run,self.review)['state'],'blocked')

    def test_vehicle_dependency_and_plan_changes_are_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan['assets'][-1]['requires'] = []
        with self.assertRaises(ValueError): validate_plan(plan)
        with self.assertRaises(ValueError): bind_plan(self.run,self.plan)
        plan = copy.deepcopy(self.plan)
        plan['assets'][0]['count'] = 1
        write(self.run/'scene-plan.json',plan)
        self.assertEqual(h.validate(self.run,self.review)['state'],'blocked')

    def test_candidate_art_and_mutated_packet_are_rejected(self):
        self.review['items'][0]['checks'][0]['result'] = 'unreviewed'
        self.assertNotEqual(export_handoff(self.run,self.review,self.root/'candidate')['state'],'accepted')
        self.review['items'][0]['checks'][0]['result'] = 'pass'
        result = export_handoff(self.run,self.review,self.root/'good')
        root,bundle,plan = validate_bundle(result['handoff'])
        (root/bundle['assets'][0]['file']).write_bytes(b'changed')
        with self.assertRaises(ValueError): validate_bundle(root)

if __name__ == '__main__': unittest.main()
