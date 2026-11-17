![Azure](https://img.shields.io/badge/Microsoft-Azure-0078D4?logo=microsoftazure&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-1.15-7B42BC?logo=terraform&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13+-blue?logo=python&logoColor=white)
![PowerShell](https://img.shields.io/badge/PowerShell-7-5391FE?logo=powershell&logoColor=white)
![CI](https://github.com/AdrianStudio/cloud-ops-playbooks/actions/workflows/ci.yml/badge.svg)
![Status](https://img.shields.io/badge/Status-In%20Progress-orange)

# cloud-ops-playbooks

Automated remediation scripts, Terraform modules, and infrastructure playbooks for common Cloud and Sysadmin pain points. Designed by autonomous agents and merged by a human Tech Lead.

---

## Scenario

A regional Managed Service Provider (MSP) managing multiple client environments. They face a constant flood of critical vulnerabilities (CVEs) and infrastructure misconfigurations. Limited budget. No dedicated security team. One clear compliance requirement: rapid response to high severity alerts without breaking production systems.

The default approach in most environments would be reacting to tickets manually, applying patches by hand, and deploying fragmented ad hoc scripts. This project shows what an automated, intelligence-driven remediation repository looks like when built with rigorous engineering standards.

---

## Architecture

![Architecture diagram](./images/architecture.png)

This repository serves as the public output state for a private, autonomous Azure architecture. An external intelligence pipeline evaluates real world technical pain points, triggers an automated engineer agent to write the remediation code (Python, Terraform, or PowerShell), and opens a Pull Request here. The human Tech Lead reviews, tests, and merges the final solution.

---

## Infrastructure

### N-Able CVE Mitigation (Python)

A Python playbook to automatically interact with the N-Able API, identify endpoints vulnerable to specific CVEs, and issue isolation commands. Built with safety defaults.

### Azure Storage Secure Baseline (Terraform)

A reusable Terraform module to enforce secure defaults on Azure Storage Accounts, disabling public access and enforcing TLS 1.2 minimums across client environments.

### Active Directory Offboarding (PowerShell)

A PowerShell utility to safely disable AD users, strip group memberships, and log the offboarding process for compliance audits.

---

## Security

- Zero hardcoded credentials. All scripts expect environment variables or secure credential injection.
- Dry run by default. All destructive scripts require explicit flags (e.g., `--apply`) to execute changes.
- Least privilege execution.

---

## Project Structure

| Directory | Purpose |
| --- | --- |
| `scripts/python/` | Python utilities for API interactions and diagnostics |
| `scripts/powershell/` | PowerShell scripts for Windows Server and AD management |
| `terraform/modules/` | Reusable IaC components for Azure infrastructure |
| `docs/` | Extended technical documentation and ADRs |

---

## CI

The continuous integration workflow runs on every Pull Request. It executes syntax validation for Python (`ruff check`), formatting checks, and Terraform validations (`tofu validate` and `tofu fmt`). It does not deploy resources or execute API calls.

---

## Deployment

Scripts are designed to be run individually by operators or integrated into larger deployment pipelines.

1. `export NABLE_API_TOKEN="your_token_here"`
2. `python scripts/python/isolate_vulnerable_endpoints.py --apply`

## Cleanup

For infrastructure deployed via the Terraform modules:

`tofu destroy -var-file=envs/dev.tfvars`

---

## Design Decisions

**Why manual review instead of automatic merges.** Autonomous systems can generate confident but incorrect logic. Requiring a human Tech Lead to review the Pull Request ensures code quality, validates architectural decisions, and prevents unexpected infrastructure downtime.

**Why dry run is the default state.** Running automated scripts against production environments carries high risk. Defaulting to a safe evaluation mode protects the infrastructure while proving the script's intended path.

---

## What I Learned

- Designing strict constraints for automated agents yields significantly safer code than open ended prompts.
- Separating the generation engine (private) from the final portfolio (public) protects intellectual property while demonstrating verifiable engineering capabilities.

---

## Project Context

This repository is the public showcase driven by the private FUBANX autonomous agent system, designed to identify and resolve high friction operations in the Sysadmin and DevOps spaces.

---

## Author

Adrian Tamargo

[GitHub](https://github.com/AdrianStudio) · [LinkedIn](https://www.linkedin.com/in/adrian-tamargo/)
