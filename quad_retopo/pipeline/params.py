from dataclasses import dataclass


@dataclass
class RetopoParams:
    # Desired number of faces in the final mesh.
    target_faces: int = 8000

    # How the all-quad constraint is enforced:
    #   'AUTO'      - solve at full target; if any non-quad survives, re-solve at
    #                 target/4 and apply one Catmull-Clark step (always all quads).
    #   'SUBDIVIDE' - always solve at target/4 + one Catmull-Clark step.
    guarantee: str = 'AUTO'

    # Preprocess: voxel remesh makes the input manifold/closed and caps density
    # so the field solver stays fast. Density is given as an approximate face count.
    fill_holes: bool = True
    use_voxel_remesh: bool = True
    voxel_faces: int = 250_000

    # Solver options
    use_symmetry: bool = False
    smooth_normals: bool = True
    seed: int = 0

    # Postprocess: tangential relaxation + reprojection onto the source surface.
    relax_iterations: int = 4
    relax_strength: float = 0.5
    reproject_passes: int = 2
