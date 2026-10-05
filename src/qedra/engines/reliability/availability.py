"""Composite availability over a dependency model.

Serial components multiply: the system needs all of them. Redundancy inside a component is
combined either in closed form (independent instances, binomial k-of-n) or with a CTMC when
failure and repair rates are given. The result feeds a simple availability property check.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import comb

from qedra.domain.ir.model import Component, DependencyModel
from qedra.engines.reliability.ctmc import group_availability_ctmc


def _instance_availability(component: Component) -> float:
    if component.instance_availability is not None:
        return component.instance_availability
    assert component.failure_rate is not None and component.repair_rate is not None
    return component.repair_rate / (component.failure_rate + component.repair_rate)


def _binomial_k_of_n(instances: int, required: int, avail: float) -> float:
    return sum(
        comb(instances, i) * (avail**i) * ((1.0 - avail) ** (instances - i))
        for i in range(required, instances + 1)
    )


def component_availability(component: Component) -> float:
    """Availability of a single component including its internal redundancy."""
    if component.instances == 1:
        return _instance_availability(component)
    if component.failure_rate is not None and component.repair_rate is not None:
        return group_availability_ctmc(
            component.instances,
            component.required,
            component.failure_rate,
            component.repair_rate,
        )
    return _binomial_k_of_n(
        component.instances, component.required, _instance_availability(component)
    )


def system_availability(model: DependencyModel) -> float:
    """Composite availability: the product across serially dependent components."""
    result = 1.0
    for component in model.components:
        result *= component_availability(component)
    return result


@dataclass(frozen=True, slots=True)
class AvailabilityResult:
    """Outcome of an availability property check."""

    achieved: float
    target: float
    meets: bool
    per_component: dict[str, float]

    @property
    def achieved_nines(self) -> str:
        """Availability rendered as a percentage, for example 99.9500%."""
        return f"{self.achieved * 100:.4f}%"

    @property
    def downtime_minutes_per_month(self) -> float:
        return (1.0 - self.achieved) * 30 * 24 * 60


class AvailabilityProver:
    """Checks whether a dependency model meets an availability target."""

    def prove_at_least(self, model: DependencyModel, target: float) -> AvailabilityResult:
        if not 0.0 < target < 1.0:
            raise ValueError("target must be a probability strictly between 0 and 1")
        per_component = {c.name: component_availability(c) for c in model.components}
        achieved = 1.0
        for value in per_component.values():
            achieved *= value
        return AvailabilityResult(
            achieved=achieved,
            target=target,
            meets=achieved >= target,
            per_component=per_component,
        )
