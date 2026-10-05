"""Network reachability, proved with Z3.

qedra encodes an NSG as a bit-vector decision function over an abstract packet, then asks
the solver one question: does a packet exist that originates on the public internet and that
the NSG admits into a protected subnet? UNSAT proves no such packet exists. SAT returns a
concrete packet, which qedra re-validates against the reference evaluator before trusting it.

This mirrors the approach behind AWS Tiros and Zelkova, adapted to Azure NSG semantics.
"""

from __future__ import annotations

from dataclasses import dataclass

import z3

from qedra.domain import netaddr, nsg_eval
from qedra.domain.ir.model import Nsg, NsgRule, PortRange, Subnet

_PROTO = z3.BitVecSort(8)
_PORT = z3.BitVecSort(16)
_ADDR = z3.BitVecSort(32)


@dataclass(frozen=True, slots=True)
class _Packet:
    src: z3.BitVecRef
    dst: z3.BitVecRef
    src_port: z3.BitVecRef
    dst_port: z3.BitVecRef
    protocol: z3.BitVecRef

    @classmethod
    def fresh(cls) -> _Packet:
        return cls(
            src=z3.BitVec("src", _ADDR),
            dst=z3.BitVec("dst", _ADDR),
            src_port=z3.BitVec("src_port", _PORT),
            dst_port=z3.BitVec("dst_port", _PORT),
            protocol=z3.BitVec("proto", _PROTO),
        )


@dataclass(frozen=True, slots=True)
class ReachabilityResult:
    """Outcome of one reachability query."""

    reachable: bool
    subnet: str
    witness: dict[str, str] | None = None
    proof_note: str | None = None


def _cidr_match(addr: z3.BitVecRef, cidr: netaddr.Cidr) -> z3.BoolRef:
    mask = z3.BitVecVal(cidr.mask, _ADDR)
    base = z3.BitVecVal(cidr.base, _ADDR)
    return (addr & mask) == base


def _is_public(addr: z3.BitVecRef) -> z3.BoolRef:
    """Not inside any reserved or non-routable range, matching netaddr.is_internet.

    Built from the same range list as the reference evaluator, so the two cannot drift.
    """
    reserved = [_cidr_match(addr, block) for block in netaddr.reserved_cidrs()]
    return z3.Not(z3.Or(*reserved))


def _endpoint_match(spec: str, addr: z3.BitVecRef, vnet_prefixes: list[str]) -> z3.BoolRef:
    if spec in {"*", "Any"}:
        return z3.BoolVal(True)
    if spec == "Internet":
        return _is_public(addr)
    if spec == "VirtualNetwork":
        prefixes = [_cidr_match(addr, netaddr.Cidr.parse(p)) for p in vnet_prefixes]
        return z3.Or(*prefixes) if prefixes else z3.BoolVal(False)
    if spec == "AzureLoadBalancer":
        return addr == z3.BitVecVal(netaddr.AZURE_LOAD_BALANCER_IP, _ADDR)
    return _cidr_match(addr, netaddr.Cidr.parse(spec))


def _port_match(prange: PortRange, port: z3.BitVecRef) -> z3.BoolRef:
    return z3.And(
        z3.UGE(port, z3.BitVecVal(prange.low, _PORT)),
        z3.ULE(port, z3.BitVecVal(prange.high, _PORT)),
    )


def _proto_match(protocol: str, proto: z3.BitVecRef) -> z3.BoolRef:
    code = nsg_eval.proto_code(protocol)  # type: ignore[arg-type]
    if code is None:
        return z3.BoolVal(True)
    return proto == z3.BitVecVal(code, _PROTO)


def _rule_matches(rule: NsgRule, pkt: _Packet, vnet_prefixes: list[str]) -> z3.BoolRef:
    return z3.And(
        _proto_match(rule.protocol, pkt.protocol),
        _endpoint_match(rule.source, pkt.src, vnet_prefixes),
        _endpoint_match(rule.destination, pkt.dst, vnet_prefixes),
        _port_match(rule.source_port_range, pkt.src_port),
        _port_match(rule.destination_port_range, pkt.dst_port),
    )


def _inbound_allowed(nsg: Nsg | None, pkt: _Packet, vnet_prefixes: list[str]) -> z3.BoolRef:
    """A bit-vector expression that is true exactly when the NSG admits the packet inbound.

    Built as nested if-then-else in ascending priority, so the first matching rule decides,
    exactly as Azure evaluates rules.
    """
    decision: z3.BoolRef = z3.BoolVal(False)  # default: deny
    for rule in reversed(nsg_eval.effective_inbound_rules(nsg)):
        allow = z3.BoolVal(rule.access == "Allow")
        decision = z3.If(_rule_matches(rule, pkt, vnet_prefixes), allow, decision)
    return decision


