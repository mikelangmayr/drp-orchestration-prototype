# Architecture

The design document for the orchestration layer. Paper §4 will be transcribed
from this; the code lives by it. Update when design decisions change, not when
the code does — implementation details that don't affect the architecture stay
out of this file.

If a decision here turns out to be wrong, write an ADR explaining the change
before editing this document. Drift between this doc and `CLAUDE.md` is a bug
to fix immediately.

## The three-layer model

The repository structure encodes the architecture. The separation is strict
and load-bearing — it is what makes the orchestration claims of the paper
true at the code level, not just in prose.

```
src/spie_prototype/
├── core/        # primitives — pure functions, no orchestration awareness
├── tasks/       # Prefect task wrappers around core/ functions
└── flows/       # flow definitions — DAG composition only, no logic
```

Each layer has a single responsibility. Crossing the boundary in the wrong
direction is forbidden:

- `core/` MAY NOT import from `tasks/`, `flows/`, or `prefect`.
- `tasks/` MAY import from `core/` and `prefect`.
- `flows/` MAY import from `tasks/` and `prefect`; MAY NOT import from `core/`
  except for type aliases.

### Why the strict separation matters

A `core/` primitive must be usable in three contexts without modification:
inside a Prefect task during production runs, inside a Jupyter notebook for
exploratory work, and inside a pytest test for verification. If a primitive
acquires any awareness of orchestration — calls `get_run_logger`, decorates
with `@task`, expects a `PrefectFuture` — it ceases to be usable in the other
two contexts, and the architecture argument collapses.

The strict separation also makes the dual-layer primitive model (paper §6)
tractable. The compiled C backend replaces a `core/` function. It does not
know about Prefect, caching, or the dashboard. The task wrapper above it is
unchanged. Backend selection is a `core/`-internal concern.

## The primitive interface contract

A primitive in `core/` is a Python function with these properties:

1. **Pure with respect to its arguments.** No reading of global state, no
   reliance on side effects, no implicit dependencies on environment variables
   except where explicitly documented (e.g. backend selection override).
2. **Numpy / Astropy in, numpy / Astropy out.** No Prefect types in
   signatures. No filesystem paths in arguments unless the primitive is
   fundamentally about I/O (e.g. `load_flat_frame`).
3. **No side effects.** Mutating an input array, writing to disk, calling
   network services — none of these belong in a primitive unless the primitive
   exists specifically for that effect.
4. **Type hints on signature and return.** Helps the task wrappers, helps
   downstream code, helps documentation generation.
5. **Docstring with shape / dtype expectations on numpy inputs.** PypeIt and
   PyReduce conventions differ; document what this primitive expects.

A primitive sourced from an external library (PypeIt, PyReduce, `ccdproc`)
is wrapped in a `core/` function that adapts its interface to this contract.
The wrapper may translate library-specific types to numpy arrays, set default
parameters appropriate for the LRIS-2 context, or split a side-effecting
library call into a pure-function form (see §"In-place mutation" below).

### Example primitive

```python
# core/tracing.py
from typing import Tuple, Optional
import numpy as np
from functools import lru_cache
from pypeit.spectrographs.util import load_spectrograph

@lru_cache(maxsize=4)
def _spectrograph(name: str):
    return load_spectrograph(name)

def trace_slits(
    data: np.ndarray,
    spectrograph_name: str = "keck_lris_red",
    fit_order: int = 5,
    ...
) -> Tuple[np.ndarray, np.ndarray, Optional[object]]:
    """
    Trace slit edges using PypeIt's EdgeTraceSet.

    Args:
        data: 2D image, shape (nspec, nspatial), float64.
        spectrograph_name: PypeIt spectrograph name. LRIS-2 currently uses
            keck_lris_red as a proxy.
        fit_order: Polynomial order for trace fitting.

    Returns:
        (left_edges, right_edges, raw_edge_object) where left and right are
        each shape (n_slits, nspec).
    """
    spec = _spectrograph(spectrograph_name)
    ...
```

