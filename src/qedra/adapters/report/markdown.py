"""Render a report as Markdown.

The prose stays plain and specific: a claim, the evidence behind it, and the WAF reference.
The report avoids the hedging and filler that mark machine-written text, by design.
"""

from __future__ import annotations

from qedra.domain.findings import Finding, Report, Verdict

_ICON = {
    Verdict.PROVEN: "PROVEN",
    Verdict.VIOLATED: "VIOLATED",
    Verdict.UNSUPPORTED: "UNSUPPORTED",
}


def to_markdown(report: Report) -> str:
    violations = report.violations()
    proven = report.proven()
    lines: list[str] = []
    lines.append(f"# qedra verification report: {report.architecture}")
    lines.append("")
    lines.append(
        f"{len(proven)} proven, {len(violations)} violated, "
        f"{len(report.findings)} properties checked."
    )
    lines.append("")

    if violations:
        lines.append("## Violations")
        lines.append("")
        for finding in violations:
            lines.extend(_finding_block(finding))
    else:
        lines.append("No violations. Every checked property is proven.")
        lines.append("")

    lines.append("## All findings")
    lines.append("")
    lines.append("| ID | Pillar | Property | Verdict | Severity |")
    lines.append("| --- | --- | --- | --- | --- |")
    for finding in report.findings:
        lines.append(
            f"| {finding.id} | {finding.pillar.value} | {finding.title} "
            f"| {_ICON[finding.verdict]} | {finding.severity.value} |"
        )
    lines.append("")
    return "\n".join(lines)


def _finding_block(finding: Finding) -> list[str]:
    block = [
        f"### {finding.id}: {finding.title}",
        "",
        f"- Pillar: {finding.pillar.value}",
        f"- Severity: {finding.severity.value}",
        f"- Target: {finding.target}",
        f"- Reference: {finding.waf_reference}",
        f"- Method: {finding.certificate.method}",
        "",
        finding.detail,
        "",
    ]
    cx = finding.certificate.counterexample
    if cx is not None:
        block.append(f"Counterexample: {cx.summary}")
        block.append("")
    return block
