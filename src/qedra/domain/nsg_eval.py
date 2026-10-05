"""Reference NSG evaluation semantics, in plain Python.

This is the specification the SMT encoder must match. The test suite runs every Z3
counterexample back through this evaluator; a disagreement fails the build. Having two
independent implementations of the same semantics is how qedra earns the word "proven".
"""

from __future__ import annotations

from qedra.domain import netaddr
from qedra.domain.ir.model import Access, Nsg, NsgRule, PortRange, Protocol

# Azure protocol numbers.
_PROTO_CODE: dict[str, int] = {"Tcp": 6, "Udp": 17, "Icmp": 1}

# Azure's built-in inbound rules, applied after any custom rule (lowest priority).
DEFAULT_INBOUND_RULES: tuple[NsgRule, ...] = (
    NsgRule(
        name="AllowVnetInBound",
        priority=65000,
        direction="Inbound",
        access="Allow",
        source="VirtualNetwork",
        destination="VirtualNetwork",
    ),
    NsgRule(
        name="AllowAzureLoadBalancerInBound",
        priority=65001,
        direction="Inbound",
        access="Allow",
        source="AzureLoadBalancer",
    ),
    NsgRule(
        name="DenyAllInBound",
        priority=65500,
        direction="Inbound",
        access="Deny",
    ),
)


def proto_code(protocol: Protocol) -> int | None:
    """Numeric protocol, or None for the wildcard."""
    if protocol == "*":
        return None
    return _PROTO_CODE[protocol]


def effective_inbound_rules(nsg: Nsg | None) -> list[NsgRule]:
    """Custom inbound rules, by priority, followed by Azure's defaults."""
    custom = nsg.inbound_rules() if nsg is not None else []
    return [*custom, *DEFAULT_INBOUND_RULES]


def _endpoint_matches(spec: str, address: int, vnet_prefixes: list[str]) -> bool:
    if spec in {"*", "Any"}:
        return True
    if spec == "Internet":
        return netaddr.is_public(address)
    if spec == "VirtualNetwork":
        return any(netaddr.Cidr.parse(p).contains(address) for p in vnet_prefixes)
    if spec == "AzureLoadBalancer":
        return address == netaddr.AZURE_LOAD_BALANCER_IP
    return netaddr.Cidr.parse(spec).contains(address)


def _rule_matches_inbound(
    rule: NsgRule,
    *,
    src: int,
    dst: int,
    src_port: int,
    dst_port: int,
    protocol: int,
    vnet_prefixes: list[str],
) -> bool:
    if rule.protocol != "*" and _PROTO_CODE[rule.protocol] != protocol:
        return False
    if not _endpoint_matches(rule.source, src, vnet_prefixes):
        return False
    if not _endpoint_matches(rule.destination, dst, vnet_prefixes):
        return False
    if not rule.source_port_range.contains(src_port):
        return False
    return rule.destination_port_range.contains(dst_port)


def evaluate_inbound(
    nsg: Nsg | None,
    *,
    src: int,
    dst: int,
    dst_port: int,
    protocol: int,
    src_port: int = 12345,
    vnet_prefixes: list[str] | None = None,
) -> Access:
    """Decide whether an inbound packet is allowed, using Azure first-match-by-priority."""
    prefixes = vnet_prefixes or []
    for rule in effective_inbound_rules(nsg):
        if _rule_matches_inbound(
            rule,
            src=src,
            dst=dst,
            src_port=src_port,
            dst_port=dst_port,
            protocol=protocol,
            vnet_prefixes=prefixes,
        ):
            return rule.access
    return "Deny"


def sensitive_port_ranges() -> tuple[PortRange, ...]:
    """Common management and database ports that should never face the internet."""
    return (
        PortRange(low=22, high=22),  # SSH
        PortRange(low=3389, high=3389),  # RDP
        PortRange(low=1433, high=1433),  # SQL Server
        PortRange(low=3306, high=3306),  # MySQL
        PortRange(low=5432, high=5432),  # PostgreSQL
        PortRange(low=6379, high=6379),  # Redis
        PortRange(low=27017, high=27017),  # MongoDB
    )
