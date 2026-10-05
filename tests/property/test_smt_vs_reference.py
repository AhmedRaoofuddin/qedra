"""Differential property test: the Z3 encoding must agree with the reference evaluator.

Across hundreds of random rule sets and packets, the SMT decision function and the plain
Python evaluator must return the same verdict. Agreement is what justifies calling an UNSAT
result a proof: both independent implementations of Azure NSG semantics concur.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from qedra.domain.ir.model import Nsg, NsgRule
from qedra.domain.nsg_eval import evaluate_inbound
from qedra.engines.smt.network import smt_inbound_allowed

VNET = ["10.0.0.0/16"]
_PROTOCOLS = ["Tcp", "Udp", "*"]
_ENDPOINTS = ["Internet", "VirtualNetwork", "Any", "10.0.2.0/24", "203.0.113.0/24", "0.0.0.0/0"]
_PORTS = ["*", "22", "443", "1433", "100-200", "1000-2000"]


@st.composite
def nsg_rules(draw: st.DrawFn) -> NsgRule:
    return NsgRule(
        name=f"r{draw(st.integers(0, 1_000_000))}",
        priority=draw(st.integers(100, 4096)),
        direction="Inbound",
        access=draw(st.sampled_from(["Allow", "Deny"])),
        protocol=draw(st.sampled_from(_PROTOCOLS)),
        source=draw(st.sampled_from(_ENDPOINTS)),
        source_ports="*",
        destination=draw(st.sampled_from(["*", "10.0.3.0/24", "VirtualNetwork"])),
        destination_ports=draw(st.sampled_from(_PORTS)),
    )


_ADDR = st.integers(min_value=0, max_value=0xFFFFFFFF)
_PORT = st.integers(min_value=0, max_value=65535)
_PROTO = st.sampled_from([1, 6, 17])


@settings(max_examples=300, deadline=None)
@given(
    rules=st.lists(nsg_rules(), max_size=4),
    src=_ADDR,
    dst=_ADDR,
    dst_port=_PORT,
    src_port=_PORT,
    protocol=_PROTO,
)
def test_encoding_matches_reference(
    rules: list[NsgRule],
    src: int,
    dst: int,
    dst_port: int,
    src_port: int,
    protocol: int,
) -> None:
    nsg = Nsg(name="nsg", rules=tuple(rules))
    reference = evaluate_inbound(
        nsg,
        src=src,
        dst=dst,
        dst_port=dst_port,
        protocol=protocol,
        src_port=src_port,
        vnet_prefixes=VNET,
    )
    smt = smt_inbound_allowed(
        nsg,
        src=src,
        dst=dst,
        dst_port=dst_port,
        protocol=protocol,
        src_port=src_port,
        vnet_prefixes=VNET,
    )
    assert smt is (reference == "Allow")
