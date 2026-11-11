# Project Context

The standing briefing on what this project is and why it exists. Read after
`CLAUDE.md` at session start. Update this file when the framing evolves.

## What we're building

A prototype data reduction pipeline (DRP) for the LRIS-2 instrument at the
W. M. Keck Observatory, built to demonstrate that modern workflow orchestration
(Prefect) can replace the script-driven design pattern that dominates current
astronomical DRPs.

The prototype itself is **a slice**, not the full LRIS-2 DRP. It exists to back
the engineering claims in a SPIE paper. The production LRIS-2 DRP will be a
larger, separately scoped project that builds on the patterns established here.

## The SPIE abstract — what we have committed to

Submitted and locked. The paper and 15–20 minute talk must defend these four
claims:

1. **Orchestration as DAG of observable tasks.** The pipeline is a directed
   acyclic graph in which each reduction step is a task with explicit state, full
   parameter visibility, and inspectable intermediate products. Real-time state
   is surfaced through a centralized dashboard, replacing ad-hoc log inspection.

2. **Selective re-execution.** Changing parameters or inputs to one step
   re-runs only that step and its downstream dependencies, with upstream results
   served from cache. This is the developer-productivity claim and probably our
   single most compelling figure.

3. **Parallel execution with consistent gains.** Independent steps run
   concurrently with no change to scientific logic. We have measurable timing
   numbers comparing serial and parallel runs across N frames.

4. **Dual-layer primitive model.** Pure-Python canonical implementations are
   the reference; optional compiled C primitives accelerate critical inner loops
   without changing scientific results. Backend selection is automatic.

Plus two framing commitments that thread through all four:

- **Astropy ecosystem compatibility,** with planned upstream contributions to
  the broader scientific Python stack.
- **Reproducibility across environments** — same code, same results, anywhere.

## The full submitted abstract

> Modern astronomical data reduction pipelines must handle increasing data
> volumes, complex instrument configurations, and the need for reproducibility
> across diverse computing environments. While most existing DRPs work effectively
> within their intended scope, they often rely on script-driven designs that can
> make monitoring, debugging, or extending them challenging as instruments and
> data rates evolve. As part of the development of the LRIS-2 instrument data
> reduction pipeline for the W. M. Keck Observatory, we introduce a new
> architecture that adapts mature data-engineering methodologies, particularly
> workflow orchestration by tools like Prefect, to enable a more transparent,
> modular, and resilient reduction system.
>
> The pipeline is built as a directed acyclic graph (DAG) of observable tasks,
> each with full state awareness. This structure enables selective re-execution
> of individual reduction steps without recomputing the entire workflow. Real-time
> task state, parameter values, intermediate products, and logs are exposed
> through a centralized dashboard, eliminating reliance on ad-hoc log inspection.
> Parallel execution of independent steps provides consistent performance gains
> with no change to scientific logic.
>
> To improve performance while maintaining accessibility, the pipeline implements
> a dual-layer primitive model: a canonical pure Python implementation for
> readability and portability, and an optional set of compiled C primitives that
> accelerate critical inner loops. The system automatically selects the fastest
> available backend, ensuring identical scientific results across environments
> while allowing sites to opt into performance enhancements. To promote
> sustainability and encourage shared maintenance, the scientific primitives are
> designed for compatibility with the Astropy ecosystem, with planned upstream
> contributions to support broader community adoption.
>
> Combining modern orchestration, transparent state management, modular
> primitives, and optional compiled acceleration, provides a flexible template
> that can be adopted by other instruments and observatories. It bridges the gap
> between traditional DRPs and contemporary data-science workflows, offering a
> sustainable path toward reproducible, maintainable, and scalable reduction
> systems.

## Architectural shape

The pipeline is structured in three concentric layers, reflected directly in
the repository layout:

- **`core/` — primitives.** Pure-function scientific operations. Bias subtraction,
  flat normalization, slit tracing, wavelength calibration, extraction. These are
  sourced where appropriate from existing libraries — currently PypeIt's
  `EdgeTraceSet` for slit tracing, with PyReduce primitives expected for
  bias/flat/normalize/extract. The orchestration layer is **primitive-agnostic**:
  primitives can come from PypeIt, PyReduce, ccdproc, specreduce, or custom
  code, and compose under a single task interface. This polyglot composition
  is itself a load-bearing architectural claim in the paper.

- **`tasks/` — Prefect task wrappers.** Each `core/` function becomes a `@task`
  with logging, caching, and retry policy. Wrappers are thin and uniform.

- **`flows/` — flow definitions.** The DAG. Flows wire tasks together, define
  parallelism boundaries, and select task runners (concurrent for I/O-bound,
  process pool for CPU-bound).

