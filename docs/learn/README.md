# Learn: Azure certifications, made concrete

These guides serve two audiences: people studying for the Azure certifications, and people who
want to understand what qedra proves and why it matters. Each guide links its exam topics to the
properties qedra decides, so the theory has something runnable behind it.

| Guide | For |
| --- | --- |
| [AZ-104 — Azure Administrator](az-104-azure-administrator.md) | The operational foundation: identity, networking, compute, storage, monitoring |
| [AZ-305 — Infrastructure Solutions](az-305-infrastructure-solutions.md) | The design layer: choosing services, topologies, and redundancy, and defending the trade-off |
| [Well-Architected Framework](well-architected-framework.md) | The five pillars mapped to properties qedra can prove |

## The fastest way to learn from this repo

```bash
# install (see the top-level README for details)
pip install -e .

qedra verify examples/contoso-secure     # a design that satisfies the WAF baseline
qedra verify examples/contoso-flawed     # the same design with two planted defects
qedra explain examples/contoso-flawed SEC-001   # read the counterexample
```

Then open `src/qedra/domain/nsg_eval.py`. It is a compact, correct reference for Azure NSG
evaluation — the clearest way to learn how network security groups actually decide a packet.

## A note on honesty

These guides mark what qedra proves today and what is on the roadmap. The exams reward precise
thinking; so does this project. Where a WAF recommendation is a human judgement rather than a
decidable property, the guides say so.
