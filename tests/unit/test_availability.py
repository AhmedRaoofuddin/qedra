from qedra.domain.ir.model import Component, DependencyModel
from qedra.engines.reliability.availability import (
    AvailabilityProver,
    component_availability,
    system_availability,
)


def test_single_instance_uses_given_availability() -> None:
    c = Component(name="x", instance_availability=0.999)
    assert component_availability(c) == 0.999


def test_k_of_n_binomial() -> None:
    # Two instances, need one, each 99%: 1 - 0.01^2 = 0.9999.
    c = Component(name="x", instances=2, required=1, instance_availability=0.99)
    assert abs(component_availability(c) - 0.9999) < 1e-12


def test_system_availability_is_product() -> None:
    model = DependencyModel(
        components=(
            Component(name="a", instance_availability=0.99),
            Component(name="b", instance_availability=0.995),
        )
    )
    assert abs(system_availability(model) - 0.99 * 0.995) < 1e-12


def test_prover_detects_shortfall() -> None:
    model = DependencyModel(components=(Component(name="a", instance_availability=0.99),))
    result = AvailabilityProver().prove_at_least(model, 0.9999)
    assert result.meets is False
    assert result.downtime_minutes_per_month > 0


def test_prover_accepts_redundant_design() -> None:
    model = DependencyModel(
        components=(
            Component(name="gw", instances=2, required=1, instance_availability=0.9995),
            Component(name="app", instances=3, required=1, instance_availability=0.99),
            Component(name="db", instances=2, required=1, instance_availability=0.9995),
        )
    )
    result = AvailabilityProver().prove_at_least(model, 0.9999)
    assert result.meets is True


def test_rates_derive_availability() -> None:
    c = Component(name="x", failure_rate=0.001, repair_rate=0.999)
    assert abs(component_availability(c) - 0.999) < 1e-9


def test_required_cannot_exceed_instances() -> None:
    try:
        Component(name="x", instances=1, required=2, instance_availability=0.99)
    except ValueError:
        return
    raise AssertionError("expected ValueError when required > instances")
