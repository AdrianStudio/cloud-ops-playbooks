# Server Dependency Mapper

A PowerShell 7 script that inventories scheduled scripts and live connections on Windows hosts that depend on critical servers such as an ERP, a database or a file share.

## Problem

Business-critical scripts often run on forgotten, unmanaged PCs that appear in no CMDB, backup or monitoring list. Shutting such a host down breaks a process nobody knew existed, and the only check today is a scream test. Periodic jobs (one SMB connection every few minutes) are easy to miss in a short look at network traffic.

## Prerequisites

- PowerShell 7 on the machine running the script.
- No environment variables are read.
- WinRM (PowerShell remoting) enabled on every target host.
- An account that is local administrator on the targets. It is needed for SMB session listing, process command lines and reading scheduled task definitions.
- Targets running Windows 8, Server 2012 or later (ScheduledTasks, SmbShare and CIM networking cmdlets).
- Critical server names must resolve in DNS from the machine running the script. Use the names clients use to reach them, because SMB sessions are matched on that name.
- The observation window must be longer than the slowest job interval.
- Linux endpoints are not covered.

## Usage

```powershell
# Report only: output to the pipeline, nothing is written
./server-dependency-mapper.ps1 -ComputerName <host1>,<host2> -CriticalServer <erp-server>,<sql-server>

# Longer observation window and JSON report saved to disk
./server-dependency-mapper.ps1 -ComputerName <host1>,<host2> -CriticalServer <erp-server>,<sql-server> -ObservationMinutes 15 -OutputPath ./inventory.json -Apply
```
