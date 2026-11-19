![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform%20%2F%20OpenTofu-IaC-7B42BC?logo=terraform&logoColor=white)
![PowerShell](https://img.shields.io/badge/PowerShell-Automation-5391FE?logo=powershell&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

# fubanx-solutions

Production-ready remediation scripts, Terraform/OpenTofu modules, and operational playbooks for real-world Cloud, DevOps, and Sysadmin problems.

Every solution in this repository starts from an actual operational pain point, either surfaced from technical communities or submitted directly via [fubanx.com](https://fubanx.com), and is generated, statically audited, and manually reviewed before being merged.

---

## What's Inside

Every solution lives in its own folder, with the code and a README covering the problem, prerequisites and usage:

```text
<stack>/<category>/<short-project-name>/
```

| Directory | Stack | Focus |
| --- | --- | --- |
| `python/` | Python 3.12 | Cloud API automation, diagnostics, Kubernetes/Azure remediation, and CVE mitigation. |
| `powershell/` | PowerShell | Windows Server, Active Directory, and Microsoft 365 administration. |
| `terraform/` | Terraform / OpenTofu | Reusable IaC modules and hardened cloud baselines. |

Categories: `security`, `windows`, `cloud`, `kubernetes`, `networking`, `monitoring`.

---

## Engineering Standards

AI-generated infrastructure code is usually fragile, over-commented, and full of silent fallbacks. Every Pull Request opened here must pass a strict automated QA gate and manual Tech Lead review before merging:

- **Dry-run by default:** Destructive or state-changing scripts run in safe evaluation mode unless an explicit execution flag (e.g., `--apply`) is passed.
- **Zero hardcoded credentials:** Secrets and configuration are strictly injected via environment variables or native cloud identity providers.
- **Fail loudly:** No silent fallbacks or swallowed exceptions (`except KeyError`, hidden defaults on required config). If a dependency or variable is missing, the script exits cleanly with a clear error.
- **No simulated code:** Placeholder logic, mock responses, and "for demonstration" blocks are automatically rejected by AST and static checks.

---

## How These Solutions Are Built

This repository is the public output catalog of [**FUBANX**](https://github.com/AdrianStudio/fubanx), an event-driven engineering system built on Azure Functions, Storage Queues, and OpenTofu.

1. **Triage:** Real operational issues are triaged by a human engineer via Discord to filter noise and prevent prompt injection.
2. **Engineering & QA:** An automated engineering agent writes the solution in Python, Terraform, or PowerShell and iterates against a strict static QA loop until all security and code-quality checks pass.
3. **Human Review:** The agent opens a Pull Request here. Nothing is auto-merged: every line is reviewed before hitting `main`.

Want to see how the engine works under the hood? Check out the main repository: **[AdrianStudio/fubanx](https://github.com/AdrianStudio/fubanx)**.

---

## Have an Operational Pain Point?

If you are dealing with a repetitive Cloud, Kubernetes, or Sysadmin issue that deserves a clean automation script, you can submit it directly at **[fubanx.com](https://fubanx.com)**.

---

## Author

**Adrián Tamargo**  
[GitHub](https://github.com/AdrianStudio) · [LinkedIn](https://www.linkedin.com/in/adrian-tamargo/) · [fubanx.com](https://fubanx.com)
