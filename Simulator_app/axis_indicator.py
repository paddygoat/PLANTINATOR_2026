"""Small, camera-synchronised 3D axis overlay for the Qt/Coin viewer."""

AXES = (
    ('X', (1, 0, 0), (1.0, 0.30, 0.27)),
    ('Y', (0, 1, 0), (0.30, 0.90, 0.44)),
    ('Z', (0, 0, 1), (0.35, 0.63, 1.0)),
)


class AxisIndicator:
    def __init__(self):
        # The caller creates this after QApplication and Coin are initialised.
        from pivy import coin
        self.coin = coin
        self.scene = coin.SoSeparator()
        self.camera = coin.SoOrthographicCamera()
        self.camera.height = 3.3
        self.camera.aspectRatio = 1
        self.camera.nearDistance = 1
        self.camera.farDistance = 9
        self.camera.focalDistance = 5
        self.scene.addChild(self.camera)
        depth = coin.SoDepthBuffer()
        depth.getField('test').setValue(True)
        depth.getField('write').setValue(True)
        depth.getField('function').setValue(coin.SoDepthBuffer.LESS)
        self.scene.addChild(depth)
        light = coin.SoDirectionalLight()
        light.direction.setValue(-0.4, -0.5, -1)
        self.scene.addChild(light)
        fill = coin.SoDirectionalLight()
        fill.direction.setValue(0.4, 0.5, 1)
        fill.intensity = 0.6
        self.scene.addChild(fill)
        self.labels = []
        for name, direction, color in AXES:
            arrow = coin.SoSeparator()
            arrow.setName('Indicator'+name)
            material = coin.SoMaterial()
            material.diffuseColor.setValue(*color)
            arrow.addChild(material)
            rotation = coin.SoRotation()
            rotation.rotation.setValue(coin.SbRotation(coin.SbVec3f(0, 1, 0), coin.SbVec3f(*direction)))
            arrow.addChild(rotation)
            shaft = coin.SoSeparator()
            move = coin.SoTranslation()
            move.translation.setValue(0, 0.42, 0)
            shaft.addChild(move)
            cylinder = coin.SoCylinder()
            cylinder.radius = 0.035
            cylinder.height = 0.84
            shaft.addChild(cylinder)
            arrow.addChild(shaft)
            tip = coin.SoSeparator()
            move = coin.SoTranslation()
            move.translation.setValue(0, 0.95, 0)
            tip.addChild(move)
            cone = coin.SoCone()
            cone.bottomRadius = 0.11
            cone.height = 0.24
            tip.addChild(cone)
            arrow.addChild(tip)
            self.scene.addChild(arrow)
            label = coin.SoSeparator()
            label.addChild(material)
            location = coin.SoTranslation()
            label.addChild(location)
            font = coin.SoFont()
            font.name = 'sans'
            font.size = 13
            label.addChild(font)
            text = coin.SoText2()
            text.string = name
            text.justification = coin.SoText2.CENTER
            label.addChild(text)
            self.scene.addChild(label)
            self.labels.append((direction, location))
        origin = coin.SoSeparator()
        material = coin.SoMaterial()
        material.diffuseColor.setValue(0.85, 0.88, 0.92)
        origin.addChild(material)
        sphere = coin.SoSphere()
        sphere.radius = 0.055
        origin.addChild(sphere)
        self.scene.addChild(origin)
        self.manager = coin.SoSceneManager()
        self.manager.setSceneGraph(self.scene)

    def set_cache_context(self, context_id):
        self.manager.getGLRenderAction().setCacheContext(context_id)

    def sync(self, main_camera):
        """Copy only orientation: model motion, pan and zoom do not move the key."""
        coin = self.coin
        rotation = main_camera.orientation.getValue()
        self.camera.orientation.setValue(rotation)
        self.camera.position.setValue(rotation.multVec(coin.SbVec3f(0, 0, 5)))
        inverse = rotation.inverse()
        for direction, location in self.labels:
            vector = coin.SbVec3f(*direction)
            view = inverse.multVec(vector)
            # When looking straight down an arrow, place its label beside the
            # visible cone end, rather than directly over the common origin.
            if view[0]**2 + view[1]**2 < 0.035:
                position = vector*1.2 + rotation.multVec(coin.SbVec3f(0.24, 0.20, 0))
            else:
                position = vector*1.28
            location.translation.setValue(position)

    @staticmethod
    def viewport(width, height, pixel_ratio=1):
        margin = max(1, round(12*pixel_ratio))
        size = max(1, min(round(145*pixel_ratio), width-2*margin, height-2*margin))
        return max(0,width-margin-size), max(0,height-margin-size), size, size

    def render(self, main_camera, width, height, pixel_ratio=1):
        self.sync(main_camera)
        region = self.coin.SbViewportRegion(width, height)
        x, y, w, h = self.viewport(width, height, pixel_ratio)
        region.setViewportPixels(x, y, w, h)
        self.manager.setViewportRegion(region)
        self.manager.getGLRenderAction().invalidateState()
        # Keep the main scene's colour image. Clear depth for this last pass so
        # the indicator cannot disappear behind the wheel or chain.
        self.manager.render(False, True)
