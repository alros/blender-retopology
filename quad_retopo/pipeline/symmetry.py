"""Exact mirror symmetry across the source object's local X plane.

Field solvers (QuadriFlow included) do not produce symmetric topology reliably,
so symmetry is imposed afterwards:

    solve full mesh -> cut at plane, keep +X -> mirror + weld seam
    -> (Catmull-Clark turns the mixed seam polygons into quads)
    -> relax/reproject, symmetrising positions after every step.
"""
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

from . import meshutil


class MirrorPlane:
    def __init__(self, source):
        mw = source.matrix_world
        self.co = np.array(mw.translation, dtype=np.float64)
        n = mw.to_3x3() @ Vector((1.0, 0.0, 0.0))
        self.no = np.array(n.normalized(), dtype=np.float64)

    def signed_dist(self, co):
        return (co - self.co) @ self.no

    def reflect(self, co):
        return co - 2.0 * self.signed_dist(co)[..., None] * self.no


def cut_half(obj, plane, snap):
    """Keep the +X side. Vertices within *snap* of the plane are moved onto it
    first, so the cut mostly follows existing vertices instead of making slivers."""
    me = obj.data
    co = meshutil.get_co(me)
    d = plane.signed_dist(co)
    near = np.abs(d) < snap
    co[near] -= d[near, None] * plane.no
    meshutil.set_co(me, co)

    bm = bmesh.new()
    bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(
        bm, geom=geom, dist=1e-7,
        plane_co=Vector(plane.co), plane_no=Vector(plane.no),
        clear_inner=True, clear_outer=False,
    )
    bm.to_mesh(me)
    bm.free()
    me.update()


def mirror_weld(obj, plane, eps=1e-6):
    """Duplicate the half, reflect it, flip its faces and weld the seam."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    seam = [v for v in bm.verts if abs(plane.signed_dist(np.array(v.co))) < eps]
    for v in seam:  # make seam exactly planar so the weld is exact
        v.co -= Vector(plane.signed_dist(np.array(v.co)) * plane.no)
    dup = bmesh.ops.duplicate(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:])
    new_verts = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]
    new_faces = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]
    for v in new_verts:
        v.co = Vector(plane.reflect(np.array(v.co)))
    bmesh.ops.reverse_faces(bm, faces=new_faces)
    seam_all = [v for v in bm.verts if abs(plane.signed_dist(np.array(v.co))) < eps]
    bmesh.ops.remove_doubles(bm, verts=seam_all, dist=eps * 10)
    bm.to_mesh(me)
    bm.free()
    me.update()


class Symmetriser:
    """Pairs each vertex with its mirror twin and enforces symmetric positions."""

    def __init__(self, obj, plane):
        self.plane = plane
        co = meshutil.get_co(obj.data)
        kd = KDTree(len(co))
        for i, p in enumerate(co):
            kd.insert(p, i)
        kd.balance()
        refl = plane.reflect(co)
        self.pairs = np.array([kd.find(p)[1] for p in refl], dtype=np.int64)

    def apply(self, obj):
        me = obj.data
        co = meshutil.get_co(me)
        mirrored = self.plane.reflect(co[self.pairs])
        meshutil.set_co(me, 0.5 * (co + mirrored))  # self-paired verts land on the plane

    def error(self, obj):
        co = meshutil.get_co(obj.data)
        return float(np.linalg.norm(co - self.plane.reflect(co[self.pairs]), axis=1).max())
