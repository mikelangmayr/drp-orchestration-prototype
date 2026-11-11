# CLAUDE.md

Operational rules for working in this repo. Read this first, every session.

## What this repo is

A prototype supporting a SPIE paper on orchestration patterns for astronomical data
reduction pipelines, demonstrated on a slice of the LRIS-2 DRP at Keck Observatory.
This is **not** the production LRIS-2 DRP — it is a focused prototype that exists
to back the four claims in the submitted SPIE abstract:

1. DAG of observable tasks with selective re-execution
2. Parallel execution of independent steps with measurable speedup
3. Dual-layer primitive model (pure-Python canonical + optional compiled C primitives)
4. Astropy ecosystem compatibility with planned upstream contributions

See `docs/context.md` for the full briefing.

## Architectural rules — unbreakable

These rules exist so the architecture story in the paper is true at the code level,
not just in prose. Do not violate them without an ADR.

- **`core/` contains pure-function primitives.** Files in `core/` MUST NOT import
  from `prefect`, MUST NOT depend on any orchestration concept, MUST NOT read from
  or write to disk except where the primitive is fundamentally about I/O (e.g.
  `load_flat_frame`). A `core/` function should be callable from a Jupyter notebook,
  a pytest test, or a Prefect task with identical behavior.

- **`tasks/` contains thin Prefect task wrappers around `core/` functions.** A task
  wrapper MUST NOT reimplement logic. It MAY add logging, retries, caching, and
  result persistence. If a wrapper is more than ~20 lines excluding the docstring,
  the logic probably belongs in `core/`.

- **`flows/` contains flow definitions.** Flows orchestrate tasks. Flows MUST NOT
  contain reduction logic. A flow reads as a wiring diagram, not as an algorithm.

- **Tasks calling tasks is forbidden.** Orchestration belongs at the flow level so
  that every step is visible on the Prefect dashboard. If a parent task wraps several
  child tasks, the children become opaque in the UI and the observability claim breaks.

## Task granularity rule

A function becomes a `@task` if and only if at least one of these is true:
- It performs I/O (disk, network, FITS read/write).
- It is computationally substantial (>~100ms typical runtime).
- It is a meaningful unit of caching or selective re-execution.
- Its output is something a human would want to inspect on the dashboard.

If none of these apply, it is a plain function called from inside another task.
Over-tasking adds scheduler overhead without observability gain; under-tasking
collapses the DAG and breaks the selective re-execution story.

## Caching convention

Every task whose output is reproducible from its inputs MUST set `cache_key_fn`,
`cache_expiration`, and `persist_result=True`. The cache key fingerprint for tasks
taking numpy arrays MUST use a content fingerprint (shape, dtype, statistical
moments) rather than the full buffer hash, except where bit-exact reproducibility
is required.

Pattern:

```python
from prefect import task
from prefect.tasks import task_input_hash
from datetime import timedelta

@task(
    name="<Human-readable name>",
    cache_key_fn=task_input_hash,  # or a custom fingerprint fn for numpy inputs
    cache_expiration=timedelta(days=7),
    persist_result=True,
    retries=2 if io_bound else 0,
    retry_delay_seconds=10,
)
def my_task(...):
    ...
```

Retries: I/O tasks get retries; CPU-bound computation tasks do not (their failures
are deterministic). See `docs/decisions/0004-retries-on-io-only.md` once written.

## Dependency policy

- All top-level dependencies are pinned in `pyproject.toml`. A lockfile is committed.
- PypeIt is **imported, not vendored**. Use `pip install pypeit==<pinned>`.
- PyReduce, when added, is also imported, not vendored.
- Before adding a new top-level dependency, ask. Transitive dependencies via existing
  packages do not require asking.
- No private forks of external libraries in this repo. If a library needs a patch,
  that patch is an upstream contribution, tracked in `docs/upstream_contributions.md`.

## Out of scope for this repo

Do not add these without explicit direction:

- Production deployment configuration (Docker, k8s, systemd units).
- Multi-instrument support beyond what serves the LRIS-2 case study.
- Backward compatibility with previous LRIS pipelines.
- CLI/UI beyond what's needed to run flows for the paper's figures.
- General-purpose astronomy utilities not used by at least one flow in this repo.

If you find yourself building something the paper does not need, stop and check.

## Commands

```bash
# Install
uv sync                              # or: pip install -e .[dev]

# Tests
pytest                               # all
pytest tests/test_<area>.py          # one file
pytest -k "<pattern>"                # by name

# Run a flow against test data
python -m spie_prototype.flows.<flow_name> --input data/test_frames --output out/

# Start Prefect server (for dashboard)
prefect server start

# Capture dashboard screenshot for a flow run
python scripts/capture_dashboard.py --flow-run-id <id> --output figures/

# Benchmarks
python scripts/benchmark_parallel.py --frames data/test_frames --output figures/
```

## Process rules

- **Read `docs/plan.md` at session start.** It is the source of truth for what to
  work on next.
- **Update `docs/plan.md` at session end.** Move completed items to Done; add new
  items surfaced during the session to Next or Parked.
- **Significant decisions get ADRs.** A decision is significant if a future
  contributor might reasonably make the opposite choice. Write the ADR before
  implementing, not after.
- **The paper is the spec.** When in doubt about scope or design, ask "does this
  serve a claim or figure in `docs/paper_outline.md`?" If not, park it.
- **Ask before:**
  - Adding a new top-level dependency.
  - Refactoring across `core/`, `tasks/`, and `flows/` boundaries.
  - Adding a new top-level directory.
  - Reframing or weakening any of the four abstract commitments.

## Anti-patterns to avoid

- Mixing reduction logic into task wrappers ("just this once").
- Adding `notebooks/` or `examples/` directories — they bit-rot and confuse the
  canonical/non-canonical distinction. Use `scripts/` for runnable demos.
- Premature configuration systems. YAML configs, plugin registries, and dynamic
  loading are seductive and out of scope until the paper needs them.
- Generic utilities. If a helper is used by exactly one caller, inline it.
- "Improving" abstract claims by softening them. The abstract is committed; the
  code adapts to it, not the other way around.
