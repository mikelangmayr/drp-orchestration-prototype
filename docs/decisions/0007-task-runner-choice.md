# 0007 — Task-runner choice: threads by default, Dask for CPU-bound throughput

- Status: accepted
- Date: 2026-07-01

## Context

Claim 3 asks for measurable parallel speedup with no change to scientific logic.
The heavy step in the pipeline is the PypeIt slit trace — CPU-bound, minutes per
full frame. Prefect 3 ships only **thread-based** task runners
(`ConcurrentTaskRunner`, `ThreadPoolTaskRunner`); there is no built-in process
runner, and distributed execution comes from separate packages
(`prefect-dask`, `prefect-ray`).

## Findings (Phase 6)

- **Threads hurt the CPU-bound trace at every task size measured.** Three traces
  ran *slower* concurrently than serially on the thread runner — ~0.38x at ~9 s
  tasks and still ~0.54x at ~72 s tasks (216.6 s serial vs 403.4 s threads). It
  is ~3x *worse* than serial, not merely equal — the classic Python GIL-contention
  pathology (CPU-bound threads thrash acquiring/releasing the GIL).
- **Cause diagnosed — GIL, not BLAS.** Pinning BLAS/OpenMP to a single thread
  (`OMP_NUM_THREADS=1` etc.) left the ratio unchanged (0.34x → 0.33x) and did not
  change serial time, ruling out BLAS thread oversubscription and memory-bandwidth
  effects. PypeIt's `EdgeTraceSet` is Python-CPU-bound and holds the GIL. It is
  *not* thread-*unsafe* (concurrent runs returned correct slit counts), so no
  primitive swap (e.g. PyReduce) is needed — process isolation is the fix.
- **True multi-core needs a process/distributed runner.** `DaskTaskRunner`
  (worker processes) sidesteps the GIL entirely: the same three ~72 s traces
  finished in **83.2 s — a 2.60x speedup** on 3 worker processes (near the ideal
  3x, minus cluster startup + per-worker import overhead). Figure F11.
- **Dask has two operational prerequisites**, both easy but non-obvious:
  1. A **persistent Prefect server** — worker processes cannot share the driver's
     ephemeral in-process API, and each spinning its own ephemeral server
     collides on the same SQLite file (`database is locked`).
  2. The flow entry point must be under `if __name__ == "__main__":` — Dask's
     spawn workers re-import the driver module.

## Decision

- **Default to the thread runner** (`ConcurrentTaskRunner` /
  `ThreadPoolTaskRunner`) for the CAL and Quicklook flows. It is dependency-free
  and ideal for the I/O-bound stages (frame load, edge save, QA render) and for
  overlapping the many short tasks in a batch.
- **Use `DaskTaskRunner` (processes) for CPU-bound throughput** — reducing a
  batch of frames where the per-frame trace dominates. Pinned as the optional
  `[parallel]` extra so the base install stays lean.
- **The runner is a per-flow choice**, swapped with `flow.with_options(
  task_runner=...)` — the same scientific logic runs under any runner. This
  one-line swap *is* the ease-of-parallelism argument (claim 3); the benchmark
  (`scripts/benchmark_parallel.py`) exercises serial → threads → Dask unchanged.

## Consequences

- Real-time observing already runs a persistent Prefect server (for the
  dashboard), so Dask's server prerequisite is met for free in that mode.
- The paper gets an honest, nuanced parallelism story — "different stages benefit
  from different runners" — rather than a single misleading speedup bar: threads
  for I/O-bound fan-out, processes for CPU-bound reduction.
- `benchmark_parallel.py` exposes `--crop` so the per-task cost (and thus the
  regime where concurrency helps) is explicit rather than hidden.

## Alternatives rejected

- **Threads for everything.** Fails for CPU-bound trace (no gain / slowdown).
- **`prefect-ray`.** Comparable to Dask; not evaluated — one distributed runner
  is enough for the prototype. Revisit if Ray fits the deployment better.
- **Hand-rolled `multiprocessing`.** Would work but bypasses the orchestration
  layer, defeating the point that the *runner* provides parallelism.
