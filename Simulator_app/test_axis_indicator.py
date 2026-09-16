import math
import unittest
from unittest.mock import Mock
from axis_indicator import AXES, AxisIndicator
from pivy import coin


class AxisTests(unittest.TestCase):
    def setUp(self):
        self.indicator = AxisIndicator()
        self.camera = coin.SoOrthographicCamera()

    def test_default_directions(self):
        self.indicator.sync(self.camera)
        inverse = self.indicator.camera.orientation.getValue().inverse()
        for (_, direction, _), expected in zip(AXES, ((1,0,0),(0,1,0),(0,0,1))):
            self.assertEqual(tuple(inverse.multVec(coin.SbVec3f(*direction)).getValue()),expected)
        # Positive camera-space Z points toward the viewer in OpenGL.
        self.assertEqual(tuple(self.indicator.camera.position.getValue()),(0,0,5))

    def test_arbitrary_rotation_matches_camera_but_not_pan_or_zoom(self):
        for axis in ((1,0,0),(0,1,0),(0,0,1),(1,2,3)):
            for angle in (0,35,90,180,270):
                rotation=coin.SbRotation(coin.SbVec3f(*axis),math.radians(angle))
                self.camera.orientation.setValue(rotation)
                self.camera.position.setValue(200,-140,1700)
                self.camera.height=2400
                self.indicator.sync(self.camera)
                self.assertEqual(tuple(self.indicator.camera.orientation.getValue().getValue()),tuple(rotation.getValue()))
                position=self.indicator.camera.position.getValue()
                self.assertAlmostEqual(position.length(),5,places=5)
                self.assertAlmostEqual(self.indicator.camera.height.getValue(),3.3,places=5)

    def test_head_on_label_is_not_hidden_at_origin(self):
        self.indicator.sync(self.camera)
        z_label=self.indicator.labels[2][1].translation.getValue()
        self.assertGreater(abs(z_label[0])+abs(z_label[1]),0.3)

    def test_top_right_viewport_resizes_and_scales(self):
        self.assertEqual(self.indicator.viewport(1000,700),(843,543,145,145))
        self.assertEqual(self.indicator.viewport(2000,1400,2),(1686,1086,290,290))

    def test_overlay_preserves_main_colour_and_clears_depth(self):
        self.indicator.manager=Mock()
        self.indicator.render(self.camera,1000,700)
        self.indicator.manager.render.assert_called_once_with(False,True)


if __name__=='__main__':
    unittest.main()
