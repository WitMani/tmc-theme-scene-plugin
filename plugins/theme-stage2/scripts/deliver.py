#!/usr/bin/env python3
"""Deliver generated PNGs without treating visual review as a user gate."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import uuid
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import harness


def deliver(run, out, review=None):
    run, out = Path(run).resolve(), Path(out).resolve()
    if out.exists():
        raise ValueError('Delivery destination already exists')
    manifest = harness.read_json(run / 'manifest.json')
    try:
        audit = harness.validate(run, review)
    except Exception as exc:
        audit = {'state': 'needs_review', 'errors': [str(exc)]}
    record = {'state': 'delivered', 'audit': audit, 'files': [], 'missing': []}
    out.mkdir(parents=True)
    for item in manifest['items']:
        try:
            artifact = item.get('artifact') or {}
            source = harness.inside(run, artifact['file'])
            with Image.open(source) as im:
                if im.format != 'PNG':
                    raise ValueError('Not a PNG')
                im.verify()
            if harness.file_hash(source) != artifact['sha256']:
                raise ValueError('Registered image changed')
            iid = item['id']
            if Path(iid).name != iid or iid in ('.', '..'):
                raise ValueError('Invalid item ID')
            target = out / harness.FOLDERS[item['category']] / (iid + '.png')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            record['files'].append(str(target))
        except Exception as exc:
            record['missing'].append({'id': item.get('id'), 'reason': str(exc)})
    record['state'] = 'delivered' if record['files'] else 'no_images'
    harness.write_json(run / 'export-records' / ('delivery-' + uuid.uuid4().hex + '.json'), record)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--review')
    args = parser.parse_args()
    print(json.dumps(deliver(args.run, args.out, args.review), ensure_ascii=False, indent=2))
