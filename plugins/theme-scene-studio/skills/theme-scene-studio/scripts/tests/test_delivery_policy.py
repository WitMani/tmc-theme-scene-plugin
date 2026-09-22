import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('delivery_contract_under_test', Path(__file__).resolve().parents[1] / 'scene_contract.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)

class DeliveryPolicyTests(unittest.TestCase):
    def plan(self, vehicles=True, **policy):
        assets = [{'id': 'house', 'class': 'building'}]
        if vehicles:
            assets.append({'id': 'van', 'class': 'vehicle'})
        base = {'requested': 'auto', 'mode': 'motion' if vehicles else 'static',
                'basis': 'user did not say; cast has vehicles' if vehicles else 'no vehicles',
                'moving_vehicle_ids': ['van'] if vehicles else [],
                'route_plan': 'enters top-left edge, junction at plaza, exits bottom-right edge'}
        base.update(policy)
        return {'assets': assets, 'delivery_policy': base}

    def test_auto_matches_layout_resolution(self):
        contract.validate_delivery_policy(self.plan())
        contract.validate_delivery_policy(self.plan(vehicles=False))
        with self.assertRaises(ValueError): contract.validate_delivery_policy(self.plan(mode='static', moving_vehicle_ids=[]))
        with self.assertRaises(ValueError): contract.validate_delivery_policy(self.plan(vehicles=False, mode='motion'))

    def test_explicit_choice_keeps_user_words(self):
        plan = self.plan(requested='static', mode='static', moving_vehicle_ids=[])
        with self.assertRaises(ValueError): contract.validate_delivery_policy(plan)
        plan['delivery_policy']['user_instruction'] = '载具静止不动'
        contract.validate_delivery_policy(plan)
        with self.assertRaises(ValueError): contract.validate_delivery_policy(self.plan(requested='motion', mode='static', user_instruction='要运动'))

    def test_motion_needs_vehicles_and_route_plan(self):
        with self.assertRaises(ValueError): contract.validate_delivery_policy(self.plan(moving_vehicle_ids=[]))
        with self.assertRaises(ValueError): contract.validate_delivery_policy(self.plan(moving_vehicle_ids=['house']))
        with self.assertRaises(ValueError): contract.validate_delivery_policy(self.plan(route_plan=''))
        with self.assertRaises(ValueError): contract.validate_delivery_policy(self.plan(vehicles=False, moving_vehicle_ids=['van']))

    def test_required_only_for_new_plans(self):
        contract.validate_delivery_policy({'assets': []})
        with self.assertRaises(ValueError): contract.validate_delivery_policy({'assets': []}, require=True)

if __name__ == '__main__': unittest.main()
