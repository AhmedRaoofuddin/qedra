from pathlib import Path

from typer.testing import CliRunner

from qedra.cli.app import app

runner = CliRunner()
EXAMPLES = Path(__file__).parents[2] / "examples"


def test_verify_secure_exits_zero() -> None:
    result = runner.invoke(app, ["verify", str(EXAMPLES / "contoso-secure")])
    assert result.exit_code == 0
    assert "proven" in result.stdout.lower()


def test_verify_flawed_exits_one() -> None:
    result = runner.invoke(app, ["verify", str(EXAMPLES / "contoso-flawed")])
    assert result.exit_code == 1
    assert "VIOLATED" in result.stdout


def test_explain_shows_counterexample() -> None:
    result = runner.invoke(app, ["explain", str(EXAMPLES / "contoso-flawed"), "SEC-001"])
    assert result.exit_code == 0
    assert "Counterexample" in result.stdout
    assert "1433" in result.stdout


def test_json_output_written(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    result = runner.invoke(app, ["verify", str(EXAMPLES / "contoso-flawed"), "--json", str(out)])
    assert result.exit_code == 1
    assert out.exists()
    assert "VIOLATED" in out.read_text(encoding="utf-8")


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "qedra" in result.stdout
