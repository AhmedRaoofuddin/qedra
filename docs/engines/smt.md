# The SMT engine: proving network reachability

qedra proves whether the public internet can reach a protected subnet by encoding Azure NSG
semantics into bit-vector logic and asking Z3 a single question. This document explains the
encoding, the soundness argument, and the limits.

## The question

> Does there exist a packet, sourced from a public address, that the subnet's effective NSG admits
> inbound on a sensitive port?

- If **no such packet exists**, Z3 returns **UNSAT**. The property holds for *every* packet. That
  is a proof, not a sample.
- If one exists, Z3 returns **SAT** with a concrete model, which qedra decodes into a packet
  (source IP, destination, port) and **re-validates** against an independent evaluator.

This is the approach behind AWS Tiros and Zelkova, adapted to Azure.

## The model

A packet is five bit-vectors: source and destination addresses (32-bit), source and destination
ports (16-bit), and protocol (8-bit). An NSG rule becomes a boolean match expression over that
packet:

- **CIDR match**: `(addr & mask) == base`, with the mask and base computed from the prefix.
- **Service tags**: `Internet` is "not in any RFC 1918 range"; `VirtualNetwork` is "in one of the
  VNet prefixes"; `AzureLoadBalancer` is the platform address `168.63.129.16`.
- **Port match**: an unsigned range comparison.
- **Protocol match**: equality, or always-true for the wildcard.

The NSG decision is built as nested if-then-else in ascending priority, so the first matching rule
decides — exactly how Azure evaluates rules. Azure's default rules (allow VNet, allow load
balancer, deny all) are appended at the lowest priority.

## Why UNSAT is a proof you can trust

Two independent implementations of the same semantics must agree:

1. `src/qedra/domain/nsg_eval.py` — a plain-Python evaluator. The specification.
2. `src/qedra/engines/smt/network.py` — the Z3 encoding.

A property-based test (`tests/property/test_smt_vs_reference.py`) generates hundreds of random
rule sets and packets and asserts both return the same verdict. Agreement across that search is
what justifies calling an UNSAT result a proof of the encoded property. Every SAT witness is also
run back through the reference evaluator before qedra reports it; a mismatch raises an error
rather than emitting a finding, because an unsound encoding is a bug, not a vulnerability.

## What the property does and does not claim

It claims: the effective NSG on the subnet admits (or denies) inbound traffic sourced from the
public internet on the ports of interest. This is a real, common WAF Security finding (SE:08).

It does not yet claim full end-to-end reachability, which also depends on public IP assignment,
routing, and load-balancer rules. Those are modelled incrementally; the roadmap extends the same
encoding to public-IP exposure and user-defined routes.

## Approximations, stated plainly

- The `Internet` service tag is modelled as "public" (not RFC 1918). Azure's real tag also
  excludes specific Azure infrastructure ranges; the model excludes the platform load-balancer
  address and treats the rest of public space as internet. This is a sound over-approximation for
  the isolation property: it never misses a true public exposure.
- Only TCP is searched for the data-tier property, because the management and database services of
  concern run over TCP.

## Reading the code

Start at `NetworkReachabilityProver.prove_no_internet_inbound`. It builds the packet, constrains
it to a public source and the subnet's address range, adds the NSG decision, and checks
satisfiability. The helper `smt_inbound_allowed` evaluates the decision for one concrete packet
and exists so the test suite can compare the encoding against the reference across random inputs.
