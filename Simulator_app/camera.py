"""Orthographic camera for the standalone 3D schematic (angles in degrees)."""
import math


class Camera:
    def __init__(self):
        self.reset()

    def reset(self):
        self.yaw = self.pitch = self.roll = 0.0
        self.zoom = 1.0
        self.pan_x = self.pan_y = 0.0

    def preset(self, name):
        self.yaw, self.pitch, self.roll = {
            'Front': (0, 0, 0), 'Back': (180, 0, 0),
            'Top': (0, 90, 0), 'Right': (90, 0, 0),
            'Isometric': (45, 35.264, 0),
        }[name]

    def project(self, x, y, z):
        yaw, pitch, roll = map(math.radians, (self.yaw, self.pitch, self.roll))
        x, z = math.cos(yaw)*x + math.sin(yaw)*z, -math.sin(yaw)*x + math.cos(yaw)*z
        y, z = math.cos(pitch)*y - math.sin(pitch)*z, math.sin(pitch)*y + math.cos(pitch)*z
        return math.cos(roll)*x-math.sin(roll)*y, math.sin(roll)*x+math.cos(roll)*y, z

    def magnify(self, factor):
        self.zoom = max(0.15, min(8.0, self.zoom*factor))
