from qedra.domain import netaddr
from qedra.domain.ir.model import Nsg, NsgRule
from qedra.domain.nsg_eval import evaluate_inbound

PUBLIC = netaddr.parse_ipv4("203.0.113.7")
INTERNAL = netaddr.parse_ipv4("10.0.2.9")
DATA = netaddr.parse_ipv4("10.0.3.5")
VNET = ["10.0.0.0/16"]


def _nsg(*rules: NsgRule) -> Nsg:
    return Nsg(name="nsg", rules=rules)


def test_default_deny_blocks_internet() -> None:
    assert evaluate_inbound(_nsg(), src=PUBLIC, dst=DATA, dst_port=1433, protocol=6) == "Deny"


def test_default_allows_vnet_to_vnet() -> None:
    decision = evaluate_inbound(
        _nsg(), src=INTERNAL, dst=DATA, dst_port=1433, protocol=6, vnet_prefixes=VNET
    )
    assert decision == "Allow"


def test_explicit_internet_allow() -> None:
    rule = NsgRule(
        name="AllowSql",
        priority=100,
        direction="Inbound",
        access="Allow",
        protocol="Tcp",
        source="Internet",
        destination_ports="1433",
    )
    assert evaluate_inbound(_nsg(rule), src=PUBLIC, dst=DATA, dst_port=1433, protocol=6) == "Allow"
    # A different port is still denied by default.
    assert evaluate_inbound(_nsg(rule), src=PUBLIC, dst=DATA, dst_port=22, protocol=6) == "Deny"


def test_priority_first_match_wins() -> None:
    allow = NsgRule(
        name="Allow",
        priority=100,
        direction="Inbound",
        access="Allow",
        protocol="Tcp",
        source="Internet",
        destination_ports="443",
    )
    deny = NsgRule(
        name="Deny",
        priority=200,
        direction="Inbound",
        access="Deny",
        protocol="Tcp",
        source="Internet",
        destination_ports="443",
    )
    assert (
        evaluate_inbound(_nsg(allow, deny), src=PUBLIC, dst=DATA, dst_port=443, protocol=6)
        == "Allow"
    )
    # Swap priorities: the deny now wins.
    allow2 = allow.model_copy(update={"priority": 200})
    deny2 = deny.model_copy(update={"priority": 100})
    assert (
        evaluate_inbound(_nsg(allow2, deny2), src=PUBLIC, dst=DATA, dst_port=443, protocol=6)
        == "Deny"
    )


def test_protocol_mismatch_falls_through() -> None:
    udp_rule = NsgRule(
        name="AllowUdp",
        priority=100,
        direction="Inbound",
        access="Allow",
        protocol="Udp",
        source="Internet",
        destination_ports="1433",
    )
    # A TCP packet does not match a UDP allow rule, so default deny applies.
    assert (
        evaluate_inbound(_nsg(udp_rule), src=PUBLIC, dst=DATA, dst_port=1433, protocol=6) == "Deny"
    )
