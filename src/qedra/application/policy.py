"""The verification contract: the properties an architecture must satisfy.

A policy is the declarative counterpart to the IR. You version it next to your infrastructure
and qedra proves the architecture against it. The format stays small on purpose; every field
maps to a property an engine can decide.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

_PERCENT = re.compile(r">=\s*([0-9]+(?:\.[0-9]+)?)\s*%")


def parse_availability_target(text: str) -> float:
    """Turn ">= 99.99%" into 0.9999."""
    match = _PERCENT.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"availability must look like '>= 99.99%', got {text!r}")
    return float(match.group(1)) / 100.0


class NoInternetInbound(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tiers: list[str] = Field(default_factory=lambda: ["data"])


class SecurityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    no_internet_inbound: NoInternetInbound | None = None


class ReliabilityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    availability: str | None = None

    def availability_target(self) -> float | None:
        return None if self.availability is None else parse_availability_target(self.availability)


class Policy(BaseModel):
    """A named set of properties to prove."""

    model_config = ConfigDict(extra="forbid")

    name: str = "waf-policy"
    security: SecurityPolicy | None = None
    reliability: ReliabilityPolicy | None = None

    @classmethod
    def from_yaml(cls, path: Path) -> Policy:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)

    @classmethod
    def baseline(cls) -> Policy:
        """A sensible default contract: data tier is private, four nines of availability."""
        return cls(
            name="waf-baseline",
            security=SecurityPolicy(no_internet_inbound=NoInternetInbound(tiers=["data"])),
            reliability=ReliabilityPolicy(availability=">= 99.99%"),
        )
