# Changelog

All notable changes to qedra are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-05

### Added
- SMT engine (Z3) that proves network internet-isolation properties and returns a concrete,
  re-validated counterexample packet on failure.
- Reliability engine that computes composite availability with a continuous-time Markov chain and
  proves it against a target.
- Reference NSG evaluator and a property-based differential test that keeps the SMT encoding sound.
- Ingestion adapters for native YAML/JSON models and ARM templates.
- CLI with `verify`, `explain`, `init`, and `version`; JSON and Markdown renderers; CI exit codes.
- A secure and a flawed Contoso example that run with no Azure subscription.
- Study guides for AZ-104, AZ-305, and the Well-Architected Framework, each linked to the
  properties qedra proves.
