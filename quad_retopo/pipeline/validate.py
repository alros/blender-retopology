"""Quality report for a retopologized mesh."""
import bmesh
import numpy as np
from mathutils.bvhtree import BVHTree

from . import meshutil


def report(obj, source, depsgraph, sample=20000):
    me = obj.data
    sizes = meshutil.face_sizes(me)

    bm = bmesh.new()
    bm.from_mesh(me)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    valence = np.array([len(v.link_edges) for v in bm.verts])
    bm.free()

    # Distance from result vertices to the source surface (subsampled).
    # The result is in world space; the BVH is in the source's local space.
    bvh = BVHTree.FromObject(source, depsgraph)
    mw_inv = source.matrix_world.inverted()
    co = meshutil.get_co(me)
    if len(co) > sample:
        co = co[np.random.default_rng(0).choice(len(co), sample, replace=False)]
    d = []
    for p in co:
        hit = bvh.find_nearest(mw_inv @ _vec(p))
        if hit[0] is not None:
            d.append(hit[3])
    d = np.array(d) if d else np.zeros(1)
    diag = float(np.linalg.norm(np.array(source.dimensions)))

    return {
        "faces": int(len(sizes)),
        "verts": int(len(me.vertices)),
        "non_quads": int((sizes != 4).sum()),
        "all_quads": bool((sizes == 4).all()),
        "non_manifold_edges": int(non_manifold),
        "irregular_vert_ratio": float((valence != 4).mean()),
        "valence_hist": {int(k): int(v) for k, v in zip(*np.unique(valence, return_counts=True))},
        "dist_mean_pct": float(d.mean() / diag * 100),
        "dist_max_pct": float(d.max() / diag * 100),
    }


def _vec(p):
    from mathutils import Vector
    return Vector((float(p[0]), float(p[1]), float(p[2])))
