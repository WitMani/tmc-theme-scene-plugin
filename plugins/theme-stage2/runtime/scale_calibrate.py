"""Per-asset proportional scale calibration against the run's scale-plan.json.

Consolidates the calibration scripts that earlier theme runs had to write by hand
(forest calibrate.py, wafu calibrate_assets.py, wild-west process_asset.py):
measure the visible alpha bounding box, scale uniformly so the primary axis hits
target_H x H_px, pad with transparent margin, register the result and bind the
measurement into scale-review.json. The visual same-scale review stays with the
executor: every touched review entry is reset to `unreviewed`.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
import harness as h
from scene_size import CONTRACT, digest

VERSION = '1.1.0'
ORIGIN = 'scale calibration to plan; not art-style approval'


def _alpha_bbox(image, threshold=CONTRACT['alpha_threshold']):
    if 'A' not in image.getbands():
        raise ValueError('Scale calibration requires real alpha; run cutout first')
    return image.getchannel('A').point(lambda v: 255 if v > threshold else 0).getbbox()


def require_real_alpha(image):
    """An RGB image or an RGBA image with every pixel opaque is not a cutout yet."""
    if 'A' not in image.getbands() or image.getchannel('A').getextrema()[0] == 255:
        raise ValueError('Scale calibration requires real alpha; run cutout first')


def _axis_index(primary_axis):
    if primary_axis not in ('width', 'height'):
        raise ValueError('primary_axis must be width or height')
    return 0 if primary_axis == 'width' else 1


def load_plan(run):
    plan_path = Path(run) / 'scale-plan.json'
    if not plan_path.is_file():
        raise ValueError('scale-plan.json missing; author the scale plan before calibrating')
    plan = h.read_json(plan_path)
    contract = h.read_json(Path(run) / 'manifest.json').get('scene_size_contract', CONTRACT)
    if plan.get('H_px') != contract['H_px'] or plan.get('alpha_threshold') != CONTRACT['alpha_threshold']:
        raise ValueError('Scale plan must match run H_px and alpha_threshold=16')
    items = plan.get('items')
    if not isinstance(items, list) or not items:
        raise ValueError('Scale plan has no items')
    ids = [x.get('id') for x in items]
    if len(set(ids)) != len(ids):
        raise ValueError('Scale plan lists an asset twice')
    if contract['H_px'] == 130:
        from size_policy import validate_scale_plan
        from size_review import validate_snapshot
        validate_snapshot(run, h.read_json(Path(run) / 'manifest.json'))
        validate_scale_plan(plan, h.read_json(Path(run) / 'scene-plan.json'))
    return plan_path, plan


def plan_entry(plan, item_id):
    entry = next((x for x in plan['items'] if x.get('id') == item_id), None)
    if entry is None:
        raise ValueError('Asset is not in scale-plan.json: ' + item_id)
    target_H = float(entry.get('target_H', 0))
    if not 0 < target_H < 100:
        raise ValueError('Invalid scale target: ' + item_id)
    _axis_index(entry.get('primary_axis'))
    return entry


def scale_to_target(image, primary_axis, target_px):
    """Uniformly scale the visible body so its primary axis measures target_px (+/-1)."""
    axis = _axis_index(primary_axis)
    box = _alpha_bbox(image)
    if not box:
        raise ValueError('No visible pixels above the alpha threshold')
    crop = image.crop(box)
    measured = crop.size[axis]
    factor = target_px / measured
    size = tuple(max(1, round(v * factor)) for v in crop.size)
    result = crop.resize(size, Image.Resampling.LANCZOS)
    # LANCZOS edge filtering can shave a pixel off the alpha bbox; the plan gate allows 1px,
    # so re-crop and set the primary axis exactly while keeping the other axis proportional.
    after = _alpha_bbox(result)
    if after and (after[axis + 2] - after[axis]) != target_px:
        result = result.crop(after)
        fixed = list(result.size)
        fixed[1 - axis] = max(1, round(result.size[1 - axis] * target_px / result.size[axis]))
        fixed[axis] = target_px
        result = result.resize(tuple(fixed), Image.Resampling.LANCZOS)
    return result, {'before_bbox': list(box), 'before_size': list(crop.size), 'measured_px': measured,
                    'factor': factor}


def pad(image, margin):
    canvas = Image.new('RGBA', (image.width + 2 * margin, image.height + 2 * margin), (0, 0, 0, 0))
    canvas.alpha_composite(image.convert('RGBA'), (margin, margin))
    return canvas


def _load_review(run, plan_path):
    path = Path(run) / 'scale-review.json'
    if path.is_file():
        review = h.read_json(path)
        if not isinstance(review.get('items'), list):
            raise ValueError('scale-review.json items must be a list')
    else:
        review = {'schema': 'stage2.scale-review.v1', 'status': 'unreviewed', 'reviewer': '',
                  'observation': '', 'items': []}
    if review.get('plan_sha256') != digest(plan_path):
        # The plan changed or this is the first calibration: every prior approval is void.
        review['plan_sha256'] = digest(plan_path)
        review['status'] = 'unreviewed'
        for entry in review['items']:
            entry['status'] = 'unreviewed'
    return path, review


def _bind_review(run, plan_path, item_id, artifact, measurement, entry):
    path, review = _load_review(run, plan_path)
    record = next((x for x in review['items'] if x.get('id') == item_id), None)
    if record is None:
        record = {'id': item_id}
        review['items'].append(record)
    record.update({'sha256': artifact['sha256'], 'status': 'unreviewed',
                   'observation': record.get('observation', '') if record.get('sha256') == artifact['sha256'] else '',
                   'primary_axis': entry['primary_axis'], 'target_H': entry['target_H'],
                   'target_px': measurement['target_px'], 'actual_px': measurement['actual_px'],
                   'before_bbox': measurement['before_bbox'], 'after_bbox': measurement['after_bbox'],
                   'factor': measurement['factor'], 'base_body_bbox': measurement.get('base_body_bbox'), 'calibrated_at': h.now()})
    review['status'] = 'unreviewed'
    h.write_json(path, review)
    return path.relative_to(Path(run)).as_posix()


def calibrate_asset(run, item_id, image=None, margin=8):
    run = Path(run).resolve()
    m = h.read_json(run / 'manifest.json')
    item = next((i for i in m['items'] if i['id'] == item_id), None)
    if item is None or item['category'] == 'background':
        raise ValueError('Scale calibration applies to an independent asset, not the background')
    if margin < 0:
        raise ValueError('margin must be non-negative')
    plan_path, plan = load_plan(run)
    entry = plan_entry(plan, item_id)
    if image is None:
        if not item.get('artifact'):
            raise ValueError('No registered candidate to calibrate; pass --image or run cutout/register first')
        source = h.inside(run, item['artifact']['file'])
    else:
        source = Path(image).resolve()
    if not source.is_file():
        raise ValueError('Calibration source image is missing: ' + str(source))
    if entry.get('source_body') and entry['source_body']['sha256'] != h.file_hash(source):
        # A repeat calibration may start from this item's previously calibrated PNG.
        for rec_file in item.get('processing_records', []):
            prior = h.read_json(h.inside(run, rec_file))
            if prior.get('output_sha256') == h.file_hash(source) and prior.get('base_body_bbox'):
                entry = dict(entry, source_body={'sha256': h.file_hash(source), 'bbox': prior['base_body_bbox']})
                break
    target_px = round(entry['target_H'] * plan['H_px'])
    signature = {'source_sha256': h.file_hash(source), 'primary_axis': entry['primary_axis'],
                 'target_H': entry['target_H'], 'H_px': plan['H_px'],
                 'alpha_threshold': CONTRACT['alpha_threshold'], 'margin': margin,
                 'algorithm_version': VERSION}
    if plan['H_px'] == 130:
        signature['size_policy_sha256'] = plan['size_policy_sha256']
        signature['entry'] = entry
    key = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
    folder = run / 'calibrated' / item_id / key[:20]
    folder.mkdir(parents=True, exist_ok=True)
    output, record_file = folder / (item_id + '.png'), folder / 'calibration.json'
    if output.exists():
        if not record_file.is_file() or h.read_json(record_file)['output_sha256'] != h.file_hash(output):
            raise ValueError('Existing calibrated output is untracked or changed')
        measurement = h.read_json(record_file)
    else:
        with Image.open(source) as im:
            require_real_alpha(im)
            scaled, measurement = scale_to_target(im.convert('RGBA'), entry['primary_axis'], target_px)
        final = pad(scaled, margin)
        if plan['H_px'] == 130:
            from size_policy import check_output_size
            after_box = _alpha_bbox(final)
            body = None
            if entry['size_class'] == 'character':
                annotation = entry.get('source_body')
                if annotation:
                    if annotation.get('sha256') != h.file_hash(source):
                        raise ValueError('Source body annotation is stale')
                    b, before = annotation.get('bbox'), measurement['before_bbox']
                    if not isinstance(b, list) or len(b) != 4 or not (before[0] <= b[0] < b[2] <= before[2] and before[1] <= b[1] < b[3] <= before[3]):
                        raise ValueError('Source body annotation must be within the visible subject')
                    sx = (after_box[2]-after_box[0]) / (before[2]-before[0])
                    sy = (after_box[3]-after_box[1]) / (before[3]-before[1])
                    body = [after_box[0]+(b[0]-before[0])*sx, after_box[1]+(b[1]-before[1])*sy, after_box[0]+(b[2]-before[0])*sx, after_box[1]+(b[3]-before[1])*sy]
                elif entry['target_wh_px'] == entry['base_body_wh_px']:
                    body = list(after_box)
                else:
                    raise ValueError('Extended character requires a source_body bbox and source sha256')
            check_output_size(entry, after_box, body)
            measurement['base_body_bbox'] = body
        final.save(output, format='PNG')
        after = _alpha_bbox(final)
        axis = _axis_index(entry['primary_axis'])
        measurement.update(signature, target_px=target_px, after_bbox=list(after),
                           actual_px=after[axis + 2] - after[axis], output_size=list(final.size),
                           source_file=str(source), output_file=output.relative_to(run).as_posix(),
                           output_sha256=h.file_hash(output), created_at=h.now(),
                           method='uniform LANCZOS resample of the alpha>16 body to target_H x plan H_px, then transparent margin')
        h.write_json(record_file, measurement)
    if abs(measurement['actual_px'] - target_px) > 1:
        raise ValueError('Calibrated size misses the plan by more than 1 px: ' + item_id)
    artifact = h.register(run, item_id, output, origin=ORIGIN)
    m = h.read_json(run / 'manifest.json')
    item = next(i for i in m['items'] if i['id'] == item_id)
    file = record_file.relative_to(run).as_posix()
    if file not in item.setdefault('processing_records', []):
        item['processing_records'].append(file)
    h.write_json(run / 'manifest.json', m)
    review_file = _bind_review(run, plan_path, item_id, artifact, measurement, entry)
    return {'artifact': artifact, 'calibration_record': file, 'scale_review': review_file,
            'target_px': target_px, 'actual_px': measurement['actual_px'], 'factor': measurement['factor'],
            'visual_review_required': True}


def calibrate_all(run, margin=8):
    run = Path(run).resolve()
    m = h.read_json(run / 'manifest.json')
    _, plan = load_plan(run)
    planned = {x['id'] for x in plan['items']}
    assets = [i for i in m['items'] if i['category'] != 'background']
    if planned != {i['id'] for i in assets}:
        raise ValueError('Scale plan must cover each non-background asset exactly once')
    results, skipped = {}, []
    for item in assets:
        if not item.get('artifact'):
            skipped.append(item['id'])
            continue
        results[item['id']] = calibrate_asset(run, item['id'], margin=margin)
    return {'calibrated': results, 'skipped_without_candidate': skipped,
            'scale_review': 'scale-review.json', 'visual_review_required': True}


def contact_sheet(run, out, columns_px=2000, gap=35, label_h=20):
    """Same-scale side-by-side sheet of the current registered assets for the visual review."""
    run, out = Path(run).resolve(), Path(out).resolve()
    if out.exists():
        raise ValueError('Contact sheet exists; use a new output path')
    m = h.read_json(run / 'manifest.json')
    images = []
    for item in m['items']:
        if item['category'] == 'background' or not item.get('artifact'):
            continue
        with Image.open(h.inside(run, item['artifact']['file'])) as im:
            images.append((item['id'], im.convert('RGBA')))
    if not images:
        raise ValueError('No registered assets to lay out')
    ruler_h = m.get('scene_size_contract', CONTRACT)['H_px']
    x, y, row_h, placements = gap, gap + label_h, 0, []
    width = max(columns_px, max(im.width for _, im in images) + 2 * gap + 40)
    for item_id, im in images:
        if x + im.width + gap > width:
            x, y, row_h = gap, y + row_h + gap + label_h, 0
        placements.append((item_id, im, x, y))
        x += im.width + gap
        row_h = max(row_h, im.height, ruler_h)
    height = y + row_h + gap
    sheet = Image.new('RGB', (width, height), '#e8e3da')
    draw = ImageDraw.Draw(sheet)
    for item_id, im, px, py in placements:
        sheet.paste(im, (px, py), im)
        draw.text((px, py - label_h), item_id, fill='#222222')
    # One 1H reference bar so the reviewer sees the run-specific scale without a separate asset.
    draw.rectangle((width - 30, height - gap - ruler_h, width - 22, height - gap), fill='#c0392b')
    draw.text((width - 60, height - gap - ruler_h - label_h), '1H', fill='#222222')
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, format='PNG')
    return {'contact_sheet': str(out), 'assets': [p[0] for p in placements], 'same_scale': True,
            'note': f'Every asset is pasted at its registered pixel size; the red bar is 1H = {ruler_h} px.'}
