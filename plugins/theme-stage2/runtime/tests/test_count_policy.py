import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('count_contract_under_test', Path(__file__).resolve().parents[1] / 'scene_contract.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)

class CountPolicyTests(unittest.TestCase):
    def plan(self, total=216):
        return {'count_policy': contract.default_count_policy(), 'assets': [{'count': total - 3}, {'count': 3}]}

    def test_default_and_exact_total(self):
        plan = self.plan()
        contract.validate_count_policy(plan, require=True)
        plan['assets'][0]['count'] -= 1
        with self.assertRaises(ValueError): contract.validate_count_policy(plan)

    def test_historical_plan_is_not_retroactively_changed(self):
        plan = {'assets': [{'count': 92}]}
        contract.validate_count_policy(plan)
        with self.assertRaises(ValueError): contract.validate_count_policy(plan, require=True)

    def test_floor_and_explicit_override(self):
        plan = self.plan(192)
        plan['count_policy'].update(mode='case_based', target_total=192, reference_case='NO_Nidaros_3')
        with self.assertRaises(ValueError): contract.validate_count_policy(plan)
        plan['count_policy'].update(mode='user_override')
        with self.assertRaises(ValueError): contract.validate_count_policy(plan)
        plan['count_policy']['user_instruction'] = 'Use192 instances for this particular experiment'
        contract.validate_count_policy(plan)
        plan = self.plan(201)
        plan['count_policy'].update(mode='case_based', target_total=201, reference_case='NO_Nidaros_3')
        contract.validate_count_policy(plan)
        plan['count_policy']['target_total'] = 200
        plan['assets'][0]['count'] -= 1
        with self.assertRaises(ValueError): contract.validate_count_policy(plan)

    def test_match3_is_explicit_and_per_prototype(self):
        plan = self.plan()
        plan['count_policy']['count_multiple'] = 3
        with self.assertRaises(ValueError): contract.validate_count_policy(plan)
        plan['count_policy']['gameplay_basis'] = 'User requested match3'
        contract.validate_count_policy(plan)
        plan['assets'][0]['count'] += 1
        plan['assets'][1]['count'] -= 1
        with self.assertRaises(ValueError): contract.validate_count_policy(plan)

if __name__ == '__main__': unittest.main()
