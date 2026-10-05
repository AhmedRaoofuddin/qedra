from pathlib import Path

from qedra.adapters.ingest import load_architecture
from qedra.adapters.report import to_json, to_markdown
from qedra.application.policy import Policy
from qedra.application.verify import verify

EXAMPLES = Path(__file__).parents[2] / "examples"


def _report(name: str):  # type: ignore[no-untyped-def]
    arch = load_architecture(EXAMPLES / name / "architecture.yaml")
    return verify(arch, Policy.baseline())


def test_markdown_lists_violations_for_flawed() -> None:
    md = to_markdown(_report("contoso-flawed"))
    assert "# qedra verification report: contoso-flawed" in md
    assert "## Violations" in md
    assert "SEC-001" in md
    assert "Counterexample" in md
    assert "| ID | Pillar |" in md  # the summary table header


def test_markdown_clean_for_secure() -> None:
    md = to_markdown(_report("contoso-secure"))
    assert "No violations" in md


def test_json_is_valid_and_contains_certificate() -> None:
    import json

    data = json.loads(to_json(_report("contoso-flawed")))
    assert data["architecture"] == "contoso-flawed"
    sec = next(f for f in data["findings"] if f["id"] == "SEC-001")
    assert sec["verdict"] == "VIOLATED"
    assert sec["certificate"]["counterexample"]["witness"]["destination_port"] == "1433"
