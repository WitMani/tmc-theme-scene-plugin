"""Image-bound evidence for size rules that cannot be inferred from alpha alone."""
import json
import math
from pathlib import Path
from PIL import Image
from size_policy import (digest, policy_fields, load_policy, validate_scene_sizes,
                         validate_scale_plan, check_output_size, number, text)

def read(path):
    return json.loads(Path(path).read_text())

def snapshot_policy(run):
    from size_policy import policy_path
    import shutil
    dest = Path(run) / 'policy/size-v2.json'
    shutil.copy2(policy_path(), dest)
    return {'file': 'policy/size-v2.json', **policy_fields()}

def validate_snapshot(run, manifest):
    pin = manifest.get('size_policy', {})
    expected = policy_fields()
    if any(pin.get(k) != v for k,v in expected.items()):
        raise ValueError('Missing or stale size policy pin; create a reviewed revision')
    path = Path(run) / 'policy/size-v2.json'
    if pin.get('file') != 'policy/size-v2.json' or digest(path) != expected['size_policy_sha256']:
        raise ValueError('Size policy snapshot changed')

def template(run):
    run = Path(run)
    m, scene = read(run/'manifest.json'), read(run/'scene-plan.json')
    validate_snapshot(run, m)
    validate_scene_sizes(scene)
    bg = next(a for a in m['items'] if a['category'] == 'background')['artifact']
    rows = {i['id']: i for i in m['items']}
    return {'schema': 'stage2.size-review.v1', **policy_fields(),
            'scene_plan_sha256': digest(run/'scene-plan.json'),
            'scale_plan_sha256': digest(run/'scale-plan.json'),
            'background_sha256': digest(run/bg['file']), 'reviewer': '',
            'large_limit_status': 'unconfigured' if scene['large_max_instances'] is None else 'unreviewed',
            'items': [{'id': a['id'], 'sha256': digest(run/rows[a['id']]['artifact']['file']),
                       'status': 'unreviewed', 'observation': '',
                       **({'base_body_bbox': None} if a['size_class'] == 'character' else {})}
                      for a in scene['assets']],
            'roads': [{'id': r['id'], 'status': 'unreviewed', 'observation': '',
                       'vehicle_id': r.get('vehicle_id'),
                       'vehicle_sha256': digest(run/rows[r['vehicle_id']]['artifact']['file']) if r.get('vehicle_id') else None,
                       'vehicle_width_px': None, 'clear_width_px': None}
                      for r in scene['road_sizes']]}

def check(run, manifest):
    run = Path(run)
    validate_snapshot(run, manifest)
    scene, scale = read(run/'scene-plan.json'), read(run/'scale-plan.json')
    status = validate_scene_sizes(scene)
    policy = validate_scale_plan(scale, scene)
    review = read(run/'size-review.json')
    if review.get('schema') != 'stage2.size-review.v1' or not text(review.get('reviewer')):
        raise ValueError('Size review requires a named reviewer')
    expected = {**policy_fields(), 'scene_plan_sha256': digest(run/'scene-plan.json'),
                'scale_plan_sha256': digest(run/'scale-plan.json')}
    if any(review.get(k) != v for k,v in expected.items()):
        raise ValueError('Size review is stale for the policy or plans')
    bg = next(i for i in manifest['items'] if i['category'] == 'background')['artifact']
    if review.get('background_sha256') != digest(run/bg['file']):
        raise ValueError('Size review is stale for the background')
    if review.get('large_limit_status') != status['large_limit_status']:
        raise ValueError('Large-instance limit status must be pass or explicitly unconfigured')
    rows = review.get('items', [])
    plans = {a['id']: a for a in scale['items']}
    if len(rows) != len(plans) or {i['id'] for i in rows} != set(plans):
        raise ValueError('Review each asset size exactly once')
    artifacts = {a['id']: a for a in manifest['items']}
    for row in rows:
        entry, item = plans[row['id']], artifacts[row['id']]
        if (item['category'] == 'character') != (entry['size_class'] == 'character'):
            raise ValueError('Character category and size class differ')
        path = run/item['artifact']['file']
        if row.get('sha256') != digest(path) or row.get('status') != 'pass' or not text(row.get('observation')):
            raise ValueError('Size review incomplete or stale: ' + row['id'])
        with Image.open(path) as im:
            if 'A' not in im.getbands():
                raise ValueError('Size check needs real alpha')
            box = im.getchannel('A').point(lambda v: 255 if v > 16 else 0).getbbox()
        check_output_size(entry, box, row.get('base_body_bbox'))
    roads = review.get('roads', [])
    planned = {r['id']: r for r in scene['road_sizes']}
    if len(roads) != len(planned) or {r['id'] for r in roads} != set(planned):
        raise ValueError('Review every road sizing row exactly once')
    for row in roads:
        original = planned[row['id']]
        if row.get('status') != 'pass' or not text(row.get('observation')) or row.get('vehicle_id') != original.get('vehicle_id'):
            raise ValueError('Road review incomplete or wrong vehicle reference')
        vehicle_id = original.get('vehicle_id')
        if vehicle_id and row.get('vehicle_sha256') != digest(run/artifacts[vehicle_id]['artifact']['file']):
            raise ValueError('Road review is stale for its vehicle')
        vw, rw = row.get('vehicle_width_px'), row.get('clear_width_px')
        if vehicle_id and number(vw):
            path = run/artifacts[vehicle_id]['artifact']['file']
            with Image.open(path) as im:
                box = im.getchannel('A').point(lambda v: 255 if v > 16 else 0).getbbox()
            if not box or vw > math.hypot(box[2]-box[0], box[3]-box[1]):
                raise ValueError('Observed vehicle width exceeds its visible subject')
        if not number(vw) or not number(rw) or not policy['road']['min_ratio'] <= rw/vw <= policy['road']['max_ratio']:
            raise ValueError('Observed road width must be 1–2.5 vehicle widths')
    return status
