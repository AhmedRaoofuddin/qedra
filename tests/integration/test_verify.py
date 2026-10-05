from pathlib import Path

from qedra.adapters.ingest import load_architecture
from qedra.application.policy import Policy
from qedra.application.verify import verify
from qedra.domain.findings import Verdict

EXAMPLES = Path(__file__).parents[2] / "examples"


def _verify(name: str):  # type: ignore[no-untyped-def]
    arch = load_architecture(EXAMPLES / name / "architecture.yaml")
    return verify(arch, Policy.baseline())


def test_secure_example_fully_proven() -> None:
    report = _verify("contoso-secure")
    assert report.exit_code() == 0
    assert all(f.verdict is Verdict.PROVEN for f in report.findings)
    assert {f.id for f in report.findings} == {"SEC-001", "REL-001"}


def test_flawed_example_has_two_violations() -> None:
    report = _verify("contoso-flawed")
    assert report.exit_code() == 1
    by_id = {f.id: f for f in report.findings}
    assert by_id["SEC-001"].verdict is Verdict.VIOLATED
    assert by_id["REL-001"].verdict is Verdict.VIOLATED
    # The security counterexample must be a real, validated packet into the data subnet.
    cx = by_id["SEC-001"].certificate.counterexample
    assert cx is not None
    assert cx.witness["destination_port"] == "1433"


def test_arm_example_flags_exposure() -> None:
    arch = load_architecture(EXAMPLES / "contoso-arm")
    report = verify(arch, Policy.baseline())
    sec = next(f for f in report.findings if f.id == "SEC-001")
    assert sec.verdict is Verdict.VIOLATED
