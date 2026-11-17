![Platform](https://img.shields.io/badge/Microsoft-Azure-0078D4?logo=microsoftazure&logoColor=white)
![Component](https://img.shields.io/badge/Azure-Functions-0062AD?logo=azurefunctions&logoColor=white)
![Language](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![CI](https://github.com/AdrianStudio/cloud-ops-playbooks/actions/workflows/ci.yml/badge.svg)
![Status](https://img.shields.io/badge/Status-In%20Progress-orange)

# cloud-ops-playbooks

Automated remediation scripts, Terraform modules, and infrastructure playbooks for common Cloud and Sysadmin pain points. Designed by autonomous agents and merged by a human Tech Lead.

Can an AI agent read a Sysadmin's complaint on Reddit and write a production ready mitigation script before the human finishes their coffee?

Spoiler: yes, if you constrain it strictly enough.

---

## Why This Exists

I did not build this repository out of boredom. I built it to solve a specific friction I saw in the tech landscape. 

On one side, Sysadmins and Cloud Engineers on communities like Reddit and Hacker News are drowning in real, immediate problems: sudden zero day CVEs, active directory nightmares, and infrastructure misconfigurations. On the other side, the internet is flooded with generic, low effort AI code that breaks in production or ignores basic security practices.

**The Idea:** I wanted to bridge that gap. I wondered if I could build a completely autonomous "virtual office" that listens to the internet, identifies high friction technical pain points, and acts as a dedicated DevOps Engineer to solve them. 

**The Execution:** I built a private Azure Serverless backend (FUBANX) that runs daily. It ingests thousands of posts, filters out the noise, and scores the "pain level" of each problem. If a problem scores an 8 or higher, my autonomous Agent Engineer kicks in. It decides on the best tool (Python, Terraform, or PowerShell), writes the code, audits itself through a strict QA loop to remove "AI smells", and opens a Pull Request here. 

I act as the Tech Lead. I review the logic, verify the safety, and merge the code.

---

## Architecture

<img width="1677" height="711" alt="image" src="https://github.com/user-attachments/assets/28b0ce51-7a65-489f-a121-d3de85aa3e05" />


This repository serves as the public output state for the private Azure architecture. The external intelligence pipeline evaluates real world technical pain points, triggers the automated engineer agent, and opens a Pull Request. The human Tech Lead reviews, tests, and merges the final solution.

---

## What I Built

| Component | Resource | Purpose |
| --- | --- | --- |
| `scripts/python/` | Python playbooks | Utilities for API interactions and diagnostics, such as CVE mitigation. |
| `scripts/powershell/` | PowerShell scripts | Windows Server and Active Directory management. |
| `terraform/modules/` | Terraform code | Reusable IaC components for Azure infrastructure and secure baselines. |

---

## Security

- **Zero hardcoded credentials.** All scripts expect environment variables or secure credential injection.
- **Dry run by default.** All destructive scripts require explicit flags (e.g., `--apply`) to execute changes.
- **Least privilege execution.**

---

## CI

The continuous integration workflow runs on every Pull Request. It executes syntax validation for Python (`ruff check`), formatting checks, and Terraform validations (`tofu validate` and `tofu fmt`). It does not deploy resources or execute API calls.

---

## Design Decisions

**Why manual review instead of automatic merges.** Autonomous systems can generate confident but incorrect logic. Requiring a human Tech Lead to review the Pull Request ensures code quality, validates architectural decisions, and prevents unexpected infrastructure downtime.

**Why dry run is the default state.** Running automated scripts against production environments carries high risk. Defaulting to a safe evaluation mode protects the infrastructure while proving the script's intended path.

**Why strict QA constraints for the agent.** Left unchecked, LLMs write overly defensive, heavily commented "slop". The agent here is forced to pass AST parsing and regex checks to ensure the code looks and acts like it was written by a senior human engineer.

---

## What I Learned

- Designing strict constraints and feedback loops for automated agents yields significantly safer code than open ended prompts.
- Separating the generation engine (private Azure backend) from the final portfolio (public GitHub repo) protects intellectual property while demonstrating verifiable engineering capabilities.

---

## Project Context

This repository is the public showcase driven by the private FUBANX autonomous agent system, designed to identify and resolve high friction operations in the Sysadmin and DevOps spaces.

---

## Author

Adrian Tamargo

[GitHub](https://github.com/AdrianStudio) · [LinkedIn](https://www.linkedin.com/in/adrian-tamargo/)
