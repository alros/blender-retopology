"""Turn the solver output into a clean, all-quad mesh that sits on the source."""
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import meshutil


def join_triangles(obj):
    """Merge adjacent triangle pairs into quads where the shape allows it."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    tris = [f for f in bm.faces if len(f.verts) == 3]
    if tris:
        bmesh.ops.join_triangles(
            bm, faces=tris,
            angle_face_threshold=np.radians(60), angle_shape_threshold=np.radians(60),
        )
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def non_quad_count(obj):
    return int((meshutil.face_sizes(obj.data) != 4).sum())


def catmull_clark(obj):
    """One Catmull-Clark step: every n-gon becomes n quads -> 100% quads."""
    meshutil.apply_modifier(
        obj, 'SUBSURF', levels=1, render_levels=1,
        subdivision_type='CATMULL_CLARK', uv_smooth='NONE', boundary_smooth='ALL',
        use_limit_surface=False,
    )


class SourceSurface:
    """BVH of the source in its local space; built once per run."""

    def __init__(self, source, depsgraph):
        self.bvh = BVHTree.FromObject(source, depsgraph)
        self.mw = source.matrix_world.copy()
        self.mw_inv = self.mw.inverted()


def reproject(obj, surf, limit):
    """Snap vertices back onto the source surface.

    Casting along ±normal (distance-limited) avoids snapping onto the wrong
    limb, which nearest-point does between legs and fingers. Vertices whose
    rays miss fall back to the nearest surface point.
    """
    me = obj.data
    co = meshutil.get_co(me)
    nrm = meshutil.get_vertex_normals(me)
    out = co.copy()
    m_inv, m, bvh = surf.mw_inv, surf.mw, surf.bvh
    l3 = m_inv.to_3x3()
    for i in range(len(co)):
        p = m_inv @ Vector(co[i])
        d = (l3 @ Vector(nrm[i])).normalized()
        best = None
        for direction in (d, -d):
            hit, _, _, dist = bvh.ray_cast(p, direction, limit)
            if hit is not None and (best is None or dist < best[1]):
                best = (hit, dist)
        if best is None:
            hit = bvh.find_nearest(p)[0]
            if hit is None:
                continue
            best = (hit, 0.0)
        out[i] = m @ best[0]
    meshutil.set_co(me, out)


def relax(obj, iterations, strength):
    """Tangential Laplacian smoothing: evens out quad sizes without shrinking."""
    me = obj.data
    edges = meshutil.get_edges(me)
    n = len(me.vertices)
    deg = np.bincount(edges.ravel(), minlength=n).astype(np.float64)
    deg[deg == 0] = 1.0
    for _ in range(iterations):
        co = meshutil.get_co(me)
        nrm = meshutil.get_vertex_normals(me)
        acc = np.zeros_like(co)
        np.add.at(acc, edges[:, 0], co[edges[:, 1]])
        np.add.at(acc, edges[:, 1], co[edges[:, 0]])
        d = acc / deg[:, None] - co
        d -= (d * nrm).sum(1)[:, None] * nrm
        meshutil.set_co(me, co + strength * d)


def mean_edge_length(obj):
    co = meshutil.get_co(obj.data)
    e = meshutil.get_edges(obj.data)
    return float(np.linalg.norm(co[e[:, 0]] - co[e[:, 1]], axis=1).mean())


def finish(obj, source, params, depsgraph, symmetriser=None):
    """Relax + reproject a few times, then shade smooth.

    With a symmetriser, positions are re-symmetrised after every step so the
    result is exactly mirrored even if the source is slightly asymmetric.
    """
    surf = SourceSurface(source, depsgraph)
    sym = symmetriser.apply if symmetriser else (lambda o: None)
    for _ in range(max(params.reproject_passes, 1)):
        limit = 2.0 * mean_edge_length(obj)
        if params.relax_iterations > 0:
            relax(obj, params.relax_iterations, params.relax_strength)
            sym(obj)
        reproject(obj, surf, limit)
        sym(obj)
    obj.data.shade_smooth()
