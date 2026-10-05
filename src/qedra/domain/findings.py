"""Verdicts, findings, and the certificates that back them.

Every finding carries a machine-checkable certificate: a counterexample for a violation, or
a proof note for a verified property. A finding without a certificate cannot be constructed.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Pillar(StrEnum):
    RELIABILITY = "Reliability"
    SECURITY = "Security"
    COST = "Cost Optimization"
    OPERATIONAL = "Operational Excellence"
    PERFORMANCE = "Performance Efficiency"


class Verdict(StrEnum):
    PROVEN = "PROVEN"  # the property holds for every case; UNSAT of its negation
    VIOLATED = "VIOLATED"  # a concrete counterexample exists
    UNSUPPORTED = "UNSUPPORTED"  # the model lacks data to decide; reported, never hidden


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Counterexample(BaseModel):
    """A concrete witness that a property fails. For networking, an admissible packet."""

    model_config = ConfigDict(frozen=True)

    summary: str
    witness: dict[str, str] = Field(default_factory=dict)


class Certificate(BaseModel):
    """The evidence behind a verdict.

    For PROVEN, `proof` names the decision procedure and any minimal core. For VIOLATED,
    `counterexample` holds the witness the solver returned and qedra re-validated.
    """

    model_config = ConfigDict(frozen=True)

    method: str  # e.g. "Z3 SMT (bit-vector)" or "CTMC steady-state"
    proof: str | None = None
    counterexample: Counterexample | None = None


class Finding(BaseModel):
    """One checked property and its outcome."""

    model_config = ConfigDict(frozen=True)

    id: str
    pillar: Pillar
    title: str
    verdict: Verdict
    severity: Severity
    target: str
    waf_reference: str
    detail: str
    certificate: Certificate

    @property
    def passed(self) -> bool:
        return self.verdict is Verdict.PROVEN


class Report(BaseModel):
    """The result of a full verification run."""

    model_config = ConfigDict(frozen=True)

    architecture: str
    findings: tuple[Finding, ...] = ()

    def violations(self) -> list[Finding]:
        return [f for f in self.findings if f.verdict is Verdict.VIOLATED]

    def proven(self) -> list[Finding]:
        return [f for f in self.findings if f.verdict is Verdict.PROVEN]

    def exit_code(self) -> int:
        """0 when nothing is violated, 1 otherwise. Lets qedra gate a pipeline like a test."""
        return 1 if self.violations() else 0
