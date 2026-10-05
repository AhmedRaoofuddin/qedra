"""qedra: a neuro-symbolic prover for Azure Well-Architected properties.

qedra compiles Azure infrastructure into formal models and proves properties with an
SMT solver (Z3) and a continuous-time Markov chain, returning a mathematical verdict
per property: PROVEN, VIOLATED (with a concrete counterexample), or UNSUPPORTED.
"""

__version__ = "0.1.0"