The boundary between layers is strict. See `CLAUDE.md` for the rules.

## The example flows the paper will demonstrate

Three flows, each pointed at a specific abstract claim:

- **Flow A — Happy path, end-to-end.** A reduction runs through the full DAG
  (currently: tracing + stub bias/dark; eventually: bias → dark → flat →
  cosmic-ray → extraction → wavelength → flux). Demonstrates DAG shape,
  parallelism between calibration arms, and the Prefect dashboard during a
  reduction. Baseline figure for the paper.

- **Flow B — Selective re-execution.** Process a batch with one set of
  parameters; modify a parameter; re-run. The dashboard shows upstream tasks
  served from cache and only downstream steps re-executing, with timing. This is
  the developer-productivity demonstration and the single most compelling figure.

- **Flow C — Graceful failure across a batch.** Process N frames concurrently
  with one frame containing a corrupt header. The bad frame fails with full
  context; the others complete normally. Demonstrates resilience and operator
  visibility — the script-driven contrast is "the batch halts or silently
  corrupts."

A fourth flow (provenance-driven re-execution: a new master bias triggers
identification and re-running of all dependent reductions) is on the wish list
but parked.

## The primitive sources

- **PypeIt** (BSD-3, `pip install`). Provides slit tracing via `EdgeTraceSet`.
  Already integrated. Already supports LRIS-1 (`keck_lris_red`, `keck_lris_blue`)
  which we use as a proxy until LRIS-2 spectrograph definitions are available.
  Active team, responsive on Slack, recent precedent for "build on PypeIt
  primitives and publish the architecture" in Carvalho et al. 2024 (NIRSPEC).
  Likely upstream contribution: a clean `trace_from_array()` entry point that
  doesn't require constructing a `TraceImage` manually.

- **PyReduce** (MIT, `pip install`). Provides bias, flat, normalization,
  wavelength calibration, and extraction primitives in a clean step-class pattern.
  Not yet integrated. Caveat: in-place mutation in some steps (curvature
  determination updates traces in place) needs functional refactoring before
  Prefect wrapping. That refactor is a candidate upstream contribution.

- **Custom.** LRIS-2-specific glue and anything neither PypeIt nor PyReduce
  provides cleanly. Kept minimal.

## What's currently working

(Snapshot — verify against `docs/plan.md` for current state)

- PypeIt slit tracing wrapped as a `core/` primitive (numpy in, numpy out).
- Prefect task wrappers for tracing, FITS loading, edge saving, QA plot.
- A basic flow that traces all FITS files in an input directory concurrently.
- The architectural separation (`core/` / `tasks/` / `flows/`) is in place.

## What's missing

(Snapshot — verify against `docs/plan.md` for current state)

- Caching policies on tasks (selective re-execution is not yet demonstrable).
- Bias and dark stub tasks (DAG has no parallel arms yet).
- Flow B (selective re-execution demo) and Flow C (graceful failure demo).
- Benchmark harness for serial-vs-parallel timing figures.
- Dashboard screenshot capture script.
- C primitives. **Parked until the orchestration story is complete.**
- Multi-frame DAG depth. Currently only the tracing slice is real.

## The paper

- Venue: SPIE (likely Astronomical Telescopes + Instrumentation).
- Page count: target 8–15 pages, two-column LaTeX, SPIE template (`spie.cls`).
- Talk: 15–20 minutes including Q&A buffer.
- Author list: confirm with the LRIS-2 instrument team before submission.

See `docs/paper_outline.md` for the section structure and figure list.

## The audience

SPIE Astronomical Instrumentation reviewers and attendees are instrument
engineers and observational astronomers. They are sophisticated about
instrumentation and DRPs, but most are **not** data engineers and will not be
familiar with Prefect, Airflow, Dagster, or the orchestration patterns from the
broader software industry. The paper must bridge that gap without condescension
— assume technical maturity, do not assume domain overlap.

The paper should explicitly answer "why not just use Airflow?" and "why not
just use PypeIt directly?" Both are predictable reviewer questions.

## Non-goals

- This repo is not the production LRIS-2 DRP and should not be treated as one.
- We are not building a general-purpose DRP framework. Generalization is implied
  by the architecture; the implementation is focused on LRIS-2 specifically.
- We are not rewriting PypeIt or PyReduce. We use their primitives and
  contribute upstream where useful.

## How to use this document

Read at session start, after `CLAUDE.md`. If the framing of any of the four
abstract commitments changes, or if a non-goal becomes a goal, this is the
file that gets updated first. Other docs follow from this one.
