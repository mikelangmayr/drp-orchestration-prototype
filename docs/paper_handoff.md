# LRIS DRP Prototype — Capabilities & Results (SPIE paper handoff)

A self-contained brief for the paper draft: what the prototype does, the concrete
results, the figures (with suggested captions), the stack, and the honest caveats.
Everything here is implemented and verified in the `spie-prototype` repository
unless explicitly marked *parked*.

---

## 1. One-paragraph summary

The prototype is a working slice of a data reduction pipeline for the LRIS
spectrograph at W. M. Keck Observatory, built to show that modern workflow
orchestration (Prefect) can replace the script-driven design of most existing
DRPs. Scientific primitives are sourced from established libraries (PypeIt for
slit tracing, ccdproc for master-bias combination) and wrapped behind a uniform
task interface; Prefect composes them into a directed acyclic graph (DAG) with
caching, retries, parallelism, and a live dashboard. It is demonstrated on LRIS-1
data plus synthetic LRIS-2 frames (LRIS-2 has no on-sky data yet; the DRP is
*built for* LRIS-2, with LRIS-1 as the proxy via PypeIt's `keck_lris_*`
spectrographs).

> Naming note for the paper: the *pipeline* is "the LRIS DRP" (it processes real
> LRIS-1 data + synthetic LRIS-2 stand-in frames). The *target instrument* is
> LRIS-2, which does not exist yet. Keep that distinction.

---

## 2. The four abstract claims — how each is demonstrated

| # | Claim | How it is demonstrated in code | Figure(s) | Headline number |
|---|-------|-------------------------------|-----------|-----------------|
| 1 | DAG of observable tasks | Every reduction step is a Prefect `@task` with logged parameters + summary stats; the run graph, states, and logs are live on the dashboard | F4 (dashboard), F7 (DAG diagram) | Full DAG of ~14 task nodes per 2-frame run, all state-inspectable |
| 2 | Selective re-execution | Content-fingerprint cache keys; changing one step's parameter re-runs only it + its downstream, upstream served from cache | F8 (dashboard), F9 (timing) | Unchanged re-run **6.7 s vs 372 s cold ≈ 55×**; cache-hit table proves only Trace + downstream recompute |
| 3 | Parallel execution, no change to science | Same flow, swap the task runner (`with_options(task_runner=...)`); serial → threads → Dask processes | F11 (timing) | **Dask processes 2.60×** on 3 workers (83.2 s vs 216.6 s serial) |
| 4 | Dual-layer primitives (pure-Python + optional compiled C) | **PARKED** per project scope — not implemented | — | — |

Plus two framing commitments, both supported:

- **Astropy-ecosystem compatibility** — primitives take/return numpy + Astropy
  types; the master-bias primitive is `ccdproc` (an Astropy-coordinated package).
- **Polyglot primitive composition** (the "why not just use PypeIt?" answer) —
  one DAG composes **PypeIt (trace) + ccdproc (bias) + custom (subtract/dark)**,
  the orchestration agnostic to which library each primitive comes from.
- **Resilience** (beyond the four claims but demonstrated) — a corrupt frame in a
  batch fails in isolation with full context; the rest complete. Figure F10.

---

## 3. Architecture (for §4 of the paper)

Three strictly separated layers (a one-directional import rule, enforced by a
test that fails if `core/` ever imports Prefect):

- **`core/`** — pure-function scientific primitives. No orchestration awareness.
  Numpy/Astropy in, numpy/Astropy out. Callable from a notebook, a test, or a task.
- **`tasks/`** — thin Prefect `@task` wrappers (logging, caching, retries, name).
  No logic. If a wrapper exceeds ~20 lines the logic belongs in `core/`.
- **`flows/`** — the DAG. Wiring only, no reduction logic. "Tasks calling tasks"
  is forbidden so every step is visible on the dashboard.

**Per-instrument flow triad** (a load-bearing design decision): a single DRP
cannot span instruments as different as LRIS and DEIMOS (different raw formats,
geometry, calibration sets), so flows are organized **per instrument × {CAL,
Quicklook, Science}**:

- **CAL DAG** — builds + caches master calibrations (the parallel calibration
  arms: master bias ∥ master dark). Real-time mode pre-processes cals as they
  arrive; reprocessing runs on demand.
- **Quicklook DAG** — fast, fixed-parameter, real-time: load → subtract bias →
  subtract dark → trace → save + QA. Consumes CAL masters as cache hits.
- **Science DAG** — full quality (optimal extraction, sky, flux). Placeholder;
  the primitives are pending.

`CAL → {Quicklook, Science}` is the cross-DAG caching edge: masters built once,
served from cache to both consumers. Instruments share `core/`/`tasks/`; only the
orchestration is split. Within an instrument, channel (Red/Blue) is a *parameter*,
not a separate flow.

