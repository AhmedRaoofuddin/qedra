import pytest

from qedra.application.policy import Policy, parse_availability_target


def test_parse_availability_target() -> None:
    assert parse_availability_target(">= 99.99%") == pytest.approx(0.9999)
    assert parse_availability_target(">=99.9%") == pytest.approx(0.999)


def test_parse_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_availability_target("four nines")


def test_baseline_has_both_pillars() -> None:
    policy = Policy.baseline()
    assert policy.security is not None
    assert policy.security.no_internet_inbound is not None
    assert "data" in policy.security.no_internet_inbound.tiers
    assert policy.reliability is not None
    assert policy.reliability.availability_target() == pytest.approx(0.9999)


def test_from_yaml_roundtrip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    text = """
name: custom
security:
  no_internet_inbound:
    tiers: [data, mgmt]
reliability:
  availability: ">= 99.95%"
"""
    path = tmp_path / "p.qedra.yaml"
    path.write_text(text, encoding="utf-8")
    policy = Policy.from_yaml(path)
    assert policy.name == "custom"
    assert policy.security.no_internet_inbound.tiers == ["data", "mgmt"]  # type: ignore[union-attr]
    assert policy.reliability.availability_target() == pytest.approx(0.9995)  # type: ignore[union-attr]
