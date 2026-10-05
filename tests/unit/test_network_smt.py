from qedra.domain import netaddr
from qedra.domain.ir.model import Nsg, NsgRule, PortRange, Subnet
from qedra.domain.nsg_eval import evaluate_inbound, sensitive_port_ranges
from qedra.engines.smt.network import NetworkReachabilityProver, smt_inbound_allowed

VNET = ["10.0.0.0/16"]


def _data_subnet(nsg: Nsg | None) -> Subnet:
    return Subnet(name="snet-data", address_prefix="10.0.3.0/24", nsg=nsg, tags={"tier": "data"})


def test_locked_down_subnet_is_proven_safe() -> None:
    nsg = Nsg(
        name="nsg-data",
        rules=(
            NsgRule(
                name="AllowAppTier",
                priority=200,
                direction="Inbound",
                access="Allow",
                protocol="Tcp",
                source="10.0.2.0/24",
                destination_ports="1433",
            ),
        ),
    )
    result = NetworkReachabilityProver(VNET).prove_no_internet_inbound(
        _data_subnet(nsg), ports=sensitive_port_ranges()
    )
    assert result.reachable is False
    assert result.proof_note is not None


def test_exposed_subnet_yields_validated_counterexample() -> None:
    nsg = Nsg(
        name="nsg-data",
        rules=(
            NsgRule(
                name="AllowSqlFromInternet",
                priority=100,
                direction="Inbound",
                access="Allow",
                protocol="Tcp",
                source="Internet",
                destination_ports="1433",
            ),
        ),
    )
    result = NetworkReachabilityProver(VNET).prove_no_internet_inbound(
        _data_subnet(nsg), ports=sensitive_port_ranges()
    )
    assert result.reachable is True
    assert result.witness is not None
    # The prover already re-validated the witness; assert it independently too.
    src = netaddr.parse_ipv4(result.witness["source_ip"])
    dst = netaddr.parse_ipv4(result.witness["destination_ip"])
    port = int(result.witness["destination_port"])
    assert netaddr.is_public(src)
    assert netaddr.Cidr.parse("10.0.3.0/24").contains(dst)
    assert (
        evaluate_inbound(nsg, src=src, dst=dst, dst_port=port, protocol=6, vnet_prefixes=VNET)
        == "Allow"
    )


def test_smt_matches_reference_on_known_packets() -> None:
    nsg = Nsg(
        name="nsg",
        rules=(
            NsgRule(
                name="AllowHttps",
                priority=100,
                direction="Inbound",
                access="Allow",
                protocol="Tcp",
                source="Internet",
                destination_ports="443",
            ),
        ),
    )
    public = netaddr.parse_ipv4("203.0.113.7")
    dst = netaddr.parse_ipv4("10.0.3.5")
    for port, expected in [(443, True), (1433, False), (22, False)]:
        smt = smt_inbound_allowed(
            nsg, src=public, dst=dst, dst_port=port, protocol=6, vnet_prefixes=VNET
        )
        ref = evaluate_inbound(
            nsg, src=public, dst=dst, dst_port=port, protocol=6, vnet_prefixes=VNET
        )
        assert smt is (ref == "Allow"), (port, expected)


def test_port_range_parsing() -> None:
    assert PortRange.parse("*") == PortRange(low=0, high=65535)
    assert PortRange.parse("443") == PortRange(low=443, high=443)
    assert PortRange.parse("100-200") == PortRange(low=100, high=200)
