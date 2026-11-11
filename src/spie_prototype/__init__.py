"""SPIE prototype: orchestration-pattern slice of the LRIS-2 DRP.

Three strictly separated layers:

- ``spie_prototype.core``  — pure-function scientific primitives (no Prefect).
- ``spie_prototype.tasks`` — thin Prefect ``@task`` wrappers around primitives.
- ``spie_prototype.flows`` — flow definitions that wire tasks into the DAG.

See ``docs/context.md`` and ``docs/plan.md`` for the briefing and roadmap.
"""

__version__ = "0.1.0"
