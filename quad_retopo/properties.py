import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty

from .pipeline.params import RetopoParams

_D = RetopoParams()


class QR_Settings(bpy.types.PropertyGroup):
    target_faces: IntProperty(
        name="Target Faces", default=_D.target_faces, min=100, soft_max=200_000,
        description="Approximate face count of the result")
    guarantee: EnumProperty(
        name="Quad Guarantee",
        items=[
            ('AUTO', "Auto", "Solve at full density; fall back to quarter density + one "
                             "Catmull-Clark step if any non-quad remains"),
            ('SUBDIVIDE', "Always Subdivide", "Solve at quarter density + one Catmull-Clark "
                                              "step (smoother flow, always all quads)"),
        ],
        default=_D.guarantee)
    fill_holes: BoolProperty(
        name="Fill Holes", default=_D.fill_holes,
        description="Cap open boundaries before cleanup so the result is a closed surface")
    use_voxel_remesh: BoolProperty(
        name="Clean Input (Voxel)", default=_D.use_voxel_remesh,
        description="Voxel-remesh a copy of the input first: closes holes, fixes "
                    "non-manifold geometry and caps density for the solver")
    voxel_faces: IntProperty(
        name="Cleanup Density", default=_D.voxel_faces, min=10_000, soft_max=1_000_000,
        description="Approximate face count of the cleaned working copy")
    use_symmetry: BoolProperty(name="X Symmetry", default=_D.use_symmetry)
    smooth_normals: BoolProperty(name="Smooth Normals", default=_D.smooth_normals)
    seed: IntProperty(name="Seed", default=_D.seed, min=0)
    relax_iterations: IntProperty(name="Relax Iterations", default=_D.relax_iterations,
                                  min=0, max=50)
    relax_strength: FloatProperty(name="Relax Strength", default=_D.relax_strength,
                                  min=0.0, max=1.0)
    reproject_passes: IntProperty(name="Reproject Passes", default=_D.reproject_passes,
                                  min=1, max=10)
    hide_source: BoolProperty(name="Hide Source", default=True,
                              description="Hide the source object after retopology")

    def to_params(self):
        return RetopoParams(
            target_faces=self.target_faces, guarantee=self.guarantee,
            fill_holes=self.fill_holes, use_voxel_remesh=self.use_voxel_remesh, voxel_faces=self.voxel_faces,
            use_symmetry=self.use_symmetry, smooth_normals=self.smooth_normals,
            seed=self.seed, relax_iterations=self.relax_iterations,
            relax_strength=self.relax_strength, reproject_passes=self.reproject_passes,
        )
