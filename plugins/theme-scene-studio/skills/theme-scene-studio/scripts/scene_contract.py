"""Portable scene-plan contract shared by Stage 1, Stage 2 and Layout.

This validates authored evidence, not image semantics or playable difficulty.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = 'scene-plan.v1'
ZONES = {'grass', 'sand', 'snow', 'seafloor', 'platform', 'road', 'rail', 'water',
         'shore', 'bridge', 'cliff', 'hazard', 'void', 'airspace', 'obstacle'}
CLASSES = {'person', 'shore_person', 'land_animal', 'aquatic', 'flying_animal',
           'prop', 'building', 'tree', 'rock', 'vehicle', 'rail_vehicle', 'boat',
           'submarine', 'aircraft'}
INFRA = {'rail', 'water', 'road', 'bridge', 'platform'}
CLASS_DEPENDENCIES = {'rail_vehicle': {'rail'}, 'boat': {'water'},
                      'submarine': {'water'}, 'vehicle': {'road'}}

def read(path):
    return json.loads(Path(path).read_text())

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def contained(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Path escapes package: ' + str(relative))
    return path

def text(value):
    return isinstance(value, str) and bool(value.strip())

def default_count_policy():
    settings = read(Path(__file__).with_name('scene-count-settings.json'))
    return {'id': settings['id'], 'mode': 'default',
            'target_total': settings['default_target'],
            'count_multiple': settings['default_count_multiple'],
            'basis': settings['source'] + '; reference ' + settings['reference_case'] +
                     '. Author per-prototype counts before binding; no capacity assumed.'}

def validate_count_policy(plan, require=False):
    policy = plan.get('count_policy')
    if policy is None:
        if require:
            raise ValueError('New theme plan requires count_policy; default target is 216 instances')
        return  # Historical plans keep their existing explicit instance contract.
    settings = read(Path(__file__).with_name('scene-count-settings.json'))
    if not isinstance(policy, dict) or policy.get('id') != settings['id']:
        raise ValueError('Unknown scene count policy')
    mode = policy.get('mode')
    target = policy.get('target_total')
    if mode not in {'default', 'case_based', 'user_override'} or type(target) is not int or target < 1:
        raise ValueError('Count policy requires a positive target_total and valid mode')
    if not text(policy.get('basis')):
        raise ValueError('Count target requires an explicit provenance basis')
    if mode == 'default' and target != settings['default_target']:
        raise ValueError('Default theme target must be 216; use case_based or explicit user_override')
    if mode != 'user_override' and target < settings['minimum_total']:
        raise ValueError('Default/case-based theme plans must contain more than 200 instances')
    if mode == 'user_override' and not text(policy.get('user_instruction')):
        raise ValueError('Count override requires the actual user instruction')
    if mode == 'case_based' and policy.get('reference_case') not in {c['case'] for c in settings['cases']}:
        raise ValueError('Case-based target requires a bundled reference case')
    multiple = policy.get('count_multiple', 1)
    if type(multiple) is not int or multiple not in (1, 3):
        raise ValueError('count_multiple must be 1, or 3 for explicitly selected match-3 gameplay')
    if multiple == 3 and not text(policy.get('gameplay_basis')):
        raise ValueError('Match-3 count multiples require a gameplay basis')
    if sum(a['count'] for a in plan['assets']) != target:
        raise ValueError('Per-prototype counts do not sum to the authored scene target')
    if any(a['count'] % multiple for a in plan['assets']):
        raise ValueError('Prototype count violates the selected gameplay multiple')

def validate_plan(plan, asset_ids=None, source_sha=None):
    if not isinstance(plan, dict) or plan.get('schema') != SCHEMA:
        raise ValueError('scene-plan.v1 is required')
    if plan.get('canvas') != [4096, 4096] or plan.get('H_px') not in (128, 130):
        raise ValueError('Scene plan must use 4096x4096 and H_px=130 (128 for historical plans)')
    if not re.fullmatch('[a-f0-9]{64}', str(plan.get('source_sha256', ''))):
        raise ValueError('Scene plan must bind the actual Stage 1 image hash')
    if source_sha and plan['source_sha256'] != source_sha:
        raise ValueError('Scene plan belongs to a different Stage 1 image')
    density = plan.get('density', {})
    if not text(density.get('intent')) or not text(density.get('basis')):
        raise ValueError('Explicit density intent and basis are required')
    goals = plan.get('goals', [])
    if not goals or any(not text(g.get('id')) or not text(g.get('description')) for g in goals):
        raise ValueError('Scene goals require stable IDs and descriptions')
    if len({g['id'] for g in goals}) != len(goals):
        raise ValueError('Duplicate scene goal IDs')
    assets = plan.get('assets', [])
    if not isinstance(assets, list) or not assets:
        raise ValueError('Explicit instance plan is required; prototypes are not counts')
    ids = set()
    for a in assets:
        name = a.get('id', '')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name) or name in ids:
            raise ValueError('Invalid or duplicate asset ID: ' + str(name))
        ids.add(name)
        if type(a.get('count')) is not int or a['count'] < 1:
            raise ValueError('Positive explicit instance count required: ' + name)
        basis = a.get('count_basis', {})
        if basis.get('mode') not in {'user', 'observed', 'authored'} or not text(basis.get('reason')):
            raise ValueError('Count provenance required: ' + name)
        if type(a.get('critical')) is not bool:
            raise ValueError('Explicit core-scene flag required: ' + name)
        if a.get('class') not in CLASSES or a.get('role') not in {'target', 'distractor'}:
            raise ValueError('Layout class and role required: ' + name)
        zones, requires = a.get('zones'), a.get('requires')
        if not isinstance(zones, list) or not zones or set(zones) - ZONES:
            raise ValueError('Invalid placement zones: ' + name)
        if not isinstance(requires, list) or set(requires) - INFRA:
            raise ValueError('Explicit infrastructure dependency list required: ' + name)
        if not CLASS_DEPENDENCIES.get(a['class'], set()).issubset(requires):
            raise ValueError('Missing vehicle infrastructure dependency: ' + name)
    if not any(a['critical'] for a in assets):
        raise ValueError('Identify at least one core scene asset')
    if asset_ids is not None and ids != set(asset_ids):
        raise ValueError('Scene plan and selected prototype IDs differ; explicitly revise the plan')
    infrastructure = plan.get('infrastructure', [])
    kinds = set()
    for row in infrastructure:
        if row.get('kind') not in INFRA or row['kind'] in kinds or not text(row.get('description')):
            raise ValueError('Unique infrastructure kind and spatial description required')
        kinds.add(row['kind'])
    needed = {kind for a in assets for kind in a['requires']}
    if needed - kinds:
        raise ValueError('Infrastructure plan missing: ' + ', '.join(sorted(needed - kinds)))
    validate_count_policy(plan)
    from size_policy import validate_scene_sizes
    validate_scene_sizes(plan)
    return plan

def dependency_prompt(plan):
    structures = '; '.join(r['kind'] + ': ' + r['description'] for r in plan['infrastructure'])
    return ('\nSCENE HANDOFF REQUIREMENTS\nRetain all required support infrastructure: ' +
            (structures or 'none declared') + '. Railway tracks are functional ground infrastructure, '
            'not decorative railings. Do not erase tracks needed by trains, water needed by boats, '
            'or roads needed by land vehicles. Preserve navigable width, continuity and bridge landings. '
            'Clear removable decoration without erasing these supports.\nInstance targets: ' +
            ', '.join(a['id'] + '=' + str(a['count']) for a in plan['assets']) +
            '. Density intent: ' + plan['density']['intent'] +
            '. These are downstream placement targets, not objects to paint back into the empty background.\n')

def check_infrastructure(plan, review, background_sha, plan_sha):
    if (review.get('schema') != 'infrastructure-review.v1' or
            review.get('background_sha256') != background_sha or
            review.get('plan_sha256') != plan_sha or not text(review.get('reviewer'))):
        raise ValueError('Infrastructure review missing or stale for this background/plan')
    rows = review.get('checks', [])
    expected = {r['kind'] for r in plan['infrastructure']}
    if len(rows) != len(expected) or {r.get('kind') for r in rows} != expected:
        raise ValueError('Review each planned infrastructure kind exactly once')
    for r in rows:
        if r.get('result') != 'pass' or not text(r.get('observation')):
            raise ValueError('Infrastructure not verified: ' + str(r.get('kind')))

def validate_bundle(path):
    path = Path(path).resolve()
    path = path/'handoff.json' if path.is_dir() else path
    root, bundle = path.parent, read(path)
    if bundle.get('schema') != 'scene-handoff.v1' or bundle.get('status') != 'art_accepted_layout_pending':
        raise ValueError('Accepted Stage 2 handoff required; candidates are not production inputs')
    for record in [bundle['plan'], bundle['background'], bundle['acceptance'], bundle['infrastructure_review']] + bundle['assets']:
        if sha(contained(root, record['file'])) != record['sha256']:
            raise ValueError('Handoff file changed: ' + record['file'])
    if len({a['id'] for a in bundle['assets']}) != len(bundle['assets']):
        raise ValueError('Duplicate handoff asset IDs')
    if any(a['file'] != 'assets/' + a['id'] + '.png' for a in bundle['assets']):
        raise ValueError('Handoff asset filename must match its stable ID')
    plan = validate_plan(read(contained(root, bundle['plan']['file'])),
                         [a['id'] for a in bundle['assets']], bundle['source_sha256'])
    if plan['H_px'] == 130:
        for key in ('size_policy', 'size_review', 'scale_plan', 'scale_review'):
            record = bundle.get(key, {})
            if not record.get('file') or sha(contained(root, record['file'])) != record.get('sha256'):
                raise ValueError('Missing or changed handoff sizing evidence: ' + key)
        if bundle['size_policy']['sha256'] != plan['size_policy_sha256']:
            raise ValueError('Handoff size policy differs from scene plan')
    acceptance = read(contained(root, bundle['acceptance']['file']))
    if acceptance.get('state') != 'accepted':
        raise ValueError('Stage 2 acceptance did not pass')
    approved = {a['id']: a['image_sha256'] for a in acceptance['items']}
    for a in bundle['assets'] + [bundle['background']]:
        if approved.get(a['id']) != a['sha256']:
            raise ValueError('Acceptance is not bound to handoff PNG: ' + a['id'])
    check_infrastructure(plan, read(contained(root, bundle['infrastructure_review']['file'])),
                         bundle['background']['sha256'], bundle['plan']['sha256'])
    return root, bundle, plan

def count_findings(plan, counts):
    findings = []
    for a in plan['assets']:
        actual = counts.get(a['id'], 0)
        if actual != a['count']:
            findings.append({'item': a['id'], 'expected': a['count'], 'actual': actual,
                             'critical': a['critical'], 'reason': 'instance_count_mismatch',
                             'route': 'layout_capacity_diagnosis'})
    for name in set(counts) - {a['id'] for a in plan['assets']}:
        findings.append({'item': name, 'reason': 'unknown_asset', 'route': 'layout'})
    return findings

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--require-count-policy', action='store_true', help='Require current count settings for new theme plans')
    args = p.parse_args()
    validate_plan(read(args.plan), source_sha=sha(args.source))
    if args.require_count_policy and read(args.plan).get('H_px') != 130:
        raise ValueError('New theme plans require H_px=130')
    validate_count_policy(read(args.plan), require=args.require_count_policy)
    print('Scene plan valid; image semantics and capacity still require review.')
