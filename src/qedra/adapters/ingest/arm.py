"""Parse an Azure Resource Manager (ARM) template into the network IR.

Scope is deliberate: virtual networks, their subnets, and network security groups, which is
enough to prove internet-isolation properties straight from deployed IaC. Subnet tier is
inferred from the subnet name (a subnet named snet-data maps to tier=data); anything the
parser does not understand is left out of the model rather than guessed at.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from qedra.domain.ir.model import (
    Architecture,
    NetworkModel,
    Nsg,
    NsgRule,
    Subnet,
    Vnet,
)

_NSG_NAME_IN_ID = re.compile(r"networkSecurityGroups'?\s*,?\s*'?([A-Za-z0-9_.-]+)")
_TIER_HINTS: tuple[tuple[str, str], ...] = (
    ("data", "data"),
    ("db", "data"),
    ("sql", "data"),
    ("web", "web"),
    ("frontend", "web"),
    ("app", "app"),
    ("bastion", "mgmt"),
)


def load_arm_template(path: Path) -> Architecture:
    template = json.loads(path.read_text(encoding="utf-8"))
    resources = _flatten_resources(template.get("resources", []))

    nsgs = {
        _resource_name(r): _parse_nsg(r)
        for r in resources
        if _type(r) == "microsoft.network/networksecuritygroups"
    }
    vnets = [
        _parse_vnet(r, nsgs) for r in resources if _type(r) == "microsoft.network/virtualnetworks"
    ]
    name = path.stem
    return Architecture(name=name, network=NetworkModel(vnets=tuple(vnets)))


def _flatten_resources(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for resource in resources:
        flat.append(resource)
        nested = resource.get("resources")
        if isinstance(nested, list):
            flat.extend(_flatten_resources(nested))
    return flat


def _type(resource: dict[str, Any]) -> str:
    return str(resource.get("type", "")).lower()


def _resource_name(resource: dict[str, Any]) -> str:
    raw = str(resource.get("name", ""))
    # ARM names can be expressions; take the last quoted literal if present.
    literals = re.findall(r"'([^']+)'", raw)
    return literals[-1] if literals else raw


def _parse_nsg(resource: dict[str, Any]) -> Nsg:
    props = resource.get("properties", {})
    rules = tuple(_parse_rule(r) for r in props.get("securityRules", []))
    return Nsg(name=_resource_name(resource), rules=rules)


def _parse_rule(rule: dict[str, Any]) -> NsgRule:
    p = rule.get("properties", {})
    return NsgRule(
        name=str(rule.get("name", "rule")),
        priority=int(p["priority"]),
        direction=p["direction"],
        access=p["access"],
        protocol=_normalise_protocol(p.get("protocol", "*")),
        source=_first(p, "sourceAddressPrefix", "sourceAddressPrefixes"),
        source_ports=_first(p, "sourcePortRange", "sourcePortRanges"),
        destination=_first(p, "destinationAddressPrefix", "destinationAddressPrefixes"),
        destination_ports=_first(p, "destinationPortRange", "destinationPortRanges"),
    )


def _normalise_protocol(value: str) -> str:
    mapping = {"tcp": "Tcp", "udp": "Udp", "icmp": "Icmp", "*": "*"}
    return mapping.get(str(value).lower(), "*")


def _first(props: dict[str, Any], singular: str, plural: str) -> str:
    if singular in props and props[singular] not in (None, ""):
        return str(props[singular])
    values = props.get(plural)
    if isinstance(values, list) and values:
        return str(values[0])
    return "*"


def _parse_vnet(resource: dict[str, Any], nsgs: dict[str, Nsg]) -> Vnet:
    props = resource.get("properties", {})
    prefixes = tuple(props.get("addressSpace", {}).get("addressPrefixes", []))
    subnets = tuple(_parse_subnet(s, nsgs) for s in props.get("subnets", []))
    return Vnet(name=_resource_name(resource), address_prefixes=prefixes, subnets=subnets)


def _parse_subnet(subnet: dict[str, Any], nsgs: dict[str, Nsg]) -> Subnet:
    name = str(subnet.get("name", "subnet"))
    props = subnet.get("properties", {})
    nsg = _resolve_nsg(props.get("networkSecurityGroup"), nsgs)
    tags = {}
    tier = _infer_tier(name)
    if tier is not None:
        tags["tier"] = tier
    return Subnet(
        name=name,
        address_prefix=str(props.get("addressPrefix", "0.0.0.0/0")),
        nsg=nsg,
        tags=tags,
    )


def _resolve_nsg(reference: dict[str, Any] | None, nsgs: dict[str, Nsg]) -> Nsg | None:
    if not reference:
        return None
    identifier = str(reference.get("id", ""))
    match = _NSG_NAME_IN_ID.search(identifier)
    if match is None:
        return None
    return nsgs.get(match.group(1))


def _infer_tier(subnet_name: str) -> str | None:
    lowered = subnet_name.lower()
    for hint, tier in _TIER_HINTS:
        if hint in lowered:
            return tier
    return None
