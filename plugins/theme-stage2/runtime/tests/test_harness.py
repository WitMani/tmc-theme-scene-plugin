"""Acceptance-gate tests use synthetic shapes, never pretend to review real art."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as h

class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'source.png'
        Image.new('RGB', (64, 64), '#d7ded4').save(self.source)
        self.profile = copy.deepcopy(h.load_profile())
        snapshot = (h.DEFAULT_PROFILE.parent/self.profile['source']['snapshot']).resolve()
        self.snapshot = self.root/'source-document.json'
        self.snapshot.write_bytes(snapshot.read_bytes())
        self.profile['source']['snapshot'] = str(self.snapshot)
        for feedback in self.profile.get('feedback_sources', []):
            feedback['snapshot'] = str((h.DEFAULT_PROFILE.parent/feedback['snapshot']).resolve())
        self.profile_path = self.root/'profile.json'
        h.write_json(self.profile_path, self.profile)
        self.inventory = {'items': [
            {'id':'goose','name':'test goose','category':'character','identity_brief':'A goose with a hat.','source_bbox':[5,5,30,45]},
            {'id':'house','name':'test house','category':'building','identity_brief':'A small pink house.','source_bbox':[31,6,61,60]},
            {'id':'background','name':'test background','category':'background','identity_brief':'The terrain.'}]}
        self.run = self.root/'run'
        h.prepare(self.source, self.inventory, self.run, self.profile_path)
        self.asset = self.root/'asset.png'
        im=Image.new('RGBA',(40,50));ImageDraw.Draw(im).rectangle((6,7,33,42),fill='#f3ab54');im.save(self.asset)
        for iid in ('goose','house'):h.register(self.run,iid,self.asset)
        h.register(self.run,'background',self.source)

    def passing_review(self):
        r=h.review_template(self.run)
        for item in r['items']:
            item['reviewer']='SYNTHETIC TEST FIXTURE; not real visual review'
            for c in item['checks']:
                c.update(result='pass',observation='Synthetic evidence to exercise gate logic only.')
        return r

    def test_planned_prompt_applies_current_style_and_scopes_two_heads(self):
        goose=(self.run/'prompts/goose.txt').read_text();house=(self.run/'prompts/house.txt').read_text()
        self.assertIn('[CHAR_TWO_HEADS]',goose);self.assertNotIn('[CHAR_TWO_HEADS]',house)
        self.assertIn('NO gradients',goose);self.assertIn('consistent stroke width',house)
        self.assertIn('override conflicting',house)
        m=h.read_json(self.run/'manifest.json')
        self.assertFalse(m['recomposition_enabled'])
        self.assertTrue(all(i['prompt_status']=='planned_not_executed' for i in m['items']))
        self.assertTrue(all(len(i['generation_inputs'])<=2 for i in m['items']))

    def test_good_alpha_does_not_auto_approve_style_or_allow_export(self):
        r=h.validate(self.run)
        self.assertEqual(r['state'],'needs_review')
        self.assertTrue(all(t['result']=='pass' for i in r['items'] for t in i['technical']))
        out=self.root/'not-exported'
        self.assertEqual(h.export(self.run,h.review_template(self.run),out)['state'],'needs_review')
        self.assertFalse(out.exists())

    def test_full_evidence_exports_identical_files_without_recomposition(self):
        out=self.root/'export'
        r=h.export(self.run,self.passing_review(),out)
        self.assertEqual(r['state'],'accepted')
        self.assertEqual((out/'characters/goose.png').read_bytes(),self.asset.read_bytes())
        records=Path(r['internal_record_dir'])
        self.assertFalse(h.read_json(records/'manifest.json')['recomposition_performed'])
        self.assertTrue((records/'acceptance.json').is_file())
        self.assertFalse(records.is_relative_to(out))
        self.assertEqual({p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()},
                         {'characters/goose.png','buildings/house.png','background/background.png'})

    def test_default_delivery_excludes_html_comparisons_and_run_records(self):
        (self.run/'result.html').write_text('<html>internal old report</html>')
        Image.new('RGB',(12,12),'white').save(self.run/'source-comparison.png')
        out=self.root/'images-only'
        result=h.export(self.run,self.passing_review(),out)
        self.assertEqual(result['delivery_mode'],'images_only')
        self.assertEqual(len([p for p in out.rglob('*') if p.is_file()]),3)
        self.assertFalse((out/'result.html').exists())
        self.assertFalse((out/'source-comparison.png').exists())
        self.assertFalse(list(out.rglob('*.json')))
        self.assertTrue((Path(result['internal_record_dir'])/'visual-review.json').is_file())

    def test_visual_failure_blocks_export(self):
        r=self.passing_review();r['items'][0]['checks'][0]['result']='fail'
        out=self.root/'blocked-export'
        self.assertEqual(h.export(self.run,r,out)['state'],'blocked')
        self.assertFalse(out.exists())

    def test_pass_without_observation_or_reviewer_is_pending(self):
        r=self.passing_review();r['items'][0]['checks'][0]['observation']='  '
        self.assertEqual(h.validate(self.run,r)['state'],'needs_review')
        r=self.passing_review();r['items'][1]['reviewer']=''
        self.assertEqual(h.validate(self.run,r)['state'],'needs_review')

    def test_image_replacement_invalidates_prior_review(self):
        r=self.passing_review()
        other=self.root/'other.png';im=Image.open(self.asset);im.putpixel((8,8),(10,20,30,255));im.save(other)
        h.register(self.run,'goose',other)
        v=h.validate(self.run,r)
        self.assertEqual(v['state'],'blocked')
        self.assertTrue(any('stale' in x for i in v['items'] for x in i['issues']))
        m=h.read_json(self.run/'manifest.json')
        self.assertTrue(m['items'][0]['artifact_history'])

    def test_policy_revision_invalidates_prior_review(self):
        r=self.passing_review()
        self.profile['source']['revision_id']=148
        h.write_json(self.profile_path,self.profile)
        v=h.validate(self.run,r)
        self.assertEqual(v['state'],'blocked')
        self.assertTrue(any('profile changed' in s for s in v['errors']))

    def test_rgb_fake_transparency_opaque_and_empty_assets_are_rejected(self):
        for mode,color in [('RGB','#ffffff'),('RGBA',(255,255,255,255)),('RGBA',(0,0,0,0))]:
            path=self.root/('bad-'+mode+str(color)+'.png');Image.new(mode,(40,50),color).save(path)
            h.register(self.run,'goose',path)
            self.assertEqual(h.validate(self.run,self.passing_review())['state'],'blocked')

    def test_wrong_and_duplicate_review_rules_cannot_pass(self):
        for edit in ('unknown','duplicate','not_applicable'):
            r=self.passing_review()
            if edit=='unknown':r['items'][0]['checks'][0]['rule_id']='UNKNOWN'
            elif edit=='duplicate':r['items'][0]['checks'].append(r['items'][0]['checks'][0].copy())
            else:r['items'][1]['checks'].append({'rule_id':'CHAR_TWO_HEADS','result':'pass','observation':'invalid scope'})
            self.assertEqual(h.validate(self.run,r)['state'],'blocked')

    def test_forged_crop_and_extra_reference_are_blocked(self):
        m=h.read_json(self.run/'manifest.json');ref=m['items'][0]['generation_inputs'][1]
        path=self.run/ref['file'];Image.new('RGB',(25,40),'red').save(path)
        ref['sha256']=h.file_hash(path);h.write_json(self.run/'manifest.json',m)
        self.assertEqual(h.validate(self.run,self.passing_review())['state'],'blocked')
        m['items'][1]['generation_inputs'].append({'file':m['source']['file'],'role':'policy_example','sha256':m['source']['sha256']})
        h.write_json(self.run/'manifest.json',m)
        self.assertEqual(h.validate(self.run,self.passing_review())['state'],'blocked')

    def test_bad_bbox_fails_before_creating_run(self):
        inv=copy.deepcopy(self.inventory);inv['items'][0]['source_bbox']=[0,0,65,40]
        out=self.root/'bad-plan'
        with self.assertRaises(ValueError):h.prepare(self.source,inv,out,self.profile_path)
        self.assertFalse(out.exists())

    def test_changed_source_or_prompt_is_blocked(self):
        r=self.passing_review()
        (self.run/'prompts/goose.txt').write_text('Old gradient-heavy prompt')
        self.assertEqual(h.validate(self.run,r)['state'],'blocked')
        Image.new('RGB',(64,64),'blue').save(self.run/'input/source.png')
        self.assertEqual(h.validate(self.run,r)['state'],'blocked')

    def test_empty_run_cannot_be_accepted(self):
        m=h.read_json(self.run/'manifest.json');m['items']=[];h.write_json(self.run/'manifest.json',m)
        self.assertEqual(h.validate(self.run)['state'],'blocked')

    def test_changed_normative_document_invalidates_review(self):
        r=self.passing_review()
        original=self.snapshot.read_bytes()
        self.snapshot.write_text('{}')
        self.assertEqual(h.validate(self.run,r)['state'],'blocked')
        self.snapshot.write_bytes(original)
        (self.run/'policy/source-document.json').write_text('{}')
        self.assertEqual(h.validate(self.run,r)['state'],'blocked')

    def test_open_edges_is_background_only_and_preserves_source_boundary(self):
        bg=(self.run/'prompts/background.txt').read_text()
        self.assertIn('[BG_OPEN_EDGES]',bg)
        self.assertIn('supporting arches',bg)
        self.assertIn('normal thin color-aware outlines',bg)
        for name in ('goose','house'):
            self.assertNotIn('[BG_OPEN_EDGES]',(self.run/f'prompts/{name}.txt').read_text())
        m=h.read_json(self.run/'manifest.json')
        self.assertEqual(len(m['items'][-1]['generation_inputs']),1)
        self.assertEqual({f['id'] for f in m['profile']['feedback_sources']},
                         {'background-open-edges-20260910', 'asset-art-v2-20260911',
                          'background-richness-20260911', 'formal-release-20260914',
                          'background-detail-volume-20260914', 'background-b-large-forms-20260915',
                      'background-placement-space-20260916'})
        self.assertFalse(m['profile']['feedback_sources'][0]['reference_image']['generation_input'])
        rule=next(c for c in h.review_template(self.run)['items'][-1]['checks'] if c['rule_id']=='BG_OPEN_EDGES')
        self.assertEqual(rule['source']['kind'],'user_feedback')
        self.assertIsNone(rule['source']['block_id'])

    def test_background_border_review_is_required_but_allows_minimal_structure(self):
        r=self.passing_review();bg=r['items'][-1]
        check=next(c for c in bg['checks'] if c['rule_id']=='BG_OPEN_EDGES')
        check['result']='unreviewed'
        self.assertEqual(h.validate(self.run,r)['state'],'needs_review')
        check.update(result='fail',observation='Synthetic unwanted raised perimeter border.')
        out=self.root/'border-blocked'
        self.assertEqual(h.export(self.run,r,out)['state'],'blocked')
        self.assertFalse(out.exists())
        check.update(result='pass',observation='Synthetic fixture: only a necessary vertical terrain face and thin outline; no raised perimeter decoration.')
        self.assertEqual(h.validate(self.run,r)['state'],'accepted')

    def test_changed_feedback_evidence_invalidates_review(self):
        r=self.passing_review();m=h.read_json(self.run/'manifest.json')
        pin=m['profile']['feedback_sources'][0]
        image=self.run/pin['reference_image']['file']
        image.write_bytes(b'changed evidence')
        self.assertEqual(h.validate(self.run,r)['state'],'blocked')
        (self.run/pin['file']).write_text('{}')
        self.assertEqual(h.validate(self.run,r)['state'],'blocked')

    def test_asset_v2_rules_are_scoped_and_do_not_flatten_backgrounds(self):
        bg=(self.run/'prompts/background.txt').read_text()
        asset=(self.run/'prompts/house.txt').read_text()
        for rule in ('ASSET_OUTLINE_LOCAL', 'ASSET_VOLUME_READABLE', 'ASSET_FORM_EXAGGERATION'):
            self.assertIn('['+rule+']',asset)
            self.assertNotIn('['+rule+']',bg)
        self.assertIn('[BG_ENVIRONMENT_RICHNESS]',bg)
        self.assertNotIn('[DETAIL_FLAT]',bg)
        self.assertNotIn('[VOLUME_WEAK]',asset)
        self.assertNotIn('NO gradients',bg)
        self.assertIn('KEEP water flow, foam and soft terrain shading',bg)
        self.assertNotIn('KEEP original trees',bg)
        self.assertIn('NOT a flat icon',asset)

    def test_each_new_asset_review_is_required_for_export(self):
        for rule in ('ASSET_OUTLINE_LOCAL', 'ASSET_VOLUME_READABLE', 'ASSET_FORM_EXAGGERATION'):
            with self.subTest(rule=rule):
                review=self.passing_review()
                check=next(c for c in review['items'][1]['checks'] if c['rule_id']==rule)
                check.update(result='fail',observation='Synthetic failure of the new required art dimension.')
                self.assertEqual(h.validate(self.run,review)['state'],'blocked')
                check.update(result='unreviewed',observation='')
                self.assertEqual(h.validate(self.run,review)['state'],'needs_review')
    def test_formal_release_preserves_v2_asset_prompts(self):
        old=h.read_json(h.ROOT/'profiles/playcity-art-1.2.0.json')
        for category in ('building','vehicle','facility','character'):
            item={'category':category,'identity_brief':'test object'}
            self.assertEqual(h.compile_prompt(item,old),h.compile_prompt(item,self.profile))

    def test_formal_background_volume_requires_review(self):
        self.assertIn('[BG_VOLUME_BALANCED]',(self.run/'prompts/background.txt').read_text())
        review=self.passing_review()
        check=next(x for x in review['items'][-1]['checks'] if x['rule_id']=='BG_VOLUME_BALANCED')
        check.update(result='fail',observation='Synthetic background too flat.')
        self.assertEqual(h.validate(self.run,review)['state'],'blocked')
        check['result']='unreviewed'
        self.assertEqual(h.validate(self.run,review)['state'],'needs_review')

    def test_background_detail_and_volume_are_independent_required_checks(self):
        bg=(self.run/'prompts/background.txt').read_text()
        self.assertIn('[BG_DETAIL_BALANCED]',bg)
        self.assertIn('[BG_PLACEMENT_SPACE]',bg)
        self.assertNotIn('Keep tree count and positions',bg)
        self.assertNotIn('[BG_PLACEMENT_SPACE]',(self.run/'prompts/house.txt').read_text())
        self.assertNotIn('[BG_DETAIL_BALANCED]',(self.run/'prompts/house.txt').read_text())
        self.assertNotIn('[BG_FORM_GRANULARITY]', (self.run/'prompts/house.txt').read_text())
        for rule in ('BG_DETAIL_BALANCED','BG_VOLUME_BALANCED','BG_FORM_GRANULARITY','BG_PLACEMENT_SPACE'):
            with self.subTest(rule=rule):
                review=self.passing_review()
                check=next(x for x in review['items'][-1]['checks'] if x['rule_id']==rule)
                check.update(result='fail',observation='Synthetic failure of this independent background dimension.')
                self.assertEqual(h.validate(self.run,review)['state'],'blocked')
                check['result']='unreviewed'
                self.assertEqual(h.validate(self.run,review)['state'],'needs_review')

if __name__=='__main__':unittest.main()
