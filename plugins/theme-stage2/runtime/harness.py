#!/usr/bin/env python3
"""Stage 2 step 1: policy-bound prompt planning, candidate intake and export gates.

No image generation API, scene placement, recomposition or automatic style scoring.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid
from PIL import Image
from selection import load_selection_policy, assess_selection, resolve_selection_policy

ROOT = Path(__file__).resolve().parent
DEFAULT_PROFILE = ROOT / 'profiles/playcity-art-v1.json'
DEFAULT_DELIVERY = ROOT / 'profiles/delivery-v1.json'
CATEGORIES = ('background', 'building', 'vehicle', 'facility', 'character')
FOLDERS = dict(zip(CATEGORIES, ('background', 'buildings', 'vehicles', 'facilities', 'characters')))

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def policy_hash(profile):
    return hashlib.sha256(json.dumps(profile, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', value):
        raise ValueError('Item id must be a short lowercase filename-safe identifier')
    return value

def inside(run, relative):
    p = (Path(run) / relative).resolve()
    if not p.is_relative_to(Path(run).resolve()):
        raise ValueError('Run-local path escapes its run directory')
    return p

def load_profile(path=DEFAULT_PROFILE):
    p = read_json(path)
    if p.get('schema') != 'stage2.art-profile.v1' or not p.get('rules'):
        raise ValueError('Unsupported or empty art profile')
    ids = [r['id'] for r in p['rules']]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate policy rule IDs')
    if p['input_contract'].get('external_scene_images') != 1:
        raise ValueError('This harness requires exactly one Stage 1 scene input')
    if p['input_contract'].get('recomposition_enabled') is not False:
        raise ValueError('Recomposition is outside this step-1 harness')
    feedback_ids = [s['id'] for s in p.get('feedback_sources', [])]
    if len(set(feedback_ids)) != len(feedback_ids):
        raise ValueError('Duplicate user feedback source IDs')
    if any(r.get('source_kind') == 'user_feedback' and r.get('source_feedback_id') not in feedback_ids for r in p['rules']):
        raise ValueError('User feedback rule has no traceable source')
    return p

def load_delivery_policy(path=DEFAULT_DELIVERY):
    path = Path(path).resolve()
    p = read_json(path)
    if p.get('schema') != 'stage2.delivery-policy.v1' or p.get('mode') != 'images_only':
        raise ValueError('This export path supports images-only delivery')
    if any(p.get(k) is not False for k in ('html', 'source_comparison', 'extra_user_report', 'run_records_in_delivery')):
        raise ValueError('Default delivery must contain background and asset PNGs only')
    source = (path.parent / p['source']['snapshot']).resolve()
    if not source.is_file() or file_hash(source) != p['source']['snapshot_sha256']:
        raise ValueError('Delivery-policy source changed or is missing')
    return p

def feedback_files(profile, profile_path):
    """Resolve feedback evidence separately from scene-generation inputs."""
    files = []
    for entry in profile.get('feedback_sources', []):
        valid_id(entry['id'])
        snapshot = (Path(profile_path).resolve().parent / entry['snapshot']).resolve()
        if not snapshot.is_file() or file_hash(snapshot) != entry['snapshot_sha256']:
            raise ValueError('User feedback source changed or is missing: ' + entry['id'])
        data = read_json(snapshot)
        if data.get('schema') != 'stage2.user-feedback.v1' or data.get('id') != entry['id']:
            raise ValueError('User feedback snapshot identity mismatch')
        example = data.get('reference_image')
        record = {**entry, 'path': snapshot}
        if example:
            if example.get('generation_input') is not False:
                raise ValueError('Policy examples cannot become scene-generation inputs')
            image_path = inside(snapshot.parent, example['file'])
            if not image_path.is_file() or file_hash(image_path) != example['sha256']:
                raise ValueError('User feedback example changed or is missing')
            record['image'] = {**example, 'path': image_path}
        files.append(record)
    return files

def rule_source(rule):
    return {'kind': rule.get('source_kind', 'feishu_document'),
            'block_id': rule.get('source_block_id'),
            'feedback_id': rule.get('source_feedback_id'), 'quote': rule['source_quote']}

def applicable(profile, category):
    return [r for r in profile['rules'] if category in r['applies_to']]

def compile_prompt(item, profile):
    """Only identity comes from the old scene; the profile controls rendering."""
    head = [
        'STAGE 2 / INDEPENDENT ART SEPARATION / PLANNED PROMPT',
        'INPUT: Image 1 is the sole original Stage 1 scene. Image 2, when present, '
        'is a deterministic crop of that same image, used only to locate the object.',
        'PRIORITY: The production art requirements below override conflicting '
        'rendering in the Stage 1 image. Use the scene for theme and object identity. '
        'Apply the category-specific rules: independent assets need locally colored '
        'outlines, restrained readable volume and deliberate cartoon exaggeration; '
        'backgrounds preserve environmental identity and prioritize clear interior placement space. '
        'Do not inherit incompatible glossy rendering, variable line weight or tall character proportions.',
        'Normative document: ' + profile['source']['title'] +
        ' / revision ' + str(profile['source']['revision_id']) + '.',
        'Later user requirements included in this versioned profile are additional '
        'constraints, not claims about the original document wording.',
        'OBJECT IDENTITY DATA: ' + json.dumps(item['identity_brief'], ensure_ascii=False),
        'REQUIRED ART RULES:',
    ]
    head += ['[' + r['id'] + '] ' + r['prompt_en'] for r in applicable(profile, item['category'])]
    if item['category'] == 'background':
        head += [
            'OUTPUT: One independent opaque PNG background plate, at the requested '
            'source framing. Remove buildings, living characters, vehicles, movable '
            'facilities and their shadows/reflections. Reduce or relocate non-interactive decoration under the background placement rules. KEEP '
            'water flow, foam and soft terrain shading. Preserve fixed terrain and '
            'explicitly retained bridge decks, supporting arches and bank connections. '
            'Railings and decorative edge structures are not automatically protected '
            'as part of a bridge; follow the background-specific rules. Keep visible land/water boundaries '
            'and connectivity wherever consistent with the required projection. '
            'Do not invent new canals, islands, barriers or decorative objects.',
            'Hidden terrain is inferred completion, not known ground truth. '
            'Do not claim pixel-locked reconstruction or verified terrain geometry.',
        ]
    else:
        head += [
            'OUTPUT: ONE complete independent object. Exclude its neighboring '
            'objects and ground. Complete only the occluded parts needed for a usable '
            'silhouette. Preserve identifying features while applying the required '
            'simplification, local outline colors, readable volume and deliberate cartoon '
            'exaggeration; for characters only, use two-head-tall proportions.',
            'Separate living riders from vehicles; keep a sculpture that belongs '
            'to a fountain with that fountain. Do not export a whole multi-object '
            'cluster as one accidental sprite.',
            'Prefer genuine transparent PNG. If the generation tool cannot provide '
            'alpha, produce a uniform reserved matte for local background removal; '
            'do not draw a checkerboard. The matte is a technical intermediate, not '
            'the asset palette. Choose a matte distinct from the subject colors. '
            'Final export must contain real RGBA transparency and clean padding.',
        ]
    head += ['No UI, text labels, watermark or contact sheet. Do not perform scene recomposition.']
    return '\n\n'.join(head) + '\n'

def prepare(source, inventory, out, profile_path=DEFAULT_PROFILE):
    from scene_size import CONTRACT
    out, source = Path(out).resolve(), Path(source).resolve()
    profile_path = Path(profile_path).resolve()
    profile = load_profile(profile_path)
    if out.exists():
        raise ValueError('Output run already exists; use a new run directory')
    rows = inventory.get('items')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Inventory must contain a non-empty items list')
    im = Image.open(source)
    im.load()
    seen = set()
    for row in rows:
        iid = valid_id(row.get('id'))
        if iid in seen:
            raise ValueError('Duplicate item id: ' + iid)
        seen.add(iid)
        if row.get('category') not in CATEGORIES:
            raise ValueError('Unknown category: ' + str(row.get('category')))
        if not isinstance(row.get('identity_brief'), str) or not row['identity_brief'].strip():
            raise ValueError('Every item needs identity_brief')
        box = row.get('source_bbox')
        if box is not None:
            if (not isinstance(box, list) or len(box) != 4 or
                any(type(x) is not int for x in box) or
                not (0 <= box[0] < box[2] <= im.width and 0 <= box[1] < box[3] <= im.height)):
                raise ValueError('Invalid source_bbox for ' + iid)
    selection_policy = resolve_selection_policy(inventory)
    selection = assess_selection(inventory, selection_policy)
    if selection['blocking_issues']:
        raise ValueError('; '.join(selection['blocking_issues']))
    snapshot = (profile_path.parent / profile['source']['snapshot']).resolve()
    if not snapshot.is_file() or file_hash(snapshot) != profile['source']['snapshot_sha256']:
        raise ValueError('Normative source snapshot missing or changed')
    feedback = feedback_files(profile, profile_path)
    delivery_policy = load_delivery_policy()
    out.mkdir(parents=True)
    (out / 'input').mkdir()
    source_name = 'input/source' + source.suffix.lower()
    shutil.copy2(source, out / source_name)
    source_sha = file_hash(source)
    write_json(out / 'policy/profile.json', profile)
    write_json(out / 'policy/selection-profile.json', selection_policy)
    write_json(out / 'policy/delivery-profile.json', delivery_policy)
    write_json(out / 'selection-assessment.json', selection)
    (out / 'policy/source-document.json').write_bytes(snapshot.read_bytes())
    pinned_feedback = []
    for entry in feedback:
        relative = 'policy/feedback/' + entry['id'] + '/feedback.json'
        dest = inside(out, relative)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry['path'], dest)
        pin = {'id': entry['id'], 'file': relative, 'sha256': entry['snapshot_sha256']}
        if entry.get('image'):
            example = entry['image']
            image_dest = inside(dest.parent, example['file'])
            image_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(example['path'], image_dest)
            pin['reference_image'] = {'file': image_dest.relative_to(out).as_posix(),
                                      'sha256': example['sha256'], 'generation_input': False}
        pinned_feedback.append(pin)
    manifest = {
        'schema': 'stage2.run.v1', 'run_id': uuid.uuid4().hex, 'created_at': now(),
        'stage': 'independent_separation', 'recomposition_enabled': False,
        'scene_size_contract': dict(CONTRACT),
        'scene_plan_contract': {'schema': 'scene-plan.v1', 'file': 'scene-plan.json', 'sha256': None},
        'inventory_scope': inventory.get('scope', 'explicit inventory; completeness not inferred'),
        'delivery': {'mode': delivery_policy['mode'], 'policy_snapshot': 'policy/delivery-profile.json',
                     'html': False, 'source_comparison': False, 'run_records_in_delivery': False},
        'selection': {'policy_snapshot': 'policy/selection-profile.json',
                      'assessment_file': 'selection-assessment.json', 'state': selection['state'],
                      'distinct_asset_prototypes': selection['distinct_asset_prototypes'],
                      'background_count': selection['background_count']},
        'source': {'file': source_name, 'sha256': source_sha, 'copied_from': str(source),
                   'dimensions': [im.width, im.height]},
        'profile': {'reference_path': str(profile_path), 'snapshot': 'policy/profile.json',
                    'sha256': policy_hash(profile), 'document_revision': profile['source']['revision_id'],
                    'feedback_sources': pinned_feedback},
        'items': [], 'events': [{'event': 'prepared', 'at': now()}],
    }
    for row in rows:
        item = dict(row)
        item['prompt_file'] = 'prompts/' + item['id'] + '.txt'
        (out / 'prompts').mkdir(exist_ok=True)
        (out / item['prompt_file']).write_text(compile_prompt(item, profile) + '\nSCENE PLAN REQUIRED: Bind an authored scene-plan.v1 before generation; preserve all dependent rail, road and water infrastructure.\nSCENE SIZE CONTRACT: Square 4096 x 4096 background delivery; ordinary character scale H=128 visible pixels (3.125% of canvas height). Independent asset canvas sizes vary; obey the per-item target_H scale plan. Preserve square scene framing.\n', encoding='utf-8')
        item['prompt_status'] = 'planned_not_executed'
        item['prompt_sha256'] = file_hash(out / item['prompt_file'])
        item['generation_inputs'] = [{'file': source_name, 'role': 'sole_scene_source', 'sha256': source_sha}]
        if row.get('source_bbox') is not None:
            crop = 'input/crops/' + item['id'] + '.png'
            (out / 'input/crops').mkdir(exist_ok=True)
            im.crop(row['source_bbox']).save(out / crop)
            item['generation_inputs'].append({'file': crop, 'role': 'derived_crop',
                'sha256': file_hash(out / crop), 'derived_from_sha256': source_sha,
                'source_bbox': row['source_bbox']})
        item['artifact'] = None
        item['artifact_history'] = []
        manifest['items'].append(item)
    write_json(out / 'manifest.json', manifest)
    from scene_handoff import pending_plan, bind_plan
    write_json(out / 'scene-plan.draft.json', pending_plan(manifest))
    if inventory.get('scene_plan') is not None:
        bind_plan(out, inventory['scene_plan'])
        manifest = read_json(out / 'manifest.json')
    write_json(out / 'review-template.json', review_template(out))
    return manifest

def register(run, item_id, image, origin='candidate_registration'):
    run, image = Path(run).resolve(), Path(image).resolve()
    m = read_json(run / 'manifest.json')
    item = next((x for x in m['items'] if x['id'] == item_id), None)
    if item is None:
        raise ValueError('Item not in run inventory')
    with Image.open(image) as im:
        info = {'mode': im.mode, 'format': im.format, 'dimensions': list(im.size)}
    sha = file_hash(image)
    file = 'artifacts/' + item_id + '/' + sha + image.suffix.lower()
    destination = inside(run, file)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and file_hash(destination) != sha:
        raise ValueError('Immutable artifact path was modified')
    if not destination.exists():
        shutil.copy2(image, destination)
    if item['artifact']:
        item['artifact_history'].append(item['artifact'])
    item['artifact'] = {'file': file, 'sha256': sha, 'registered_at': now(),
                        'origin': origin, 'copied_from': str(image), **info}
    m['events'].append({'event': 'candidate_registered', 'item': item_id, 'sha256': sha, 'at': now()})
    write_json(run / 'manifest.json', m)
    return item['artifact']

def review_template(run):
    run = Path(run)
    m = read_json(run / 'manifest.json')
    p = read_json(inside(run, m['profile']['snapshot']))
    return {'schema': 'stage2.visual-review.v1', 'run_id': m['run_id'],
        'profile_sha256': m['profile']['sha256'], 'items': [{
            'id': i['id'], 'image_sha256': (i['artifact'] or {}).get('sha256'), 'reviewer': '',
            'checks': [{'rule_id': r['id'], 'result': 'unreviewed', 'observation': '',
                        'criterion': r['review_criterion'], 'source_quote': r['source_quote'],
                        'source': rule_source(r)}
                       for r in applicable(p, i['category'])]} for i in m['items']]}

def technical_checks(path, category):
    checks = []
    def add(name, passed, evidence):
        checks.append({'id': name, 'result': 'pass' if passed else 'fail', 'evidence': evidence})
    try:
        with Image.open(path) as im:
            im.load()
            add('PNG_FORMAT', im.format == 'PNG', str(im.format))
            if category == 'background':
                opaque = im.mode in ('RGB', 'RGBA') and ('A' not in im.getbands() or im.getchannel('A').getextrema() == (255, 255))
                add('OPAQUE_BACKGROUND', opaque, 'mode=' + im.mode)
            else:
                add('REAL_RGBA', im.mode == 'RGBA', 'mode=' + im.mode)
                if im.mode == 'RGBA':
                    alpha = im.getchannel('A')
                    ext = alpha.getextrema()
                    add('ALPHA_CONTENT', ext == (0, 255), 'alpha extrema=' + str(ext))
                    borders = [(0, 0, im.width, 1), (0, im.height-1, im.width, im.height),
                               (0, 0, 1, im.height), (im.width-1, 0, im.width, im.height)]
                    clear = all(alpha.crop(b).getextrema()[1] == 0 for b in borders)
                    add('CLEAR_BORDER', clear, 'all four canvas edges fully transparent=' + str(clear))
    except (OSError, ValueError) as e:
        add('READABLE_IMAGE', False, str(e))
    return checks

def validate(run, review=None, profile_path=None):
    run = Path(run).resolve()
    m = read_json(run / 'manifest.json')
    current_path = Path(profile_path or m['profile']['reference_path']).resolve()
    current = load_profile(current_path)
    ph = policy_hash(current)
    from scene_size import check_run
    errors = check_run(run, m)
    from scene_handoff import check_run as check_scene_handoff
    errors += check_scene_handoff(run, m)
    item_ids = [i['id'] for i in m['items']]
    if not item_ids or len(set(item_ids)) != len(item_ids):
        errors.append('Empty or duplicate run inventory')
    if any(i['category'] not in CATEGORIES for i in m['items']):
        errors.append('Unknown item category')
    if m.get('stage') != 'independent_separation' or m.get('recomposition_enabled') is not False:
        errors.append('Run is not in independent separation scope')
    if ph != m['profile']['sha256']:
        errors.append('Art profile changed; rebuild prompts and repeat visual review')
    if policy_hash(read_json(inside(run, m['profile']['snapshot']))) != m['profile']['sha256']:
        errors.append('Run profile snapshot changed')
    document = inside(run, 'policy/source-document.json')
    if not document.is_file() or file_hash(document) != current['source']['snapshot_sha256']:
        errors.append('Run normative document snapshot changed or is missing')
    current_document = (current_path.parent / current['source']['snapshot']).resolve()
    if not current_document.is_file() or file_hash(current_document) != current['source']['snapshot_sha256']:
        errors.append('Normative source document changed; refresh the versioned profile')
    try:
        current_feedback = feedback_files(current, current_path)
        pins = m['profile'].get('feedback_sources', [])
        if (len({p['id'] for p in pins}) != len(pins) or
            {p['id'] for p in pins} != {p['id'] for p in current_feedback}):
            errors.append('Run user feedback sources differ from the current profile')
        for fb in current_feedback:
            pin = next((p for p in pins if p['id'] == fb['id']), None)
            if not pin:
                continue
            snapshot = inside(run, pin['file'])
            if not snapshot.is_file() or file_hash(snapshot) != fb['snapshot_sha256']:
                errors.append('Pinned user feedback changed or is missing')
            if fb.get('image'):
                im = pin.get('reference_image', {})
                image_path = inside(run, im.get('file', ''))
                if not image_path.is_file() or file_hash(image_path) != fb['image']['sha256']:
                    errors.append('Pinned feedback example changed or is missing')
    except (ValueError, OSError, KeyError) as e:
        errors.append(str(e))
    source = inside(run, m['source']['file'])
    if not source.exists() or file_hash(source) != m['source']['sha256']:
        errors.append('Sole source image changed or is missing')
    rev = read_json(review) if isinstance(review, (str, Path)) else review
    rev = rev or {'items': []}
    ritems = rev.get('items', [])
    if not isinstance(ritems, list):
        raise ValueError('Review items must be a list')
    rids = [i['id'] for i in ritems]
    if len(set(rids)) != len(rids) or set(rids) - {i['id'] for i in m['items']}:
        errors.append('Unknown or duplicate reviewed item IDs')
    if ritems and (rev.get('schema') != 'stage2.visual-review.v1' or rev.get('run_id') != m['run_id'] or rev.get('profile_sha256') != ph):
        errors.append('Review schema, run or policy fingerprint mismatch')
    results = []
    for item in m['items']:
        issues = []
        artifact = item['artifact']
        for ref in item['generation_inputs']:
            f = inside(run, ref['file'])
            if not f.is_file() or file_hash(f) != ref['sha256']:
                issues.append('Generation input changed: ' + ref['file'])
            if ref['role'] not in ('sole_scene_source', 'derived_crop'):
                issues.append('Additional visual reference is not allowed')
            if ref['role'] == 'sole_scene_source' and (ref['file'] != m['source']['file'] or ref['sha256'] != m['source']['sha256']):
                issues.append('Generation source differs from the sole registered scene')
            if ref['role'] == 'derived_crop' and f.is_file() and source.is_file():
                try:
                    with Image.open(source) as original, Image.open(f) as crop:
                        expected = original.crop(ref['source_bbox'])
                        if crop.mode != expected.mode or crop.size != expected.size or crop.tobytes() != expected.tobytes():
                            issues.append('Crop pixels do not match the declared sole-source rectangle')
                except (OSError, ValueError, KeyError, TypeError):
                    issues.append('Cannot verify derived crop provenance')
        refs = item['generation_inputs']
        if sum(r['role'] == 'sole_scene_source' for r in refs) != 1:
            issues.append('Exactly one scene source is required')
        if any(r['role'] == 'derived_crop' and r.get('derived_from_sha256') != m['source']['sha256'] for r in refs):
            issues.append('Crop is not bound to the sole source')
        prompt = inside(run, item['prompt_file'])
        if not prompt.is_file() or file_hash(prompt) != item['prompt_sha256']:
            issues.append('Planned prompt changed; regenerate it from the profile')
        if not artifact:
            tech = [{'id': 'CANDIDATE_PRESENT', 'result': 'fail', 'evidence': 'No candidate registered'}]
            actual_hash = None
        else:
            path = inside(run, artifact['file'])
            actual_hash = file_hash(path) if path.is_file() else None
            tech = technical_checks(path, item['category'])
            if actual_hash != artifact['sha256']:
                issues.append('Registered image bytes changed')
        ri = next((r for r in ritems if r['id'] == item['id']), None)
        rules = applicable(current, item['category'])
        raw_checks = ri.get('checks', []) if ri else []
        rule_ids = [c['rule_id'] for c in raw_checks]
        if len(set(rule_ids)) != len(rule_ids) or set(rule_ids) - {r['id'] for r in rules}:
            issues.append('Unknown, duplicate or non-applicable visual review rule')
        stale = bool(ri and (not actual_hash or ri.get('image_sha256') != actual_hash))
        if stale:
            issues.append('Visual review is stale or bound to a different image')
        visual = []
        for rule in rules:
            check = next((c for c in raw_checks if c['rule_id'] == rule['id']), {})
            result = check.get('result', 'unreviewed')
            observation = check.get('observation', '')
            if result not in ('pass', 'fail', 'unreviewed'):
                issues.append('Invalid review result: ' + str(result))
                result = 'unreviewed'
            evidence_ok = isinstance(observation, str) and bool(observation.strip())
            reviewer_ok = bool(ri and isinstance(ri.get('reviewer'), str) and ri['reviewer'].strip())
            if result == 'pass' and (not evidence_ok or not reviewer_ok or stale):
                result = 'unreviewed'
            visual.append({'rule_id': rule['id'], 'name': rule['name'], 'result': result,
                           'observation': observation, 'source_block_id': rule.get('source_block_id'),
                           'source': rule_source(rule)})
        blocked = issues or any(t['result'] == 'fail' for t in tech) or any(v['result'] == 'fail' for v in visual)
        state = 'blocked' if blocked else 'accepted' if all(v['result'] == 'pass' for v in visual) else 'needs_review'
        results.append({'id': item['id'], 'category': item['category'], 'image_sha256': actual_hash,
                        'state': state, 'technical': tech, 'visual': visual, 'issues': issues})
    state = 'blocked' if errors or any(i['state'] == 'blocked' for i in results) else 'needs_review' if any(i['state'] != 'accepted' for i in results) else 'accepted'
    return {'schema': 'stage2.validation.v1', 'run_id': m['run_id'], 'checked_at': now(),
            'state': state, 'profile_sha256': ph, 'source_revision': current['source']['revision_id'],
            'summary': {s: sum(i['state'] == s for i in results) for s in ('accepted', 'needs_review', 'blocked')},
            'errors': errors, 'items': results,
            'scope_note': 'Technical file checks are automatic; visual style compliance requires image-bound reviewer evidence.'}

def export(run, review, out, profile_path=None):
    run, out = Path(run).resolve(), Path(out).resolve()
    delivery_policy = load_delivery_policy()
    review_data = read_json(review) if isinstance(review, (str, Path)) else review
    result = validate(run, review_data, profile_path)
    if result['state'] != 'accepted':
        return result
    if out.exists():
        raise ValueError('Export directory exists; use a fresh destination')
    record_root = run / 'export-records'
    if out == record_root or out.is_relative_to(record_root):
        raise ValueError('Export destination must be separate from internal export records')
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.stage2-export-', dir=out.parent))
    record_dir = record_root / uuid.uuid4().hex
    try:
        m = read_json(run / 'manifest.json')
        approved = {i['id']: i['image_sha256'] for i in result['items']}
        if set(approved) != {i['id'] for i in m['items']} or m['profile']['sha256'] != result['profile_sha256']:
            raise ValueError('Run changed after validation')
        exported = []
        for item in m['items']:
            relative = FOLDERS[item['category']] + '/' + item['id'] + '.png'
            dest = temporary / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(inside(run, item['artifact']['file']), dest)
            if file_hash(dest) != item['artifact']['sha256'] or file_hash(dest) != approved[item['id']]:
                raise ValueError('Artifact changed during export')
            exported.append({'id': item['id'], 'file': relative, 'sha256': file_hash(dest)})
        # Audit data stays in the working run; the delivery directory contains
        # exactly the validated background/asset PNGs and nothing else.
        write_json(record_dir / 'acceptance.json', result)
        write_json(record_dir / 'visual-review.json', review_data)
        write_json(record_dir / 'manifest.json', {'schema': 'stage2.export.v1', 'run_id': m['run_id'],
            'source_sha256': m['source']['sha256'], 'profile_sha256': m['profile']['sha256'],
            'items': exported, 'recomposition_performed': False, 'destination': str(out),
            'delivery_mode': delivery_policy['mode'], 'state': 'validated_for_export'})
        write_json(record_dir / 'delivery-policy.json', delivery_policy)
        if m.get('scene_plan_contract'):
            from scene_handoff import export_handoff
            handoff = export_handoff(run, review_data, record_dir / 'layout-handoff', profile_path)
            if handoff.get('state') != 'accepted':
                raise ValueError('Handoff validation changed during PNG export')
            result['layout_handoff'] = handoff['handoff']
        temporary.rename(out)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    result['exported_to'] = str(out)
    result['internal_record_dir'] = str(record_dir)
    result['delivery_mode'] = delivery_policy['mode']
    return result

def import_case(case, out, profile_path=DEFAULT_PROFILE, inventory_path=None):
    case = Path(case).resolve()
    old = read_json(case / 'manifest.json')
    if not isinstance(old.get('input'), str) or not isinstance(old.get('assets'), list):
        raise ValueError('Adapter expects the existing independent-split case manifest')
    inventory = read_json(inventory_path) if inventory_path else {'scope': old.get('scope', 'legacy samples'), 'items': [
        {'id': a['id'], 'name': a['name'], 'category': a['category'],
         'identity_brief': a['id'].replace('-', ' '), 'source_bbox': a['source_bbox']}
        for a in old['assets']] + [{'id': 'background', 'name': '空背景', 'category': 'background',
        'identity_brief': 'The source scene terrain and its retained structural bridges.'}]}
    candidates = {a['id']: case / a['file'] for a in old['assets']}
    candidates['background'] = case / old['background_file']
    if {i['id'] for i in inventory['items']} != set(candidates):
        raise ValueError('Import inventory must match every asset and background in the case')
    prepare(case / old['input'], inventory, out, profile_path)
    for iid, path in candidates.items():
        register(out, iid, path, origin='legacy_candidate; not generated under this art profile')
    write_json(Path(out) / 'review-template.json', review_template(out))
    return read_json(Path(out) / 'manifest.json')

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--source', required=True); p.add_argument('--inventory', required=True); p.add_argument('--out', required=True); p.add_argument('--profile', default=str(DEFAULT_PROFILE))
    p.add_argument('--scene-plan', help='Authored scene-plan.v1 for this source image')
    p = sub.add_parser('bind-scene-plan'); p.add_argument('--run', required=True); p.add_argument('--plan', required=True)
    p = sub.add_parser('infrastructure-template'); p.add_argument('--run', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('handoff'); p.add_argument('--run', required=True); p.add_argument('--review', required=True); p.add_argument('--out', required=True); p.add_argument('--profile', default=str(DEFAULT_PROFILE))
    p = sub.add_parser('import-case'); p.add_argument('--case', required=True); p.add_argument('--out', required=True); p.add_argument('--inventory'); p.add_argument('--profile', default=str(DEFAULT_PROFILE))
    p = sub.add_parser('register'); p.add_argument('--run', required=True); p.add_argument('--id', required=True); p.add_argument('--image', required=True)
    p = sub.add_parser('review-template'); p.add_argument('--run', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('selection-check'); p.add_argument('--inventory', required=True); p.add_argument('--out')
    p = sub.add_parser('record-call'); p.add_argument('--run', required=True); p.add_argument('--id', required=True); p.add_argument('--image', required=True); p.add_argument('--prompt', required=True); p.add_argument('--input', action='append', required=True); p.add_argument('--tool', default='image_gen.imagegen')
    p = sub.add_parser('cutout'); p.add_argument('--run', required=True); p.add_argument('--id', required=True); p.add_argument('--image', required=True); p.add_argument('--matte', default='auto'); p.add_argument('--shadowed-matte', action='store_true')
    p = sub.add_parser('calibrate', help='uniformly scale the alpha body of an asset to its scale-plan target, register it and bind scale-review.json'); p.add_argument('--run', required=True); p.add_argument('--id'); p.add_argument('--all', action='store_true'); p.add_argument('--image', help='defaults to the currently registered candidate'); p.add_argument('--margin', type=int, default=8)
    p = sub.add_parser('scale-contact', help='same-scale side-by-side sheet of the registered assets for the visual scale review'); p.add_argument('--run', required=True); p.add_argument('--out', required=True)
    for cmd in ('validate', 'export'):
        p = sub.add_parser(cmd); p.add_argument('--run', required=True); p.add_argument('--review', required=cmd == 'export'); p.add_argument('--out', required=cmd == 'export'); p.add_argument('--profile', default=str(DEFAULT_PROFILE))
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare':
            inventory = read_json(args.inventory)
            if args.scene_plan:
                inventory['scene_plan'] = read_json(args.scene_plan)
            m = prepare(args.source, inventory, args.out, args.profile)
            result = {'run': str(Path(args.out).resolve()), 'planned_items': len(m['items']),
                      'selection': m['selection'], 'generation_calls': 0}
        elif args.command == 'bind-scene-plan':
            from scene_handoff import bind_plan
            result = bind_plan(args.run, read_json(args.plan))
        elif args.command == 'infrastructure-template':
            from scene_handoff import infrastructure_template
            if Path(args.out).exists():
                raise ValueError('Review exists; use a new output path')
            write_json(args.out, infrastructure_template(args.run))
            result = {'template': args.out}
        elif args.command == 'handoff':
            from scene_handoff import export_handoff
            result = export_handoff(args.run, args.review, args.out, args.profile)
        elif args.command == 'import-case':
            m = import_case(args.case, args.out, args.profile, args.inventory)
            result = {'run': str(Path(args.out).resolve()), 'imported_candidates': len(m['items']), 'generation_calls': 0, 'new_style_approval': False}
        elif args.command == 'register':
            result = register(args.run, args.id, args.image)
        elif args.command == 'review-template':
            if Path(args.out).exists():
                raise ValueError('Review file exists; refusing to overwrite reviewer work')
            write_json(args.out, review_template(args.run)); result = {'template': args.out}
        elif args.command == 'selection-check':
            result = assess_selection(read_json(args.inventory))
            if args.out:
                write_json(args.out, result)
        elif args.command == 'record-call':
            from production import record_call
            result = record_call(args.run, args.id, args.image, args.prompt, args.input, args.tool)
        elif args.command == 'cutout':
            from production import cutout_candidate
            result = cutout_candidate(args.run, args.id, args.image, args.matte, args.shadowed_matte)
        elif args.command == 'calibrate':
            from scale_calibrate import calibrate_asset, calibrate_all
            if bool(args.id) == bool(args.all):
                raise ValueError('Pass exactly one of --id or --all')
            if args.all and args.image:
                raise ValueError('--image applies to a single --id')
            result = calibrate_all(args.run, args.margin) if args.all else calibrate_asset(args.run, args.id, args.image, args.margin)
        elif args.command == 'scale-contact':
            from scale_calibrate import contact_sheet
            result = contact_sheet(args.run, args.out)
        elif args.command == 'validate':
            result = validate(args.run, args.review, args.profile)
            write_json(args.out or Path(args.run) / 'validation.json', result)
        else:
            result = export(args.run, args.review, args.out, args.profile)
        print(json.dumps(result if 'items' not in result else {k: v for k, v in result.items() if k != 'items'}, ensure_ascii=False, indent=2))
        if args.command == 'selection-check':
            return 1 if result['blocking_issues'] else 0
        return {'accepted': 0, 'needs_review': 3, 'blocked': 1}.get(result.get('state'), 0)
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
