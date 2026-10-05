from qedra.domain import netaddr


def test_parse_and_format_roundtrip() -> None:
    for text in ["0.0.0.0", "10.0.3.1", "203.0.113.7", "255.255.255.255"]:
        assert netaddr.format_ipv4(netaddr.parse_ipv4(text)) == text


def test_cidr_contains() -> None:
    block = netaddr.Cidr.parse("10.0.3.0/24")
    assert block.contains(netaddr.parse_ipv4("10.0.3.1"))
    assert block.contains(netaddr.parse_ipv4("10.0.3.255"))
    assert not block.contains(netaddr.parse_ipv4("10.0.4.1"))


def test_cidr_normalises_base() -> None:
    assert str(netaddr.Cidr.parse("10.0.3.57/24")) == "10.0.3.0/24"


def test_zero_prefix_matches_everything() -> None:
    block = netaddr.Cidr.parse("0.0.0.0/0")
    assert block.contains(netaddr.parse_ipv4("8.8.8.8"))
    assert block.contains(netaddr.parse_ipv4("10.0.0.1"))


def test_private_and_public() -> None:
    for private in ["10.1.2.3", "172.16.5.5", "192.168.1.1"]:
        assert netaddr.is_private(netaddr.parse_ipv4(private))
        assert not netaddr.is_public(netaddr.parse_ipv4(private))
    for public in ["8.8.8.8", "203.0.113.7", "1.1.1.1"]:
        assert netaddr.is_public(netaddr.parse_ipv4(public))


def test_sample_public_address_is_public() -> None:
    assert netaddr.is_public(netaddr.sample_public_address())
