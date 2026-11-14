"""Make a clean, closed, manifold, moderately dense working copy of the source."""
import math

import bmesh
import numpy as np

from . import meshutil


def voxel_size_for(area, faces):
    # A voxel remesh produces roughly one quad per voxel² of surface.
    return math.sqrt(area / max(faces, 1))


def make_working_copy(src, params, depsgraph, name):
    obj = meshutil.new_object_from_evaluated(src, name, depsgraph, world_space=True)
    info = {"input_faces": len(obj.data.polygons)}

    if params.fill_holes:
        info["holes_filled"] = fill_holes(obj)

    if params.use_voxel_remesh:
        area = meshutil.surface_area(obj.data)
        vs = voxel_size_for(area, params.voxel_faces)
        meshutil.apply_modifier(obj, 'REMESH', mode='VOXEL', voxel_size=vs, adaptivity=0.0)
        info["voxel_size"] = vs

    info["preprocessed_faces"] = len(obj.data.polygons)
    return obj, info


def fill_holes(obj):
    """Cap every boundary loop so the voxel step sees a closed volume.

    Without this an open surface voxelises into a paper-thin double shell.
    """
    me = obj.data
    loop_edges = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("edge_index", loop_edges)
    if not (np.bincount(loop_edges, minlength=len(me.edges)) == 1).any():
        return 0  # closed already: skip the (slow on dense meshes) bmesh pass

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary = [e for e in bm.edges if e.is_boundary]
    n = 0
    if boundary:
        n = len(bmesh.ops.holes_fill(bm, edges=boundary, sides=0)["faces"])
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return n
