"""Flow definitions.

A flow is a wiring diagram: ``.submit()`` calls that build the DAG, with
``.result()`` only where data must materialize for control flow. Flows contain
no reduction logic and never nest task-calling-task. See
``docs/architecture.md`` §"Flow composition".
"""
