"""Pure-function scientific primitives.

Modules here MUST NOT import ``prefect`` or depend on any orchestration
concept. Every primitive is callable identically from a notebook, a pytest
test, or a Prefect task. Disk I/O is allowed only where the primitive is
fundamentally about I/O (e.g. loading a FITS frame).
"""
