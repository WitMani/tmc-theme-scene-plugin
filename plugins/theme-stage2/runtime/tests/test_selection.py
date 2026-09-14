from pathlib import Path
import copy
import json
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from selection import assess_selection

class SelectionTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'examples/venice-representative-14.json'
        self.inventory=json.loads(path.read_text())

    def test_fourteen_assets_and_background_count_separately(self):
        result=assess_selection(self.inventory)
        self.assertEqual(result['state'],'within_target')
        self.assertEqual(result['distinct_asset_prototypes'],14)
        self.assertEqual(result['background_count'],1)
        self.assertEqual(result['category_counts'],{'building':4,'vehicle':3,'facility':4,'character':3})

    def test_color_variant_does_not_fill_another_prototype_slot(self):
        variant=copy.deepcopy(self.inventory['items'][0]);variant['id']='recolored-house'
        self.inventory['items'].append(variant)
        result=assess_selection(self.inventory)
        self.assertEqual(result['distinct_asset_prototypes'],14)
        self.assertEqual(result['state'],'needs_revision')
        self.assertTrue(result['duplicate_prototypes'])

    def test_short_source_does_not_trigger_invented_slots(self):
        self.inventory['items']=self.inventory['items'][:5]
        before=copy.deepcopy(self.inventory)
        result=assess_selection(self.inventory)
        self.assertEqual(result['state'],'under_target')
        self.assertEqual(self.inventory,before)
        self.assertEqual(result['distinct_asset_prototypes'],5)

    def test_allocation_can_adapt_inside_total_range(self):
        self.inventory['items'][4]['category']='facility'
        result=assess_selection(self.inventory)
        self.assertEqual(result['state'],'within_target')
        self.assertEqual(result['category_counts']['vehicle'],2)
        self.assertTrue(result['notes'])

    def test_absent_source_object_is_not_a_valid_filler(self):
        self.inventory['items'][0]['source_evidence']['present']=False
        result=assess_selection(self.inventory)
        self.assertEqual(result['state'],'needs_revision')
        self.assertTrue(any('absent' in issue for issue in result['blocking_issues']))

if __name__=='__main__':unittest.main()
