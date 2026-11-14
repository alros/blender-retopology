import json

import bpy


class QR_PT_panel(bpy.types.Panel):
    bl_label = "Quad Retopo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Retopo"

    def draw(self, context):
        s = context.scene.quad_retopo
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(s, "target_faces")
        layout.prop(s, "guarantee")

        col = layout.column(heading="Input")
        col.prop(s, "fill_holes")
        col.prop(s, "use_voxel_remesh")
        sub = col.column()
        sub.active = s.use_voxel_remesh
        sub.prop(s, "voxel_faces")

        col = layout.column(heading="Solver")
        col.prop(s, "use_symmetry")
        col.prop(s, "smooth_normals")
        col.prop(s, "seed")

        col = layout.column(heading="Finish")
        col.prop(s, "relax_iterations")
        col.prop(s, "relax_strength")
        col.prop(s, "reproject_passes")
        col.prop(s, "hide_source")

        layout.operator("object.quad_retopo", icon='MOD_REMESH')

        ob = context.active_object
        if ob is not None and "quad_retopo_report" in ob:
            rep = json.loads(ob["quad_retopo_report"])
            box = layout.box()
            box.label(text="Last result", icon='INFO')
            box.label(text=f"Faces: {rep['faces']}  (all quads: {rep['all_quads']})")
            box.label(text=f"Irregular verts: {rep['irregular_vert_ratio']:.1%}")
            box.label(text=f"Deviation mean/max: {rep['dist_mean_pct']:.3f}% / "
                           f"{rep['dist_max_pct']:.2f}%")
