"""Headless regression tests.

    blender -b path/to/file.blend --python tests/run_tests.py -- [object_name ...]

Without object names, a generated test corpus is used. Exits non-zero on failure.
"""
import json
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from quad_retopo import pipeline  # noqa: E402
from quad_retopo.pipeline import RetopoParams  # noqa: E402


def _corpus():
    """Shapes that stress the solver: genus>0, thin parts, non-manifold input."""
    objs = []

    def add(name, build):
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        build(bm)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        objs.append(ob)

    add("sphere", lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1))
    add("torus_like", lambda bm: _torus(bm))
    add("open_cube", lambda bm: _open_cube(bm))  # has a hole -> must be cleaned
    return objs


def _torus(bm):
    import math
    R, r, U, V = 1.0, 0.3, 48, 16
    verts = [[bm.verts.new(((R + r * math.cos(v / V * 2 * math.pi)) * math.cos(u / U * 2 * math.pi),
                            (R + r * math.cos(v / V * 2 * math.pi)) * math.sin(u / U * 2 * math.pi),
                            r * math.sin(v / V * 2 * math.pi)))
              for v in range(V)] for u in range(U)]
    for u in range(U):
        for v in range(V):
            bm.faces.new((verts[u][v], verts[(u + 1) % U][v],
                          verts[(u + 1) % U][(v + 1) % V], verts[u][(v + 1) % V]))


def _open_cube(bm):
    bmesh.ops.create_cube(bm, size=2)
    bm.faces.ensure_lookup_table()
    bm.faces.remove(bm.faces[0])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    objs = [bpy.data.objects[n] for n in argv] or _corpus()
    failures = 0
    for ob in objs:
        for guarantee in ("AUTO", "SUBDIVIDE"):
            params = RetopoParams(target_faces=2000, guarantee=guarantee, voxel_faces=60_000)
            try:
                res, rep = pipeline.run(ob, params)
                ok = rep["all_quads"] and rep["non_manifold_edges"] == 0
                ok &= 0.6 < rep["faces"] / params.target_faces < 1.6
            except Exception as ex:  # noqa: BLE001
                ok, rep = False, {"error": str(ex)}
            failures += not ok
            print(("PASS" if ok else "FAIL"), ob.name, guarantee, json.dumps(rep))
    print(f"{failures} failure(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
