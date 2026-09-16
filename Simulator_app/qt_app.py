"""Qt5 + Coin/OpenGL viewer of meshes tessellated from the original CAD solids."""
import math
import time
from gl_runtime import configure_environment, ContextCheck, check_display
configure_environment()
from PySide2 import QtCore, QtWidgets, QtOpenGL

# Initialise Coin only after QApplication exists (its Qt sensor bridge needs it).
coin = None
from cad_geometry import build, surface_mesh
from model import DEFAULT_SOURCE
from axis_indicator import AxisIndicator


class Viewer(QtOpenGL.QGLWidget):
    render_failed = QtCore.Signal(str)
    projection_changed = QtCore.Signal(bool)

    def __init__(self, parent=None):
        global coin
        if coin is None:
            from pivy import coin as coin_module
            coin = coin_module
        fmt = QtOpenGL.QGLFormat()
        fmt.setVersion(2, 1)
        fmt.setProfile(QtOpenGL.QGLFormat.CompatibilityProfile)
        fmt.setSampleBuffers(False)
        fmt.setDepth(True)
        fmt.setDepthBufferSize(24)
        super().__init__(fmt, parent)
        self.context_check = ContextCheck()
        self.render_error = None
        self.rendered_frames = 0
        self.setMinimumSize(450, 350)
        self.scene = coin.SoSeparator()
        self.camera = coin.SoOrthographicCamera()
        self.scene.addChild(self.camera)
        depth = coin.SoDepthBuffer()
        depth.getField('test').setValue(True)
        depth.getField('write').setValue(True)
        depth.getField('function').setValue(coin.SoDepthBuffer.LESS)
        self.scene.addChild(depth)
        light = coin.SoDirectionalLight()
        light.direction.setValue(-0.4, -0.6, -1)
        self.scene.addChild(light)
        fill = coin.SoDirectionalLight()
        fill.direction.setValue(0.7, 0.2, 1)
        fill.intensity = 0.5
        self.scene.addChild(fill)
        hints = coin.SoShapeHints()
        hints.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE
        hints.shapeType = coin.SoShapeHints.SOLID
        hints.creaseAngle = 0.45
        self.scene.addChild(hints)
        self.manager = coin.SoSceneManager()
        self.manager.setSceneGraph(self.scene)
        self.manager.setBackgroundColor(coin.SbColor(0.06, 0.10, 0.14))
        self.axis_indicator = AxisIndicator()
        self.drag = None
        self.restore()

    def initializeGL(self):
        # Each viewer/context needs its own Coin display-list/cache namespace.
        context_id = coin.SoGLCacheContextElement.getUniqueCacheContext()
        self.manager.getGLRenderAction().setCacheContext(context_id)
        self.axis_indicator.set_cache_context(context_id)
        self.manager.setViewportRegion(coin.SbViewportRegion(max(1,self.width()), max(1,self.height())))

    def resizeGL(self, width, height):
        ratio = self.devicePixelRatioF()
        self.manager.setViewportRegion(coin.SbViewportRegion(max(1,int(width*ratio)), max(1,int(height*ratio))))

    def paintGL(self):
        if self.render_error:
            return
        self.makeCurrent()
        context = self.context()
        current = QtOpenGL.QGLContext.currentContext()
        problem = self.context_check.problem(bool(context and context.isValid() and current == context))
        if problem:
            self.render_error = problem
            self.render_failed.emit(problem)
            return
        # Tight clipping preserves precision between thin, closely spaced plates.
        self.update_clipping()
        self.manager.getGLRenderAction().invalidateState()
        self.manager.render(True, True)
        ratio = self.devicePixelRatioF()
        self.axis_indicator.render(self.camera, max(1, round(self.width()*ratio)),
                                   max(1, round(self.height()*ratio)), ratio)
        self.rendered_frames += 1

    def update_clipping(self):
        action = coin.SoGetBoundingBoxAction(coin.SbViewportRegion(max(1,self.width()), max(1,self.height())))
        action.apply(self.scene)
        bounds = action.getBoundingBox()
        if bounds.isEmpty():
            return
        lo, hi = bounds.getMin().getValue(), bounds.getMax().getValue()
        radius = math.sqrt(sum(max(abs(lo[i]-self.target[i]),abs(hi[i]-self.target[i]))**2 for i in range(3)))
        distance = self.camera.focalDistance.getValue()
        self.camera.nearDistance = max(0.1, distance-radius-50)
        self.camera.farDistance = max(self.camera.nearDistance.getValue()+1, distance+radius+50)

    def verify_context(self):
        # Some Qt plugins never call paintGL when context creation fails.
        if not self.rendered_frames and not self.render_error:
            self.paintGL()

    def is_perspective(self):
        return self.camera.isOfType(coin.SoPerspectiveCamera.getClassTypeId())

    def view_height(self):
        if self.is_perspective():
            return 2*self.camera.focalDistance.getValue()*math.tan(self.camera.heightAngle.getValue()/2)
        return self.camera.height.getValue()

    def set_view_height(self, height):
        height = max(2, min(5000, height))
        if self.is_perspective():
            distance = self.camera.focalDistance.getValue()
            self.camera.heightAngle = 2*math.atan(height/(2*distance))
        else:
            self.camera.height = height
        self.update()

    def set_perspective(self, enabled):
        enabled = bool(enabled)
        if self.is_perspective() == enabled:
            return
        height = self.view_height()
        previous = self.camera
        replacement = coin.SoPerspectiveCamera() if enabled else coin.SoOrthographicCamera()
        for field in ('position', 'orientation', 'focalDistance', 'nearDistance',
                      'farDistance', 'aspectRatio', 'viewportMapping'):
            replacement.getField(field).setValue(previous.getField(field).getValue())
        self.scene.replaceChild(previous, replacement)
        self.camera = replacement
        self.set_view_height(height)
        self.projection_changed.emit(enabled)

    def restore(self):
        self.set_perspective(False)
        self.target = (0, 0, 0)
        self.camera.position.setValue(0, 0, 1500)
        self.camera.orientation.setValue(coin.SbRotation())
        self.camera.focalDistance = 1500
        self.camera.height = 760
        self.camera.nearDistance = 500
        self.camera.farDistance = 2500
        self.update()

    def orient(self, rotation):
        target = coin.SbVec3f(*self.target)
        forward = rotation.multVec(coin.SbVec3f(0, 0, -1))
        self.camera.orientation.setValue(rotation)
        self.camera.position.setValue(target-forward*self.camera.focalDistance.getValue())
        self.update()

    def orbit(self, axis, angle):
        # Compose in camera-local coordinates, keeping the focal point fixed.
        current = self.camera.orientation.getValue()
        increment = coin.SbRotation(coin.SbVec3f(*axis), math.radians(angle))
        # SbRotation multiplication applies its left operand first.
        self.orient(increment*current)

    def pan(self, x, y):
        amount = self.view_height()
        shift = self.camera.orientation.getValue().multVec(coin.SbVec3f(x*amount,y*amount,0))
        self.target = tuple(a+b for a,b in zip(self.target,shift.getValue()))
        self.camera.position.setValue(self.camera.position.getValue()+shift)
        self.update()

    def zoom(self, factor):
        self.set_view_height(self.view_height()*factor)
        self.update()

    def preset(self, name):
        rotations = {'Front': ((1,0,0),0), 'Back': ((0,1,0),180),
                     'Top': ((1,0,0),90), 'Right': ((0,1,0),90)}
        if name == 'Isometric':
            q = coin.SbRotation(coin.SbVec3f(0,1,0),math.pi/4)*coin.SbRotation(coin.SbVec3f(1,0,0),math.radians(35.264))
        else:
            axis, angle = rotations[name]
            q = coin.SbRotation(coin.SbVec3f(*axis), math.radians(angle))
        self.orient(q)

    def mousePressEvent(self, event):
        self.drag = event.pos()

    def mouseReleaseEvent(self, event):
        self.drag = None

    def mouseMoveEvent(self, event):
        if self.drag is None:
            return
        delta = event.pos()-self.drag
        if event.modifiers() & QtCore.Qt.ShiftModifier or event.buttons() & QtCore.Qt.RightButton:
            self.pan(-delta.x()/max(1,self.height()),delta.y()/max(1,self.height()))
        else:
            self.orbit((0,1,0),-delta.x()*0.4)
            self.orbit((1,0,0),-delta.y()*0.4)
        self.drag = event.pos()

    def wheelEvent(self, event):
        self.zoom(0.85 if event.angleDelta().y()>0 else 1/0.85)


