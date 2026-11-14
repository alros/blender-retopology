import bmesh
import bpy
from mathutils import Matrix

from .base import Backend

# Blender's QuadriFlow pre-check rejects edges whose endpoints are within 1e-4
# on every axis (absolute units). We normalise the mesh size and collapse
# anything shorter than this before solving.
_NORMALISED_DIAGONAL = 10.0
_MIN_EDGE = 3e-4


def _diagonal(me):
    import numpy as np
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    return float(np.linalg.norm(co.max(0) - co.min(0)))


def _collapse_short_edges(me, dist):
    bm = bmesh.new()
    bm.from_mesh(me)
    for _ in range(5):
        short = [e for e in bm.edges if e.calc_length() < dist]
        if not short:
            break
        bmesh.ops.collapse(bm, edges=short, uvs=False)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=dist)
    bm.to_mesh(me)
    bm.free()
    me.update()


class QuadriFlowBackend(Backend):
    id = "QUADRIFLOW"
    name = "QuadriFlow (built-in)"

    def solve(self, obj, target_faces, params):
        me = obj.data
        scale = _NORMALISED_DIAGONAL / max(_diagonal(me), 1e-9)
        me.transform(Matrix.Scale(scale, 4))
        _collapse_short_edges(me, _MIN_EDGE)

        override = dict(
            object=obj,
            active_object=obj,
            selected_objects=[obj],
            selected_editable_objects=[obj],
        )
        try:
            with bpy.context.temp_override(**override):
                res = bpy.ops.object.quadriflow_remesh(
                    use_mesh_symmetry=params.use_symmetry,
                    use_preserve_sharp=False,
                    use_preserve_boundary=False,
                    preserve_attributes=False,
                    smooth_normals=params.smooth_normals,
                    mode='FACES',
                    target_faces=int(target_faces),
                    seed=params.seed,
                )
        finally:
            obj.data.transform(Matrix.Scale(1.0 / scale, 4))
            obj.data.update()
        if 'FINISHED' not in res:
            raise RuntimeError(f"QuadriFlow failed: {res}")
        return obj
