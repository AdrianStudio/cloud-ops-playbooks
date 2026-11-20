<#
.SYNOPSIS
Audits the Narrator and Ease of Access binaries that run on the Windows lock screen for tampering.

.DESCRIPTION
Checks Narrator.exe and the other accessibility executables started from the lock screen for:
  - an Image File Execution Options Debugger value (native and Wow6432Node views)
  - a missing or non-Microsoft Authenticode signature
  - write, delete or permission-change access for anyone other than TrustedInstaller

The run is read-only by default. With -Apply, only the Image File Execution Options
Debugger values are removed. Signature and ACL findings are reported and need manual
investigation, since a modified binary means the host may be compromised.
The findings and the removed Debugger values are written to a JSON file.
Exits with code 1 when findings remain after the run.

.PARAMETER ReportPath
Path of the JSON report to write.

.PARAMETER Apply
Remove Debugger values found under Image File Execution Options. Supports -WhatIf and -Confirm.

.EXAMPLE
./narrator-tamper-audit.ps1 -ReportPath ./narrator-audit.json

.EXAMPLE
./narrator-tamper-audit.ps1 -ReportPath ./narrator-audit.json -Apply
#>
#Requires -Version 7.0
#Requires -RunAsAdministrator
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [string]$ReportPath,

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$accessibilityBinaries = @('Narrator.exe', 'Utilman.exe', 'sethc.exe', 'osk.exe', 'Magnify.exe', 'DisplaySwitch.exe', 'AtBroker.exe')
$ifeoRoots = @(
    'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\Image File Execution Options'
)
$trustedInstaller = 'NT SERVICE\TrustedInstaller'
$modifyRights = [System.Security.AccessControl.FileSystemRights]'WriteData, AppendData, Delete, ChangePermissions, TakeOwnership'
$systemDirectory = [System.Environment]::SystemDirectory

$findings = [System.Collections.Generic.List[object]]::new()

foreach ($binaryName in $accessibilityBinaries) {
    # A Debugger value makes Winlogon start another program in place of the accessibility tool, as SYSTEM, before sign-in.
    foreach ($ifeoRoot in $ifeoRoots) {
        $ifeoKeyPath = Join-Path $ifeoRoot $binaryName
        if (-not (Test-Path -LiteralPath $ifeoKeyPath)) {
            continue
        }
        $ifeoKey = Get-Item -LiteralPath $ifeoKeyPath
        if ($ifeoKey.GetValueNames() -contains 'Debugger') {
            $findings.Add([pscustomobject]@{
                Check       = 'IfeoDebugger'
                Target      = $ifeoKeyPath
                Detail      = $ifeoKey.GetValue('Debugger')
                Remediation = 'Removable with -Apply'
                Removed     = $false
            })
        }
    }

    $binaryPath = Join-Path $systemDirectory $binaryName

    $signature = Get-AuthenticodeSignature -LiteralPath $binaryPath
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
        $findings.Add([pscustomobject]@{
            Check       = 'InvalidSignature'
            Target      = $binaryPath
            Detail      = "Signature status $($signature.Status)"
            Remediation = 'Manual: restore the file with sfc /scannow and investigate the host'
            Removed     = $false
        })
    }

    $binaryAcl = Get-Acl -LiteralPath $binaryPath
    $unexpectedWriters = $binaryAcl.Access | Where-Object {
        $_.AccessControlType -eq 'Allow' -and
        $_.IdentityReference.Value -ne $trustedInstaller -and
        [int]($_.FileSystemRights -band $modifyRights) -ne 0
    }
    foreach ($writeRule in $unexpectedWriters) {
        $findings.Add([pscustomobject]@{
            Check       = 'WritableBinary'
            Target      = $binaryPath
            Detail      = "$($writeRule.IdentityReference.Value) has $($writeRule.FileSystemRights)"
            Remediation = 'Manual: restore the default ACL and investigate the host'
            Removed     = $false
        })
    }
}

if ($Apply) {
    $debuggerFindings = $findings | Where-Object { $_.Check -eq 'IfeoDebugger' }
    foreach ($debuggerFinding in $debuggerFindings) {
        if ($PSCmdlet.ShouldProcess($debuggerFinding.Target, 'Remove Debugger value')) {
            Remove-ItemProperty -LiteralPath $debuggerFinding.Target -Name 'Debugger'
            $debuggerFinding.Removed = $true
        }
    }
}

$audit = [pscustomobject]@{
    ComputerName = [System.Environment]::MachineName
    OsVersion    = [System.Environment]::OSVersion.Version.ToString()
    CheckedAt    = (Get-Date).ToUniversalTime().ToString('o')
    ApplyMode    = [bool]$Apply
    Findings     = $findings
}
$audit | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ReportPath -Encoding utf8

$findings | Format-Table Check, Target, Detail, Removed -AutoSize | Out-String | Write-Host

$remainingFindings = $findings | Where-Object { -not $_.Removed }
if ($remainingFindings) {
    Write-Warning "$(@($remainingFindings).Count) finding(s) remain. Report written to $ReportPath"
    exit 1
}
Write-Host "No findings. Report written to $ReportPath"
