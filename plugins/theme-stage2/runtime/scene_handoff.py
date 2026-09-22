"""Author, pin and export scene dependencies without adding reports to PNG delivery."""
from pathlib import Path
import shutil
import tempfile
from scene_contract import (read, write, sha, validate_plan, dependency_prompt,
                            check_infrastructure, SCHEMA, default_count_policy)

def pending_plan(manifest):
    return {'schema': SCHEMA, 'source_sha256': manifest['source']['sha256'],
            'canvas': [4096, 4096], 'H_px': manifest.get('scene_size_contract', {}).get('H_px', 130),
            'count_policy': default_count_policy(),
            'density': {'intent': '', 'basis': ''}, 'goals': [], 'infrastructure': [],
            'assets': [{'id': a['id'], 'count': None, 'critical': None, 'class': None,
                        'role': 'distractor', 'zones': [], 'requires': [],
                        'count_basis': {'mode': 'authored', 'reason': ''}}
                       for a in manifest['items'] if a['category'] != 'background']}

def bind_plan(run, plan):
    import harness as h
    run = Path(run).resolve()
    m = read(run/'manifest.json')
    if any(a.get('artifact') or a.get('generation_records') for a in m['items']):
        raise ValueError('Bind the scene plan before generation; use a new revision run for changes')
    validate_plan(plan, [a['id'] for a in m['items'] if a['category'] != 'background'], m['source']['sha256'])
    if plan['H_px'] != m.get('scene_size_contract', {}).get('H_px', plan['H_px']):
        raise ValueError('Scene plan H_px must match run contract; revise inherited Stage 1 scale explicitly')
    write(run/'scene-plan.json', plan)
    m['scene_plan_contract'] = {'schema': SCHEMA, 'file': 'scene-plan.json',
                               'sha256': sha(run/'scene-plan.json')}
    profile = read(run/m['profile']['snapshot'])
    for a in m['items']:
        prompt = h.compile_prompt(a, profile) + '\nFIXED SIZE: 4096 x 4096 square background, character base body 75 x 130 px; accessories may extend beyond. Small objects 150-300 px per axis; medium 301-500; large 501-830. Road width 1-2.5 vehicle widths.\n' + dependency_prompt(plan)
        (run/a['prompt_file']).write_text(prompt)
        a['prompt_sha256'] = sha(run/a['prompt_file'])
    write(run/'manifest.json', m)
    return {'state': 'plan_bound', 'scene_plan': str(run/'scene-plan.json')}

def check_run(run, manifest):
    if 'scene_plan_contract' not in manifest:
        return []
    run = Path(run)
    try:
        pin = manifest['scene_plan_contract']
        if not pin.get('sha256') or sha(run/'scene-plan.json') != pin['sha256']:
            raise ValueError('Scene plan is missing, unbound or changed; bind before generation')
        plan = validate_plan(read(run/'scene-plan.json'),
                             [a['id'] for a in manifest['items'] if a['category'] != 'background'],
                             manifest['source']['sha256'])
        backgrounds = [a for a in manifest['items'] if a['category'] == 'background']
        if len(backgrounds) != 1 or not backgrounds[0].get('artifact'):
            raise ValueError('Exactly one registered background required for infrastructure review')
        bg = backgrounds[0]['artifact']
        check_infrastructure(plan, read(run/'infrastructure-review.json'),
                             sha(run/bg['file']), pin['sha256'])
        return []
    except (ValueError, KeyError, OSError, TypeError) as exc:
        return ['Scene handoff: ' + str(exc)]

def infrastructure_template(run):
    run = Path(run)
    m = read(run/'manifest.json')
    plan = validate_plan(read(run/'scene-plan.json'))
    bg = next(a['artifact'] for a in m['items'] if a['category'] == 'background')
    if not bg:
        raise ValueError('Register the final background first')
    return {'schema': 'infrastructure-review.v1', 'plan_sha256': sha(run/'scene-plan.json'),
            'background_sha256': sha(run/bg['file']), 'reviewer': '',
            'checks': [{'kind': r['kind'], 'result': 'unreviewed', 'observation': ''}
                       for r in plan['infrastructure']]}

def export_handoff(run, review, out, profile_path=None):
    import harness as h
    run, out = Path(run).resolve(), Path(out).resolve()
    m = read(run/'manifest.json')
    if not m.get('scene_plan_contract', {}).get('sha256'):
        raise ValueError('Legacy/candidate run needs an explicitly authored and reviewed scene plan')
    result = h.validate(run, review, profile_path)
    if result['state'] != 'accepted':
        return result
    if out.exists():
        raise ValueError('Handoff destination exists; preserve earlier revisions')
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.scene-handoff-', dir=out.parent))
    try:
        plan = read(run/'scene-plan.json')
        shutil.copy2(run/'scene-plan.json', temporary/'scene-plan.json')
        shutil.copy2(run/'infrastructure-review.json', temporary/'infrastructure-review.json')
        write(temporary/'acceptance.json', result)
        assets, background = [], None
        for a in m['items']:
            rel = 'background.png' if a['category'] == 'background' else 'assets/' + a['id'] + '.png'
            dest = temporary/rel
            dest.parent.mkdir(exist_ok=True)
            shutil.copy2(run/a['artifact']['file'], dest)
            if sha(dest) != a['artifact']['sha256']:
                raise ValueError('Image changed during handoff export')
            rec = {'id': a['id'], 'file': rel, 'sha256': sha(dest)}
            if a['category'] == 'background': background = rec
            else: assets.append(rec)
        write(temporary/'asset-manifest.json', {'schemaVersion':1, 'assets': [
            {'name': a['id'], 'file': a['id']+'.png', 'count':a['count'],
             'class':a['class'], 'role':a['role'], 'zones':a['zones']} for a in plan['assets']]})
        write(temporary/'handoff.json', {'schema':'scene-handoff.v1',
            'status':'art_accepted_layout_pending', 'source_sha256':m['source']['sha256'],
            'stage2_run_id':m['run_id'], 'background':background, 'assets':assets,
            'plan':{'file':'scene-plan.json','sha256':sha(temporary/'scene-plan.json')},
            'acceptance':{'file':'acceptance.json','sha256':sha(temporary/'acceptance.json')},
            'infrastructure_review':{'file':'infrastructure-review.json','sha256':sha(temporary/'infrastructure-review.json')}})
        from scene_contract import validate_bundle
        validate_bundle(temporary)
        temporary.rename(out)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return {'state':'accepted', 'handoff':str(out/'handoff.json'),
            'layout_status':'pending_capacity_and_visual_review'}
