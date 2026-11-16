# Project rules

## Releases

- A release tag `vX.Y.Z` must point at a commit where `version` in
  `quad_retopo/blender_manifest.toml` is exactly `X.Y.Z`. Bump and commit the
  manifest first, then tag that commit. The CI release job fails otherwise.
- Never reuse a version that already has a tag (check `git tag -l`), even a
  failed one; go to the next patch number.
- `.githooks/pre-push` enforces the tag/version match; keep
  `git config core.hooksPath .githooks` set.
