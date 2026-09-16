#!/usr/bin/env python3
"""World-space layout primitives -> shared orthographic SVG/PNG and auditable JSON.

No reference image is read or edited. Pillow is only needed for PNG rendering.
"""
import argparse
import copy
import json
import math
from pathlib import Path


def point(value):
    if len(value) != 3 or not all(math.isfinite(float(v)) for v in value):
        raise ValueError('Each world point must contain three finite XYZ values')
    return tuple(float(v) for v in value)


class Camera:
    def __init__(self, azimuth_deg=45, elevation_deg=45, scale=20, origin=(512, 512), override_reason=None):
        values = [azimuth_deg, elevation_deg, scale, *origin]
        if len(origin) != 2 or not all(math.isfinite(float(v)) for v in values):
            raise ValueError('Invalid camera parameters')
        if not 0 < elevation_deg < 90 or scale <= 0:
            raise ValueError('Require 0 < elevation < 90 and positive scale')
        if (azimuth_deg != 45 or elevation_deg != 45) and not override_reason:
            raise ValueError('Non-default camera requires an explicit user override reason')
        self.azimuth_deg, self.elevation_deg = azimuth_deg, elevation_deg
        self.scale, self.origin, self.override_reason = scale, tuple(origin), override_reason
        a, e = math.radians(azimuth_deg), math.radians(elevation_deg)
        self.matrix = [
            [scale * math.cos(a), -scale * math.sin(a), 0.0],
            [scale * math.sin(e) * math.sin(a), scale * math.sin(e) * math.cos(a), -scale * math.cos(e)],
        ]

    def project(self, xyz):
        xyz = point(xyz)
        return [sum(v * q for v, q in zip(row, xyz)) + o for row, o in zip(self.matrix, self.origin)]

    def spec(self):
        return dict(azimuth_deg=self.azimuth_deg, elevation_deg=self.elevation_deg,
                    scale=self.scale, origin=list(self.origin), override_reason=self.override_reason)

    def checks(self):
        x, y = self.matrix
        dot = sum(a * b for a, b in zip(x, y))
        norms = [math.sqrt(sum(a * a for a in row)) for row in self.matrix]
        return dict(row_dot_product=dot, row_norms=norms,
                    ground_circle_axis_ratio=math.sin(math.radians(self.elevation_deg)),
                    parallel_projection=True, scope='Authored sketch geometry only; not final image geometry')


def primitives(item):
    """Return world polygons. Ground widths and circles are never drawn in screen space."""
    kind = item['kind']
    if kind in ('polygon', 'polyline'):
        points = [point(v) for v in item['points']]
        if len(points) < (3 if kind == 'polygon' else 2):
            raise ValueError('Too few primitive vertices')
        return [(kind, points)]
    if kind == 'circle':
        cx, cy, z = point(item['center'])
        radius = float(item['radius'])
        if not math.isfinite(radius) or radius <= 0:
            raise ValueError('Circle radius must be positive')
        return [('polygon', [(cx + radius * math.cos(t * math.tau / 64),
                              cy + radius * math.sin(t * math.tau / 64), z) for t in range(64)])]
    if kind == 'band':
        path = [point(v) for v in item['points']]
        width = float(item['width'])
        if len(path) < 2 or not math.isfinite(width) or width <= 0:
            raise ValueError('Band requires positive world width and at least two points')
        result = []
        for p, q in zip(path, path[1:]):
            dx, dy = q[0] - p[0], q[1] - p[1]
            length = math.hypot(dx, dy)
            if length == 0:
                raise ValueError('Band contains a zero-length ground segment')
            nx, ny = -dy / length * width / 2, dx / length * width / 2
            result.append(('polygon', [(p[0]+nx,p[1]+ny,p[2]), (q[0]+nx,q[1]+ny,q[2]),
                                       (q[0]-nx,q[1]-ny,q[2]), (p[0]-nx,p[1]-ny,p[2])]))
        # Rounded ground-plane joins, also projected, prevent gaps at bends.
        for p in path[1:-1]:
            result += primitives(dict(kind='circle', center=p, radius=width / 2))
        return result
    if kind == 'box':
        x, y, z = point(item['center'])
        w, d, h = point(item['size'])
        if min(w, d, h) <= 0:
            raise ValueError('Box dimensions must be positive')
        a = math.radians(float(item.get('rotation_deg', 0)))
        if not math.isfinite(a):
            raise ValueError('Invalid box rotation')
        base = [(x+u*math.cos(a)-v*math.sin(a), y+u*math.sin(a)+v*math.cos(a), z)
                for u, v in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]
        top = [(p[0],p[1],z+h) for p in base]
        # Uniform flat fill; no roof shape, material or hard face shading.
        return [('polygon', [base[i],base[(i+1)%4],top[(i+1)%4],top[i]]) for i in range(4)] + [('polygon', top)]
    raise ValueError('Unknown world primitive: ' + str(kind))