The paper's Flow A / B / C are *demonstrations run against these DAGs*, not flows
themselves: A = a happy-path Quicklook run, B = selective re-execution, C =
graceful failure.

---

## 4. Figure inventory (files in `figures/`, with suggested captions)

Attach these images to the paper chat. Dashboard shots are currently full-page
screenshots and may want tighter crops for print.

- **F4 — `flow_a_dashboard.png`** (claim 1). The Quicklook DAG live on the Prefect
  dashboard: the `LRIS CAL` subflow feeding the per-frame chain (Discover → Load →
  Subtract Bias → Subtract Dark → Trace Slits (PypeIt) → Save Edges + Trace QA)
  across two frames, every step an observable node with state and logs.
  *Caption:* "The reduction as a DAG of observable tasks. Each node is a cached,
  retryable task with logged parameters; state, timing, and logs are live in the
  dashboard, replacing ad-hoc log inspection."

- **F7 — `flow_a_dag.png`** (+ editable `flow_a_dag.mmd`) (claim 1). A clean
  schematic of the same DAG: two parallel calibration arms joining the per-frame
  chain, which fans out concurrently across frames.
  *Caption:* "Flow A DAG. The master-bias and master-dark calibration arms run in
  parallel and join each frame's reduction chain; frames fan out concurrently."

- **F8 — `flow_b_dashboard.png`** (claim 2). A re-run after changing the trace
  `fit_order` (5→7): the timeline shows upstream tasks served instantly from cache
  (`Cached` in the logs) while only the Trace tasks recompute.
  *Caption:* "Selective re-execution. Changing one parameter re-runs only that
  step and its dependents; upstream results are served from cache."

- **F9 — `selective_rerun_timing.png`** (claim 2). Bar chart: cold full run
  (372 s) vs unchanged re-run (6.7 s, all cached, ~55×) vs a parameter change
  (461 s — the changed parameter feeds the dominant Trace step, so it correctly
  recomputes). *Caption:* "Caching eliminates recomputation on re-run (~55×); a
  parameter change recomputes exactly its subgraph. The time win grows as steps
  are added downstream of the expensive step."

- **F10 — `flow_c_dashboard.png`** (resilience). A batch of 3 frames (2 good + 1
  deliberately corrupt) on the dashboard: the corrupt frame's Load task is red
  (Failed, with the `OSError` traceback in its logs) while the rest are green and
  the flow completes. *Caption:* "Graceful failure. A corrupt frame fails in
  isolation with full context; the rest of the batch completes. The script-driven
  counterfactual is a halted or silently-corrupted batch."

- **F11 — `serial_vs_parallel_timing.png`** (claim 3). Serial (216.6 s) vs
  thread-concurrent (403.4 s, 0.54×) vs Dask processes (83.2 s, 2.60×) for the
  same 3 trace tasks, changing only the task runner. *Caption:* "Parallel
  execution by swapping the task runner, with no change to scientific logic.
  Threads are GIL-bound for the CPU-bound trace; process (Dask) workers give a
  2.60× speedup on three cores."

Per-frame data products the pipeline also writes (available to screenshot for a
"real output" figure): `slit_edges.npz` and a `trace_qa.png` showing the 72
traced slit-edge pairs overlaid on the flat.

---

## 5. Concrete results & numbers (all measured)

- **Slit tracing (PypeIt):** both synthetic LRIS-2 flats (4080×4080) → **72 slits
  each** (matching the mask design "slits-1-72"), median slit width ~52 px, edges
  spanning the full detector, slit centers monotonic across the focal plane.
- **Caching / selective re-execution:** cold 2-frame reduction **372 s**;
  unchanged re-run **6.7 s** (~**55×**, everything cached); parameter-change re-run
  **461 s** with masters + load + bias + dark cached and only Trace + Save/QA
  recomputed (verified by per-task cache-hit accounting).
- **Parallelism (N=3 traces, ~72 s each, 3 workers):** serial **216.6 s**;
  threads **403.4 s (0.54×, slower)**; Dask processes **83.2 s (2.60×)**.
- **Why threads lose — diagnosed:** pinning BLAS/OpenMP to 1 thread left the ratio
  unchanged (0.34× → 0.33×) and serial time identical → **not** BLAS
  oversubscription; PypeIt's `EdgeTraceSet` is Python-CPU-bound and holds the GIL
  (classic GIL-contention, ~3× worse than serial). It is *not* thread-*unsafe*
  (correct slit counts either way), so no primitive swap is needed — process
  isolation (Dask) is the fix.
- **Polyglot primitive (ccdproc):** median-combined **7 real LRIS-1 bias frames**
  into a master (2048×2148, median ≈ **1601 ADU**), composed in the CAL DAG.
