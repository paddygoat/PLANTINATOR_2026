import unittest
from cad_geometry import build, mesh


class CADTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env,cls.doc = build()
        cls.lug = next(o for o in cls.doc.objects if o.Name=='WheelLug_01').Shape

    def test_lug_is_valid_and_has_real_hole_and_chamfers(self):
        self.assertTrue(self.lug.isValid())
        vector = self.env['V']
        inside = lambda x,y,z: self.lug.isInside(vector(x,y,z),1e-6,True)
        self.assertTrue(inside(300,0,26))  # Blade material.
        self.assertFalse(inside(317,0,26))  # Centre of the 12 mm through-hole.
        self.assertTrue(inside(309,0,26))  # Material just beyond the hole radius.
        self.assertFalse(inside(334,0,7))  # Lower outer corner removed by chamfer.
        self.assertFalse(inside(334,0,45))  # Upper outer corner removed by chamfer.
        self.assertFalse(inside(246,0,45))  # Third chamfer removes inner upper corner.
        self.assertTrue(inside(246,0,34))  # Material below the third chamfer.
        self.assertTrue(inside(256,0,45))  # Material beside the third chamfer.
        self.assertTrue(inside(334,0,26))  # Material between chamfers.

    def test_mesh_contains_hole_surface_and_chamfer_vertices(self):
        vertices,faces = mesh(self.lug)
        self.assertGreater(len(faces),100)
        for expected in ((335,-3,16),(335,-3,36),(325,-3,6),(325,-3,46),(245,-3,36),(255,-3,46)):
            self.assertTrue(any(sum((a-b)**2 for a,b in zip(v,expected))<1e-8 for v in vertices))
        self.assertTrue(any(abs((x-317)**2+(z-26)**2-36)<1e-5 for x,y,z in vertices))

    def test_motion_preserves_wheel_shaft_lock(self):
        e=self.env
        for offset in (0,123.4,-58.3,736.6):
            e['animation_offset']=offset
            e['apply_simulation_state']()
            self.assertTrue(e['ground_drive_wheel'].Placement.Rotation.isSame(e['sprockets'][0].Placement.Rotation,1e-8))
            self.assertEqual(e['ground_drive_wheel'].Placement.Base.z,-50)


if __name__=='__main__':
    unittest.main()


class DiscRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cad_geometry import surface_mesh
        cls.env,doc=build()
        cls.doc=doc
        cls.shape=next(o.Shape for o in doc.objects if o.Name=='WheelFrontDisc')
        cls.vertices,cls.triangles,cls.normals=surface_mesh(cls.shape)

    def test_stepped_disc_is_valid_and_has_two_rearward_chamfers(self):
        self.assertTrue(self.shape.isValid())
        self.assertEqual(len(self.shape.Solids), 1)
        self.assertFalse(any(o.Name in ('WheelOuterStep', 'WheelInnerStep') for o in self.doc.objects))
        vector=self.env['V']
        # Three lands and the midpoint of each 45-degree transition.
        for radius, front in ((250,6),(150,-6),(60,-18),(194,0),(99,-12)):
            self.assertTrue(self.shape.isInside(vector(radius,0,front-0.1),1e-6,True))
            self.assertFalse(self.shape.isInside(vector(radius,0,front+0.1),1e-6,True))
            self.assertTrue(self.shape.isInside(vector(radius,0,front-5.9),1e-6,True))
            self.assertFalse(self.shape.isInside(vector(radius,0,front-6.1),1e-6,True))
        for radius,z in ((200,6),(188,-6),(105,-6),(93,-18)):
            self.assertTrue(any(abs((x*x+y*y)**0.5-radius)<1e-7 and abs(vz-z)<1e-7
                                for x,y,vz in self.vertices))
        hub=next(o.Shape for o in self.doc.objects if o.Name=='WheelCentreBoss')
        self.assertAlmostEqual(hub.BoundBox.ZMin,-18)
        self.assertAlmostEqual(hub.distToShape(self.shape)[0],0)

    def test_extended_rim_and_rear_closing_disc(self):
        shapes={o.Name:o.Shape for o in self.doc.objects if hasattr(o,'Shape')}
        rim=shapes['WheelRearRim']
        cap=shapes['WheelRearDisc']
        for shape in (rim,cap):
            self.assertTrue(shape.isValid())
            self.assertEqual(len(shape.Solids),1)
            self.assertAlmostEqual(shape.BoundBox.XLength,550)
        self.assertAlmostEqual(rim.BoundBox.ZMin,-74)
        self.assertAlmostEqual(rim.BoundBox.ZMax,0)
        self.assertAlmostEqual(cap.BoundBox.ZMin,-80)
        self.assertAlmostEqual(cap.BoundBox.ZMax,rim.BoundBox.ZMin)
        self.assertEqual(len(rim.fuse(cap).Solids),1)
        vector=self.env['V']
        self.assertTrue(cap.isInside(vector(100,0,-77),1e-6,True))
        self.assertFalse(cap.isInside(vector(0,0,-77),1e-6,True))
        self.assertAlmostEqual(cap.common(shapes['WheelShaft']).Volume,0,places=5)

    def test_rear_boss_seats_outside_closing_disc(self):
        import math
        shapes={o.Name:o.Shape for o in self.doc.objects if hasattr(o,'Shape')}
        boss=shapes['WheelRearBoss']
        cap=shapes['WheelRearDisc']
        self.assertTrue(boss.isValid())
        self.assertEqual(len(boss.Solids),1)
        self.assertAlmostEqual(boss.BoundBox.XLength,40)
        self.assertAlmostEqual(boss.BoundBox.ZLength,7)
        self.assertAlmostEqual(boss.BoundBox.ZMin,-87)
        self.assertAlmostEqual(boss.BoundBox.ZMax,cap.BoundBox.ZMin)
        self.assertAlmostEqual(boss.Volume,math.pi*(20**2-15**2)*7,places=5)
        self.assertEqual(len(boss.fuse(cap).Solids),1)
        self.assertAlmostEqual(boss.common(shapes['WheelShaft']).Volume,0,places=5)

    def test_plain_boss_shaft_and_locking_fasteners(self):
        import math
        shapes={o.Name:o.Shape for o in self.doc.objects if hasattr(o,'Shape')}
        boss,shaft,bolt,nut=[shapes[n] for n in
            ('WheelCentreBoss','WheelShaft','WheelLockBolt','WheelLockNut')]
        for shape in (boss,shaft,bolt,nut):
            self.assertTrue(shape.isValid())
            self.assertEqual(len(shape.Solids),1)
        radii=[f.Surface.Radius for f in boss.Faces if type(f.Surface).__name__=='Cylinder']
        self.assertIn(25.0,radii)  # Analytic OD; cut-surface bounds can overestimate.
        self.assertIn(15.0,radii)
        self.assertIn(6.0,radii)
        self.assertAlmostEqual(boss.BoundBox.ZLength,30)
        v=self.env['V']
        for x in (-20,20):
            self.assertFalse(boss.isInside(v(x,0,-3),1e-6,True))
            self.assertTrue(boss.isInside(v(x,0,5),1e-6,True))
        self.assertFalse(boss.isInside(v(0,0,5),1e-6,True))
        self.assertAlmostEqual(shaft.BoundBox.ZMax,boss.BoundBox.ZMax)
        self.assertAlmostEqual(shaft.BoundBox.ZMin,-942)
        self.assertAlmostEqual(shaft.BoundBox.ZLength,954)
        self.assertAlmostEqual(shaft.BoundBox.XLength,30)
        self.assertAlmostEqual(shaft.Volume,math.pi*15**2*954,places=5)
        self.assertAlmostEqual(boss.common(shaft).Volume,0,places=5)
        self.assertAlmostEqual(boss.common(bolt).Volume,0,places=5)
        self.assertGreater(shaft.common(bolt).Volume,0)  # Intentional: shaft undrilled.
        self.assertAlmostEqual(bolt.common(nut).Volume,0,places=5)

    def test_second_wheel_spacing_orientation_and_shared_shaft(self):
        shapes={o.Name:o.Shape for o in self.doc.objects if hasattr(o,'Shape')}
        originals={n:s for n,s in shapes.items() if n.startswith('Wheel')
                   and not n.startswith('WheelSecond') and n!='WheelShaft'}
        second={n:s for n,s in shapes.items() if n.startswith('WheelSecond')}
        self.assertEqual(len(originals),len(second))
        self.assertEqual(sum(n.startswith('WheelSecondLug_') for n in second),12)
        for name,original in originals.items():
            copied=second['WheelSecond'+name[5:]]
            self.assertTrue(copied.isValid())
            self.assertAlmostEqual(copied.Volume,original.Volume,places=5)
            self.assertAlmostEqual(copied.Solids[0].CenterOfMass.x,-original.Solids[0].CenterOfMass.x,places=6)
            self.assertAlmostEqual(copied.Solids[0].CenterOfMass.y,original.Solids[0].CenterOfMass.y,places=6)
            self.assertAlmostEqual(copied.Solids[0].CenterOfMass.z,-930-original.Solids[0].CenterOfMass.z,places=6)
        def centre(prefix):
            rim=shapes[prefix+'RearRim'].BoundBox
            disc=shapes[prefix+'RearDisc'].BoundBox
            return (min(rim.ZMin,disc.ZMin)+max(rim.ZMax,disc.ZMax))/2
        self.assertAlmostEqual(centre('Wheel')-centre('WheelSecond'),850)
        shaft=shapes['WheelShaft']
        self.assertNotIn('WheelSecondShaft',shapes)
        self.assertAlmostEqual(shaft.BoundBox.ZMin,shapes['WheelSecondCentreBoss'].BoundBox.ZMin)
        self.assertAlmostEqual(shaft.BoundBox.ZMax,shapes['WheelCentreBoss'].BoundBox.ZMax)

    def test_flat_and_chamfer_normals(self):
        import math
        counts={}
        for triangle in self.triangles:
            points=[self.vertices[i] for i in triangle]
            if max(p[2] for p in points)-min(p[2] for p in points)<1e-8:
                radius=sum(math.hypot(p[0],p[1]) for p in points)/3
                top=6 if radius>200 else (-6 if radius>105 else -18)
                z=points[0][2]
                self.assertTrue(abs(z-top)<1e-8 or abs(z-(top-6))<1e-8)
                sign=1 if abs(z-top)<1e-8 else -1
                counts[(top,sign)]=counts.get((top,sign),0)+1
                for i in triangle:
                    for actual,target in zip(self.normals[i],(0,0,sign)):
                        self.assertAlmostEqual(actual,target,places=8)
        self.assertEqual(len(counts),6)  # Three front and three rear lands.
        cones=[f for f in self.shape.Faces if type(f.Surface).__name__=='Cone']
        self.assertEqual(len(cones),4)  # Two front ramps and matching rear ramps.
        for face in cones:
            u0,u1,v0,v1=face.ParameterRange
            normal=face.normalAt((u0+u1)/2,(v0+v1)/2)
            self.assertAlmostEqual(abs(normal.z),math.sqrt(0.5),places=7)

    def test_mesh_volume_and_bounds_preserve_the_disc(self):
        import math
        signed_volume=0
        for a,b,c in self.triangles:
            x,y,z=self.vertices[a],self.vertices[b],self.vertices[c]
            cross=(y[1]*z[2]-y[2]*z[1],y[2]*z[0]-y[0]*z[2],y[0]*z[1]-y[1]*z[0])
            signed_volume+=sum(p*q for p,q in zip(x,cross))/6
        self.assertAlmostEqual(signed_volume/self.shape.Volume,1,delta=.001)
        for x,y,z in self.vertices:
            self.assertGreaterEqual(math.hypot(x,y),15.0-1e-7)
            self.assertLessEqual(math.hypot(x,y),295+1e-7)
            self.assertGreaterEqual(z,-24-1e-7)
            self.assertLessEqual(z,6+1e-7)
