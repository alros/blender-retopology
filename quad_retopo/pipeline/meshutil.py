"""Small helpers shared by the pipeline stages (no bpy.ops, only data API)."""
import bpy
import numpy as np


def link_like(obj, src):
    """Link *obj* into the same collections as *src* (or the scene collection)."""
    cols = list(src.users_collection) or [bpy.context.scene.collection]
    for c in cols:
        c.objects.link(obj)


def new_object_from_evaluated(src, name, depsgraph, world_space=True):
    """Copy the evaluated mesh of *src* (modifiers applied) into a new object."""
    ev = src.evaluated_get(depsgraph)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=False, depsgraph=depsgraph)
    me.name = name
    if world_space:
        me.transform(src.matrix_world)
    obj = bpy.data.objects.new(name, me)
    link_like(obj, src)
    return obj


def apply_modifier(obj, mod_type, **props):
    """Add a modifier, evaluate it, and bake the result into obj.data.

    Done via the depsgraph instead of bpy.ops.object.modifier_apply so it does
    not depend on UI context, selection or mode.
    """
    mod = obj.modifiers.new("_qr_tmp", mod_type)
    for k, v in props.items():
        setattr(mod, k, v)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    new_me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    obj.modifiers.remove(mod)
    old = obj.data
    new_me.name = old.name
    obj.data = new_me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return obj


def surface_area(me):
    a = np.empty(len(me.polygons), dtype=np.float64)
    me.polygons.foreach_get("area", a)
    return float(a.sum())


def get_co(me):
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def set_co(me, co):
    me.vertices.foreach_set("co", co.astype(np.float32).ravel())
    me.update()


def get_edges(me):
    e = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", e)
    return e.reshape(-1, 2)


def get_vertex_normals(me):
    n = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertex_normals.foreach_get("vector", n)
    return n.reshape(-1, 3)


def face_sizes(me):
    s = np.empty(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get("loop_total", s)
    return s
