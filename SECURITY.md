# Security policy

qedra analyses infrastructure for security properties, so its own correctness matters.

## Reporting a vulnerability

Report suspected vulnerabilities privately through GitHub Security Advisories on this repository,
or by email to the maintainer. Please include a minimal reproduction. Expect an acknowledgement
within a few working days.

## What counts as a security bug here

- An **unsound proof**: a property reported `PROVEN` while a real counterexample exists. This is the
  most serious class, because it hides a genuine exposure. The differential test suite exists to
  prevent exactly this; a case that defeats it is a priority fix.
- A false `VIOLATED` that misrepresents a safe design is a correctness bug, reported the same way.

## Scope and trust

qedra runs locally and reads the files you point it at. It uses keyless Azure authentication for
live state and never writes to your subscription. Treat any model file from an untrusted source as
data, the same as you would any other input.