This is the canonical shape. The task wrapper around it is in `tasks/tracing.py`
and adds nothing of substance — see §"Task wrapping pattern" below.

### Handling in-place mutation from external libraries

Some libraries (notably PyReduce) implement steps as side-effecting class
methods that mutate shared state — for example, slit curvature determination
updates the `traces` object in place rather than returning a new one. This
breaks selective re-execution: cache keys are derived from inputs, but if a
task mutates its input, downstream tasks may receive different versions of
"the same" object depending on which other tasks have run.

The `core/` wrapper for such a primitive must convert it to a pure-function
form, typically with a `copy.deepcopy` of the mutated argument followed by an
explicit return:

```python
def slit_curvature(curvature_files, traces, mask, bias, **par):
    new_traces = copy.deepcopy(traces)
    SlitCurvatureDetermination(par=par).run(curvature_files, new_traces, mask, bias)
    return new_traces
```

This refactor is local to our `core/` layer; the upstream library is
unchanged. It is also a candidate upstream contribution (see paper §9).

## The task wrapping pattern

A task wrapper is a thin Prefect decoration over a `core/` function. It adds
exactly four things, and nothing else:

1. **Logging.** Parameter values at entry, summary statistics at exit.
2. **Caching.** `cache_key_fn`, `cache_expiration`, `persist_result=True`.
3. **Retries.** Configured per task type; see §"Failure handling" below.
4. **A human-readable task name** that appears in the dashboard.

Wrappers do not implement logic. If a wrapper is more than ~20 lines
excluding the docstring, the logic probably belongs in `core/`.

### Canonical wrapper template

```python
# tasks/tracing.py
from datetime import timedelta
import numpy as np
from prefect import task, get_run_logger
from prefect.tasks import task_input_hash
from spie_prototype.core.tracing import trace_slits

@task(
    name="Trace Slits (PypeIt)",
    cache_key_fn=task_input_hash,        # or custom fingerprint; see §Caching
    cache_expiration=timedelta(days=7),
    persist_result=True,
    retries=0,                            # CPU-bound, deterministic failure
)
def trace_slits_task(data: np.ndarray, **kwargs) -> tuple:
    logger = get_run_logger()
    logger.info(
        f"Tracing: shape={data.shape}, dtype={data.dtype}, "
        f"spectrograph={kwargs.get('spectrograph_name', 'keck_lris_red')}, "
        f"fit_order={kwargs.get('fit_order', 5)}"
    )
    left, right, _ = trace_slits(data, **kwargs)
    n_slits = left.shape[0] if left.size > 0 else 0
    if n_slits == 0:
        logger.warning("No slits found — check input and parameters")
    else:
        median_width = float(np.median(
            right[:, right.shape[1]//2] - left[:, left.shape[1]//2]
        ))
        logger.info(f"Found {n_slits} slits, median width = {median_width:.1f} px")
    return left, right
```

The logging at entry and exit is not boilerplate — it is what makes the
dashboard screenshots in the paper substantive rather than just "task
succeeded." See §"Observability" below.

## Task granularity

Not every function should be a task. The rule:

A function MUST be a `@task` if at least one is true:

- It performs I/O (disk, network, FITS read/write).
- It is computationally substantial (>~100ms typical runtime).
- It is a meaningful unit of caching or selective re-execution.
- Its output is something a human would want to inspect on the dashboard.

If none apply, it is a plain function called from inside another task.
Over-tasking adds Prefect scheduler overhead, result-serialization cost, and
visual clutter on the dashboard without observability gain. Under-tasking
collapses the DAG into opaque blobs and breaks the selective re-execution
story.

Concrete examples from this codebase:

- `trace_slits` → task. Substantial computation, expensive to recompute,
  worth caching, parameters worth inspecting.
- `get_slit_centers` (numpy median of edge arrays) → plain function. Runs
  in microseconds, no I/O, no value in dashboard visibility.
