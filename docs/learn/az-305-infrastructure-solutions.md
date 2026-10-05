# AZ-305 study guide: Designing Microsoft Azure Infrastructure Solutions

AZ-305 is a design exam. It does not ask whether you can click through a VM wizard; it asks
whether you can choose the right service, topology, and redundancy for a stated requirement, and
justify the trade-off. This guide walks each skill area, the decisions it tests, and the way
qedra turns those design decisions into properties you can prove.

> Prerequisite. AZ-305 assumes AZ-104-level operational knowledge. If the networking or identity
> sections here feel thin, that is deliberate; read `az-104-azure-administrator.md` first.
> Confirm the live [skills outline](https://learn.microsoft.com/credentials/certifications/azure-solutions-architect-expert/).

## The exam at a glance

| Skill area | Weight | The decision it tests |
| --- | --- | --- |
| Design identity, governance, and monitoring | 25–30% | How access, policy, and observability scale across an estate |
| Design data storage solutions | 20–25% | Which store fits the data shape, consistency, and scale |
| Design business continuity solutions | 15–20% | How the workload survives failure and meets RTO/RPO |
| Design infrastructure solutions | 30–35% | Compute, networking, integration, and migration design |

Expect long case studies with a customer scenario, explicit requirements (often including a cost
or compliance constraint), and answers that are all technically valid but only one of which
*best* meets every stated requirement. Read the requirements twice. The word "minimise cost" or
"no data loss" is usually the discriminator.

The design thread running through the whole exam is the **Well-Architected Framework** — its five
pillars and, more than anything, the **trade-offs** between them. See
`well-architected-framework.md` for how the pillars map to provable properties.

---

## 1. Design identity, governance, and monitoring (25–30%)

### Identity and access at scale
- **Entra ID tenant design**: single vs multi-tenant, B2B guest access, and B2C for customer
  identity. Know when each applies.
- **Managed identities** (system-assigned vs user-assigned) remove secrets from code; prefer
  them over service principals with client secrets. A design that stores a key in app config is
  usually the wrong answer.
- **Conditional Access** and **Privileged Identity Management (PIM)** provide just-in-time,
  approval-gated, time-bound elevation. A requirement for "temporary admin access with approval"
  is PIM.
- **RBAC vs ABAC**: role assignments plus attribute conditions for fine-grained data access.

### Governance across an estate
- **Management group hierarchy** carries policy and RBAC down to subscriptions. Design the
  hierarchy to match the org's compliance boundaries, not its org chart.
- **Azure Policy** and **initiatives** enforce standards as code; `deployIfNotExists` and
  `modify` remediate drift. This is governance by construction.
- **Landing zones** (the Cloud Adoption Framework enterprise-scale architecture) give a
  subscription-vending model with platform and workload separation, centralised networking, and
  baseline policy. Expect questions that ask you to place a new workload in the right landing
  zone.
- **Blueprints / template specs** package repeatable environments.

### Monitoring and observability
- **Azure Monitor** (metrics + logs), **Log Analytics** workspaces (centralised vs per-team),
  and **Application Insights** for app telemetry.
- Design decisions: workspace topology, data retention vs cost, and alert routing through action
  groups. A multi-region estate usually wants a centralised workspace with RBAC-scoped access.

> **qedra link.** "No principal outside the platform team can reach Owner on a production
> subscription" is a governance invariant. Encoding RBAC assignments and scopes as logic and
> proving the absence of an escalation path is the SMT engine's next module; the network engine
> already demonstrates the technique on reachability.

---

## 2. Design data storage solutions (20–25%)

Match the store to the data shape, access pattern, consistency need, and scale.

| Need | Service | Why |
| --- | --- | --- |
| Relational, managed | Azure SQL Database / Managed Instance | OLTP, elastic pools, PaaS |
| Relational, open source | Azure Database for PostgreSQL / MySQL | portability |
| Global, multi-model, low latency | Azure Cosmos DB | tunable consistency, multi-region writes |
| Unstructured objects | Blob Storage | tiers, lifecycle, cheapest at scale |
| File shares | Azure Files / NetApp Files | SMB/NFS lift-and-shift |
| Analytics at scale | Synapse / Data Lake Storage Gen2 | columnar, big data |

Design decisions the exam tests:
- **Cosmos DB consistency levels** (strong, bounded staleness, session, consistent prefix,
  eventual) and their latency and availability trade-offs. Strong consistency costs latency and
  constrains multi-region writes.
- **Azure SQL tiers and purchasing models** (DTU vs vCore, serverless, Hyperscale) matched to a
  cost and scale requirement.
- **Partitioning and sharding** for scale; choosing a partition key that avoids hot spots.
- **Data protection**: encryption at rest (service-managed vs customer-managed keys), private
  endpoints, and firewall rules to keep the store off the public internet.

> **qedra link.** The single most common data-tier WAF failure is public exposure. qedra proves
> a data store's subnet denies internet inbound, with a concrete counterexample when it does not.
> That is `SEC-001` in the bundled examples.

---

## 3. Design business continuity solutions (15–20%)

This area is about surviving failure within stated **RTO** (how fast you recover) and **RPO**
(how much data you can lose).

### Backup
- **Azure Backup** with Recovery Services vaults; design retention, geo-redundant vault storage,
  and soft delete against ransomware.
- Match backup frequency to RPO: hourly snapshots for a tight RPO, daily for a loose one.

### Disaster recovery
- **Azure Site Recovery** replicates VMs to a secondary region; design for the region pair and
  the failover/failback runbook.
- **Database DR**: SQL active geo-replication and auto-failover groups; Cosmos DB multi-region
  with automatic failover.
- **Storage redundancy** (GRS/GZRS) covers the data layer; it is not a substitute for
  application failover.

### High availability design
- **Availability zones** protect against a datacentre failure within a region; **region pairs**
  protect against a regional failure.
- Compose redundancy across the dependency chain: a single non-redundant component caps the
  whole system's availability, no matter how redundant the rest is.

> **qedra link.** This is the reliability engine's purpose. qedra builds a continuous-time Markov
> chain from the dependency model, computes steady-state availability and expected monthly
> downtime, and proves whether the design meets an availability target. A single-instance tier
> shows up immediately as the component dragging the composite figure down. See
> `src/qedra/engines/reliability/`.

---

## 4. Design infrastructure solutions (30–35%)

The largest area: compute, networking, application integration, and migration.

### Compute
- Choose between VMs, VM scale sets, App Service, Azure Functions, Container Apps, and AKS by
  matching the operational model and scale pattern. Serverless (Functions, Container Apps) for
  event-driven and spiky load; AKS for complex orchestration; App Service for standard web apps.
- **Batch and HPC** for large parallel compute.

### Networking topology
- **Hub-and-spoke** centralises shared services (firewall, DNS, gateways) in a hub, with
  workloads in spokes. **Azure Virtual WAN** scales this to many regions and branches.
- **Connectivity**: VPN Gateway (site-to-site, point-to-site) vs ExpressRoute (private, higher
  bandwidth, SLA-backed). A compliance or bandwidth requirement points to ExpressRoute.
- **Secure ingress and egress**: Application Gateway with WAF and Azure Firewall; force-tunnel
  egress through the firewall with user-defined routes.
- **Private connectivity to PaaS**: private endpoints plus private DNS zones.

### Application integration
- **Messaging**: Service Bus (enterprise, ordered, transactional), Event Hubs (high-throughput
  streaming), Event Grid (reactive events). Match the tool to the delivery semantics.
- **API Management** for a managed API gateway.

### Migration
- The **5 Rs** (rehost, refactor, re-architect, rebuild, replace) and the tooling: Azure
  Migrate for discovery and assessment, Database Migration Service for data. Match the business
  driver (speed vs modernisation) to the R.

> **qedra link.** Network topology is where design intent most often drifts from implementation.
> qedra proves reachability invariants over the topology the IaC actually declares — not the
> diagram someone drew in a review — so "the data tier is private" becomes a checked fact rather
> than a claim.

---

## The trade-off mindset the exam rewards

Every case study hides a tension between pillars. A few that recur:

- **Cost vs reliability**: a second region doubles cost and raises availability. The right
  answer depends on the stated RTO and budget, not on "more is better."
- **Security vs operational simplicity**: private endpoints and forced tunnelling harden a
  design and complicate operations. Justify the complexity against the stated threat.
- **Performance vs consistency**: strong consistency in Cosmos DB costs latency. Choose the
  weakest consistency the requirement tolerates.

qedra is built around this mindset. It records a design that is cheap *and* single-region as a
deliberate trade-off (cost satisfied, reliability violated) rather than a mistake, and it reports
both verdicts so the architect decides with the numbers in front of them.

## A design-practice routine

1. Take a published Azure reference architecture and write down, for each pillar, the one
   property it must satisfy.
2. Express two of those as a qedra policy (`.qedra.yaml`): an internet-isolation invariant and an
   availability target.
3. Model the architecture (native YAML or ARM) and run `qedra verify`.
4. Change one design decision — remove a redundant instance, open an NSG rule — and watch the
   verdict flip. Reasoning about *why* it flipped is the exact skill AZ-305 tests.

## Further reading in this repo

- `well-architected-framework.md` — the five pillars mapped to provable properties.
- `docs/engines/smt.md` and `docs/engines/reliability.md` — how the proofs work.
- `examples/` — a secure and a flawed reference architecture you can run in seconds.
