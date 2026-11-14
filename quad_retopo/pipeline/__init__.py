"""Retopology pipeline: preprocess -> solve -> enforce quads -> relax/reproject -> validate."""
import time

import bpy

from . import postprocess, preprocess, validate
from .backends import get_backend
from .params import RetopoParams

__all__ = ["RetopoParams", "run"]


def run(source, params=None, backend_id="QUADRIFLOW", progress=None, name=None):
    """Retopologize *source* into a new object. The source is never modified.

    Returns (new_object, report_dict).
    """
    params = params or RetopoParams()
    progress = progress or (lambda frac, msg: None)
    timings = {}
    t0 = time.perf_counter()

    def step(label, frac):
        nonlocal t0
        now = time.perf_counter()
        progress(frac, label)
        timings[label] = round(now - t0, 2)
        t0 = now

    depsgraph = bpy.context.evaluated_depsgraph_get()
    name = name or f"{source.name}_retopo"
    backend = get_backend(backend_id)

    progress(0.0, "preprocess")
    obj, info = preprocess.make_working_copy(source, params, depsgraph, name)
    step("preprocess", 0.2)
    try:
        return _solve_and_finish(obj, source, params, backend, info, step, timings)
    except Exception:
        me = obj.data
        bpy.data.objects.remove(obj)
        if me.users == 0:
            bpy.data.meshes.remove(me)
        raise


def _solve_and_finish(obj, source, params, backend, info, step, timings):
    # Keep the preprocessed mesh so a fallback re-solve does not redo it.
    base_mesh = obj.data.copy()

    def reset():
        old = obj.data
        obj.data = base_mesh.copy()
        bpy.data.meshes.remove(old)

    def solve(target):
        """Solve, then re-solve once with a corrected request if the solver
        missed the face count by more than 10% (QuadriFlow tends to undershoot)."""
        backend.solve(obj, target, params)
        got = len(obj.data.polygons)
        if got and abs(got / target - 1.0) > 0.10:
            reset()
            factor = min(max(target / got, 0.5), 2.0)
            backend.solve(obj, target * factor, params)
            info.setdefault("calibrated", []).append([round(target), got])
        postprocess.join_triangles(obj)

    subdivided = False
    if params.guarantee == 'SUBDIVIDE':
        solve(params.target_faces / 4)
        postprocess.catmull_clark(obj)
        subdivided = True
    else:
        solve(params.target_faces)
        if postprocess.non_quad_count(obj) > 0:
            # Fallback that always yields 100% quads at the requested density.
            info["fallback_non_quads"] = postprocess.non_quad_count(obj)
            reset()
            solve(params.target_faces / 4)
            postprocess.catmull_clark(obj)
            subdivided = True
    bpy.data.meshes.remove(base_mesh)
    info["subdivided"] = subdivided
    step("solve", 0.7)

    postprocess.finish(obj, source, params, bpy.context.evaluated_depsgraph_get())
    step("relax_reproject", 0.9)

    rep = validate.report(obj, source, bpy.context.evaluated_depsgraph_get())
    step("validate", 1.0)

    if not rep["all_quads"]:
        # Should be unreachable: Catmull-Clark output is quads by construction.
        raise RuntimeError(f"All-quad constraint violated: {rep['non_quads']} non-quad faces")

    rep.update(info)
    rep["timings_s"] = timings
    return obj, rep