- `load_flat_frame` → task. I/O, retry-relevant, error-prone.
- `save_edge_trace` → task. I/O, success/failure worth surfacing.
- `np.median(arr, axis=0)` → not a function we own; just call it.

## Caching and selective re-execution

This is where the paper's developer-productivity claim (claim 2) lives in
code. Caching is not an optimization; it is the mechanism by which selective
re-execution exists at all.

### The fingerprint approach

Prefect's `task_input_hash` hashes the full content of inputs. For numpy
arrays that means hashing the entire buffer — correct, but slow on the
multi-megabyte arrays this pipeline operates on. We use a content fingerprint
instead:

```python
import hashlib
from prefect.context import TaskRunContext

def numpy_aware_cache_key(context: TaskRunContext, parameters: dict) -> str:
    """
    Hash arguments to a Prefect task, using a fingerprint (shape, dtype, and
    statistical moments) for numpy arrays rather than the full buffer.
    """
    h = hashlib.sha256()
    h.update(context.task.name.encode())
    for key, value in sorted(parameters.items()):
        h.update(key.encode())
        if isinstance(value, np.ndarray):
            fingerprint = (
                value.shape,
                str(value.dtype),
                float(value.mean()),
                float(value.std()),
                float(value.min()),
                float(value.max()),
            )
            h.update(repr(fingerprint).encode())
        else:
            h.update(repr(value).encode())
    return h.hexdigest()
```

### Why a fingerprint, not a full hash?

Two reasons:

1. **Cost.** A full SHA-256 of a 16 MB float64 array runs in tens of
   milliseconds per array, repeated for every task in every flow run. For
   a batch of 32 frames through a 10-task DAG, that's seconds of pure
   hashing overhead per run. With the fingerprint it's microseconds.

2. **Stability.** The full buffer hash is fragile to bit-level noise that
   doesn't matter scientifically. If a calibration step is rerun and
   produces results identical to within float epsilon, we want the cache
   to hit. The fingerprint approach makes the cache key robust to
   non-meaningful differences while remaining sensitive to any meaningful
   change in the data.

### Tradeoff: hash collisions

The fingerprint can theoretically collide — two different arrays with
identical shape, dtype, mean, std, min, and max. In practice this is
astronomically unlikely for real reduction data. For tasks where bit-exact
reproducibility is required (regression tests in CI, the C-vs-Python
equivalence check), use `task_input_hash` directly to force full-content
comparison.

This tradeoff and the parameters are documented in
`docs/decisions/0005-numpy-cache-fingerprint.md`.

## Flow composition

A flow is a wiring diagram. It reads as a sequence of `.submit()` calls that
build a DAG, with `.result()` calls only where data must materialize for
control flow.

### Flow taxonomy: per-instrument CAL / Quicklook / Science

Flows are organized as a matrix of **instrument × purpose** (ADR 0006). A single
DRP cannot span instruments as different as LRIS and DEIMOS — raw format,
geometry, calibration sets, and spectrograph definitions differ enough that one
parameterized flow would become unreadable branching. So each instrument gets
its own flow module, and within it three DAGs:

- **CAL DAG** — builds and caches master calibrations (master bias, master flat,
  wavelength solution) per configuration group. The parallel calibration arms of
  ADR 0003 live here.
- **Quicklook DAG** — fast, fixed-parameter, real-time: 2D wavelength-calibrated,
  sky-subtracted frames with fixed-boxcar 1D extraction. Consumes CAL masters.
- **Science DAG** — full science quality: optimal extraction, full sky model,
  flux calibration. Consumes the same CAL masters.

`CAL → {Quicklook, Science}` is the cross-DAG caching edge: masters are built
once and served from cache to both consumers. Instruments share `core/`
primitives and `tasks/` wrappers wherever the algorithm is general; only the
loader/preprocessor and the spectrograph/config parameters differ. The
no-Red/Blue-fork rule holds within an instrument — channel is a parameter, not a
separate flow. The paper's Flow A / B / C are demonstrations *run against* these
DAGs (e.g. selective re-execution on the Science DAG), not flows themselves.

