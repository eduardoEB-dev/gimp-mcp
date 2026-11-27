"""Transfer Blender mesh indices to the 3MF packager."""

import json


def write_indexed_mesh(path, objects):
    vertices = []
    triangles = []
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        offset = len(vertices)
        matrix = obj.matrix_world
        vertices.extend(list(matrix @ v.co) for v in mesh.vertices)
        triangles.extend([offset + i for i in t.vertices] for t in mesh.loop_triangles)
    with open(path, "w", encoding="utf-8") as stream:
        json.dump({"vertices": vertices, "triangles": triangles}, stream)
