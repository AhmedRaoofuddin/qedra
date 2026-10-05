# The reliability engine: composite availability with a CTMC

qedra computes the availability of a workload from its dependency model and proves whether it
meets a target. The engine combines closed-form composition with a continuous-time Markov chain
(CTMC) for redundancy groups.

## Composition

A workload is modelled as serially dependent components; the system needs all of them. Serial
composition multiplies component availabilities:

```
A_system = A_1 × A_2 × ... × A_n
```

A single weak component therefore caps the whole system, which is why a lone non-redundant tier
shows up immediately as the limiting factor.

## Redundancy within a component

A component can run several instances with a k-of-n requirement (need `k` of `n` healthy). Two
paths compute its availability:

- **Closed form** (independent instances): the binomial probability that at least `k` of `n` are
  up, given per-instance availability `a`.
- **CTMC** (when failure and repair rates are given): build the generator matrix of a birth-death
  chain over the number of healthy instances, solve for the stationary distribution, and sum the
  probability mass where at least `k` are up.

The two agree when repair is independent, which the test suite verifies. The CTMC path also
handles cases the binomial cannot, such as a single shared repair channel.

## Why a Markov chain

When availability depends on the interplay of failure and repair rates, the steady-state
distribution is not a simple product. Solving `π Q = 0` with `Σ π = 1` gives the exact stationary
probabilities. This is the method behind probabilistic model checkers such as PRISM and Storm,
implemented here with a focused solver on top of NumPy so qedra stays a self-contained,
pip-installable CLI.

## From availability to a verdict

`AvailabilityProver.prove_at_least` computes the composite availability and compares it to the
target. The result carries:

- the achieved availability, rendered as a percentage,
- expected downtime in minutes per month,
- a per-component breakdown, so the limiting tier is obvious.

A design that meets the target is PROVEN with the composition as its proof note; one that falls
short is VIOLATED with the shortfall and the per-component figures as the counterexample.

## State-space growth

A redundancy group of `n` instances has `n + 1` states, so the chain is small and exact.
Modelling many interacting components at once would grow the state space; the roadmap addresses
this with lumping (collapsing symmetric states) when such models are added.

## Reading the code

- `src/qedra/engines/reliability/ctmc.py` — the generator builder and the steady-state solver.
- `src/qedra/engines/reliability/availability.py` — composition and the prover.
