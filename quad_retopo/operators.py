import json

import bpy

from . import pipeline


class QR_OT_retopologize(bpy.types.Operator):
    """Create an all-quad retopology of the active mesh as a new object"""
    bl_idname = "object.quad_retopo"
    bl_label = "Quad Retopologize"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return ob is not None and ob.type == 'MESH' and context.mode == 'OBJECT'

    def execute(self, context):
        settings = context.scene.quad_retopo
        src = context.active_object
        wm = context.window_manager
        wm.progress_begin(0, 100)

        def progress(frac, msg):
            wm.progress_update(int(frac * 100))
            if context.workspace:
                context.workspace.status_text_set(f"Quad Retopo: {msg}…")

        try:
            obj, rep = pipeline.run(src, settings.to_params(), progress=progress)
        except Exception as ex:  # surface solver errors to the user
            self.report({'ERROR'}, f"Quad Retopo failed: {ex}")
            return {'CANCELLED'}
        finally:
            wm.progress_end()
            if context.workspace:
                context.workspace.status_text_set(None)

        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        if settings.hide_source:
            src.hide_set(True)

        obj["quad_retopo_report"] = json.dumps(rep)
        self.report(
            {'INFO'},
            f"{rep['faces']} quads, {rep['irregular_vert_ratio']:.1%} irregular verts, "
            f"mean dev {rep['dist_mean_pct']:.3f}% of size")
        return {'FINISHED'}
