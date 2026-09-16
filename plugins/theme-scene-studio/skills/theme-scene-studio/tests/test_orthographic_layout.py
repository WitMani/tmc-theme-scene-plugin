import copy
import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from orthographic_layout import Camera, build, primitives, validate, validate_group


class OrthographicTests(unittest.TestCase):
    def test_camera_is_orthonormal_up_to_scale(self):
        c = Camera()
        checks = c.checks()
        self.assertAlmostEqual(checks['row_dot_product'], 0)
        for n in checks['row_norms']:
            self.assertAlmostEqual(n, c.scale)

    def test_45_pitch_is_not_45_screen_diagonals(self):
        c = Camera(origin=(0,0), scale=1)
        x, y, z = [c.project(p) for p in [(1,0,0),(0,1,0),(0,0,1)]]
        self.assertAlmostEqual(x[1]/x[0], 1/math.sqrt(2))
        self.assertAlmostEqual(y[1]/y[0], -1/math.sqrt(2))
        self.assertAlmostEqual(z[0], 0)
        self.assertLess(z[1], 0)

    def test_translation_preserves_lengths_and_parallelism(self):
        c = Camera()
        deltas = []
        for start in [(0,0,0), (200,-400,15), (-80,90,0)]:
            a = c.project(start)
            b = c.project((start[0]+3,start[1]+2,start[2]+1))
            deltas.append([b[i]-a[i] for i in range(2)])
        for delta in deltas[1:]:
            for a,b in zip(delta,deltas[0]):
                self.assertAlmostEqual(a,b)

    def test_ground_circle_becomes_ellipse(self):
        c = Camera(origin=(0,0), scale=1)
        pts = primitives(dict(kind='circle', center=[0,0,0], radius=3))[0][1]
        projected = [c.project(p) for p in pts]
        widths = [max(p[i] for p in projected)-min(p[i] for p in projected) for i in range(2)]
        self.assertAlmostEqual(widths[1]/widths[0], math.sin(math.pi/4))

    def test_world_road_width_varies_in_screen(self):
        c = Camera(origin=(0,0), scale=1)
        # Perpendicular world directions have different screen widths under foreshortening.
        widths = []
        for end in ([4,4,0],[4,-4,0]):
            poly = primitives(dict(kind='band', points=[[0,0,0],end], width=2))[0][1]
            p,q = c.project(poly[0]),c.project(poly[-1])
            widths.append(math.dist(p,q))
        self.assertNotAlmostEqual(*widths)

    def test_roundtrip_and_screen_tamper_rejection(self):
        d = build(dict(items=[dict(kind='circle', center=[0,0,0], radius=2)]))
        d = json.loads(json.dumps(d))
        self.assertEqual(validate(d)['status'],'passed')
        bad = copy.deepcopy(d)
        bad['geometry'][0]['screen'][0][0] += 3
        with self.assertRaises(ValueError):
            validate(bad)

    def test_shear_and_undeclared_angle_rejected(self):
        d = build(dict(items=[dict(kind='box',center=[0,0,0],size=[2,2,1])]))
        d['matrix'][1][0] += 1
        with self.assertRaises(ValueError):
            validate(d)
        with self.assertRaises(ValueError):
            Camera(elevation_deg=34)
        self.assertEqual(Camera(elevation_deg=34,override_reason='User requested 34 degree elevation').elevation_deg,34)

    def test_invalid_geometry_rejected(self):
        for item in [dict(kind='circle',center=[0,0,0],radius=-1),
                     dict(kind='band',points=[[0,0,0],[0,0,0]],width=1),
                     dict(kind='box',center=[0,0,0],size=[1,0,1]),
                     dict(kind='polygon',points=[[0,0,float('nan')]]*3)]:
            with self.assertRaises(ValueError):
                primitives(item)

    def test_cross_candidate_camera_mismatch_rejected(self):
        scene = dict(items=[dict(kind='circle',center=[0,0,0],radius=1)])
        a = build(scene)
        scene['camera'] = dict(scale=21)
        b = build(scene)
        with self.assertRaises(ValueError):
            validate_group([a,b])
        self.assertTrue(validate_group([a,a])['shared_camera'])


if __name__ == '__main__':
    unittest.main()
