# The Well-Architected Framework, mapped to provable properties

The Azure Well-Architected Framework (WAF) organises cloud design into five pillars. Each pillar
ships design principles, a design-review checklist with stable identifiers (RE:05, SE:08, CO:14),
trade-offs, and recommendation guides. This document maps the pillars to the properties qedra can
decide, and marks honestly which are implemented today versus on the roadmap.

The point of a formal reviewer is to move claims from "we think the data tier is private" to
"the data tier is private, and here is the proof." Not every WAF recommendation is decidable —
many are organisational or qualitative — but a meaningful core is, and that core is where qedra
lives.

## The five pillars

### Reliability
Keep the workload available and recoverable. Design principles cover redundancy, defined
availability targets, failure-mode analysis, and tested recovery.

- Checklist anchors: RE:04 (define targets), RE:05 (redundancy), RE:09 (disaster recovery).
- **Decidable here:** composite availability against a target, and expected downtime, via a
  continuous-time Markov chain over the dependency model. **Implemented.**
- **Roadmap:** RTO/RPO modelling and zone/region failure-mode simulation on the same chain.

### Security
Protect confidentiality, integrity, and availability. Principles cover segmentation, least
privilege, keeping data off the public internet, and encryption.

- Checklist anchors: SE:06 (network controls), SE:08 (segment and isolate).
- **Decidable here:** network reachability — whether the public internet can reach a protected
  subnet through its effective NSG — proved with Z3, with a concrete counterexample packet on
  failure. **Implemented.**
- **Roadmap:** RBAC privilege-escalation reachability (can a principal reach Owner on a scope?),
  encoded with the same solver.

### Cost Optimization
Spend only where it buys value. Principles cover right-sizing, consumption models, and
eliminating waste.

- Checklist anchors: CO:05 (rates and SKUs), CO:07 (component cost).
- **Decidable here:** exact monthly cost from the Azure Retail Prices API, and reserved-instance
  or savings-plan coverage solved as an integer program. **Roadmap.**

### Operational Excellence
Run the workload with safe, repeatable practice. Principles cover IaC, deployment safety, and
observability.

- Checklist anchors: OE:05 (IaC), OE:07 (observability).
- **Decidable here:** drift between the IaC-declared model and live Resource Graph state, and
  conformance against deterministic scanners (PSRule, Checkov) as ground-truth evidence.
  **Roadmap.**

### Performance Efficiency
Match resources to demand. Principles cover scaling, data partitioning, and bottleneck analysis.

- Checklist anchors: PE:05 (scaling), PE:07 (optimise code and infrastructure).
- **Decidable here:** a narrower set than the others; capacity and queueing properties are
  partially decidable on the same CTMC machinery. **Roadmap.**

## Trade-offs: the pillar that matters most for AZ-305

WAF documents trade-offs between pillars because no design maximises all five. A single-region
deployment satisfies Cost (CO:07) and violates Reliability (RE:05). Strong Cosmos DB consistency
satisfies a correctness need and costs Performance. The architect's job is to pick the trade-off
on purpose and record why.

qedra treats this directly. It reports a cheap single-region design as a cost win *and* a
reliability violation, each with its own verdict, so the trade-off is explicit rather than
hidden. A future arbiter module will reconcile conflicting verdicts and rank remediations by
their effect across pillars.

## How a property becomes a proof

1. A policy clause states the property (for example, the data tier denies internet inbound).
2. An adapter compiles the architecture into the canonical IR.
3. An engine encodes the property into a formal model: bit-vector logic for reachability, a
   Markov chain for availability.
4. The solver returns a verdict: PROVEN (UNSAT of the negation), VIOLATED (a re-validated
   counterexample), or UNSUPPORTED (the model lacks the data to decide).
5. The verdict carries a certificate — a proof note or a concrete witness — so the result is
   auditable.

## Using the pillars to study

For each pillar, pick one checklist item, express it as a property, and decide whether it is the
kind of claim a solver can settle or the kind a human must judge. That sorting exercise — what is
decidable versus what is a judgement call — is the fastest way to understand both the framework
and the limits of automated review.

## References

- [Azure Well-Architected Framework](https://learn.microsoft.com/azure/well-architected/)
- [Reliability design review checklist](https://learn.microsoft.com/azure/well-architected/reliability/checklist)
- [Security design review checklist](https://learn.microsoft.com/azure/well-architected/security/checklist)
