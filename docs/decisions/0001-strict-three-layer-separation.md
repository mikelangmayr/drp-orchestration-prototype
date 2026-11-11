# 0001 — Strict three-layer separation (core / tasks / flows)

- Status: accepted
- Date: 2026-06-29

## Context

The SPIE paper claims that orchestration patterns make a DRP more transparent,
modular, and resilient. For that claim to be true *in the code* and not just in
prose, the orchestration layer (Prefect) and the scientific algorithms must be
separable in fact: a primitive must run unchanged inside a Prefect task, a
Jupyter notebook, and a pytest test.

## Decision

The repository is split into three layers with a one-directional import rule:

- `core/` — pure-function primitives. MUST NOT import `prefect`, `tasks`, or
  `flows`. Disk I/O only where the primitive is fundamentally about I/O.
- `tasks/` — thin Prefect `@task` wrappers. MAY import `core/` and `prefect`.
  Add logging/caching/retries/name only; never reimplement logic.
- `flows/` — DAG wiring. MAY import `tasks/` and `prefect`; MUST NOT import
  `core/` except for type aliases. No reduction logic; no task-calling-task.

The `core`-imports-no-prefect invariant is enforced by a static test
(`tests/test_layering.py`) so a violation fails CI, not just review.

## Consequences

- Primitives are trivially unit-testable and upstreamable to specreduce /
  PyReduce / PypeIt, supporting the paper's open-source intent.
- The dual-layer primitive model (paper §6) becomes tractable: a compiled C
  backend replaces a `core/` function without the task wrapper noticing.
- Cost: some boilerplate (a wrapper per primitive) and the discipline of not
  "just this once" mixing logic into a task. Accepted deliberately.

## Alternatives rejected

- **One layer (tasks with embedded logic).** Simplest, but makes the
  separation claim false and primitives un-upstreamable.
- **Two layers (primitives + flows, no task layer).** Loses uniform
  caching/retry/observability and the task-granularity story.
