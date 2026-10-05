"""The verification pipeline: architecture plus policy produces a report of findings.

Each finding binds a verdict to a certificate the engines produced. The pipeline holds no
heuristics; it routes each policy clause to the engine that decides it and records the result.
"""

from __future__ import annotations

from qedra.application.policy import Policy
from qedra.domain.findings import (
    Certificate,
    Counterexample,
    Finding,
    Pillar,
    Report,
    Severity,
    Verdict,
)
from qedra.domain.ir.model import Architecture
from qedra.domain.nsg_eval import sensitive_port_ranges
from qedra.engines.reliability import AvailabilityProver
from qedra.engines.smt import NetworkReachabilityProver

_WAF_SE08 = "WAF Security SE:08 (segment and isolate; keep data stores off the public internet)"
_WAF_RE04 = "WAF Reliability RE:04 (define and meet availability targets through redundancy)"


def verify(architecture: Architecture, policy: Policy) -> Report:
    """Run every applicable property and collect the findings."""
    findings: list[Finding] = []
    findings.extend(_verify_internet_isolation(architecture, policy))
    findings.extend(_verify_availability(architecture, policy))
    return Report(architecture=architecture.name, findings=tuple(findings))


def _verify_internet_isolation(arch: Architecture, policy: Policy) -> list[Finding]:
    if policy.security is None or policy.security.no_internet_inbound is None:
        return []
    prover = NetworkReachabilityProver(vnet_prefixes=arch.network.vnet_prefixes())
    findings: list[Finding] = []
    counter = 0
    for tier in policy.security.no_internet_inbound.tiers:
        subnets = arch.network.subnets_in_tier(tier)
        for subnet in subnets:
            counter += 1
            result = prover.prove_no_internet_inbound(subnet, ports=sensitive_port_ranges())
            if result.reachable:
                assert result.witness is not None
                findings.append(
                    Finding(
                        id=f"SEC-{counter:03d}",
                        pillar=Pillar.SECURITY,
                        title=f"Public internet can reach the {tier} tier subnet {subnet.name!r}",
                        verdict=Verdict.VIOLATED,
                        severity=Severity.CRITICAL,
                        target=f"subnet/{subnet.name}",
                        waf_reference=_WAF_SE08,
                        detail=(
                            "The effective NSG admits an inbound TCP packet sourced from a "
                            "public address on a sensitive port. A data-tier subnet must deny "
                            "all internet-sourced inbound traffic."
                        ),
                        certificate=Certificate(
                            method="Z3 SMT (bit-vector)",
                            counterexample=Counterexample(
                                summary=(
                                    f"{result.witness['source_ip']} -> "
                                    f"{result.witness['destination_ip']}:"
                                    f"{result.witness['destination_port']}/"
                                    f"{result.witness['protocol']} is admitted"
                                ),
                                witness=result.witness,
                            ),
                        ),
                    )
                )
            else:
                findings.append(
                    Finding(
                        id=f"SEC-{counter:03d}",
                        pillar=Pillar.SECURITY,
                        title=(
                            f"The {tier} tier subnet {subnet.name!r} rejects all internet inbound"
                        ),
                        verdict=Verdict.PROVEN,
                        severity=Severity.INFO,
                        target=f"subnet/{subnet.name}",
                        waf_reference=_WAF_SE08,
                        detail="No public-internet packet satisfies the NSG decision function.",
                        certificate=Certificate(
                            method="Z3 SMT (bit-vector)", proof=result.proof_note
                        ),
                    )
                )
    return findings


def _verify_availability(arch: Architecture, policy: Policy) -> list[Finding]:
    if policy.reliability is None:
        return []
    target = policy.reliability.availability_target()
    if target is None:
        return []
    if arch.reliability is None:
        return [
            Finding(
                id="REL-001",
                pillar=Pillar.RELIABILITY,
                title="Availability target cannot be decided",
                verdict=Verdict.UNSUPPORTED,
                severity=Severity.MEDIUM,
                target=arch.name,
                waf_reference=_WAF_RE04,
                detail="The architecture carries no dependency model, so availability is unknown.",
                certificate=Certificate(method="CTMC steady-state", proof="no reliability model"),
            )
        ]
    result = AvailabilityProver().prove_at_least(arch.reliability, target)
    breakdown = ", ".join(
        f"{name} {value * 100:.4f}%" for name, value in result.per_component.items()
    )
    if result.meets:
        return [
            Finding(
                id="REL-001",
                pillar=Pillar.RELIABILITY,
                title=f"Composite availability meets the {policy.reliability.availability} target",
                verdict=Verdict.PROVEN,
                severity=Severity.INFO,
                target=arch.name,
                waf_reference=_WAF_RE04,
                detail=(
                    f"Composite availability {result.achieved_nines} "
                    f"(~{result.downtime_minutes_per_month:.1f} min/month downtime). "
                    f"Components: {breakdown}."
                ),
                certificate=Certificate(
                    method="CTMC steady-state",
                    proof=f"serial composition of per-component availabilities: {breakdown}",
                ),
            )
        ]
    return [
        Finding(
            id="REL-001",
            pillar=Pillar.RELIABILITY,
            title=(
                "Composite availability falls short of the "
                f"{policy.reliability.availability} target"
            ),
            verdict=Verdict.VIOLATED,
            severity=Severity.HIGH,
            target=arch.name,
            waf_reference=_WAF_RE04,
            detail=(
                f"Composite availability {result.achieved_nines} "
                f"(~{result.downtime_minutes_per_month:.1f} min/month downtime), "
                f"below the required {target * 100:.4f}%. Components: {breakdown}."
            ),
            certificate=Certificate(
                method="CTMC steady-state",
                counterexample=Counterexample(
                    summary=f"achieved {result.achieved_nines} < target {target * 100:.4f}%",
                    witness={name: f"{value:.6f}" for name, value in result.per_component.items()},
                ),
            ),
        )
    ]
