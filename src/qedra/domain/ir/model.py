"""The canonical intermediate representation that every engine reads.

Adapters translate Bicep, ARM, or live Resource Graph state into these models. The engines
never see raw Azure shapes, so adding a new input format never touches the prover.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Direction = Literal["Inbound", "Outbound"]
Access = Literal["Allow", "Deny"]
Protocol = Literal["Tcp", "Udp", "Icmp", "*"]

_MAX_PORT = 65535


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PortRange(_Frozen):
    """An inclusive TCP/UDP port range. Parsed from "443", "100-200", or "*"."""

    low: int = Field(ge=0, le=_MAX_PORT)
    high: int = Field(ge=0, le=_MAX_PORT)

    @classmethod
    def parse(cls, text: str) -> PortRange:
        text = text.strip()
        if text in {"*", "Any", "any"}:
            return cls(low=0, high=_MAX_PORT)
        if "-" in text:
            lo, _, hi = text.partition("-")
            return cls(low=int(lo), high=int(hi))
        port = int(text)
        return cls(low=port, high=port)

    def contains(self, port: int) -> bool:
        return self.low <= port <= self.high

    def __str__(self) -> str:
        if self.low == 0 and self.high == _MAX_PORT:
            return "*"
        if self.low == self.high:
            return str(self.low)
        return f"{self.low}-{self.high}"


class NsgRule(_Frozen):
    """A single network security group rule, faithful to Azure's evaluation fields.

    `source` and `destination` hold either a CIDR block (10.0.0.0/16) or a service tag
    (Internet, VirtualNetwork, AzureLoadBalancer, Any). Rules apply in ascending priority.
    """

    name: str
    priority: int = Field(ge=100, le=65500)
    direction: Direction
    access: Access
    protocol: Protocol = "*"
    source: str = "*"
    source_ports: str = "*"
    destination: str = "*"
    destination_ports: str = "*"

    @property
    def source_port_range(self) -> PortRange:
        return PortRange.parse(self.source_ports)

    @property
    def destination_port_range(self) -> PortRange:
        return PortRange.parse(self.destination_ports)


class Nsg(_Frozen):
    """A network security group: a named, ordered set of rules."""

    name: str
    rules: tuple[NsgRule, ...] = ()

    def inbound_rules(self) -> list[NsgRule]:
        return sorted((r for r in self.rules if r.direction == "Inbound"), key=lambda r: r.priority)


class Subnet(_Frozen):
    """A subnet, its address space, an optional NSG, and free-form tags such as tier=data."""

    name: str
    address_prefix: str
    nsg: Nsg | None = None
    tags: dict[str, str] = Field(default_factory=dict)

    def tier(self) -> str | None:
        return self.tags.get("tier")


class Vnet(_Frozen):
    """A virtual network containing subnets."""

    name: str
    address_prefixes: tuple[str, ...]
    subnets: tuple[Subnet, ...] = ()


class NetworkModel(_Frozen):
    """The full network topology of an architecture."""

    vnets: tuple[Vnet, ...] = ()

    def subnets(self) -> list[Subnet]:
        return [s for v in self.vnets for s in v.subnets]

    def subnets_in_tier(self, tier: str) -> list[Subnet]:
        return [s for s in self.subnets() if s.tier() == tier]

    def vnet_prefixes(self) -> list[str]:
        return [p for v in self.vnets for p in v.address_prefixes]


class Component(_Frozen):
    """A reliability component.

    Supply `instance_availability` directly, or supply `failure_rate` and `repair_rate`
    (per hour) and let the engine derive availability from a continuous-time Markov chain.
    `instances` sets redundancy; `required` sets how many must stay up (k-of-n).
    """

    name: str
    instances: int = Field(default=1, ge=1)
    required: int = Field(default=1, ge=1)
    instance_availability: float | None = Field(default=None, ge=0.0, le=1.0)
    failure_rate: float | None = Field(default=None, gt=0.0)
    repair_rate: float | None = Field(default=None, gt=0.0)
    zone_redundant: bool = False

    @field_validator("required")
    @classmethod
    def _required_fits(cls, v: int, info: object) -> int:
        return v

    def model_post_init(self, _: object) -> None:
        if self.required > self.instances:
            raise ValueError(
                f"component {self.name!r}: required ({self.required}) exceeds instances"
            )
        has_avail = self.instance_availability is not None
        has_rates = self.failure_rate is not None and self.repair_rate is not None
        if not has_avail and not has_rates:
            raise ValueError(f"component {self.name!r}: give instance_availability, or both rates")


class DependencyModel(_Frozen):
    """A system modelled as serial components, each with internal k-of-n redundancy.

    Serial composition multiplies component availabilities; redundancy within a component
    is combined by the reliability engine. This matches Azure composite-SLA guidance.
    """

    components: tuple[Component, ...] = ()


class Architecture(_Frozen):
    """The top-level IR bundle: everything the engines need to reason about one workload."""

    name: str
    network: NetworkModel = Field(default_factory=NetworkModel)
    reliability: DependencyModel | None = None
    tags: dict[str, str] = Field(default_factory=dict)