def smt_inbound_allowed(
    nsg: Nsg | None,
    *,
    src: int,
    dst: int,
    dst_port: int,
    protocol: int,
    src_port: int = 12345,
    vnet_prefixes: list[str] | None = None,
) -> bool:
    """Evaluate the SMT decision function for one concrete packet.

    Fully constraining the packet makes the decision deterministic, so a satisfiable check
    means the NSG admits the packet. The test suite compares this against the reference
    evaluator across random inputs to prove the encoding is sound and complete.
    """
    pkt = _Packet.fresh()
    solver = z3.Solver()
    solver.add(pkt.src == z3.BitVecVal(src, _ADDR))
    solver.add(pkt.dst == z3.BitVecVal(dst, _ADDR))
    solver.add(pkt.src_port == z3.BitVecVal(src_port, _PORT))
    solver.add(pkt.dst_port == z3.BitVecVal(dst_port, _PORT))
    solver.add(pkt.protocol == z3.BitVecVal(protocol, _PROTO))
    solver.add(_inbound_allowed(nsg, pkt, vnet_prefixes or []))
    return bool(solver.check() == z3.sat)


class NetworkReachabilityProver:
    """Proves whether the public internet can reach a subnet through its NSG."""

    def __init__(self, vnet_prefixes: list[str] | None = None) -> None:
        self._vnet_prefixes = vnet_prefixes or []

    def prove_no_internet_inbound(
        self, subnet: Subnet, ports: tuple[PortRange, ...] | None = None
    ) -> ReachabilityResult:
        """Try to prove no internet-sourced packet is admitted to `subnet`.

        `ports` restricts the destination ports of interest; None means any port.
        """
        pkt = _Packet.fresh()
        solver = z3.Solver()

        subnet_cidr = netaddr.Cidr.parse(subnet.address_prefix)
        solver.add(_cidr_match(pkt.dst, subnet_cidr))
        solver.add(_is_public(pkt.src))
        # Azure's Internet service tag excludes the platform load-balancer address, so an
        # external attacker cannot source traffic from it. Exclude it from the search.
        solver.add(pkt.src != z3.BitVecVal(netaddr.AZURE_LOAD_BALANCER_IP, _ADDR))
        # Restrict to TCP; management and database services of concern run over TCP.
        solver.add(pkt.protocol == z3.BitVecVal(6, _PROTO))
        if ports:
            solver.add(z3.Or(*[_port_match(p, pkt.dst_port) for p in ports]))
        solver.add(_inbound_allowed(subnet.nsg, pkt, self._vnet_prefixes))

        outcome = solver.check()
        if outcome == z3.unsat:
            return ReachabilityResult(
                reachable=False,
                subnet=subnet.name,
                proof_note=(
                    "Z3 returned UNSAT: no public-internet TCP packet satisfies the NSG "
                    "decision function for this subnet."
                ),
            )
        if outcome == z3.unknown:
            raise RuntimeError(f"Z3 returned unknown for subnet {subnet.name!r}")

        model = solver.model()
        witness = self._decode(model, pkt)
        self._revalidate(subnet, witness)
        return ReachabilityResult(reachable=True, subnet=subnet.name, witness=witness)

    def _decode(self, model: z3.ModelRef, pkt: _Packet) -> dict[str, str]:
        src = model.eval(pkt.src, model_completion=True).as_long()
        dst = model.eval(pkt.dst, model_completion=True).as_long()
        dst_port = model.eval(pkt.dst_port, model_completion=True).as_long()
        return {
            "source_ip": netaddr.format_ipv4(src),
            "destination_ip": netaddr.format_ipv4(dst),
            "destination_port": str(dst_port),
            "protocol": "Tcp",
        }

    def _revalidate(self, subnet: Subnet, witness: dict[str, str]) -> None:
        """Re-run the witness through the reference evaluator; a mismatch means the encoding
        is unsound, which is a bug rather than a finding."""
        decision = nsg_eval.evaluate_inbound(
            subnet.nsg,
            src=netaddr.parse_ipv4(witness["source_ip"]),
            dst=netaddr.parse_ipv4(witness["destination_ip"]),
            dst_port=int(witness["destination_port"]),
            protocol=6,
            vnet_prefixes=self._vnet_prefixes,
        )
        if decision != "Allow":
            raise AssertionError(
                f"SMT witness rejected by reference evaluator; encoding is unsound: {witness}"
            )
