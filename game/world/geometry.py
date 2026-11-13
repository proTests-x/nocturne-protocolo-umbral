"""Small original, flat-shaded meshes without external model assets."""

import math
from panda3d.core import (
    Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
    GeomVertexWriter, Vec3,
)


def _rgba(color):
    return tuple(color) if len(color) == 4 else (*color, 1)


def _mesh(parent, name, vertices, normals, triangles, color):
    data = GeomVertexData(name, GeomVertexFormat.getV3n3c4(), Geom.UHStatic)
    data.setNumRows(len(vertices))
    positions = GeomVertexWriter(data, "vertex")
    normal_writer = GeomVertexWriter(data, "normal")
    colors = GeomVertexWriter(data, "color")
    rgba = _rgba(color)
    for vertex, normal in zip(vertices, normals):
        positions.addData3(*vertex)
        normal_writer.addData3(*normal)
        colors.addData4(*rgba)
    primitive = GeomTriangles(Geom.UHStatic)
    for triangle in triangles:
        primitive.addVertices(*triangle)
    primitive.closePrimitive()
    geom = Geom(data)
    geom.addPrimitive(primitive)
    node = GeomNode(name)
    node.addGeom(geom)
    return parent.attachNewNode(node)


def box(parent, name, pos, scale, color):
    """Centred cube with independent, flat-shaded face normals."""
    faces = [
        ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)]),
        ((0, 1, 0), [(1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)]),
        ((-1, 0, 0), [(-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)]),
        ((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
        ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
        ((0, 0, -1), [(-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1)]),
    ]
    vertices, normals, triangles = [], [], []
    for normal, face in faces:
        base = len(vertices)
        vertices.extend(tuple(v * .5 for v in point) for point in face)
        normals.extend([normal] * 4)
        triangles.extend([(base, base + 1, base + 2), (base, base + 2, base + 3)])
    result = _mesh(parent, name, vertices, normals, triangles, color)
    result.setPos(*pos)
    result.setScale(*scale)
    return result


def cylinder(parent, name, pos, radius, depth, color, sides=12):
    """Capped regular cylinder centred on pos and aligned with Z."""
    sides = max(3, int(sides))
    vertices, normals, triangles = [], [], []
    for side in range(sides):
        a, b = side * math.tau / sides, (side + 1) * math.tau / sides
        nx, ny = math.cos((a + b) * .5), math.sin((a + b) * .5)
        ax, ay = math.cos(a), math.sin(a)
        bx, by = math.cos(b), math.sin(b)
        index = len(vertices)
        vertices.extend([(ax, ay, -.5), (bx, by, -.5), (bx, by, .5), (ax, ay, .5)])
        normals.extend([(nx, ny, 0)] * 4)
        triangles.extend([(index, index + 1, index + 2), (index, index + 2, index + 3)])
        index = len(vertices)
        vertices.extend([(0, 0, .5), (ax, ay, .5), (bx, by, .5)])
        normals.extend([(0, 0, 1)] * 3)
        triangles.append((index, index + 1, index + 2))
        index = len(vertices)
        vertices.extend([(0, 0, -.5), (bx, by, -.5), (ax, ay, -.5)])
        normals.extend([(0, 0, -1)] * 3)
        triangles.append((index, index + 1, index + 2))
    result = _mesh(parent, name, vertices, normals, triangles, color)
    result.setPos(*pos)
    result.setScale(radius, radius, depth)
    return result


def beam(parent, start, end, width, color):
    """Rectangular beam joining two points, useful for tracers and braces."""
    start, end = Vec3(*start), Vec3(*end)
    delta = end - start
    length = delta.length()
    node = box(parent, "beam", (start + end) * .5, (width, max(length, .001), width), color)
    if length > .0001:
        node.lookAt(end)
    return node


def cone(parent, name, pos, radius, depth, color, sides=8):
    """An original pointed roof, centred vertically on pos."""
    vertices, normals, triangles = [], [], []
    for side in range(sides):
        a, b = side * math.tau / sides, (side + 1) * math.tau / sides
        points = [(math.cos(a) * radius, math.sin(a) * radius, -depth / 2),
                  (math.cos(b) * radius, math.sin(b) * radius, -depth / 2),
                  (0, 0, depth / 2)]
        normal = (Vec3(*points[1]) - Vec3(*points[0])).cross(
            Vec3(*points[2]) - Vec3(*points[0]))
        normal.normalize()
        index = len(vertices)
        vertices.extend(points)
        normals.extend([tuple(normal)] * 3)
        triangles.append((index, index + 1, index + 2))
    result = _mesh(parent, name, vertices, normals, triangles, color)
    result.setPos(*pos)
    return result
