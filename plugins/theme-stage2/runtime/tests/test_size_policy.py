"""P1 regression tests use synthetic evidence, never actual art approval."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as h
from scene_contract import read, write, sha, validate_plan
from size_policy import validate_scene_sizes, validate_scale_plan, policy_fields, check_output_size
from size_review import template
from scale_calibrate import calibrate_asset
from test_scene_handoff import make_fixture

class SizePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run, self.visual, self.scene = make_fixture(self.root)

    def test_missing_policy_and_wrong_dimensions_are_rejected(self):
        for key in ('size_policy_id', 'size_policy_sha256'):
            p = copy.deepcopy(self.scene);p.pop(key)
            with self.assertRaises(ValueError): validate_plan(p)
        p = copy.deepcopy(self.scene)
        p['assets'][0]['target_wh_px'] = [1000,1000]
        with self.assertRaisesRegex(ValueError,'outside size'): validate_plan(p)

    def test_large_limit_and_explicit_unconfigured_state(self):
        p = copy.deepcopy(self.scene)
        p['assets'][0].update(size_class='large',target_wh_px=[600,600])
        p['large_max_instances'] = 1
        with self.assertRaisesRegex(ValueError,'instance count'): validate_plan(p)
        p['large_max_instances'] = None
        self.assertEqual(validate_scene_sizes(p)['large_limit_status'],'unconfigured')
        p['large_max_instances'] = 2
        self.assertEqual(validate_scene_sizes(p)['large_limit_status'],'pass')
        p['assets'][0].update(size_class='small',size_exception={'reason':'long object','basis':'synthetic example'})
        p['large_max_instances']=1
        with self.assertRaisesRegex(ValueError,'instance count'): validate_plan(p)

    def test_road_width_and_reference_validation(self):
        p=copy.deepcopy(self.scene)
        p['infrastructure']=[{'kind':'road','description':'test road'}]
        p['assets'][-1]['class']='vehicle';p['assets'][-1]['requires']=['road']
        p['assets'][-1]['zones']=['road']
        road={'id':'r1','vehicle_id':'train','vehicle_width_px':100,'clear_width_px':200,'measurement_basis':'same projection transverse widths'}
        p['road_sizes']=[road]
        validate_plan(p)
        for width in (99,251):
            road['clear_width_px']=width
            with self.assertRaisesRegex(ValueError,'Road width'):validate_plan(p)
        road['clear_width_px']=200;road['vehicle_id']='missing'
        with self.assertRaisesRegex(ValueError,'vehicle ID'):validate_plan(p)

    def test_scale_targets_cannot_diverge_from_scene(self):
        scale=read(self.run/'scale-plan.json')
        scale['items'][0]['target_wh_px']=[410,390]
        with self.assertRaisesRegex(ValueError,'bound scene'):validate_scale_plan(scale,self.scene)

    def test_policy_and_review_tampering_blocks_export(self):
        path=self.run/'policy/size-v2.json';path.write_text(path.read_text()+' ')
        self.assertEqual(h.export(self.run,self.visual,self.root/'bad')['state'],'blocked')
        self.assertFalse((self.root/'bad').exists())

    def test_character_width_is_not_silently_stretched(self):
        path=self.root/'skinny.png'
        im=Image.new('RGBA',(55,280));im.paste(Image.new('RGBA',(35,260),'red'),(10,10));im.save(path)
        old=read(self.run/'manifest.json')['items'][1]['artifact']['sha256']
        with self.assertRaisesRegex(ValueError,'width/height'):
            calibrate_asset(self.run,'person',path)
        self.assertEqual(read(self.run/'manifest.json')['items'][1]['artifact']['sha256'],old)

    def test_both_axes_and_base_body_are_required(self):
        entry=next(a for a in self.scene['assets'] if a['id']=='person')
        with self.assertRaises(ValueError):check_output_size(entry,[0,0,35,130],[0,0,35,130])
        with self.assertRaises(ValueError):check_output_size(entry,[0,0,75,130])
        review=read(self.run/'size-review.json');review['items'][1]['base_body_bbox']=[12,12,47,142]
        write(self.run/'size-review.json',review)
        self.assertEqual(h.validate(self.run,self.visual)['state'],'blocked')

    def test_character_extensions_preserve_full_sprite_and_body(self):
        # Full visible art includes a hat/prop; only the annotated base is 75x130.
        scene=read(self.run/'scene-plan.json');scene['assets'][1]['target_wh_px']=[100,160]
        write(self.run/'scene-plan.json',scene)
        m=read(self.run/'manifest.json');m['scene_plan_contract']['sha256']=sha(self.run/'scene-plan.json');write(self.run/'manifest.json',m)
        raw=self.root/'extended.png'
        im=Image.new('RGBA',(220,340));im.paste(Image.new('RGBA',(200,320),'red'),(10,10));im.save(raw)
        scale=read(self.run/'scale-plan.json');entry=scale['items'][1]
        entry.update(target_wh_px=[100,160],target_H=160/130,source_body={'sha256':sha(raw),'bbox':[30,60,180,320]})
        write(self.run/'scale-plan.json',scale)
        result=calibrate_asset(self.run,'person',raw)
        measurement=read(self.run/result['calibration_record'])
        self.assertEqual(measurement['actual_px'],160)
        body=measurement['base_body_bbox']
        self.assertEqual([body[2]-body[0],body[3]-body[1]],[75,130])
        self.assertEqual(read(self.run/'scale-review.json')['status'],'unreviewed')
        repeated = calibrate_asset(self.run,'person')
        self.assertEqual(repeated['actual_px'],160)
        # Reusing a different image with the old annotation must fail.
        altered=self.root/'changed.png';im.putpixel((20,20),(0,0,255,255));im.save(altered)
        with self.assertRaisesRegex(ValueError,'stale'):calibrate_asset(self.run,'person',altered)

    def test_stale_observed_road_review_and_ratio(self):
        # Build a fresh vehicle+road revision; none of these approvals describe real art.
        scene=copy.deepcopy(self.scene);scene['infrastructure']=[{'kind':'road','description':'test road'}]
        scene['assets'][-1].update({'class':'vehicle','requires':['road'],'zones':['road']})
        scene['road_sizes']=[{'id':'road1','vehicle_id':'train','vehicle_width_px':100,'clear_width_px':200,'measurement_basis':'test transverse widths'}]
        write(self.run/'scene-plan.json',scene)
        m=read(self.run/'manifest.json');m['scene_plan_contract']['sha256']=sha(self.run/'scene-plan.json');write(self.run/'manifest.json',m)
        sizes=template(self.run);sizes['reviewer']='SYNTHETIC'
        for row in sizes['items']:
            row.update(status='pass',observation='test')
            if row['id']=='person':row['base_body_bbox']=[12,12,87,142]
        sizes['roads'][0].update(status='pass',observation='test',vehicle_width_px=100,clear_width_px=300)
        write(self.run/'size-review.json',sizes)
        from size_review import check
        with self.assertRaisesRegex(ValueError,'Observed road width'):check(self.run,m)
        sizes['roads'][0]['clear_width_px']=200;write(self.run/'size-review.json',sizes)
        check(self.run,m)
        sizes['roads'][0]['vehicle_sha256']='stale';write(self.run/'size-review.json',sizes)
        with self.assertRaisesRegex(ValueError,'stale'):check(self.run,m)

    def test_stage1_to_stage2_to_real_layout_init(self):
        plugins=Path(__file__).resolve().parents[3]
        stage1=plugins/'theme-scene-studio/skills/theme-scene-studio/scripts'
        layout=Path(os.environ.get('THEME_LAYOUT_PLUGIN', str(plugins/'tmc-level-layout')))/'scripts'
        if not (stage1/'scene_contract.py').is_file() or not (layout/'tmc_harness.py').is_file():
            self.skipTest('Cross-plugin test needs sibling Stage 1 and Layout (or THEME_LAYOUT_PLUGIN)')
        for directory in (stage1,layout):
            self.assertEqual((directory/'size_policy.py').read_bytes(),(Path(h.__file__).parent/'size_policy.py').read_bytes())
        command=[sys.executable,str(stage1/'scene_contract.py'),'--plan',str(self.run/'scene-plan.json'),'--source',str(self.root/'source.png'),'--require-count-policy']
        r=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        result=h.export(self.run,self.visual,self.root/'export')
        self.assertEqual(result['state'],'accepted',result)
        command=[sys.executable,str(layout/'tmc_harness.py'),'init','--handoff',result['layout_handoff'],'--project',str(self.root/'layout')]
        r=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr+r.stdout)
        self.assertEqual(read(self.root/'layout/scene-handoff/scene-plan.json')['H_px'],130)
        with Image.open(self.root/'layout/item/person.png') as imported, Image.open(self.run/read(self.run/'manifest.json')['items'][1]['artifact']['file']) as source:
            self.assertEqual(imported.size,source.size)
        self.assertEqual(read(self.root/'layout/level.json')['placement']['uniformScale'],1.0)
        # Re-load the pinned package, including its copied size evidence.
        r=subprocess.run([sys.executable,'-c',"from scene_loop import load_project; import sys; load_project(sys.argv[1])",str(self.root/'layout')],cwd=layout,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        packet=Path(result['layout_handoff']).parent
        (packet/'size-review.json').write_text('{}')
        r=subprocess.run([sys.executable,str(layout/'tmc_harness.py'),'init','--handoff',str(packet),'--project',str(self.root/'tampered')],capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0)
        self.assertFalse((self.root/'tampered').exists())

if __name__=='__main__':unittest.main()
