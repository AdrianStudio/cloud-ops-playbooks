# Narrator Tamper Audit

PowerShell script that audits Narrator and the other Ease of Access binaries used on the Windows lock screen for signs of tampering, and writes a JSON report.

## Problem
The FastUnlock Narrator lock screen bypass has no Microsoft patch. Sysadmins cannot tell whether Narrator, Utilman, sethc and similar binaries on their endpoints were replaced or hijacked. Until a fix ships, the only option is to check these known tampering points by hand on every machine.

## Prerequisites
- PowerShell 7.0 or later on Windows.
- Local administrator rights (the script uses `#Requires -RunAsAdministrator`).
- Read access to `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options` and the System32 directory.
- Write access to that registry key, needed only with `-Apply`.
- Write access to the folder that will hold the report.
- No environment variables, tokens or extra modules are needed.

## Usage
```powershell
# Report only, nothing is changed
./narrator-tamper-audit.ps1 -ReportPath ./narrator-audit.json

# Remove Image File Execution Options Debugger values
./narrator-tamper-audit.ps1 -ReportPath ./narrator-audit.json -Apply

# Preview what -Apply would remove
./narrator-tamper-audit.ps1 -ReportPath ./narrator-audit.json -Apply -WhatIf
```

The script exits with code 1 while findings remain. Signature and ACL findings are never changed automatically. Treat them as a possible compromise and investigate the host.

## Unverified
- The internal mechanism of FastUnlock was not verified. The script checks generic tampering of lock screen accessibility binaries and does not detect or block the exploit itself.
