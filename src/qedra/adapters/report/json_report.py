"""The JSON proof database: the machine-readable source of truth for a run."""

from __future__ import annotations

from qedra.domain.findings import Report


def to_json(report: Report, *, indent: int = 2) -> str:
    return report.model_dump_json(indent=indent)