def build(scene):
    canvas = scene.get('canvas', [1024, 1024])
    if len(canvas) != 2 or any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in canvas):
        raise ValueError('Canvas must contain two positive integers')
    camera = Camera(**scene.get('camera', {}))
    geometry = []
    items = scene['items']
    if not items:
        raise ValueError('Scene must contain world-space geometry')
    # Items are painter-ordered by the designer: terrain, routes, then depth-sorted masses.
    for index, item in enumerate(items):
        for kind, world in primitives(item):
            world = [list(v) for v in world]
            geometry.append(dict(id=item.get('id', str(index)), role=item.get('role', 'placement'),
                                 kind=kind, world=world, screen=[camera.project(v) for v in world]))
    return dict(candidate_id=scene.get('candidate_id'), canvas=canvas, camera=camera.spec(),
                matrix=camera.matrix, geometry=geometry, source_scene=copy.deepcopy(scene),
                checks=camera.checks(), visual_review_status='pending')


def validate(document):
    camera = Camera(**document['camera'])
    if document['matrix'] != camera.matrix:
        raise ValueError('Matrix differs from the declared orthographic camera')
    geometry = document['geometry']
    if not geometry:
        raise ValueError('Empty geometry cannot pass validation')
    max_error, count = 0.0, 0
    for g in geometry:
        if not g['world'] or len(g['world']) != len(g['screen']):
            raise ValueError('Missing or unequal world/screen vertex counts')
        for world, screen in zip(g['world'], g['screen']):
            if len(screen) != 2 or not all(math.isfinite(float(v)) for v in screen):
                raise ValueError('Invalid projected vertex')
            error = max(abs(a-b) for a,b in zip(camera.project(world), screen))
            max_error, count = max(max_error, error), count + 1
    if max_error > 1e-7:
        raise ValueError(f'Unprojected or inconsistent screen geometry: error={max_error}')
    # Rebuild from world primitives so a screen-space circle cannot be disguised by editing metadata.
    expected = build(document['source_scene'])
    if expected['camera'] != document['camera'] or expected['geometry'] != geometry:
        raise ValueError('Geometry does not match its world-space source primitives')
    return dict(status='passed', checked_vertices=count, max_reprojection_error_px=max_error, **camera.checks())


def validate_group(documents):
    if not documents:
        raise ValueError('No candidate documents')
    checks = [validate(d) for d in documents]
    first = documents[0]
    for document in documents[1:]:
        if document['camera'] != first['camera'] or document['canvas'] != first['canvas']:
            raise ValueError('Candidates must share camera, scale, origin and canvas')
    return dict(status='passed', shared_camera=True, candidates=checks)


def render(scene, prefix):
    from PIL import Image, ImageDraw
    document = build(scene)
    checks = validate(document)
    width, height = document['canvas']
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    paths = [Path(str(prefix)+ext) for ext in ('.svg','.png','.json','.validation.json')]
    if any(p.exists() for p in paths):
        raise FileExistsError('Output exists; use a new version suffix')
    # Neutral palette: geometry-only guidance, not western/theme art direction.
    colors = dict(environment='#dddfe1', ground='#fafafa', route='#eeeeee', placement='#f4f4f4')
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#fafafa"/>']
    im = Image.new('RGB', (width,height), '#fafafa')
    draw = ImageDraw.Draw(im)
    for g in document['geometry']:
        fill = colors.get(g['role'], colors['placement'])
        pts = [tuple(v) for v in g['screen']]
        coords = ' '.join(f'{x:.9f},{y:.9f}' for x,y in pts)
        closed = g['kind'] == 'polygon'
        tag = 'polygon' if closed else 'polyline'
        svg.append(f'<{tag} points="{coords}" fill="{fill if closed else "none"}" stroke="#9a9da1" stroke-width="1"/>')
        if closed:
            draw.polygon(pts, fill=fill)
        draw.line(pts + ([pts[0]] if closed else []), fill='#9a9da1', width=1)
    svg.append('</svg>')
    paths[0].write_text('\n'.join(svg))
    im.save(paths[1])
    paths[2].write_text(json.dumps(document, ensure_ascii=False, indent=2))
    paths[3].write_text(json.dumps(checks, indent=2))
    return [str(p) for p in paths]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    r = sub.add_parser('render')
    r.add_argument('scene', type=Path)
    r.add_argument('--output-prefix', required=True)
    v = sub.add_parser('validate')
    v.add_argument('document', type=Path, nargs='+')
    args = parser.parse_args()
    if args.command == 'render':
        print(json.dumps(render(json.loads(args.scene.read_text()), args.output_prefix), ensure_ascii=False))
    else:
        print(json.dumps(validate_group([json.loads(p.read_text()) for p in args.document]), indent=2))


if __name__ == '__main__':
    main()
