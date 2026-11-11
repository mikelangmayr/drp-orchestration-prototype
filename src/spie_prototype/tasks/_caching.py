"""Shared caching configuration for task wrappers.

Centralizes the cache policy so every reproducible task uses the same
expiration and key function. The cache key for numpy inputs is a *content
fingerprint* (shape, dtype, statistical moments) rather than a full-buffer hash:
on the multi-megabyte arrays this pipeline handles, the moments are microseconds
to compute and robust to bit-level noise, where a full SHA-256 of the buffer is
tens of milliseconds per array per task. See
``docs/decisions/0005-numpy-cache-fingerprint.md`` and ``docs/architecture.md``
§"Caching and selective re-execution".
"""
from __future__ import annotations

import hashlib
from datetime import timedelta

import numpy as np
from prefect.context import TaskRunContext
from prefect.tasks import task_input_hash

# Master calibrations and trace solutions are reusable for days, not minutes.
CACHE_EXPIRATION = timedelta(days=7)

# Transient I/O failures (disk contention, NFS blips) are worth retrying;
# deterministic compute failures are not (see retries=0 on CPU tasks).
IO_RETRIES = 2
IO_RETRY_DELAY_SECONDS = 10


def numpy_aware_cache_key(context: TaskRunContext, parameters: dict) -> str:
    """Cache key that fingerprints numpy arrays instead of hashing their buffers.

    For each task argument: a numpy array contributes ``(shape, dtype, mean, std,
    min, max)``; any other value contributes its ``repr``. The task name is mixed
    in so distinct tasks never collide. This makes the key cheap on large arrays
    and stable against bit-level noise, at the cost of a vanishing collision risk
    (two distinct arrays sharing all six moments) — use ``BITEXACT_CACHE_KEY_FN``
    where exact reproduction is required.
    """
    digest = hashlib.sha256()
    digest.update(context.task.name.encode())
    for key, value in sorted(parameters.items()):
        digest.update(key.encode())
        if isinstance(value, np.ndarray):
            fingerprint = (
                value.shape,
                str(value.dtype),
                float(value.mean()),
                float(value.std()),
                float(value.min()),
                float(value.max()),
            )
            digest.update(repr(fingerprint).encode())
        else:
            digest.update(repr(value).encode())
    return digest.hexdigest()


# Default for reproducible tasks. Swap in BITEXACT where bit-exact reproduction
# matters (CI regression, the C-vs-Python equivalence check).
DEFAULT_CACHE_KEY_FN = numpy_aware_cache_key
BITEXACT_CACHE_KEY_FN = task_input_hash
