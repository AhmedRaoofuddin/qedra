from math import comb

import numpy as np

from qedra.engines.reliability.ctmc import (
    group_availability_ctmc,
    redundancy_group_generator,
    steady_state,
)


def test_generator_rows_sum_to_zero() -> None:
    q = redundancy_group_generator(3, failure_rate=0.01, repair_rate=1.0)
    assert np.allclose(q.sum(axis=1), 0.0)


def test_two_state_steady_state_matches_closed_form() -> None:
    # A single repairable instance: availability = mu / (lambda + mu).
    lam, mu = 0.001, 0.1
    avail = group_availability_ctmc(1, 1, lam, mu)
    assert abs(avail - mu / (lam + mu)) < 1e-12


def test_ctmc_matches_binomial_for_independent_repair() -> None:
    # With independent repair, the k-of-n CTMC equals the binomial closed form.
    lam, mu = 0.01, 2.0
    a = mu / (lam + mu)
    n, k = 3, 1
    expected = sum(comb(n, i) * a**i * (1 - a) ** (n - i) for i in range(k, n + 1))
    assert abs(group_availability_ctmc(n, k, lam, mu) - expected) < 1e-9


def test_redundancy_improves_availability() -> None:
    lam, mu = 0.05, 1.0
    single = group_availability_ctmc(1, 1, lam, mu)
    dual = group_availability_ctmc(2, 1, lam, mu)
    assert dual > single


def test_steady_state_rejects_bad_generator() -> None:
    bad = np.array([[1.0, 0.0], [0.0, 1.0]])
    try:
        steady_state(bad)
    except ValueError:
        return
    raise AssertionError("expected ValueError for non-generator matrix")
