"""The qedra CLI.

qedra behaves like a compiler for architecture: it reads a model and a policy, proves each
property, prints the verdicts, and exits non-zero when any property is violated, so it gates a
pipeline the same way a test suite does.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from qedra import __version__
from qedra.adapters.ingest import load_architecture
from qedra.adapters.report import to_json, to_markdown
from qedra.application.policy import Policy
from qedra.application.verify import verify as run_verify
from qedra.domain.findings import Report, Verdict

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Prove Azure Well-Architected properties with an SMT solver.",
)
console = Console()
err_console = Console(stderr=True)

_VERDICT_STYLE = {
    Verdict.PROVEN: "bold green",
    Verdict.VIOLATED: "bold red",
    Verdict.UNSUPPORTED: "bold yellow",
}


@app.command()
def verify(
    path: Path = typer.Argument(..., help="Architecture file or directory (native YAML or ARM)."),
    policy: Path | None = typer.Option(
        None, "--policy", "-p", help="Policy file. Defaults to the built-in WAF baseline."
    ),
    json_out: Path | None = typer.Option(
        None, "--json", help="Write the JSON proof database to this path."
    ),
    markdown_out: Path | None = typer.Option(
        None, "--markdown", help="Write the Markdown report to this path."
    ),
) -> None:
    """Prove an architecture against a policy. Exit 0 if all properties hold, 1 otherwise."""
    report = _run(path, policy)
    _print_report(report)
    if json_out is not None:
        json_out.write_text(to_json(report), encoding="utf-8")
        console.print(f"Wrote JSON proof database to [cyan]{json_out}[/cyan]")
    if markdown_out is not None:
        markdown_out.write_text(to_markdown(report), encoding="utf-8")
        console.print(f"Wrote Markdown report to [cyan]{markdown_out}[/cyan]")
    raise typer.Exit(code=report.exit_code())


@app.command()
def explain(
    path: Path = typer.Argument(..., help="Architecture file or directory."),
    finding_id: str = typer.Argument(..., help="The finding id to explain, for example SEC-001."),
    policy: Path | None = typer.Option(None, "--policy", "-p"),
) -> None:
    """Show the full certificate, proof note, or counterexample for one finding."""
    report = _run(path, policy)
    match = next((f for f in report.findings if f.id == finding_id), None)
    if match is None:
        err_console.print(f"No finding with id {finding_id!r}")
        raise typer.Exit(code=2)
    lines = [
        f"{match.id}: {match.title}",
        "",
        f"Verdict:   {match.verdict.value}",
        f"Pillar:    {match.pillar.value}",
        f"Severity:  {match.severity.value}",
        f"Target:    {match.target}",
        f"Reference: {match.waf_reference}",
        f"Method:    {match.certificate.method}",
        "",
        match.detail,
    ]
    if match.certificate.proof:
        lines += ["", f"Proof: {match.certificate.proof}"]
    if match.certificate.counterexample:
        cx = match.certificate.counterexample
        lines += ["", f"Counterexample: {cx.summary}"]
        lines += [f"  {k}: {v}" for k, v in cx.witness.items()]
    # Plain output so the certificate is captured reliably in any terminal or pipeline.
    typer.echo("\n".join(lines))


@app.command()
def init(
    path: Path = typer.Option(
        Path("waf-baseline.qedra.yaml"), "--out", "-o", help="Where to write the policy."
    ),
) -> None:
    """Write a starter policy file you can version next to your infrastructure."""
    import yaml

    policy = Policy.baseline()
    path.write_text(yaml.safe_dump(policy.model_dump(exclude_none=True), sort_keys=False), "utf-8")
    console.print(f"Wrote baseline policy to [cyan]{path}[/cyan]")


@app.command()
def version() -> None:
    """Print the qedra version."""
    console.print(f"qedra {__version__}")


def _run(path: Path, policy_path: Path | None) -> Report:
    try:
        architecture = load_architecture(path)
    except (FileNotFoundError, ValueError) as exc:
        err_console.print(f"[red]Failed to load architecture:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    policy = Policy.from_yaml(policy_path) if policy_path else Policy.baseline()
    return run_verify(architecture, policy)


def _print_report(report: Report) -> None:
    table = Table(title=f"qedra: {report.architecture}", show_lines=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Pillar")
    table.add_column("Property")
    table.add_column("Verdict")
    table.add_column("Severity")
    for finding in report.findings:
        table.add_row(
            finding.id,
            finding.pillar.value,
            finding.title,
            f"[{_VERDICT_STYLE[finding.verdict]}]{finding.verdict.value}[/]",
            finding.severity.value,
        )
    console.print(table)

    for finding in report.violations():
        cx = finding.certificate.counterexample
        detail = f"\n\n[dim]Counterexample:[/dim] {cx.summary}" if cx else ""
        console.print(
            Panel(
                f"{finding.detail}{detail}\n\n[dim]Reference:[/dim] {finding.waf_reference}",
                title=f"[red]{finding.id}  {finding.title}[/red]",
                border_style="red",
            )
        )

    proven = len(report.proven())
    violated = len(report.violations())
    summary = f"{proven} proven, {violated} violated, {len(report.findings)} checked"
    style = "green" if violated == 0 else "red"
    console.print(Panel(summary, border_style=style, title="Result"))


if __name__ == "__main__":
    app()
