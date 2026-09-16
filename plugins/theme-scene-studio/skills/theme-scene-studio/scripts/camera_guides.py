#!/usr/bin/env python3
"""Overlay deterministic camera axes without regenerating reference art."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw
from orthographic_layout import Camera


def clipped_line(center, direction, width, height):
    lo, hi = -math.inf, math.inf
    for p, d, bound in zip(center, direction, (width - 1, height - 1)):
        if abs(d) < 1e-12:
            if not 0 <= p <= bound:
                raise ValueError('Line outside canvas')
            continue
        a, b = sorted((-p / d, (bound - p) / d))
        lo, hi = max(lo, a), min(hi, b)
    if lo >= hi:
        raise ValueError('Line does not cross canvas')
    return [[center[i] + t * direction[i] for i in range(2)] for t in (lo, hi)]


def generate(source, out, camera_spec=None):
    source, out = Path(source).resolve(), Path(out).resolve()
    report_path = out.with_suffix('.json')
    if source == out or out.exists() or report_path.exists():
        raise ValueError('Use a new output filename; source and prior outputs are preserved')
    camera = Camera(**(camera_spec or {}))
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    with Image.open(source) as im:
        original = im.convert('RGBA')
    w, h = original.size
    overlay = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(overlay)
    thickness = max(1, round(min(w, h) / 640))
    lines = []
    for axis, color in ((0, (0, 210, 235, 210)), (1, (230, 40, 200, 210))):
        direction = [camera.matrix[0][axis], camera.matrix[1][axis]]
        norm = math.hypot(*direction)
        direction = [v / norm for v in direction]
        normal = [-direction[1], direction[0]]
        for offset in (-0.24, 0, 0.24):
            center = [w / 2 + offset * min(w, h) * normal[0],
                      h / 2 + offset * min(w, h) * normal[1]]
            endpoints = clipped_line(center, direction, w, h)
            draw.line([tuple(p) for p in endpoints], fill=color, width=thickness)
            dx, dy = [endpoints[1][i] - endpoints[0][i] for i in range(2)]
            error = abs(dx * direction[1] - dy * direction[0]) / math.hypot(dx, dy)
            if error > 1e-10:
                raise ValueError('Projection direction validation failed')
            lines.append(dict(axis='XY'[axis], endpoints=endpoints, direction=direction,
                              direction_error=error))
    for x, y in ((.2, .25), (.55, .45), (.8, .7)):
        endpoints = [[x * w, y * h], [x * w, (y - .065) * h]]
        draw.line([tuple(p) for p in endpoints], fill=(245, 220, 35, 220), width=thickness)
        lines.append(dict(axis='Z', endpoints=endpoints, direction=[0, -1], direction_error=0))
    result = Image.alpha_composite(original, overlay)
    unchanged = all(a == b for a, b, mask in zip(original.getdata(),
                    result.getdata(), overlay.getchannel('A').getdata()) if mask == 0)
    if not unchanged or hashlib.sha256(source.read_bytes()).hexdigest() != original_hash:
        raise ValueError('Reference preservation check failed')
    out.parent.mkdir(parents=True, exist_ok=True)
    result.save(out, format='PNG')
    report = dict(schema='camera-guides.v1', method='deterministic_script', status='passed',
                  source=str(source), source_sha256=original_hash, output=str(out),
                  output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(), canvas=[w, h],
                  camera=camera.spec(), matrix=camera.matrix, lines=lines,
                  source_unchanged=True, pixels_outside_lines_unchanged=unchanged,
                  visual_review_status='pending', scope='Overlay geometry only, not generated scene geometry')
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--scene', help='Layout scene or validated layout JSON supplying the shared camera')
    args = parser.parse_args()
    camera = json.loads(Path(args.scene).read_text())['camera'] if args.scene else None
    print(json.dumps(generate(args.source, args.out, camera), indent=2))


if __name__ == '__main__':
    main()