### Flat orchestration, not nested

Tasks calling tasks is forbidden. The orchestration belongs at the flow
level so every step is visible on the dashboard. If a sub-flow is genuinely
warranted, use Prefect's subflow mechanism (`@flow` decorated function called
from another `@flow`), not a task that calls tasks.

### Canonical flow shape (Quicklook DAG)

The CAL DAG (`flows/lris/cal.py`) builds the master arms and returns them; the
Quicklook DAG (`flows/lris/quicklook.py`) runs it as a subflow and reduces each
frame. See the modules for the full implementations.

```python
# flows/lris/cal.py
@flow(name="LRIS CAL", task_runner=ConcurrentTaskRunner())
def cal_flow(bias_level=0.0, dark_level=0.0):
    # Parallel calibration arms: independent, run concurrently, cached and reused
    # across the Quicklook/Science DAGs and re-runs.
    master_bias = make_master_bias_task.submit(bias_level)
    master_dark = make_master_dark_task.submit(dark_level)
    return {"bias": master_bias.result(), "dark": master_dark.result()}

# flows/lris/quicklook.py
@flow(name="LRIS Quicklook", task_runner=ConcurrentTaskRunner())
def quicklook_flow(input_dir, output_dir):
    masters = cal_flow()                       # CAL subflow -> cached masters
    paths = discover_fits_task(input_dir)
    # Submit all loads + calibration before resolving any, so the CPU-bound
    # traces overlap across frames instead of serializing.
    raw = {p: load_flat_frame_task.submit(p).result()[0] for p in paths}
    debiased = {p: bias_subtract_task.submit(raw[p], masters["bias"]) for p in paths}
    calibrated = {p: dark_subtract_task.submit(debiased[p], masters["dark"]) for p in paths}
    traces = {p: trace_slits_task.submit(calibrated[p]) for p in paths}
    for p in paths:
        left, right = traces[p].result()
        save_edges_task.submit(left, right, ...)
        generate_trace_qa_plot_task.submit(calibrated[p].result(), left, right, ...)
```

Two kinds of parallelism live here. The **calibration arms** (master bias and
master dark) are mutually independent and run concurrently, then *join* each
frame's chain at the subtract steps. Within a frame the chain is sequential
(bias → dark → trace carry data dependencies); across frames the chains fan out
concurrently because all steps are submitted before any result is awaited. This
is the shape the paper's claim 3 rests on, and the master arms — built once,
cached, reused — are also the natural setup for the selective-re-execution
demo (claim 2). The masters are stubs in Phase 3 (constant pedestals); see
`docs/decisions/0003-calibration-arms-via-master-construction.md`.

### Task runner selection

Different stages benefit from different concurrency models:

- **`ConcurrentTaskRunner`** (threads). For I/O-bound tasks: FITS loading,
  result persistence, dashboard updates. Default for flows that are
  predominantly I/O.
- **`ProcessPoolTaskRunner`**. For CPU-bound tasks where the GIL is a
  bottleneck: tracing, extraction, cosmic-ray rejection. Use when concurrency
  must translate to wall-clock parallelism.
- **`DaskTaskRunner`**. For distributed execution across multiple machines.
  Reserved for cases where a single host isn't enough (large reprocessing
  campaigns).

The choice is per-flow, not per-task. Phase 6 of the plan benchmarks all
three and picks the appropriate runner for the case-study flow.

## Polyglot primitive composition

The orchestration layer is **primitive-source-agnostic**. A Prefect task does
not know whether the function it wraps came from PypeIt, PyReduce, `ccdproc`,
`specreduce`, or our own code. It cares only that the function satisfies the
primitive interface contract above.

