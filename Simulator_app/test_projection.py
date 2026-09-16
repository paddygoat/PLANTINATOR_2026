import unittest
from types import SimpleNamespace, MethodType
from unittest.mock import Mock, patch
from pivy import coin
import qt_app


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.patch=patch.object(qt_app,'coin',coin)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.view=SimpleNamespace(camera=coin.SoOrthographicCamera(),scene=coin.SoSeparator(),
                                  update=Mock(),projection_changed=Mock())
        self.view.camera.position.setValue(0,0,1500)
        self.view.camera.focalDistance=1500
        self.view.camera.height=760
        self.view.scene.addChild(self.view.camera)
        for name in ('is_perspective','view_height','set_view_height','set_perspective'):
            setattr(self.view,name,MethodType(getattr(qt_app.Viewer,name),self.view))

    def test_projection_round_trip_preserves_framing_and_pose(self):
        v=self.view
        v.camera.orientation.setValue(coin.SbRotation(coin.SbVec3f(0,1,0),.6))
        orientation=tuple(v.camera.orientation.getValue().getValue())
        position=tuple(v.camera.position.getValue())
        for enabled in (True,False,True,False):
            v.set_perspective(enabled)
            self.assertEqual(v.is_perspective(),enabled)
            self.assertAlmostEqual(v.view_height(),760,places=3)
            self.assertEqual(tuple(v.camera.position.getValue()),position)
            self.assertEqual(tuple(v.camera.orientation.getValue().getValue()),orientation)
            self.assertEqual(v.scene.getChild(0),v.camera)

    def test_near_objects_are_larger_only_in_perspective(self):
        v=self.view
        def projected_width(z):
            volume=v.camera.getViewVolume(1)
            a=volume.projectToScreen(coin.SbVec3f(-100,0,z))
            b=volume.projectToScreen(coin.SbVec3f(100,0,z))
            return b[0]-a[0]
        self.assertAlmostEqual(projected_width(0),projected_width(500),places=6)
        v.set_perspective(True)
        self.assertAlmostEqual(projected_width(500)/projected_width(0),1.5,places=5)

    def test_zoom_limits_and_closeup_height(self):
        v=self.view
        v.set_perspective(True)
        for requested,expected in ((145,145),(300,300),(.001,2),(100000,5000)):
            v.set_view_height(requested)
            self.assertAlmostEqual(v.view_height(),expected,places=2)


if __name__=='__main__':
    unittest.main()
