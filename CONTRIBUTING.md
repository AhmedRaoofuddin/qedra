# Contributing to qedra

Thanks for your interest. qedra holds a high bar on correctness because it claims to *prove*
things. Contributions are welcome when they keep that bar.

## Ground rules

- **Soundness first.** Any new property must have a reference implementation and a test that checks
  the solver encoding against it. A finding without a certificate is not a finding.
- **The domain and engines stay pure.** No I/O, no Azure SDK, no network calls in
  `src/qedra/domain` or `src/qedra/engines`. Infrastructure lives in adapters.
- **Honesty over coverage.** If a property is only partially decidable, report `UNSUPPORTED` and
  document the limit. Do not paper over a gap with a heuristic.

## Before you open a pull request

```bash
pip install -e ".[dev]"
make check     # ruff, mypy --strict, pytest with coverage
```

All three must pass. CI runs them on Python 3.11 and 3.12, and verifies the bundled examples.

## Adding a new property

1. Define the semantics as plain Python (the reference).
2. Encode it for the solver (Z3 or the CTMC engine).
3. Add a property-based test asserting the two agree.
4. Route it in `application/verify.py` and render it.
5. Add or extend an example in `examples/` with an `expected` outcome.

## Writing style

Documentation and generated reports avoid filler and hedging. Write plainly: a claim, the evidence,
the reference. Active voice, specific nouns, no em dashes.