This is what justifies the paper's "polyglot primitive composition" claim
and answers the predictable reviewer question "why not just use PypeIt
directly?": because no single existing library has all the primitives a
modern multi-slit DRP needs in the form we want them, and the orchestration
substrate is what lets us assemble the best primitive from each library
under one DAG.

Concretely for LRIS-2:

| Primitive | Source | Notes |
|-----------|--------|-------|
| Slit tracing | PypeIt `EdgeTraceSet` | Multi-slit support, mature |
| Bias subtraction | PyReduce or `ccdproc` | Straightforward |
| Flat normalization | PyReduce | Clean step interface |
| Cosmic-ray rejection | TBD (PypeIt has L.A.Cosmic; `ccdproc` also) | Decide empirically |
| Wavelength calibration | PyReduce | Three-step pattern wraps cleanly |
| Extraction | PyReduce or PypeIt | Decide based on slit geometry fit |
| LRIS-2-specific glue | Custom | Minimal; only where neither library fits |

Each row is a `core/` function with the same shape: numpy/astropy in,
numpy/astropy out. The task wrappers above them are uniform. The flow
doesn't care.

## Failure handling

The architecture distinguishes two kinds of failure:

**Transient failures** (network blips, disk contention, temporarily
unavailable resources) are retried with backoff. Applies to I/O tasks:
FITS loading, result saving. Retries are 2–3 with exponential backoff.

**Deterministic failures** (bad data, malformed inputs, primitive
preconditions violated) are not retried. Applies to computation tasks:
tracing, extraction, calibration. Failing fast surfaces the problem
immediately in the dashboard with full context (parameters, input
fingerprint, exception traceback).

In Flow C (graceful failure across a batch), this distinction is what makes
the demo work: a corrupt frame fails its `load_flat_frame_task` after retry
exhaustion, the failure is logged with full context, and the per-frame
work for other frames continues unaffected. The script-driven counterfactual
— the whole batch halts or silently produces wrong output — is the contrast
the paper draws.

## Observability

The Prefect dashboard is the observability surface. The architecture's
contribution to observability is making sure the dashboard has useful
content to show:

1. **Parameter visibility.** Task wrappers log all parameters at entry.
2. **Intermediate product inspection.** `persist_result=True` on cached
   tasks means intermediate outputs are persisted and can be loaded from
   the dashboard for inspection.
3. **Per-task log surfacing.** `get_run_logger()` writes to the task's log
   stream, viewable in the dashboard without grepping a global log file.
4. **DAG shape.** Flat orchestration (no nested task calls) means the
   dashboard's DAG view reflects the actual reduction structure.
5. **State and timing.** Standard Prefect surface — task state transitions,
   wall-clock duration, cache hit/miss.

Points 1–4 are architectural choices in this codebase. Point 5 is
Prefect's contribution.

## Out of scope

The architecture deliberately does not solve:

- **Provenance tracking.** A new master bias should ideally trigger
  identification and re-running of dependent reductions. This requires a
  provenance graph layered above the DAG; useful but beyond paper scope.
  Parked as Flow D.
- **Multi-instrument abstraction.** The architecture should generalize to
  other instruments, but the implementation targets LRIS-2 specifically.
  Generalization is an implication discussed in the paper, not a code
  contribution.
- **Configuration management.** Currently kwargs and defaults; no YAML
  config system, no plugin registry. Premature.
- **Production deployment.** No Docker, no k8s, no systemd. Out of paper
  scope; the production LRIS-2 DRP is a separate project.
- **Backward compatibility.** This is a prototype; no commitment to API
  stability.

## Cross-references

- Per-decision ADRs live in `docs/decisions/`. Each significant choice
  here should have one when it's a decision a future contributor might
  reasonably make the opposite way.
- Operational rules (what Claude Code must / must not do) are in
  `CLAUDE.md`; this document is the *why*, that one is the *what*.
- Paper section structure that distills from this doc is in
  `docs/paper_outline.md` §4.