- **Graceful failure:** a 3-frame batch with one corrupt FITS → the corrupt frame
  `Failed` with `OSError: No SIMPLE card found…`, the flow ran to `Completed`, both
  good frames succeeded.
- **Tests:** 21 fast unit/integration tests green + 1 slow real-frame trace
  integration test; a static test enforces that `core/` never imports Prefect.

---

## 6. Tech stack & reproducibility (for §2/§7 and the methods)

- **Python** 3.10+ (developed on 3.12). **OS targets** Ubuntu 22 / Rocky 9.
- **Orchestration:** Prefect **3.4.11** (thread runners built in; process/
  distributed via `prefect-dask` **0.3.7** + dask/distributed 2026.6.0).
- **Primitives:** PypeIt **1.18.1** (slit tracing, `keck_lris_red` proxy),
  ccdproc **2.5.1** (master-bias combine; Astropy-coordinated).
- **Support:** numpy 2.3.1, scipy 1.15.3, astropy 7.1.0, matplotlib 3.10.5.
  Dashboard capture via Playwright 1.61.0 (optional).
- **Reproducibility:** top-level deps pinned; PypeIt imported not vendored; each
  KOA dataset carries a `koaids.txt` manifest so it is re-downloadable; content-
  fingerprint cache keys make re-runs deterministic.

Task-runner requirements worth a sentence in the paper: Prefect 3 ships only
thread runners; true multi-core needs a process/distributed runner (Dask), which
requires a persistent Prefect server (worker processes cannot share the ephemeral
in-process API) and a standard `__main__` guard.

---

## 7. Data / case study (for §3)

- **Synthetic LRIS-2 flats + arcs** (ray-traced, 4080², single-HDU) — the current
  tracing/Quicklook input.
- **Real KOA data** (downloadable via manifests): a full LRIS-Blue night
  (2002-01-07, Martin program on the Abell 851 / CL0024 clusters — 104 cal + 61
  MOS science + bias/flat/arc, both channels) as the **primary case-study
  candidate**; a DEEP2-style DEIMOS night (2003-10-27, GOODS-South / MS0451 / DEEP2
  masks, 67 cal + 59 science) as a ground-truth cross-check (DEEP2 DR4 is a
  published reduction); plus Feige 34 spectrophotometric standards on both
  instruments.
- **Real-data finding worth reporting:** raw Keck frames are not in tracing
  orientation and carry overscan/multi-amplifier structure. A raw LRIS MOS flat
  traced 0 slits as delivered but 4 once transposed to PypeIt's `(nspec, nspatial)`
  convention — i.e. real reductions need a raw-image preprocessing/assembly step
  the synthetic single-HDU flats hid.

---

## 8. Honest caveats (state these plainly; they strengthen the paper)

- **Claim 4 (compiled-C dual-layer primitives) is not implemented** — deliberately
  parked until the orchestration story was complete. The pure-Python layer is
  real; the C-acceleration layer is future work.
- **Selective re-execution wall-clock win is topology-dependent.** In the current
  shallow DAG the tunable parameter (`fit_order`) feeds the expensive terminal
  Trace step, so a parameter change re-runs it (no time saving); the dramatic win
  appears when steps are added downstream of the expensive step. The *cache
  correctness* (only the changed subgraph recomputes) holds regardless.
- **Threads hurt CPU-bound reduction** (GIL); the parallel speedup comes from
  process isolation (Dask). Presented honestly as "different stages benefit from
  different runners."
- **Dashboard figures are full-page screenshots** — may want tighter crops.
- **The case-study end-to-end reduction on real frames is not yet wired** — it
  needs the multi-amp raw loader (parked). ccdproc bias is demonstrated on the
  real LRIS-1 bias stack, but applying it through a full real-frame trace awaits
  that loader.
- **PyReduce** (a spectroscopic-package polyglot primitive + upstream-contribution
  target) is deferred — it ships a C library to build and has in-place-mutation
  steps needing a functional wrapper.

---

## 9. Predictable reviewer questions (answers the code supports)

- **"Why not just use Airflow/Dagster?"** — DRP-appropriate content-fingerprint
  caching for large arrays, in-process primitive composition, and a light
  operational footprint (runs on a laptop, an observatory server, or a cluster by
  swapping the task runner). Demonstrated by F9 (caching) and F11 (runner swap).
- **"Why not just use PypeIt directly?"** — no single library has every primitive
  a multi-slit DRP needs in the desired form; the orchestration substrate composes
  the best primitive from each library under one DAG. Demonstrated by PypeIt +
  ccdproc + custom composing in one flow (Phase 7 / ADR 0008).

---

*Provenance: generated from the `spie-prototype` repo state on 2026-07-02. The
authoritative sources are `docs/architecture.md`, `docs/plan.md` (Done section +
state snapshot), the ADRs in `docs/decisions/`, and `docs/data.md`.*
