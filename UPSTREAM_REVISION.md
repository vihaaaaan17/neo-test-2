# Upstream Revision

This file documents the pinned version of the Open Notebook implementation used as the Ground Engine runtime for NeosisLM. 

## Source Information
- **Repository URL:** https://github.com/lfnovo/open-notebook (inferred from references/open-notebook)
- **Git Reference:** `v1.14.0` (Git Tag)
- **Git SHA:** `30c7e2a63e43b7f270fc2c638f0b6246934a53f4`

## Docker Runtime
- **Docker Image Tag:** `lfnovo/open_notebook:1.14.0`
- **Docker Image Digest:** `lfnovo/open_notebook@sha256:e53f90d6153fcf4a64604d9a0c12cb0428a32cfb8dbcbb72e81ab12c013ee330`
- **Acquisition Date:** 2026-09-18

## Integration Notes
- Phase 1 integration uses HTTP API boundary (`:5055`) to the isolated Docker container.
- *Note:* The user spec originally stated the image tag was `v1.14.0`, but Docker Hub only publishes `1.14.0`. We have adopted `1.14.0` to match the actual published image for the `v1.14.0` git tag release.
