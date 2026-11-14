import bpy

from . import operators, properties, ui

_classes = (
    properties.QR_Settings,
    operators.QR_OT_retopologize,
    ui.QR_PT_panel,
)


def register():
    for c in _classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.quad_retopo = bpy.props.PointerProperty(type=properties.QR_Settings)


def unregister():
    del bpy.types.Scene.quad_retopo
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)
