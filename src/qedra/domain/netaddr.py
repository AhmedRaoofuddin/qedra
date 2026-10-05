"""IPv4 and CIDR helpers plus Azure service-tag semantics.

These functions define the ground truth that the SMT encoder mirrors in bit-vector logic.
Keeping them here, as plain Python, lets the test suite check the Z3 encoding against an
independent reference implementation (differential testing).
"""

from __future__ import annotations

from dataclasses import dataclass

IPV4_BITS = 32
_FULL_MASK = 0xFFFFFFFF

# RFC 1918 private ranges.
_PRIVATE_RANGES: tuple[tuple[int, int], ...] = (
    (0x0A000000, 8),  # 10.0.0.0/8
    (0xAC100000, 12),  # 172.16.0.0/12
    (0xC0A80000, 16),  # 192.168.0.0/16
)

# Non-routable and reserved ranges that never carry real public-internet traffic. Azure's
# "Internet" service tag excludes these, so an external attacker cannot source from them.
# Excluding them keeps counterexamples credible (a real routable address, not 0.x or 127.x).
_RESERVED_RANGES: tuple[tuple[int, int], ...] = (
    *_PRIVATE_RANGES,
    (0x00000000, 8),  # 0.0.0.0/8      this network
    (0x64400000, 10),  # 100.64.0.0/10  carrier-grade NAT
    (0x7F000000, 8),  # 127.0.0.0/8    loopback
    (0xA9FE0000, 16),  # 169.254.0.0/16 link-local
    (0xC6120000, 15),  # 198.18.0.0/15  benchmarking
    (0xE0000000, 4),  # 224.0.0.0/4    multicast
    (0xF0000000, 4),  # 240.0.0.0/4    reserved
)

# The fixed address Azure uses for its platform load balancer / health probes.
AZURE_LOAD_BALANCER_IP = 0xA83F8110  # 168.63.129.16

SERVICE_TAGS = frozenset({"Internet", "VirtualNetwork", "AzureLoadBalancer", "Any"})


def parse_ipv4(address: str) -> int:
    """Convert dotted-quad text to a 32-bit integer."""
    octets = address.strip().split(".")
    if len(octets) != 4:
        raise ValueError(f"not an IPv4 address: {address!r}")
    value = 0
    for octet in octets:
        n = int(octet)
        if not 0 <= n <= 255:
            raise ValueError(f"octet out of range in {address!r}")
        value = (value << 8) | n
    return value


def format_ipv4(value: int) -> str:
    """Convert a 32-bit integer back to dotted-quad text."""
    if not 0 <= value <= _FULL_MASK:
        raise ValueError(f"value out of IPv4 range: {value}")
    return ".".join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))


def prefix_mask(prefix_len: int) -> int:
    """Return the 32-bit mask for a CIDR prefix length."""
    if not 0 <= prefix_len <= IPV4_BITS:
        raise ValueError(f"prefix length out of range: {prefix_len}")
    if prefix_len == 0:
        return 0
    return (_FULL_MASK << (IPV4_BITS - prefix_len)) & _FULL_MASK


@dataclass(frozen=True, slots=True)
class Cidr:
    """A parsed CIDR block, for example 10.1.0.0/16."""

    base: int
    prefix_len: int

    @classmethod
    def parse(cls, text: str) -> Cidr:
        text = text.strip()
        if "/" not in text:
            # A bare address is a /32 host route.
            return cls(parse_ipv4(text), IPV4_BITS)
        addr, _, length = text.partition("/")
        prefix_len = int(length)
        mask = prefix_mask(prefix_len)
        return cls(parse_ipv4(addr) & mask, prefix_len)

    @property
    def mask(self) -> int:
        return prefix_mask(self.prefix_len)

    def contains(self, address: int) -> bool:
        return (address & self.mask) == self.base

    def __str__(self) -> str:
        return f"{format_ipv4(self.base)}/{self.prefix_len}"


def is_private(address: int) -> bool:
    """True when the address falls inside any RFC 1918 range."""
    return any(Cidr(base, length).contains(address) for base, length in _PRIVATE_RANGES)


def reserved_cidrs() -> list[Cidr]:
    """The reserved/non-routable blocks, as Cidr objects. Shared by the reference and SMT paths."""
    return [Cidr(base, length) for base, length in _RESERVED_RANGES]


def is_reserved(address: int) -> bool:
    """True when the address is private, non-routable, or otherwise reserved."""
    return any(block.contains(address) for block in reserved_cidrs())


def is_internet(address: int) -> bool:
    """True when the address can appear as a real public-internet source.

    This models Azure's "Internet" service tag: routable public space, with private and
    reserved ranges excluded.
    """
    return not is_reserved(address)


def is_public(address: int) -> bool:
    """Alias for is_internet, kept for readability at call sites."""
    return is_internet(address)


def sample_public_address() -> int:
    """A concrete public address, handy for building human-readable counterexamples."""
    return parse_ipv4("203.0.113.7")  # TEST-NET-3, reserved for documentation
