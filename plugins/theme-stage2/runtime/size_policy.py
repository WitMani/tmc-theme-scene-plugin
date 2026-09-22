"""Portable size-plan validation; identical module is bundled by all three stages."""
import hashlib
import json
import math
from pathlib import Path

POLICY_ID = 'scene-4096-h130-v2'
ROUNDING_PX = 1  # Raster rounding only, not an artistic proportion tolerance.

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def policy_path():
    root = Path(__file__).resolve().parent
    return root / 'profiles/size-v2.json' if (root / 'profiles').is_dir() else root / 'size-v2.json'

def load_policy(path=None):
    path = Path(path or policy_path())
    data = json.loads(path.read_text())
    if data.get('id') != POLICY_ID or data.get('canvas') != [4096, 4096]:
        raise ValueError('Unknown size policy')
    return data

def number(value):
    return type(value) in (float, int) and math.isfinite(value) and value > 0

def pair(value):
    return isinstance(value, list) and len(value) == 2 and all(number(x) for x in value)

def text(value):
    return isinstance(value, str) and bool(value.strip())

def policy_fields():
    return {'size_policy_id': POLICY_ID, 'size_policy_sha256': digest(policy_path())}

def validate_header(plan, policy=None):
    policy = policy or load_policy()
    if plan.get('H_px') != policy['character']['base_height_px']:
        raise ValueError('Size policy and H_px disagree')
    if any(plan.get(k) != v for k, v in policy_fields().items()):
        raise ValueError('Size policy ID/hash missing or changed; rebuild the plan and repeat review')
    return policy

def validate_item(item, policy=None):
    policy = policy or load_policy()
    cls, target = item.get('size_class'), item.get('target_wh_px')
    if not pair(target) or not text(item.get('size_basis')):
        raise ValueError('Each size target requires target_wh_px and size_basis: ' + str(item.get('id')))
    if cls == 'character':
        base = [policy['character']['base_width_px'], policy['character']['base_height_px']]
        if item.get('base_body_wh_px') != base or any(x < y for x, y in zip(target, base)):
            raise ValueError('Character requires base_body_wh_px=75x130 and a full target enclosing that body')
        return
    if cls not in policy['objects']:
        raise ValueError('Unknown or missing size_class: ' + str(item.get('id')))
    limits = policy['objects'][cls]
    if any(not lo <= x <= hi for x, lo, hi in zip(target, limits['min_wh_px'], limits['max_wh_px'])):
        exception = item.get('size_exception', {})
        if not (text(exception.get('reason')) and text(exception.get('basis'))):
            raise ValueError('Target outside size class; explicit size_exception required: ' + str(item.get('id')))

def validate_scene_sizes(plan):
    if plan.get('H_px') == 128:
        if plan.get('size_policy_id'):
            raise ValueError('Legacy H128 cannot claim the H130 policy')
        return  # Preserve the historical contract.
    policy = validate_header(plan)
    assets = plan.get('assets', [])
    for item in assets:
        validate_item(item, policy)
        if item.get('class') in ('person', 'shore_person') and item['size_class'] != 'character':
            raise ValueError('Person must use character size class')
    if 'large_max_instances' not in plan:
        raise ValueError('Specify large_max_instances; null explicitly means not configured')
    cap = plan['large_max_instances']
    if cap is not None and (type(cap) is not int or cap < 0):
        raise ValueError('large_max_instances must be a nonnegative integer or null')
    # Oversized exceptions cannot hide from the large-object count limit.
    large_count = sum(a['count'] for a in assets if a['size_class'] == 'large' or
                      (a['size_class'] != 'character' and max(a['target_wh_px']) > max(policy['objects']['medium']['max_wh_px'])))
    if cap is not None and large_count > cap:
        raise ValueError('Large object instance count exceeds large_max_instances')
    roads = plan.get('road_sizes')
    if not isinstance(roads, list):
        raise ValueError('road_sizes must be an explicit list (empty for no roads)')
    has_road = any(r.get('kind') == 'road' for r in plan.get('infrastructure', []))
    if bool(roads) != has_road:
        raise ValueError('Road infrastructure and road_sizes must agree')
    ids = [r.get('id') for r in roads]
    if any(not text(x) for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('Road sizing rows require unique IDs')
    by_id = {a['id']: a for a in assets}
    for road in roads:
        vehicle = by_id.get(road.get('vehicle_id'))
        if vehicle is None:
            if road.get('vehicle_id') is not None or not text(road.get('reference_vehicle_basis')):
                raise ValueError('Road needs a real vehicle ID or an explicit virtual-vehicle basis')
        elif vehicle.get('class') != 'vehicle':
            raise ValueError('Road reference must be a road vehicle')
        vw, rw = road.get('vehicle_width_px'), road.get('clear_width_px')
        if not number(vw) or not number(rw) or not text(road.get('measurement_basis')):
            raise ValueError('Road requires transverse vehicle/clear widths and measurement_basis')
        if vehicle and vw > math.hypot(*vehicle['target_wh_px']):
            raise ValueError('Transverse vehicle width exceeds the planned subject extent')
        if not policy['road']['min_ratio'] <= rw / vw <= policy['road']['max_ratio']:
            raise ValueError('Road width must be 1–2.5 transverse vehicle widths')
    return {'large_instances': large_count, 'large_limit_status': 'unconfigured' if cap is None else 'pass'}

def validate_scale_plan(plan, scene=None):
    policy = validate_header(plan)
    rows = plan.get('items', [])
    if not rows or len({i['id'] for i in rows}) != len(rows):
        raise ValueError('Scale items require unique IDs')
    by_id = {a['id']: a for a in scene['assets']} if scene else None
    if by_id is not None and set(by_id) != {i['id'] for i in rows}:
        raise ValueError('Scene and scale asset IDs differ')
    for item in rows:
        validate_item(item, policy)
        axis = item.get('primary_axis')
        if axis not in ('width', 'height') or not number(item.get('target_H')):
            raise ValueError('Invalid primary-axis scale target')
        if abs(item['target_H'] * plan['H_px'] - item['target_wh_px'][axis == 'height']) > ROUNDING_PX:
            raise ValueError('target_H disagrees with target_wh_px')
        if by_id is not None:
            original = by_id[item['id']]
            for key in ('size_class', 'target_wh_px', 'base_body_wh_px', 'size_exception'):
                if item.get(key) != original.get(key):
                    raise ValueError('Scale target differs from bound scene plan: ' + item['id'])
    return policy

def check_output_size(entry, bbox, body_bbox=None):
    if not bbox:
        raise ValueError('No visible subject')
    actual = [bbox[2] - bbox[0], bbox[3] - bbox[1]]
    if any(abs(a-b) > ROUNDING_PX for a,b in zip(actual, entry['target_wh_px'])):
        raise ValueError('Visible width/height differs from size target: ' + entry['id'])
    if entry['size_class'] == 'character':
        if (not isinstance(body_bbox, list) or len(body_bbox) != 4 or
                not all(type(v) in (int, float) and math.isfinite(v) for v in body_bbox) or
                not (bbox[0] <= body_bbox[0] < body_bbox[2] <= bbox[2] and
                     bbox[1] <= body_bbox[1] < body_bbox[3] <= bbox[3])):
            raise ValueError('Character needs an image-bound base_body_bbox within its visible subject')
        if any(abs(a-b) > ROUNDING_PX for a,b in zip(
                [body_bbox[2]-body_bbox[0], body_bbox[3]-body_bbox[1]], entry['base_body_wh_px'])):
            raise ValueError('Character base body is not 75x130')
