# 0005 — Numpy content-fingerprint cache key

- Status: accepted
- Date: 2026-06-30

## Context

Selective re-execution (abstract claim 2) exists only because task outputs are
cached and keyed on their inputs. Prefect's default `task_input_hash` hashes the
full content of every argument. For the multi-megabyte numpy frames this pipeline
passes between tasks, that means a full SHA-256 of each buffer — tens of
milliseconds per array, per task, per run. Across a batch through a multi-task
DAG it adds up to seconds of pure hashing overhead per run.

## Decision

Reproducible tasks use `numpy_aware_cache_key` (in `tasks/_caching.py`) as their
`cache_key_fn`. For each argument it contributes:

- numpy array → `(shape, dtype, mean, std, min, max)`;
- anything else → its `repr`.

The task name is mixed in so distinct tasks never share a key. `task_input_hash`
remains available as `BITEXACT_CACHE_KEY_FN` for the cases that need full-content
comparison.

## Why a fingerprint, not a full hash

- **Cost.** The six moments are microseconds to compute regardless of array size;
  a full-buffer hash scales with the bytes. On 16 MB float64 frames the
  difference is microseconds vs tens of milliseconds, multiplied by every cached
  task in every run.
- **Stability.** The fingerprint is robust to bit-level noise that is not
  scientifically meaningful: a recomputed calibration identical to within float
  epsilon still hits the cache, where a buffer hash would miss.

## Tradeoffs and limits

- **Collision risk.** Two genuinely different arrays could share all six moments.
  For real reduction data this is astronomically unlikely, but it is non-zero —
  hence `BITEXACT_CACHE_KEY_FN` for regression tests in CI and the planned
  C-vs-Python equivalence check, where bit-exact reproduction is required.
- **Cross-environment float reproducibility.** `mean`/`std` can differ in their
  last digits across BLAS builds, so a cache populated on one machine may miss
  (never falsely hit) on another. This is safe — a miss just recomputes — and is
  acceptable for the in-session selective-re-execution story; if cross-machine
  cache sharing is ever needed, round the moments to a fixed precision.

## Alternatives rejected

- **Full `task_input_hash` everywhere.** Correct but slow on large arrays and
  fragile to non-meaningful bit differences. Kept only as the opt-in bit-exact
  policy.
- **Hashing a downsampled buffer.** More faithful than moments but still scales
  with size and complicates the key; the moments are simpler and sufficient.
