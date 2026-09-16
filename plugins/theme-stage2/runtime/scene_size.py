"""Fixed scene delivery size; resampling is not native high-resolution generation."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

CONTRACT = {'id': 'scene-4096-h128-v1', 'canvas': [4096, 4096],
            'H_px': 128, 'alpha_threshold': 16}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def normalize_scene(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    record = output.with_suffix('.size.json')
    if output.exists() or record.exists() or source == output:
        raise ValueError('Use a new output path; preserve source and prior records')
    with Image.open(source) as im:
        if im.width != im.height:
            raise ValueError('Scene must be square; regenerate framing, do not stretch or crop')
        original_size = list(im.size)
        result = im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
        if result.size != (4096, 4096):
            result = result.resize((4096, 4096), Image.Resampling.LANCZOS)
        output.parent.mkdir(parents=True, exist_ok=True)
        result.save(output, format='PNG')
    info = {'contract': CONTRACT, 'source': str(source), 'source_sha256': digest(source),
            'source_dimensions': original_size, 'output': str(output),
            'output_sha256': digest(output), 'output_dimensions': [4096, 4096],
            'resampled': original_size != [4096, 4096],
            'native_4096': original_size == [4096, 4096]}
    record.write_text(json.dumps(info, indent=2) + '\n')
    return info

def check_run(run, manifest):
    """Check fixed dimensions plus independently authored, image-bound scale review."""
    if 'scene_size_contract' not in manifest:
        return []  # Historical runs retain their original contract.
    errors = []
    run = Path(run)
    try:
        if manifest['scene_size_contract'] != CONTRACT:
            raise ValueError('Scene size contract differs from scene-4096-h128-v1')
        plan_path = run / 'scale-plan.json'
        plan = json.loads(plan_path.read_text())
        review = json.loads((run / 'scale-review.json').read_text())
        if plan.get('H_px') != 128 or plan.get('alpha_threshold') != 16:
            raise ValueError('Scale plan requires H_px=128 and alpha_threshold=16')
        if review.get('plan_sha256') != digest(plan_path):
            raise ValueError('Scale review is not bound to the current scale plan')
        if review.get('status') != 'pass' or not review.get('observation', '').strip():
            raise ValueError('Scale visual review is incomplete')
        plans = {x['id']: x for x in plan['items']}
        reviews = {x['id']: x for x in review['items']}
        asset_ids = {x['id'] for x in manifest['items'] if x['category'] != 'background'}
        if set(plans) != asset_ids or len(plans) != len(plan['items']):
            raise ValueError('Scale plan must cover each non-background asset exactly once')
        if set(reviews) != asset_ids or len(reviews) != len(review['items']):
            raise ValueError('Scale review must cover each non-background asset exactly once')
        for item in manifest['items']:
            artifact = item.get('artifact')
            if not artifact:
                errors.append('Size check: missing artifact ' + item['id'])
                continue
            path = (run / artifact['file']).resolve()
            if not path.is_relative_to(run.resolve()):
                raise ValueError('Artifact is outside the run')
            with Image.open(path) as im:
                if item['category'] == 'background':
                    if im.size != (4096, 4096):
                        errors.append('Background must be 4096x4096')
                    continue
                p, r = plans[item['id']], reviews[item['id']]
                if r.get('sha256') != digest(path) or r.get('status') != 'pass':
                    errors.append('Stale or incomplete scale review: ' + item['id'])
                if 'A' not in im.getbands():
                    errors.append('Scale requires real alpha: ' + item['id'])
                    continue
                box = im.getchannel('A').point(lambda v: 255 if v > 16 else 0).getbbox()
                axis = p['primary_axis']
                if axis not in ('width', 'height') or not 0 < float(p['target_H']) < 100:
                    raise ValueError('Invalid scale target: ' + item['id'])
                size = (box[2] - box[0] if axis == 'width' else box[3] - box[1]) if box else 0
                if abs(size - round(float(p['target_H']) * 128)) > 1:
                    errors.append('Visible size differs from plan: ' + item['id'])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append('Scene size verification: ' + str(exc))
    return errors

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    print(json.dumps(normalize_scene(args.source, args.out), indent=2))
