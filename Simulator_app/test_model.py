import ast
import math
import tempfile
import unittest
from pathlib import Path
from model import Model, DEFAULT_SOURCE, read_dimensions


class Vector:
    def __init__(self, x, y, z=0):
        self.x, self.y, self.z = x, y, z
    def __add__(self, other):
        return Vector(self.x+other.x, self.y+other.y, self.z+other.z)
    def __sub__(self, other):
        return Vector(self.x-other.x, self.y-other.y, self.z-other.z)
    def __mul__(self, value):
        return Vector(self.x*value, self.y*value, self.z*value)


class ModelTests(unittest.TestCase):
    def test_original_path_and_rotation(self):
        m = Model()
        # Execute only the original's three pure path helpers with a small vector stub.
        tree = ast.parse(DEFAULT_SOURCE.read_text())
        selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('make_left_outer_tangent', 'build_chain_path', 'get_path_pos')]
        env = dict(math=math, V=Vector, R1=m.radii[0], R2=m.radii[1], R3=m.radii[2], THIRD_SPROCKET_SPACING=m.dim['THIRD_SPROCKET_SPACING'])
        exec(compile(ast.Module(body=selected, type_ignores=[]), '<original path functions>', 'exec'), env)
        original = env['build_chain_path'](m.x)
        self.assertAlmostEqual(original['length'], m.count*m.pitch, places=8)
        for i in range(-150, 151):
            distance = i*8.43
            p = env['get_path_pos'](distance, original['segments'], original['length'])
            q = m.position(distance)
            self.assertAlmostEqual(p.x, q[0], places=8)
            self.assertAlmostEqual(p.y, q[1], places=8)
            for j, arc in enumerate(original['arc_segments']):
                expected = arc['start_angle'] + arc['start']/arc['radius'] - distance/m.radii[j]
                self.assertAlmostEqual(m.angles(distance)[j], expected, places=10)

    def test_loop_and_boundary_continuity(self):
        m = Model()
        for segment in m.segments:
            a, b = m.position(segment['end']-1e-7), m.position(segment['end']+1e-7)
            self.assertLess(math.dist(a, b), 3e-7)
        self.assertLess(math.dist(m.position(0), m.position(m.length)), 1e-9)
        self.assertEqual(m.teeth, [28, 15, 21])

    def test_input_is_not_executed_and_bad_chain_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'sample.py'
            source.write_text("raise RuntimeError('must not run')\nT1 = 13\n")
            self.assertEqual(read_dimensions(source)['T1'], 13)
            self.assertEqual(Model(source).teeth[0], 13)
            source.write_text('NUM_LINKS = 4\n')
            with self.assertRaisesRegex(ValueError, 'too short'):
                Model(source)
            source.write_text('T1 = 0\n')
            with self.assertRaisesRegex(ValueError, 'Tooth counts'):
                Model(source)


if __name__ == '__main__':
    unittest.main()
