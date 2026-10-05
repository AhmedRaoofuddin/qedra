"""Continuous-time Markov chains for repairable redundancy groups.

A group of n identical instances, each failing at rate `failure_rate` and repaired at rate
`repair_rate`, is a birth-death chain over the number of healthy instances. Solving for the
stationary distribution gives steady-state availability without a closed-form shortcut, and
scales to models where the binomial assumption breaks (for example a shared repair channel).
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

Matrix = npt.NDArray[np.float64]
Vector = npt.NDArray[np.float64]


def steady_state(generator: Matrix) -> Vector:
    """Solve pi @ Q = 0 with sum(pi) = 1 for a CTMC generator matrix Q.

    Replaces one balance equation with the normalisation constraint, then solves the
    resulting linear system. Raises if the chain is not a valid generator.
    """
    q = np.asarray(generator, dtype=np.float64)
    n = q.shape[0]
    if q.shape != (n, n):
        raise ValueError("generator must be square")
    if not np.allclose(q.sum(axis=1), 0.0, atol=1e-9):
        raise ValueError("generator rows must sum to zero")

    a = q.T.copy()
    a[-1, :] = 1.0  # replace last balance equation with normalisation
    b = np.zeros(n, dtype=np.float64)
    b[-1] = 1.0
    pi = np.linalg.solve(a, b)
    if np.any(pi < -1e-9):
        raise ValueError("negative stationary probability; check the rates")
    return np.clip(pi, 0.0, 1.0)


def redundancy_group_generator(
    instances: int, failure_rate: float, repair_rate: float, *, shared_repair: bool = False
) -> Matrix:
    """Build the generator for a birth-death chain over the number of healthy instances.

    State j (0..n) is the count of healthy instances. With independent repair, repair rate
    from state j is (n - j) * repair_rate; with a single shared repair channel it is
    repair_rate whenever at least one instance is down.
    """
    if instances < 1:
        raise ValueError("instances must be >= 1")
    n = instances
    q = np.zeros((n + 1, n + 1), dtype=np.float64)
    for healthy in range(n + 1):
        down = n - healthy
        fail = healthy * failure_rate  # a healthy instance fails
        repair = repair_rate if (shared_repair and down > 0) else down * repair_rate
        if healthy > 0:
            q[healthy, healthy - 1] = fail
        if down > 0:
            q[healthy, healthy + 1] = repair
        q[healthy, healthy] = -(fail + repair)
    return q


def group_availability_ctmc(
    instances: int,
    required: int,
    failure_rate: float,
    repair_rate: float,
    *,
    shared_repair: bool = False,
) -> float:
    """Steady-state probability that at least `required` of `instances` are healthy."""
    if required > instances:
        raise ValueError("required cannot exceed instances")
    q = redundancy_group_generator(
        instances, failure_rate, repair_rate, shared_repair=shared_repair
    )
    pi = steady_state(q)
    # pi index == number of healthy instances.
    return float(pi[required:].sum())
