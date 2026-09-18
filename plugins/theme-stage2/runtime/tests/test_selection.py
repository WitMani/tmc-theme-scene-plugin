from pathlib import Path
import copy
import json
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from selection import assess_selection, load_selection_policy

class SelectionTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'examples/venice-representative-14.json'
        self.inventory=json.loads(path.read_text())
        self.legacy_policy=load_selection_policy(path.parents[1]/"profiles/representative-selection-1.0.0.json")

    def test_fourteen_assets_and_background_count_separately(self):
        result=assess_selection(self.inventory, self.legacy_policy)
        self.assertEqual(result['state'],'within_target')
        self.assertEqual(result['distinct_asset_prototypes'],14)
        self.assertEqual(result['background_count'],1)
        self.assertEqual(result['category_counts'],{'building':4,'vehicle':3,'facility':4,'character':3})

    def test_color_variant_does_not_fill_another_prototype_slot(self):
        variant=copy.deepcopy(self.inventory['items'][0]);variant['id']='recolored-house'
        self.inventory['items'].append(variant)
        result=assess_selection(self.inventory, self.legacy_policy)
        self.assertEqual(result['distinct_asset_prototypes'],14)
        self.assertEqual(result['state'],'needs_revision')
        self.assertTrue(result['duplicate_prototypes'])

    def test_short_source_does_not_trigger_invented_slots(self):
        self.inventory['items']=self.inventory['items'][:5]
        before=copy.deepcopy(self.inventory)
        result=assess_selection(self.inventory, self.legacy_policy)
        self.assertEqual(result['state'],'under_target')
        self.assertEqual(self.inventory,before)
        self.assertEqual(result['distinct_asset_prototypes'],5)

    def test_allocation_can_adapt_inside_total_range(self):
        self.inventory['items'][4]['category']='facility'
        result=assess_selection(self.inventory, self.legacy_policy)
        self.assertEqual(result['state'],'within_target')
        self.assertEqual(result['category_counts']['vehicle'],2)
        self.assertTrue(result['notes'])

    def test_absent_source_object_is_not_a_valid_filler(self):
        self.inventory['items'][0]['source_evidence']['present']=False
        result=assess_selection(self.inventory, self.legacy_policy)
        self.assertEqual(result['state'],'needs_revision')
        self.assertTrue(any('absent' in issue for issue in result['blocking_issues']))

class DefaultSpeciesTests(unittest.TestCase):
    def inventory(self):
        return {'items': [
            {'id': f'{category}-{i}', 'category': category,
             'prototype_key': f'{category}-{i}', 'source_evidence': {'present': True, 'basis': 'test fixture'}}
            for category, number in [('building',8),('facility',6),('vehicle',3),('character',5)]
            for i in range(number)
        ] + [{'id':'background','category':'background'}]}

    def test_default_22_species(self):
        result=assess_selection(self.inventory())
        self.assertEqual(result['state'],'within_target')
        self.assertEqual(result['distinct_asset_prototypes'],22)
        self.assertEqual(result['background_count'],1)

    def test_same_total_cannot_hide_wrong_category(self):
        inventory=self.inventory()
        inventory['items'][0]['category']='facility'
        self.assertEqual(assess_selection(inventory)['state'],'needs_revision')

    def test_missing_source_is_not_accepted(self):
        inventory=self.inventory()
        inventory['items'][0]['source_evidence']['present']=False
        self.assertEqual(assess_selection(inventory)['state'],'needs_revision')

    def test_missing_species_does_not_mutate_input(self):
        inventory=self.inventory(); inventory['items'].pop(0)
        original=copy.deepcopy(inventory)
        self.assertEqual(assess_selection(inventory)['state'],'needs_revision')
        self.assertEqual(inventory,original)


class UserOverrideTests(unittest.TestCase):
    def test_explicit_total_replaces_default_without_mutating_it(self):
        inventory=json.loads((Path(__file__).resolve().parents[1]/'examples/venice-representative-14.json').read_text())
        self.assertNotEqual(assess_selection(inventory)['state'], 'within_target')
        inventory['selection_override']={'user_instruction':'只要14种素材', 'asset_count':14}
        self.assertEqual(assess_selection(inventory)['state'], 'within_target')
        self.assertEqual(load_selection_policy()['asset_count']['recommended'],22)

    def test_explicit_allocation_replaces_default(self):
        inventory={'items':[{'id':'house','category':'building'}, {'id':'bg','category':'background'}],
                   'selection_override':{'user_instruction':'只要一种建筑和背景','allocation':{'building':1}}}
        self.assertEqual(assess_selection(inventory)['state'],'within_target')
        inventory['items'][0]['category']='vehicle'
        self.assertEqual(assess_selection(inventory)['state'],'needs_revision')

    def test_conflicting_override_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection({'items':[], 'selection_override':{'user_instruction':'test','asset_count':3,'allocation':{'building':1}}})

    def test_override_requires_user_instruction(self):
        with self.assertRaises(ValueError):
            assess_selection({'items':[], 'selection_override':{'asset_count':14}})

if __name__=='__main__':unittest.main()
