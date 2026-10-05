"""Ingestion: turn IaC or a native model file into the canonical Architecture IR."""

from pathlib import Path

from qedra.adapters.ingest.arm import load_arm_template
from qedra.adapters.ingest.native import load_native
from qedra.domain.ir.model import Architecture


def load_architecture(path: Path) -> Architecture:
    """Load an architecture from a path, dispatching on file type.

    A directory is searched for `architecture.yaml` or `azuredeploy.json`. ARM templates are
    detected by their `$schema`; everything else is treated as a native qedra model.
    """
    target = _resolve(path)
    if _looks_like_arm(target):
        return load_arm_template(target)
    return load_native(target)


def _resolve(path: Path) -> Path:
    if path.is_dir():
        for name in ("architecture.yaml", "architecture.yml", "azuredeploy.json", "main.json"):
            candidate = path / name
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"no architecture file found in {path}")
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _looks_like_arm(path: Path) -> bool:
    if path.suffix.lower() != ".json":
        return False
    head = path.read_text(encoding="utf-8")[:4000]
    return "schema.management.azure.com" in head and "deploymentTemplate" in head


__all__ = ["load_architecture", "load_arm_template", "load_native"]
