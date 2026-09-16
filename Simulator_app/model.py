"""Dependency-free, continuous pitch-circle kinematics from the supplied macro."""
import ast
import math
from pathlib import Path

BUNDLED_SOURCE = Path(__file__).with_name('source_model.py')
DEFAULT_SOURCE = Path(__file__).resolve().parent.parent / 'lugged_wheel_with_sprockets_chain.py'


def read_dimensions(path):
    """Read numeric constants without importing or executing the selected macro."""
    values = {}
    def number(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return (-1 if isinstance(node.op, ast.USub) else 1) * number(node.operand)
        raise ValueError('not a numeric literal')
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node, ast.Assign):
            try:
                value = number(node.value)
            except ValueError:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    values[target.id] = value
    return values


class Model:
    def __init__(self, source=DEFAULT_SOURCE):
        self.dim = read_dimensions(BUNDLED_SOURCE)
        self.dim.update(read_dimensions(source))
        d = self.dim
        self.teeth = [d['T1'], d['T2'], d['T3']]
        if any(t < 3 or int(t) != t for t in self.teeth):
            raise ValueError('Tooth counts must be integers of at least 3.')
        self.pitch = d['PITCH']
        self.count = d['NUM_LINKS']
        if self.pitch <= 0 or self.count < 4 or int(self.count) != self.count or self.count % 2:
            raise ValueError('Pitch must be positive and link count must be an even integer ≥ 4.')
        self.count = int(self.count)
        if d['THIRD_SPROCKET_SPACING'] <= 0 or d['FRONT_DISC_OD'] <= 0 or d['LUG_COUNT'] < 1 or int(d['LUG_COUNT']) != d['LUG_COUNT']:
            raise ValueError('Wheel diameter, lug count and centre spacing must be positive.')
        self.radii = [self.pitch / (2 * math.sin(math.pi / t)) for t in self.teeth]
        if d['THIRD_SPROCKET_SPACING'] <= self.radii[0] + self.radii[2] + 4.6:
            raise ValueError('The fixed sprockets overlap. Increase third sprocket spacing.')
        target = self.count * self.pitch
        low = self.radii[0] + self.radii[1] + 4.6 + 1e-6
        if self.build(low)[0] > target:
            raise ValueError('Chain is too short for non-overlapping sprockets.')
        high = max(target, low * 2)
        while self.build(high)[0] < target:
            high *= 2
        for _ in range(80):
            mid = (low + high) / 2
            if self.build(mid)[0] < target:
                low = mid
            else:
                high = mid
        self.x = (low + high) / 2
        self.length, self.segments, self.centres = self.build(self.x)
        self.phases = [s['angle'] + s['start'] / s['radius'] for s in self.segments if s['kind'] == 'arc']

    def build(self, x):
        centres = [(0, 0), (x, 0), (0, -self.dim['THIRD_SPROCKET_SPACING'])]
        tangents = []
        for i in range(3):
            a, b = centres[i], centres[(i + 1) % 3]
            r, q = self.radii[i], self.radii[(i + 1) % 3]
            dx, dy = b[0] - a[0], b[1] - a[1]
            distance = math.hypot(dx, dy)
            if distance <= abs(q - r):
                raise ValueError('Sprocket centres are too close.')
            ux, uy = dx / distance, dy / distance
            parallel = (r - q) / distance
            perpendicular = math.sqrt(1 - parallel ** 2)
            nx, ny = parallel * ux - perpendicular * uy, parallel * uy + perpendicular * ux
            tangents.append(((a[0] + r * nx, a[1] + r * ny), (b[0] + q * nx, b[1] + q * ny), math.atan2(ny, nx), math.sqrt(distance ** 2 - (q-r) ** 2)))
        segments, length = [], 0.0
        for i in range(3):
            angle = tangents[(i-1) % 3][2]
            arc_length = self.radii[i] * ((angle - tangents[i][2]) % math.tau)
            segments.append(dict(kind='arc', start=length, end=length+arc_length, angle=angle, radius=self.radii[i], centre=centres[i]))
            length += arc_length
            a, b, _, span = tangents[i]
            segments.append(dict(kind='line', start=length, end=length+span, a=a, b=b))
            length += span
        return length, segments, centres

    def position(self, distance):
        distance %= self.length
        for s in self.segments:
            if distance < s['end']:
                local = distance - s['start']
                if s['kind'] == 'arc':
                    angle = s['angle'] - local / s['radius']
                    return (s['centre'][0] + s['radius'] * math.cos(angle), s['centre'][1] + s['radius'] * math.sin(angle))
                t = local / (s['end'] - s['start'])
                return tuple(a + t * (b-a) for a, b in zip(s['a'], s['b']))
        raise RuntimeError('Invalid chain path')

    def angles(self, offset):
        return [phase - offset/r for phase, r in zip(self.phases, self.radii)]
