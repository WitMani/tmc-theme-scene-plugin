"""Count-driven screen-space terrain budget; estimates, not mask capacity."""
import argparse
import json
import math
from pathlib import Path


def number(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f'{name} must be finite and >= {minimum}')
    return value


def estimate(plan):
    canvas = plan.get('canvas', [4096, 4096])
    if canvas != [4096, 4096]:
        raise ValueError('Keep fixed 4096x4096 canvas')
    assets = plan['assets']
    if not assets:
        raise ValueError('Explicit nonempty assets required')
    options = plan.get('placement_area_options', {})
    reserve = number(options.get('reserve_ratio', .25), 'reserve_ratio')
    zones, ids = {}, set()
    total = targets = target_types = 0
    for asset in assets:
        aid = asset['id']
        if aid in ids:
            raise ValueError('Duplicate prototype ID')
        ids.add(aid)
        count = asset['count']
        if type(count) is not int or count < 1:
            raise ValueError('Each count must be a positive integer')
        if asset.get('role') not in {'target', 'distractor'}:
            raise ValueError('Explicit target/distractor role required')
        w, h = asset['target_wh_px']
        number(w, 'width', 1); number(h, 'height', 1)
        spacing = number(asset.get('placement_gap_px', max(w, h)*.2), 'placement_gap_px')
        zone = asset.get('placement_area_zone')
        if zone is None:
            allowed = asset.get('zones', [])
            if len(allowed) != 1:
                raise ValueError(f'{aid}: select placement_area_zone from zones explicitly')
            zone = allowed[0]
        if zone not in asset.get('zones', []):
            raise ValueError('Budget zone must be compatible with asset zones')
        row = zones.setdefault(zone, {'instances': 0, 'envelope_area_px2': 0, 'items': []})
        area = count*(w+spacing)*(h+spacing)
        row['instances'] += count
        row['envelope_area_px2'] += area
        row['items'].append({'id': aid, 'count': count, 'gap_px': spacing, 'area_px2': area})
        total += count
        if asset['role'] == 'target':
            targets += count; target_types += 1
    expected = plan.get('count_policy', {}).get('target_total', total)
    if total != expected:
        raise ValueError('Counts do not match total')
    routes = options.get('route_area_px2', {})
    if set(routes)-set(zones):
        raise ValueError('Route zone requires an explicit compatible asset group')
    for zone, row in zones.items():
        route = number(routes.get(zone, 0), 'route_area_px2')
        row['reserve_area_px2'] = row['envelope_area_px2']*reserve
        row['route_area_px2'] = route
        row['planned_area_px2'] = math.ceil(row['envelope_area_px2']*(1+reserve)+route)
        row['canvas_fraction'] = row['planned_area_px2']/(4096**2)
    required = sum(row['planned_area_px2'] for row in zones.values())
    return {'schema': 'placement-area.v1', 'basis': 'Authored screen-space bounding envelopes, not measured ground footprints or proven packing capacity',
            'instance_total': total, 'prototype_total': len(ids), 'target_total': targets,
            'target_prototype_total': target_types, 'reserve_ratio': reserve, 'zones': zones,
            'planned_area_px2': required, 'canvas_fraction': required/(4096**2),
            'status': 'over_canvas_budget' if required > 4096**2 else 'planning_estimate',
            'exact_visual_count_required': total <= 30}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = estimate(json.loads(Path(args.plan).read_text()))
    dest = Path(args.out); dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'instances': result['instance_total'], 'canvas_fraction': result['canvas_fraction']}))
