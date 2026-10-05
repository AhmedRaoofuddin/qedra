# AZ-104 study guide: Microsoft Azure Administrator

A working engineer's guide to the AZ-104 exam. It covers every skill area with the depth the
questions actually demand, the mistakes that cost people marks, and a link from each topic to
the property qedra proves. Read it as a study companion, not a substitute for hands-on labs.

> Scope note. Microsoft revises exam skills over time. Treat the weightings below as the shape
> of the exam, confirm the current [skills outline](https://learn.microsoft.com/credentials/certifications/azure-administrator/),
> and spend your lab time where the weighting is heaviest.

## The exam at a glance

| Skill area | Weight | What it really tests |
| --- | --- | --- |
| Manage identities and governance | 20–25% | Entra ID, RBAC, subscriptions, policy, cost |
| Implement and manage storage | 15–20% | Accounts, access control, redundancy, file shares |
| Deploy and manage compute | 20–25% | VMs, scale sets, App Service, containers |
| Implement and manage virtual networking | 15–20% | VNets, NSGs, peering, DNS, load balancing |
| Monitor and maintain resources | 10–15% | Azure Monitor, backup, recovery |

The exam runs 40–60 questions in about 100 minutes, with a scaled passing score of 700/1000.
Expect case studies, drag-and-drop ordering, and "choose the least-privilege option" questions.
The exam rewards the answer that is correct *and* minimal: the cheapest SKU that meets the
requirement, the narrowest role that grants the access, the simplest redundancy that hits the SLA.

---

## 1. Manage identities and governance (20–25%)

### Microsoft Entra ID
Entra ID (formerly Azure AD) is the identity plane. Know the difference between Entra ID and
on-premises Active Directory: Entra ID is not a domain controller and does not speak LDAP or
Kerberos natively. Key objects are users, groups (security vs Microsoft 365, assigned vs
dynamic), and administrative units.

- **Self-service password reset (SSPR)** needs registration methods and, for writeback to
  on-premises AD, Entra Connect with password writeback enabled.
- **Conditional Access** is the policy engine for sign-in: signals (user, device, location,
  risk) produce a grant or block, optionally with MFA. It sits in the P1/P2 licensing tier.
- **Entra Connect** synchronises identities; know password hash sync vs pass-through
  authentication vs federation, and which survives an on-premises outage (password hash sync).

### Role-based access control (RBAC)
RBAC answers "who can do what, where." A role assignment binds a **security principal** (user,
group, service principal, managed identity) to a **role definition** (a set of `Actions` /
`NotActions` / `DataActions`) at a **scope** (management group, subscription, resource group,
resource). Assignments are inherited downward and are additive; an explicit deny assignment
overrides allows.

Exam traps:
- Built-in roles you must know cold: Owner, Contributor, Reader, User Access Administrator.
  Contributor can manage everything *except* granting access; granting access needs Owner or
  User Access Administrator.
- RBAC (control plane, the `Microsoft.Authorization` space) is distinct from data-plane access
  such as a storage account's keys or a Key Vault access policy.
- Scope matters: pick the *narrowest* scope that satisfies the requirement.

### Governance: policy, locks, tags, cost
- **Azure Policy** enforces or audits resource properties (allowed locations, required tags,
  allowed SKUs) with effects such as `deny`, `audit`, `append`, `deployIfNotExists`. Policy
  governs *configuration*; RBAC governs *access*. A question that says "prevent anyone from
  creating a public IP" is Policy, not RBAC.
- **Management groups** organise subscriptions into a hierarchy for inherited policy and RBAC.
- **Resource locks** (`CanNotDelete`, `ReadOnly`) protect against accidental change and are
  inherited; a `ReadOnly` lock blocks operations that a Contributor would otherwise allow.
- **Tags** drive cost allocation and automation; they do not inherit to child resources by
  default (you enforce inheritance with Policy).
- **Cost Management** budgets raise alerts; they do not cap spend.

> **qedra link.** RBAC privilege-escalation reachability (can a principal reach Owner on a
> protected scope through an assignment chain?) is exactly the kind of property an SMT solver
> decides. The v1 engine focuses on network reachability; the RBAC encoder is the next step on
> the roadmap and reuses the same solver.

---

## 2. Implement and manage storage (15–20%)

### Storage accounts
Know the account kinds and the redundancy options, because the exam loves to test the
cheapest option that survives a given failure:

| Redundancy | Copies | Survives | Notes |
| --- | --- | --- | --- |
| LRS | 3 in one datacentre | disk/rack failure | cheapest, no zone protection |
| ZRS | 3 across zones | a zone outage | synchronous |
| GRS | LRS + async to paired region | a regional outage | secondary not readable |
| GZRS | ZRS + async to paired region | zone *and* region | highest durability |
| RA-GRS / RA-GZRS | adds read access to secondary | regional outage with reads | app must use the `-secondary` endpoint |

### Access control and security
- **Shared keys** grant full account access; prefer **Entra ID RBAC** for data (for example the
  Storage Blob Data Reader role) or scoped **SAS tokens**.
- **Network rules**: default-deny the public endpoint and reach the account over a **private
  endpoint**, or restrict to selected VNets with service endpoints.
- **Encryption** is on by default with Microsoft-managed keys; customer-managed keys live in
  Key Vault.
- **Blob lifecycle management** tiers data (hot / cool / cold / archive) to cut cost.
- **Azure Files** supports SMB and NFS; identity-based access uses Entra Kerberos or on-prem AD.

> **qedra link.** "A storage account must not be reachable from the public internet" is a
> reachability property. Model the account behind a subnet or private endpoint and prove no
> public path exists, the same way qedra proves data-tier isolation today.

---

## 3. Deploy and manage compute (20–25%)

### Virtual machines
- **Sizing families**: general purpose (B, D), compute optimised (F), memory optimised (E, M).
  The exam tests matching a workload to a family and resizing without data loss.
- **Availability**: a single VM has a lower SLA than two VMs across an **availability set**
  (fault and update domains) or an **availability zone**. Zones protect against datacentre
  failure; sets protect against rack and maintenance events.
- **Disks**: OS vs data vs temporary; Standard HDD / Standard SSD / Premium SSD / Ultra. The
  temporary disk is ephemeral and must never hold state.
- **Extensions** (custom script, DSC) and **cloud-init** handle post-deployment configuration.

### Scale and platform services
- **Virtual machine scale sets** give identical VMs with autoscale rules on metrics or a
  schedule.
- **App Service** runs web apps on a shared or dedicated plan; know deployment slots and
  slot swaps for zero-downtime releases.
- **Containers**: Azure Container Instances for a single container, Azure Kubernetes Service
  for orchestration.

> **qedra link.** VM and scale-set redundancy is the input to composite availability. qedra's
> CTMC engine turns "2× gateway, 3× app, 2× SQL" into a steady-state availability figure you
> can compare against an SLA target. See `docs/learn/well-architected-framework.md`.

---

## 4. Implement and manage virtual networking (15–20%)

This is the most formalisable area, and the one qedra proves directly.

### Core building blocks
- **VNets and subnets**: a VNet owns an address space; subnets carve it up. Subnets cannot
  overlap, and some services require a *delegated* or *dedicated* subnet (for example Azure
  Bastion needs `AzureBastionSubnet`).
- **Network security groups (NSGs)**: ordered allow/deny rules evaluated by **priority**, with
  the first match winning. Each rule matches on protocol, source, source port, destination,
  and destination port, where source and destination are a CIDR block or a **service tag**
  (`Internet`, `VirtualNetwork`, `AzureLoadBalancer`). Azure adds default rules at the lowest
  priority: allow VNet-to-VNet inbound, allow the load balancer, and deny everything else.
- **Application security groups** let you write rules against workload groups instead of IPs.

### Connectivity and name resolution
- **Peering** connects VNets; it is non-transitive, so a hub-and-spoke topology needs a network
  virtual appliance or a route table to route spoke-to-spoke traffic.
- **User-defined routes** override system routes; the `0.0.0.0/0` next hop sends egress through
  a firewall or NVA.
- **Private endpoints** bring a PaaS service into your VNet with a private IP; **service
  endpoints** keep the public endpoint but restrict it to selected subnets.
- **DNS**: Azure-provided DNS, private DNS zones for private endpoints, and custom DNS servers.

### Load balancing
- **Azure Load Balancer** is layer 4; **Application Gateway** is layer 7 with WAF; **Front
  Door** is global layer 7; **Traffic Manager** is DNS-based global routing. Match the tool to
  the layer and the scope (regional vs global).

Exam traps:
- NSG rules are stateful: an allowed inbound flow's response is allowed outbound automatically.
- A deny at a higher priority (lower number) beats an allow at a lower priority.
- NSGs apply at the subnet and the NIC; both must allow a flow for it to pass.

> **qedra link.** This section is qedra's home ground. The SMT engine encodes NSG first-match
> semantics, service tags, CIDR matching, and the Azure default rules, then proves whether a
> public packet can reach a protected subnet. Read the encoding in `docs/engines/smt.md` and the
> code in `src/qedra/engines/smt/network.py`.

---

## 5. Monitor and maintain resources (10–15%)

### Azure Monitor
- **Metrics** are numeric time series; **logs** live in a Log Analytics workspace and are
  queried with **KQL**. Know the difference and when each applies.
- **Alerts** fire on metric thresholds, log queries, or activity-log events, and route through
  **action groups**.
- **Application Insights** instruments application-level telemetry.

### Backup and recovery
- **Azure Backup** uses a Recovery Services vault for VMs, files, and SQL; know retention
  policies and restore options.
- **Azure Site Recovery** replicates VMs to a secondary region for disaster recovery; know RPO
  and failover/failback.
- A **recovery point objective (RPO)** is how much data you can lose; a **recovery time
  objective (RTO)** is how long recovery may take. Match the service to the objective.

> **qedra link.** RTO and RPO are reliability targets. qedra treats availability as a provable
> property today and models downtime per month from the CTMC result; recovery-time modelling is
> a natural extension of the same engine.

---

## A two-week study plan

1. **Days 1–3 — identity and governance.** Build a tenant, create users and groups, assign
   RBAC at three scopes, write an Azure Policy that denies a resource type, apply a lock.
2. **Days 4–6 — networking.** Build a hub-and-spoke, write NSG rules, add a private endpoint,
   and trace a packet by hand through the rule priorities. Then run qedra against the examples
   in this repo to see the same logic proved.
3. **Days 7–9 — compute and storage.** Deploy a VM and a scale set, resize them, attach a data
   disk, create a storage account for each redundancy tier, and reason about which survives
   what.
4. **Days 10–12 — monitoring and recovery.** Wire a metric alert through an action group, back
   up a VM, and configure Site Recovery.
5. **Days 13–14 — practice and review.** Take timed practice questions, then revisit every
   question you missed and write down *why* the right answer was minimal.

## How this repo helps you study

Clone qedra and run it against the bundled examples:

```bash
qedra verify examples/contoso-secure    # a well-architected three-tier design
qedra verify examples/contoso-flawed    # the same design with two planted defects
qedra explain examples/contoso-flawed SEC-001
```

Reading `src/qedra/domain/nsg_eval.py` is a compact, correct reference for how Azure evaluates
NSG rules. If you can follow that file, you understand the networking section well enough for
the exam.
