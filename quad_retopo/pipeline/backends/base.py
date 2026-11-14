class Backend:
    """A field-aligned quad remesher.

    solve() replaces obj.data in place with a quad(-dominant) remesh of it,
    aiming for roughly *target_faces* faces.
    """

    id = "BASE"
    name = "Base"

    def solve(self, obj, target_faces, params):
        raise NotImplementedError
