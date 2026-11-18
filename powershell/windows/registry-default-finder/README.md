# registry-default-finder
Retrieves the default value for specified registry keys from a clean Windows installation.

## Problem
Administrators need to revert registry changes that enabled Print Nightmare, but the default values for modified keys are unknown. Manually comparing against a clean OS installation is time-consuming and error-prone.

## Prerequisites
* `PSRemoting` enabled on the `ReferenceComputerName` if a remote machine is used.
* The account running the script needs read access to the specified registry keys on both the local and reference machines.
* PowerShell 7 or higher.

## Usage
The script defines the `Get-RegistryDefaultValue` function. Load it into the session, then call it:

```powershell
. ./registry-default-finder.ps1
Get-RegistryDefaultValue -RegistryKeys 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Printers\PointAndPrint\RestrictDriverInstallationToAdministrators'
Get-RegistryDefaultValue -RegistryKeys 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Printers\PointAndPrint\RestrictDriverInstallationToAdministrators', 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Printers\PointAndPrint\NoWarningNoElevationOnInstall' -ReferenceComputerName 'CleanVM01'
Get-RegistryDefaultValue -RegistryKeys 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Printers\PointAndPrint\RestrictDriverInstallationToAdministrators' -Apply
```
