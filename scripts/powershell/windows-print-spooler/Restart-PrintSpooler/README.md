# Restart-PrintSpooler
Restarts the Print Spooler service on a remote computer.

## Problem
Clients with many printers often experience frequent printing issues, leading to a high volume of support tickets. Many of these issues can be resolved by simply restarting the Print Spooler service, but this often requires manual intervention.

## Prerequisites
*   `ComputerName`: The target computer must be accessible over the network.
*   PowerShell Remoting (WinRM) must be configured and enabled on the target computer.
*   The executing user account requires administrative privileges on the target computer to manage services.
*   PowerShell 7 or later.

## Usage
```powershell
./Restart-PrintSpooler.ps1 -ComputerName 'ClientPC01'
```
```powershell
./Restart-PrintSpooler.ps1 -ComputerName 'ClientPC01' -Apply
```
