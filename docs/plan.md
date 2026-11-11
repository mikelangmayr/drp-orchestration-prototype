# Plan

Volatile state. Source of truth for "what next." Read at session start; update
at session end. Items move between sections as work progresses; finished items
are summarized briefly under Done and detail-pruned over time.

## In progress

_(Between milestones — Phases 1–7 + the ADR 0006 flow restructure + dashboard
captures complete and verified; Phase 8 (paper) is next.)_

## Next (priority order)

Items in this section are paper-critical and should be worked on roughly in
order. Each item should fit in one focused session.

### Phase 8 — Paper

21. **Draft `docs/architecture.md` revisions** based on what was actually
    built (the design doc must match the code by the time §4 is transcribed).
22. **First full paper draft.** Sections in order: 4, 5, 7, 6, 3, 2, 8, 9,
    10, 1. (Intro and conclusion last; they're easier when the body is done.)
23. **Citation gathering pass** — work through `docs/citations.md`, find
    canonical references for everything marked `need`.

## Parked

These are not next, but are not abandoned. They will become Next when their
preconditions are met (or when the paper post-mortem opens space).

- **C primitives + benchmark (paper §6).** Picked back up only after Phase 7
  is complete. Targets: one trivial (bias subtraction) and one heavy (cosmic-
  ray rejection or median-combine). Cython for the C layer. Backend selection
  via decorator registry.
- **`trace_from_array()` PR upstream to PypeIt.** Wait until our primitive is
  stable; coordinate via PypeIt Slack first.
- **Functional refactors PR upstream to PyReduce.** Same gating.
- **Wavelength calibration primitive.** Useful for completeness but not load-
  bearing for the paper's claims. Add only if Phase 7 lands early.
- **Provenance-driven re-execution (Flow D).** Compelling but needs provenance
  infrastructure beyond paper scope.
- **Raw-image preprocessing + multi-amp loader primitive.** Surfaced while
  validating the real LRIS night (see `docs/data.md`): raw Keck frames need
  orientation (to `(nspec, nspatial)`), overscan/trim/bias, and amplifier
  assembly before tracing — a raw flat traced 0 slits as-is, 4 once transposed.
  Precondition for using real data (the 2002-01-07 case study) end-to-end;
  becomes Next when the case-study reduction is taken on. Pairs with the
  canonical `CCDData` data model (the not-yet-written ADR the dataset docs cite).

## Done

### Phase 1 — Bootstrap (2026-06-29)

- `pyproject.toml` with pinned deps (`prefect==3.4.11`, `pypeit==1.18.1`,
  `numpy`, `scipy`, `astropy`, `matplotlib`); dev extras `pytest`, `ruff`.
  **Caveat:** no lockfile committed yet (repo is not under git; `uv.lock`
  pending — see open questions).
- `src/spie_prototype/{core,tasks,flows}/` skeleton with `__init__.py` docstrings
  and a `tests/` tree. Seeded `docs/` (context, architecture, plan, paper_outline)
  and root `CLAUDE.md` / `AGENTS.md` from `plans/`. ADRs 0001 (three-layer
  separation) and 0002 (pin PypeIt) written.
- Prefect 3.4.11 confirmed working (smoke flow runs on the temporary server).
- Smoke flow `flows/smoke.py` (one no-op task) runs green.

### Phase 2 — Tracing slice (2026-06-29)

- `core/tracing.py`: `trace_slits` (numpy in, `(left, right, raw_edges)` out),
  `lru_cache`'d `_spectrograph`, `(nspec, nspatial)` axis convention, module-level
  PypeIt version check (warns on mismatch), pure `get_slit_centers`.
- `core/io.py`: `discover_fits`, `load_flat_frame`, `save_edges`. `core/qa.py`:
  `generate_trace_qa_plot`.
- Thin task wrappers (`tasks/io.py`, `tasks/tracing.py`, `tasks/qa.py`) with the
  caching convention via `task_input_hash`; shared config in `tasks/_caching.py`.
  `discover_fits_task` is a visible fan-out node.
- `flows/tracing.py`: flat orchestration (all `.submit()`/`.result()` at flow
  level), `ConcurrentTaskRunner`, CLI entry point.
- Tests: layering guardrail (AST-based: core imports no prefect), I/O + QA on
  synthetic data, `get_slit_centers`, and a `@slow` real-flat `trace_slits`
  integration test. `pytest -m "not slow"` green (7 passed).
- **Verified end-to-end:** traced both LRIS-2 flats → 72 slits each (median width
  ~52 px), edges + QA PNGs written, flow `Completed`.

### Phase 3 — DAG shape for Flow A (2026-06-29)

- `core/calibration.py`: stub `make_master_bias` / `make_master_dark` (constant
  pedestals) + real `subtract_bias` / `subtract_dark` (broadcast scalar or 2D
  master, no input mutation).
- `tasks/calibration.py`: parallel-arm `make_master_bias_task` ∥
  `make_master_dark_task` (cached, reused across frames) + `bias_subtract_task` /
  `dark_subtract_task`. Re-exported from `tasks/__init__.py`.
- `flows/reduce.py` — **Flow A**: master arms join per-frame chains
  (load → bias → dark → trace → save + QA); frames fan out concurrently.
- **Design decision (ADR 0003):** parallel calibration arms realized as
  independent *master-construction* tasks, not parallel per-frame subtraction —
  resolved a plan-vs-architecture inconsistency; `architecture.md` Flow A snippet
  updated to match.
- Figures: `scripts/render_dag.py` → F7 (`figures/flow_a_dag.{mmd,png}`, matplotlib
  + Mermaid, no Graphviz binary needed). `scripts/capture_dashboard.py` → F4
  (resolves the run URL via the Prefect client; screenshots with Playwright if
  installed). **Caveat:** F4 screenshot needs a running `prefect server` and
  Playwright (optional, un-pinned — ask before adding).
- Tests: `tests/test_calibration.py` (4 tests). `pytest -m "not slow"` → 11 passed.
- **Verified end-to-end:** Flow A `Completed` on both flats; both master arms ran
  concurrently; 72 edges + QA per frame. Bonus: `trace_slits_task` was served
  from cache across runs (level-0 calibration leaves the array fingerprint
  unchanged), an early preview of the Phase 4 selective-re-execution story.

### Phase 3.5 — Flow restructure to CAL/Quicklook/Science triad (2026-06-30)

- **ADR 0006:** flows organized per-instrument × {CAL, Quicklook, Science};
  instruments don't share a DAG but share `core/`/`tasks/`. `architecture.md`
  §"Flow composition" updated.
- `flows/lris/{cal,quicklook,science}.py` created; `flows/reduce.py` removed.
  `cal_flow` = the parallel master arms (cached); `quicklook_flow` runs CAL as a
  subflow then load → bias → dark → trace → save + QA; `science_flow` is a
  documented `NotImplementedError` placeholder. `flows/tracing.py` kept as a
  standalone building block.
- **Verified:** `pytest -m "not slow"` → 12 passed; CAL DAG runs standalone;
  Quicklook runs CAL as a nested subflow then reduces both flats (72 slits each,
  edges + QA), `Completed`; Science stub raises with a clear message.

### Phase 4 — Selective re-execution (2026-06-30)

- **Item 12:** `numpy_aware_cache_key` (shape/dtype/mean/std/min/max fingerprint)
  in `tasks/_caching.py`, now the default for all reproducible tasks;
  `task_input_hash` kept as `BITEXACT_CACHE_KEY_FN`. ADR 0005 documents the
  cost/stability/collision tradeoff. 5 unit tests in `tests/test_caching.py`.
  `pytest -m "not slow"` → 17 passed.
- **Items 13–14:** `scripts/benchmark_selective_rerun.py` runs the LRIS Quicklook
  DAG cold / re-run / selective on an isolated `PREFECT_HOME`, tallies per-task
  cache hits via the Prefect client, and writes **F9** (`figures/selective_rerun_timing.png`).
- **Measured:** cold **372s**; unchanged re-run **6.7s** (all cached, ~55×);
  selective (`fit_order` 5→7) **461s** with masters/load/bias/dark **cached** and
  only **Trace + Save/QA recomputed** — the cache-hit table is the rigorous proof
  of claim 2.
- **Honest finding:** the selective *wall-clock* win is topology-dependent. Here
  `fit_order` feeds Trace, the dominant near-terminal step, so it correctly
  recomputes and there is no time saving vs cold; the win grows as steps are added
  downstream of Trace (extraction/wavecal/flux). F9's caption states this.
- **F8** (dashboard before/after) still needs a live `prefect server` + Playwright
  (via `scripts/capture_dashboard.py`) — not automated.

### Phase 5 — Graceful failure (2026-07-01)

- **Resilience is now a property of the DAG:** `quicklook_flow` isolates
  per-frame failures — a frame that fails at load or reduction is logged with
  full context and skipped, the rest of the batch completes, and the flow
  returns `{"succeeded": [...], "failed": {path: reason}}`. Broad catches are
  deliberate fault-isolation boundaries.
- **Item 15:** `scripts/demo_graceful_failure.py` (Flow C) symlinks good frames +
  injects one corrupt FITS and runs the batch.
- **Core test:** `load_flat_frame` raises on a corrupt FITS. `pytest -m "not slow"`
  → 18 passed.
- **Verified:** batch of 3 (2 good + 1 corrupt) → the corrupt frame's Load task
  `Failed` with full traceback (`OSError: No SIMPLE card…`), logged and skipped;
  both good frames succeeded; flow `Completed` (did not halt). The script-driven
  counterfactual (whole batch halts) is the contrast.
- **F10** (dashboard: batch with one Failed frame) still needs a live
  `prefect server` + Playwright — not automated.

### Phase 6 — Performance numbers (2026-07-01)

- `scripts/benchmark_parallel.py` (item 17): times the same N load+trace tasks
  under three runners — serial, concurrent (threads), Dask (processes) — via
  `flow.with_options(task_runner=...)`, uncached (`NO_CACHE`), with a `--crop`
  knob for per-task cost. Resilient per-runner timing. F11 (item 18):
  `figures/serial_vs_parallel_timing.png`.
- **Measured (N=3, ~72 s tasks, 3 workers):** serial **216.6 s**; threads
  **403.4 s (0.54x — slower)**; Dask **83.2 s (2.60x)**. Threads hurt the
  CPU-bound trace even at ~1 min tasks (PypeIt is GIL-bound); process parallelism
  (Dask) delivers the real speedup.
- **Adaptations documented (ADR 0007):** Prefect 3 has no built-in
  `ProcessPoolTaskRunner`; `DaskTaskRunner` needs `prefect-dask` (pinned optional
  `[parallel]` extra), a **persistent Prefect server** (workers collide on the
  ephemeral SQLite otherwise), and an `if __name__ == "__main__":` guard (spawn
  re-imports the driver). A persistent `prefect server` is now running locally
  (also unblocks the F4/F8/F10 dashboard captures).
- **PypeIt thread-safety:** the concurrent-threads run completed (all traces
  returned correct slit counts), so PypeIt is not *unsafe* under threads — just
  GIL-bound, so threads give no speedup. The PyReduce-tracing swap is therefore
  not forced; process isolation (Dask) is the answer.

### Phase 7 — Polyglot primitives (2026-07-02)

- **ADR 0008:** added a real primitive from a second library — `ccdproc`
  (Astropy-coordinated) — to demonstrate the orchestration is
  primitive-source-agnostic. `core.combine_master_bias` median-combines a bias
  stack via `ccdproc.combine` (numpy-in/out; fresh `CCDData`, no in-place
  mutation). `combine_master_bias_task` (cached) + re-export.
- `cal_flow` gains `--bias-dir`: real ccdproc master bias (discover → load →
  combine) or the pedestal stub. The CAL DAG now composes **ccdproc + custom +
  (downstream) PypeIt** — three sources under one flow.
- `ccdproc==2.5.1` pinned in main deps. Tests: synthetic median-combine + empty
  guard + real LRIS-1 bias stack → `pytest -m "not slow"` 21 passed.
- **Verified:** `cal_flow(--bias-dir <7 real LRIS-1 biases>)` → "Combined 7 bias
  frames via ccdproc (median), master (2048,2148), median≈1601 ADU", `Completed`.
- **Not claim 4:** this is polyglot composition + the Astropy-ecosystem claim, not
  the dual-layer compiled-C primitive model (still parked). PyReduce deferred
  (C-lib build + in-place refactor) as a future second polyglot primitive.

### Dashboard captures — F4 / F8 / F10 (2026-07-02)

- Closes the claim-1 (observability) gap. `playwright==1.61.0` added as the
  optional `[dashboard]` extra (`python -m playwright install chromium`).
- `scripts/capture_dashboard.py` hardened: `--flow-name` to target a flow's most
  recent run, `--name` for the output file, dismisses the "Join the Prefect
  Community" popup, and waits for the polling SPA to render (no `networkidle`).
- Flows run against the persistent server (`PREFECT_API_URL=.../api`) so the runs
  are visible; captured **F4** (Quicklook DAG), **F8** (fit_order 5→7: cached
  upstream + recomputed Trace), **F10** (corrupt-batch run, failed Load node in
  red, rest green). Files in `figures/`.
- Supersedes the "F4/F8/F10 not automated" caveats in the Phase 3/4/5 entries.
  Refinement (zoomed graph / Task-Runs table crops) left as paper polish.

### Real KOA data + case study (2026-06-30)

- Verified the added KOA datasets against headers; corrected `docs/deimos-feige34.md`
  (count 40→38, naming, MOS→longslit) and `docs/lris-calibration.md` (program-IDs
  mislabeled as gratings); wrote `koaids.txt` manifests + `data/.gitignore`.
- Adopted the **2002-01-07 LRIS night** (Abell 851 / CL0024, 104 cal + 61 sci,
  Blue+Red) as the real multi-slit **case study**; documented in new `docs/data.md`
  with the `(channel, mask, grism)` config-grouping plan.
- `discover_fits` now matches `*.fits.gz` and takes `recursive=True` (KOA carts
  nest frames deep); task wrapper + tests updated. `pytest -m "not slow"` → 12 passed.
- **Real-data validation:** a raw LRIS MOS dome flat traced **0 slits** as-is but
  **4 once transposed** to `(nspec, nspatial)` — surfaced the raw-preprocessing /
  multi-amp-loader requirement now parked above.

Once an item has been Done for a while and isn't a useful reference, prune the
detail to a one-liner.

## Open questions / decisions needed

Questions that block or shape upcoming work. Resolve via ADR where the answer
isn't obvious, then update this section.

- **Which PypeIt version to pin?** _Resolved (ADR 0002):_ pinned `1.18.1`, the
  version verified in this environment. `core/tracing.py` warns on mismatch.
- **Lockfile + git.** The prototype is not yet a git repo and has no committed
  lockfile (Phase 1 item 1 only partially satisfied). Decide: `git init` here
  vs. fold into the parent repo; generate `uv.lock`.
- **Test-data location.** Frames currently live in the sibling checkout
  (`../lris2-drp/data/lris2_flats`, `.../lris2_arcs`), not in `spie-prototype/`.
  Flows take an explicit `--input`. Decide whether to copy a minimal frame
  subset in, symlink, or keep pointing at the sibling tree.
- **Case study: LRIS 2002-01-07 vs DEIMOS 2003-10-27.** Both are real multi-slit
  nights on disk (see `docs/data.md`). LRIS loads today (single-HDU) and is the
  on-message LRIS-2 proxy; DEIMOS is richer with DEEP2 DR4 published ground truth
  but needs the multi-amp loader first. Recommendation: LRIS primary, DEIMOS as
  ground-truth/second-instrument cross-check. Confirm before building the loader.
- **Task runner for CPU-bound tasks.** _Resolved (ADR 0007, Phase 6):_ threads
  are GIL-bound for the PypeIt trace (0.54x — slower; BLAS ruled out as cause);
  `DaskTaskRunner` (processes) gives 2.60x. `prefect-dask` added as pinned
  optional `[parallel]` extra. Default flows use the thread runner (fine for the
  I/O-bound stages); use Dask for CPU-bound batch throughput.
- **LRIS-2 commissioning data availability.** Default fallback: use LRIS-1 data
  via `keck_lris_red` as a proxy. State this explicitly in §3 and §7 of the
  paper. Revisit if commissioning data lands before submission.
- **SPIE conference confirmation.** Which specific SPIE — AS&I, SPIE
  Astronomical Telescopes, something else? Lock the proceedings deadline.
- **Author list.** Coordinate with the LRIS-2 instrument team before any draft
  circulates.

## Notes for session handoffs

- At session start: re-read `CLAUDE.md`, `docs/context.md`, this file, and
  `docs/architecture.md` (when it exists).
- At session end: update this file. Move completed items to Done. Add new
  items surfaced during the session — to Next if paper-critical, Parked
  otherwise. Update open questions if any were resolved or newly discovered.
- If something feels like scope creep, write it in Parked rather than just
  doing it. Future-you will thank present-you.

### Current state snapshot (2026-07-01)

- **Done:** Phases 1–6 + the ADR 0006 flow restructure + real-KOA-data work. All
  four abstract claims demonstrated in code (DAG, selective re-execution,
  parallelism, resilience). **Next: Phase 7 (polyglot primitives).**
- **ADRs written:** 0001 layering, 0002 pin PypeIt, 0003 calibration arms, 0005
  numpy cache fingerprint, 0006 per-instrument flow triad, 0007 task-runner
  choice, 0008 polyglot primitive (ccdproc). **ADR 0004 (canonical `CCDData` data
  model) is referenced but NOT yet written** — home for the multi-amp/raw-frame
  loader (see Parked).
- **Figures produced:** F4 `flow_a_dashboard.png`, F7 `flow_a_dag.{png,mmd}`,
  F8 `flow_b_dashboard.png`, F9 `selective_rerun_timing.png`, F10
  `flow_c_dashboard.png`, F11 `serial_vs_parallel_timing.png` — all in `figures/`.
  Dashboard shots (F4/F8/F10) captured via Playwright against the live server;
  they are full-page and may want tighter crops for the paper.
- **Operational state (runtime, not durable):** a **persistent `prefect server`
  is running at http://localhost:4200** (started this session; also powers the
  dashboard). Dask runs require `PREFECT_API_URL=http://127.0.0.1:4200/api` and
  the `if __name__ == "__main__":` guard (see ADR 0007). `prefect-dask` is
  installed. If the server is gone after a restart, relaunch with
  `prefect server start`.
- **Env:** prefect 3.4.11, pypeit 1.18.1, python 3.12; real data lives in the
  sibling `../lris2-drp/data/lris2_flats` (synthetic) and the top-level KOA dirs
  (`data/LRIS-2002-01-07`, `data/Deimos-2003-10-27`, etc. — see `docs/data.md`).
  Run flows/tests from the `spie-prototype/` dir with `PYTHONPATH=src`.
- **Naming:** the instrument pipeline is **LRIS** (`flows/lris/`), processing
  LRIS-1 real data + synthetic LRIS-2 stand-in flats; the DRP is *built for*
  LRIS-2 (which does not exist yet). Keep that distinction.

### Small parked refinements (surfaced, not yet done)

- **Retry-on-corrupt:** `load_flat_frame_task` retries a corrupt FITS twice
  (I/O retry policy) before failing — wasteful for a deterministic parse error.
  Optional: a `retry_condition_fn` that skips retries on `OSError`/FITS-parse
  failures. Harmless as-is (Flow C still isolates it).