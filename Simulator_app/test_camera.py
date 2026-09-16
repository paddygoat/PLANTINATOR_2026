import math
import unittest
from types import SimpleNamespace
from camera import Camera
from model import Model
from schematic_app import Simulator


class Value:
    def __init__(self, value): self.value = value
    def get(self): return self.value


class Canvas:
    def __init__(self): self.items = []
    def delete(self, _): self.items.clear()
    def winfo_width(self): return 1100
    def winfo_height(self): return 500
    def __getattr__(self, name):
        if name.startswith('create_'):
            def record(*coords, **options):
                assert all(math.isfinite(v) for v in coords)
                self.items.append((name, coords, options))
            return record
        raise AttributeError(name)


class CameraTests(unittest.TestCase):
    def test_front_default_and_restore(self):
        camera = Camera()
        self.assertEqual(camera.project(12, 34, -50), (12, 34, -50))
        camera.preset('Isometric')
        camera.magnify(2)
        camera.pan_x = 100
        camera.reset()
        self.assertEqual(camera.project(12, 34, -50), (12, 34, -50))
        self.assertEqual((camera.zoom, camera.pan_x, camera.pan_y), (1, 0, 0))

    def test_rotation_preserves_distances(self):
        camera = Camera()
        for name in ('Front', 'Back', 'Top', 'Right', 'Isometric'):
            camera.preset(name)
            camera.roll = 27
            self.assertAlmostEqual(math.dist((0, 0, 0), camera.project(12, 34, -50)), math.sqrt(12**2+34**2+50**2))
        camera.preset('Right')
        self.assertAlmostEqual(camera.project(0, 0, -50)[0], -50)

    def test_all_views_render_and_keep_simulation_state(self):
        fake = SimpleNamespace(canvas=Canvas(), model=Model(), camera=Camera(),
                               offset=123.4, chain_zoom=Value(False), show_wheel=Value(True),
                               speed=Value(100), info=SimpleNamespace(configure=lambda **kw: None))
        for name in ('Front', 'Back', 'Top', 'Right', 'Isometric'):
            fake.camera.preset(name)
            Simulator.draw(fake)
            self.assertGreater(len(fake.canvas.items), 100)
            self.assertEqual(fake.offset, 123.4)
        fake.show_wheel.value = False
        fake.chain_zoom.value = True
        Simulator.draw(fake)
        self.assertGreater(len(fake.canvas.items), 100)


if __name__ == '__main__':
    unittest.main()
