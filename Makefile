.PHONY: install lint format type test cov check demo clean

PY ?= python

install:
	$(PY) -m pip install -e ".[dev]"

lint:
	$(PY) -m ruff check src tests

format:
	$(PY) -m ruff format src tests

type:
	$(PY) -m mypy

test:
	$(PY) -m pytest

cov:
	$(PY) -m pytest --cov

check: lint type cov

demo:
	$(PY) -m qedra.cli.app verify examples/contoso-flawed

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .hypothesis .coverage htmlcov
