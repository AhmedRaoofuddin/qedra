"""Load a native qedra architecture file (YAML or JSON) straight into the IR.

The native format is the IR serialised. It keeps examples and tests readable and gives users
a way to model an architecture by hand before wiring up IaC ingestion.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from qedra.domain.ir.model import Architecture


def load_native(path: Path) -> Architecture:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    return Architecture.model_validate(data)
