# SPIE Prototype — orchestration patterns for the LRIS-2 DRP

A focused prototype backing a SPIE paper on adapting modern workflow
orchestration (Prefect) to astronomical data reduction pipelines, demonstrated
on a slice of the LRIS-2 DRP at the W. M. Keck Observatory.

This is **not** the production LRIS-2 DRP. It exists to make four claims true at
the code level, not just in prose:

1. DAG of observable tasks with selective re-execution.
2. Parallel execution of independent steps with measurable speedup.
3. Dual-layer primitive model (pure-Python canonical + optional compiled C).
4. Astropy-ecosystem compatibility with planned upstream contributions.

## Architecture

Three strictly separated layers (see [docs/architecture.md](docs/architecture.md)):

```
src/spie_prototype/
├── core/   # pure-function primitives — no Prefect, no orchestration awareness
├── tasks/  # thin Prefect @task wrappers around core/ functions
└── flows/  # flow definitions — DAG composition only, no science logic
```

## Setup

```bash
uv sync                 # or: pip install -e .[dev]
```

Requires Python ≥ 3.10. PypeIt is imported, never vendored.

## Run

```bash
# Smoke test: trivial no-op flow (validates the Prefect environment)
python -m spie_prototype.flows.smoke

# LRIS flow triad (per-instrument CAL / Quicklook / Science — ADR 0006).
# Test frames currently live in the sibling lris2-drp checkout.
python -m spie_prototype.flows.lris.cal                                                   # build + cache masters
python -m spie_prototype.flows.lris.quicklook --input ../lris2-drp/data/lris2_flats --output out/

# Standalone tracing slice (building block / Phase 2 figure)
python -m spie_prototype.flows.tracing --input ../lris2-drp/data/lris2_flats --output out/

# Prefect dashboard
prefect server start     # then open http://localhost:4200
```

## Tests

```bash
pytest                   # primitives are tested with no orchestration running
```

## Docs

- [docs/context.md](docs/context.md) — the standing briefing (read first).
- [docs/architecture.md](docs/architecture.md) — the design the code lives by.
- [docs/plan.md](docs/plan.md) — volatile "what next" (read at session start).
- [docs/decisions/](docs/decisions/) — ADRs for significant choices.
