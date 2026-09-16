"""Build the trusted bundled CAD source without requiring FreeCADGui or a document GUI."""
import ast
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from model import BUNDLED_SOURCE, DEFAULT_SOURCE, Model


def cad_modules():
    try:
        import FreeCAD
    except ImportError:
        candidates = [os.environ.get('FREECAD_LIB', ''), '/usr/lib/freecad/lib', '/usr/lib/freecad-python3/lib']
        for folder in candidates:
            if folder and Path(folder, 'FreeCAD.so').exists():
                sys.path.append(folder)
                break
        import FreeCAD
    import Part
    return FreeCAD, Part


class Object:
    def __init__(self, name, app):
        self.Name = name
        self.Label = name
        self.ViewObject = SimpleNamespace(ShapeColor=(0.6, 0.6, 0.6))
        self.Placement = app.Placement()
        self.children = []
    def addObject(self, obj):
        self.children.append(obj)


class Document:
    def __init__(self, app):
        self.app = app
        self.objects = []
    def addObject(self, kind, name):
        obj = Object(name, self.app)
        self.objects.append(obj)
        return obj


def build(source=DEFAULT_SOURCE):
    """Only bundled geometry code executes; user files contribute numeric dimensions."""
    app, part = cad_modules()
    model = Model(source)
    doc = Document(app)
    env = dict(App=app, Part=part, math=math, doc=doc)
    nodes = []
    for node in ast.parse(BUNDLED_SOURCE.read_text()).body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value.func
            if isinstance(call, ast.Attribute) and call.attr == 'recompute':
                break
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Try)):
            continue
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if 'doc' in names:
                continue
            if len(names) == 1 and names[0] in model.dim:
                node.value = ast.Constant(model.dim[names[0]])
        nodes.append(node)
    tree = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    exec(compile(tree, str(BUNDLED_SOURCE), 'exec'), env)
    env['apply_simulation_state']()
    return env, doc


def mesh(shape, tolerance=0.15):
    vertices, faces = shape.tessellate(tolerance)
    return [(v.x, v.y, v.z) for v in vertices], faces


def surface_mesh(shape, tolerance=0.15):
    """Mesh each CAD face separately, preserving analytic normals and hard edges.

    Shared vertices across a plate's front, rim, and back must not share normals.
    Face-local vertex indices also prevent the renderer from inferring smoothing
    across bore walls or across a large planar disc's triangulation.
    """
    vertices, triangles, normals = [], [], []
    for face in shape.Faces:
        local_vertices, local_triangles = face.tessellate(tolerance)
        offset = len(vertices)
        local_normals = []
        for vertex in local_vertices:
            u, v = face.Surface.parameter(vertex)
            normal = face.normalAt(u, v)
            normal.normalize()
            local_normals.append(normal)
            vertices.append((vertex.x, vertex.y, vertex.z))
            normals.append((normal.x, normal.y, normal.z))
        for a, b, c in local_triangles:
            cross = (local_vertices[b]-local_vertices[a]).cross(local_vertices[c]-local_vertices[a])
            if cross.Length < 1e-12:
                continue
            reference = local_normals[a]+local_normals[b]+local_normals[c]
            if cross.dot(reference) < 0:
                b, c = c, b
            triangles.append((offset+a, offset+b, offset+c))
    return vertices, triangles, normals
