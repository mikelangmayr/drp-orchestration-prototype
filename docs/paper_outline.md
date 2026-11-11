# Paper Outline (stub)

Section structure and figure inventory for the SPIE paper. This is a working
skeleton; prose is drafted in Phase 8 (see `docs/plan.md`). Section order for
drafting differs from presentation order — body first, intro/conclusion last.

## Sections

1. **Introduction.** The problem: rising data volumes, complex configurations,
   reproducibility needs vs. script-driven DRPs. The LRIS-2 context.
2. **Background.** Astronomical DRPs today; what "script-driven" costs in
   monitoring/debugging/extension. Brief orchestration primer for an
   instrumentation audience (assume no Prefect/Airflow familiarity).
3. **Instrument & data.** LRIS-2 overview; LRIS-1 (`keck_lris_red`) as a proxy
   for commissioning data; the test frames used.
4. **Architecture.** Transcribed from `docs/architecture.md`: three-layer model,
   primitive contract, task wrapping, caching, flow composition, polyglot
   primitives, failure handling, observability. Answers "why not Airflow?" and
   "why not just PypeIt?".
5. **Selective re-execution.** Claim 2. Cache fingerprinting; Flow B before/after.
6. **Dual-layer primitives.** Claim 4. Pure-Python canonical + optional compiled
   C; automatic backend selection. (Parked in code until the orchestration story
   lands; see `docs/plan.md`.)
7. **Parallelism & performance.** Claim 3. Serial vs concurrent timing; task
   runner comparison.
8. **Resilience.** Flow C: graceful failure across a batch; the script-driven
   counterfactual.
9. **Open-source intent.** Astropy-ecosystem compatibility; planned upstream
   contributions (`trace_from_array` to PypeIt; functional refactors to PyReduce).
10. **Conclusion.** A reusable template for other instruments/observatories.

## Figure inventory

Figure IDs are referenced by `docs/plan.md` capture tasks.

- **F4** — Flow A dashboard screenshot during a reduction (claim 1).
- **F7** — Flow A DAG visualization (claim 1).
- **F8** — Flow B dashboard before/after selective re-execution (claim 2).
- **F9** — Flow B timing comparison: cache hit vs full recompute (claim 2).
- **F10** — Flow C dashboard view: one failed frame, rest complete (resilience).
- **F11** — Serial vs parallel timing across N frames and task runners (claim 3).

## Predictable reviewer questions to answer explicitly

- *Why not just use Airflow/Dagster?* — DRP-appropriate caching/fingerprinting,
  in-process primitive composition, lighter operational footprint for an
  observatory; addressed in §4.
- *Why not just use PypeIt directly?* — no single library has all needed
  primitives in the desired form; the orchestration substrate is what composes
  the best primitive from each library under one DAG (§4 polyglot primitives).