def mesh_node(shape):
    vertices, faces, normals = surface_mesh(shape)
    group = coin.SoSeparator()
    coordinates = coin.SoCoordinate3()
    coordinates.point.setValues(0, len(vertices), vertices)
    group.addChild(coordinates)
    normal_node = coin.SoNormal()
    normal_node.vector.setValues(0, len(normals), normals)
    group.addChild(normal_node)
    binding = coin.SoNormalBinding()
    binding.value = coin.SoNormalBinding.PER_VERTEX_INDEXED
    group.addChild(binding)
    triangles = coin.SoIndexedFaceSet()
    indices = [index for face in faces for index in (*face, -1)]
    triangles.coordIndex.setValues(0,len(indices),indices)
    triangles.normalIndex.setValues(0,len(indices),indices)
    group.addChild(triangles)
    return group


class Simulator(QtWidgets.QMainWindow):
    def __init__(self, source=DEFAULT_SOURCE):
        super().__init__()
        self.setWindowTitle('WEEDINATOR · detailed CAD viewer · Qt5 · v3.4')
        self.resize(1250, 850)
        self.viewer = Viewer()
        central = QtWidgets.QWidget()
        central_layout = QtWidgets.QVBoxLayout(central)
        self.render_notice = QtWidgets.QLabel()
        self.render_notice.setWordWrap(True)
        self.render_notice.setStyleSheet('background: #fff0cf; color: #382b0f; padding: 12px;')
        self.render_notice.hide()
        central_layout.addWidget(self.render_notice)
        central_layout.addWidget(self.viewer, 1)
        self.setCentralWidget(central)
        self.viewer.render_failed.connect(self.render_failed)
        self.running = False
        self.last = time.perf_counter()
        self.env, self.doc = build(source)
        self.transforms = []
        wheel_group = coin.SoSeparator()
        self.wheel_transform = coin.SoTransform()
        wheel_group.addChild(self.wheel_transform)
        self.wheel_switch = coin.SoSwitch()
        self.wheel_switch.whichChild = coin.SO_SWITCH_ALL
        self.wheel_switch.addChild(wheel_group)
        self.viewer.scene.addChild(self.wheel_switch)
        shared = {}
        for obj in self.doc.objects:
            if not hasattr(obj, 'Shape'):
                continue
            group = coin.SoSeparator()
            transform = coin.SoTransform()
            group.addChild(transform)
            material = coin.SoMaterial()
            material.diffuseColor.setValue(*obj.ViewObject.ShapeColor)
            material.ambientColor.setValue(0.25,0.25,0.25)
            material.specularColor.setValue(0.25,0.25,0.25)
            material.shininess = 0.3
            group.addChild(material)
            key = ('link',int(obj.Name.rsplit('_',1)[1])%2) if obj.Name.startswith('ChainLink_') else obj.Name
            if key not in shared:
                shared[key] = mesh_node(obj.Shape)
            group.addChild(shared[key])
            (wheel_group if obj.Name.startswith('Wheel') else self.viewer.scene).addChild(group)
            self.transforms.append((obj,transform))
        self.controls()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30)
        self.apply()

    def showEvent(self, event):
        super().showEvent(event)
        QtCore.QTimer.singleShot(500, self.viewer.verify_context)

    def render_failed(self, message):
        self.pause()
        self.render_notice.setText(
            '3D rendering stopped safely: '+message+'\n'
            'The geometry is loaded, but this graphics session cannot display it. '
            'Close the app and try: python3 app.py --software '
            '(uses Mesa software OpenGL). A working X11 or XWayland display is required.'
        )
        self.render_notice.show()

    def controls(self):
        dock = QtWidgets.QDockWidget('Simulation & 3D camera',self)
        dock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        self.play = QtWidgets.QPushButton('Play')
        self.play.clicked.connect(self.toggle)
        layout.addWidget(self.play)
        def row(actions):
            box = QtWidgets.QHBoxLayout()
            for text, callback in actions:
                button = QtWidgets.QPushButton(text)
                button.clicked.connect(lambda checked=False, callback=callback: callback())
                box.addWidget(button)
            layout.addLayout(box)
        row([('Step one pitch',self.step),('Reset motion',self.reset_motion)])
        self.speed = QtWidgets.QDoubleSpinBox()
        self.speed.setRange(-1000,1000)
        self.speed.setValue(100)
        self.speed.setSuffix(' mm/s')
        layout.addWidget(self.speed)
        layout.addWidget(QtWidgets.QLabel('Chain loop position'))
        self.scrubber = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.scrubber.setRange(0,1000)
        self.scrubber.sliderMoved.connect(self.scrub)
        layout.addWidget(self.scrubber)
        layout.addWidget(QtWidgets.QLabel('3D CAMERA'))
        self.projection_tabs = QtWidgets.QTabBar()
        self.projection_tabs.addTab('Orthographic')
        self.projection_tabs.addTab('Perspective')
        self.projection_tabs.setExpanding(True)
        self.projection_tabs.setTabToolTip(0, 'Parallel projection: the existing default view.')
        self.projection_tabs.setTabToolTip(1, 'Perspective projection: nearer parts appear larger.')
        self.projection_tabs.currentChanged.connect(lambda index: self.viewer.set_perspective(index == 1))
        self.viewer.projection_changed.connect(self.sync_projection_tab)
        layout.addWidget(self.projection_tabs)
        row([(name,lambda name=name:self.viewer.preset(name)) for name in ('Front','Top','Right')])
        row([(name,lambda name=name:self.viewer.preset(name)) for name in ('Back','Isometric')])
        for label,axis in [('Orbit horizontal',(0,1,0)),('Orbit vertical',(1,0,0)),('Roll',(0,0,1))]:
            row([(label+' −',lambda axis=axis:self.viewer.orbit(axis,-10)),
                 (label+' +',lambda axis=axis:self.viewer.orbit(axis,10))])
        row([('Pan ←',lambda:self.viewer.pan(-0.08,0)),('Pan →',lambda:self.viewer.pan(0.08,0))])
        row([('Pan ↑',lambda:self.viewer.pan(0,0.08)),('Pan ↓',lambda:self.viewer.pan(0,-0.08))])
        row([('Zoom +',lambda:self.viewer.zoom(0.8)),('Zoom −',lambda:self.viewer.zoom(1.25))])
        row([('Restore startup view',self.viewer.restore)])
        row([('Lug detail',self.lug_detail),('Chain close-up',self.chain_detail)])
        self.wheel_visible = QtWidgets.QCheckBox('Show wheel')
        self.wheel_visible.setChecked(True)
        self.wheel_visible.toggled.connect(self.show_wheel)
        layout.addWidget(self.wheel_visible)
        row([('Load dimensions…',self.load)])
        note = QtWidgets.QLabel('Drag: orbit\nShift-drag / right-drag: pan\nScroll: zoom\n\nActual CAD solids, meshed at 0.15 mm.\nLug holes run sideways through blades.\n\nKinematics only; no contact/load physics.')
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        dock.setWidget(scroll)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea,dock)

    def sync_projection_tab(self, perspective):
        blocked = self.projection_tabs.blockSignals(True)
        self.projection_tabs.setCurrentIndex(1 if perspective else 0)
        self.projection_tabs.blockSignals(blocked)

    def show_wheel(self, checked):
        self.wheel_switch.whichChild = coin.SO_SWITCH_ALL if checked else coin.SO_SWITCH_NONE
        self.viewer.update()

    def apply(self):
        self.env['apply_simulation_state']()
        for obj, node in self.transforms+[(self.env['ground_drive_wheel'],self.wheel_transform)]:
            p = obj.Placement
            node.translation.setValue(p.Base.x,p.Base.y,p.Base.z)
            node.rotation.setValue(coin.SbRotation(*p.Rotation.Q))
        self.scrubber.setValue(round(self.env['animation_offset']%self.env['total_chain_length']/self.env['total_chain_length']*1000))
        self.statusBar().showMessage('Chain travel {:.1f} mm · {}T / {}T / {}T · {} links'.format(self.env['animation_offset'],self.env['T1'],self.env['T2'],self.env['T3'],self.env['NUM_LINKS']))
        self.viewer.update()

    def toggle(self):
        self.running = not self.running
        self.last = time.perf_counter()
        self.play.setText('Pause' if self.running else 'Play')

    def pause(self):
        self.running = False
        self.play.setText('Play')

    def tick(self):
        now = time.perf_counter()
        if self.running:
            self.env['animation_offset'] += self.speed.value()*min(now-self.last,0.15)
            self.apply()
        self.last = now

    def step(self):
        self.pause()
        self.env['animation_offset'] += self.env['PITCH']
        self.apply()

    def reset_motion(self):
        self.pause()
        self.env['animation_offset'] = 0
        self.apply()

    def scrub(self,value):
        self.pause()
        self.env['animation_offset'] = value/1000*self.env['total_chain_length']
        self.apply()

    def lug_detail(self):
        self.pause()
        self.wheel_visible.setChecked(True)
        e = self.env
        angle = e['ground_drive_wheel'].Placement.Rotation
        local_angle = math.radians(e['LUG_START_ANGLE']+e['LUG_SKEW_ANGLE'])
        radius = e['FRONT_DISC_OD']/2-e['LUG_WELD_OVERLAP']+e['LUG_LENGTH']/2
        point = angle.multVec(e['V'](radius*math.cos(local_angle),radius*math.sin(local_angle),e['FRONT_DISC_THK']+e['LUG_WIDTH']/2))
        point.z += e['WHEEL_Z_OFFSET']
        self.viewer.target = (point.x,point.y,point.z)
        # View toward the blade's broad X-Z face, slightly oblique to show thickness.
        q = angle.multiply(e['App'].Rotation(e['V'](0,0,1),math.degrees(local_angle))).multiply(e['App'].Rotation(e['V'](1,0,0),70))
        self.viewer.set_view_height(145)
        self.viewer.orient(coin.SbRotation(*q.Q))

    def chain_detail(self):
        self.viewer.target = (self.env['upper_right_x']/2,-60,0)
        self.viewer.set_view_height(300)
        self.viewer.preset('Front')

    def load(self):
        path,_ = QtWidgets.QFileDialog.getOpenFileName(self,'Load numeric dimensions',str(DEFAULT_SOURCE),'Python macro (*.py)')
        if not path:
            return
        self.pause()
        try:
            replacement = Simulator(path)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self,'Cannot load dimensions',str(error))
            return
        self.replacement = replacement
        replacement.show()
        self.close()

    def closeEvent(self,event):
        self.timer.stop()
        super().closeEvent(event)


def launch(source=DEFAULT_SOURCE):
    check_display()
    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseDesktopOpenGL)
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = Simulator(source)
    window.show()
    return application.exec_()
