import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placement_area import estimate

class PlacementAreaTests(unittest.TestCase):
    def setUp(self):
        self.plan={'count_policy': {'target_total':9},'assets':[
            {'id':'hut','count':3,'role':'target','target_wh_px':[430,400],'zones':['sand']},
            {'id':'raft','count':3,'role':'distractor','target_wh_px':[250,200],'zones':['water']},
            {'id':'goose','count':3,'role':'target','target_wh_px':[75,130],'zones':['sand']}]}
    def test_targets_are_subset_and_terrain_is_separate(self):
        r=estimate(self.plan)
        self.assertEqual((r['instance_total'],r['target_total'],r['target_prototype_total']),(9,6,2))
        self.assertEqual(r['zones']['sand']['instances'],6)
        self.assertEqual(r['zones']['water']['instances'],3)
    def test_more_or_larger_objects_need_more_space(self):
        base=estimate(self.plan)['planned_area_px2']
        self.plan['assets'][0]['target_wh_px']=[700,700]
        self.assertGreater(estimate(self.plan)['planned_area_px2'],base)
        self.plan['assets'][0]['count']=300
        self.plan['count_policy']['target_total']=306
        self.assertEqual(estimate(self.plan)['status'],'over_canvas_budget')
    def test_ambiguous_or_incompatible_terrain_rejected(self):
        self.plan['assets'][0]['zones']=['sand','grass']
        with self.assertRaises(ValueError): estimate(self.plan)
        self.plan['assets'][0]['placement_area_zone']='water'
        with self.assertRaises(ValueError): estimate(self.plan)
    def test_invalid_counts_totals_and_nonfinite_values(self):
        for value in [-1,0,True,1.5]:
            p=copy.deepcopy(self.plan); p['assets'][0]['count']=value
            with self.assertRaises(ValueError): estimate(p)
        self.plan['assets'][0]['count']=4
        with self.assertRaises(ValueError): estimate(self.plan)
        self.plan['assets'][0]['count']=3
        self.plan['assets'][0]['placement_gap_px']=float('nan')
        with self.assertRaises(ValueError): estimate(self.plan)

if __name__=='__main__': unittest.main()
