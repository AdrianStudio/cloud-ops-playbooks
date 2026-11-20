<#
.SYNOPSIS
Inventories jobs on Windows hosts that depend on critical servers.

.DESCRIPTION
Runs read-only collection on each target through PowerShell remoting. It reports:
- Enabled non-Microsoft scheduled tasks that run script files, with the critical
  servers named in the task command line or in the script content.
- SMB sessions and TCP connections to the critical servers, sampled over an
  observation window. The window must be longer than the slowest job interval
  (for example 4 minutes) for periodic jobs to appear.

The inventory is always written to the pipeline. Nothing on the targets is
changed. With -Apply the inventory is also saved as JSON to -OutputPath.

Requires local administrator rights on the targets (SMB sessions and process
command lines) and WinRM enabled on them. Targets need Windows 8 or Server 2012
or later. No environment variables are read.

.PARAMETER ComputerName
Hosts to inspect.

.PARAMETER CriticalServer
Host names of critical systems (ERP, databases, file servers), written the way
clients address them, because SMB sessions are matched on the name used.

.PARAMETER CriticalPort
Remote TCP ports that count as critical traffic.

.PARAMETER ObservationMinutes
Length of the passive observation window on each target.

.PARAMETER SampleIntervalSeconds
Pause between two samples of connections.

.PARAMETER OutputPath
JSON file written when -Apply is passed.

.PARAMETER Apply
Save the inventory to OutputPath.

.EXAMPLE
./server-dependency-mapper.ps1 -ComputerName pc01,pc02 -CriticalServer erp01,sql01

.EXAMPLE
./server-dependency-mapper.ps1 -ComputerName pc01,pc02 -CriticalServer erp01,sql01 -ObservationMinutes 15 -Apply
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string[]]$ComputerName,

    [Parameter(Mandatory)]
    [string[]]$CriticalServer,

    [Parameter(Mandatory = $false)]
    [ValidateRange(1, 65535)]
    [int[]]$CriticalPort = @(445, 1433, 1521, 3306, 5432),

    [Parameter(Mandatory = $false)]
    [ValidateRange(1, 1440)]
    [int]$ObservationMinutes = 10,

    [Parameter(Mandatory = $false)]
    [ValidateRange(5, 3600)]
    [int]$SampleIntervalSeconds = 30,

    [Parameter(Mandatory = $false)]
    [string]$OutputPath = './server-dependency-inventory.json',

    [switch]$Apply
)

$ErrorActionPreference = 'Stop'

$criticalAddress = @(foreach ($server in $CriticalServer) {
    [System.Net.Dns]::GetHostAddresses($server).IPAddressToString
})

$collectionScript = {
    param(
        [string[]]$CriticalServer,
        [string[]]$CriticalAddress,
        [int[]]$CriticalPort,
        [int]$ObservationMinutes,
        [int]$SampleIntervalSeconds
    )

    $ErrorActionPreference = 'Stop'

    # Quoted paths may contain spaces; unquoted ones end at the first whitespace.
    $scriptPathPattern = '"(?<path>[^"]+\.(?:ps1|bat|cmd|vbs|js|py))"|(?<path>(?:[A-Za-z]:\\|\\\\)[^\s"''<>|]+\.(?:ps1|bat|cmd|vbs|js|py))'
    $referenceTerms = @($CriticalServer) + @($CriticalAddress)

    $candidateTasks = Get-ScheduledTask |
        Where-Object { $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled' }

    $taskFindings = [System.Collections.Generic.List[object]]::new()
    foreach ($task in $candidateTasks) {
        $searchText = ''
        $commandLines = @()
        $scriptPaths = @()
        $missingScriptPaths = @()

        $execActions = $task.Actions | Where-Object { $_.CimClass.CimClassName -eq 'MSFT_TaskExecAction' }
        foreach ($action in $execActions) {
            $commandLine = [Environment]::ExpandEnvironmentVariables("$($action.Execute) $($action.Arguments)")
            $commandLines += $commandLine
            $searchText += $commandLine
            foreach ($match in [regex]::Matches($commandLine, $scriptPathPattern, 'IgnoreCase')) {
                $scriptPath = $match.Groups['path'].Value
                $scriptPaths += $scriptPath
                if (Test-Path -LiteralPath $scriptPath -PathType Leaf) {
                    $searchText += "`n" + (Get-Content -LiteralPath $scriptPath -Raw)
                }
                else {
                    $missingScriptPaths += $scriptPath
                }
            }
        }

        $referencedServers = @($referenceTerms | Where-Object { $searchText -match [regex]::Escape($_) })
        if ($scriptPaths.Count -eq 0 -and $referencedServers.Count -eq 0) {
            continue
        }

        $taskInfo = Get-ScheduledTaskInfo -InputObject $task
        $taskFindings.Add([pscustomobject]@{
            TaskPath                  = $task.TaskPath
            TaskName                  = $task.TaskName
            RunAs                     = $task.Principal.UserId
            CommandLines              = $commandLines
            ScriptPaths               = $scriptPaths
            MissingScriptPaths        = $missingScriptPaths
            ReferencedCriticalServers = $referencedServers
            LastRunTime               = $taskInfo.LastRunTime
            LastTaskResult            = $taskInfo.LastTaskResult
        })
    }

    $smbObservations = @{}
    $tcpObservations = @{}
    $sampleCount = [int][math]::Floor($ObservationMinutes * 60 / $SampleIntervalSeconds) + 1

    for ($sampleIndex = 0; $sampleIndex -lt $sampleCount; $sampleIndex++) {
        $sampleTime = Get-Date

        $criticalSmbConnections = Get-SmbConnection |
            Where-Object { $CriticalServer -contains $_.ServerName -or $CriticalAddress -contains $_.ServerName }
        foreach ($smbConnection in $criticalSmbConnections) {
            $observationKey = "$($smbConnection.ServerName)|$($smbConnection.ShareName)|$($smbConnection.UserName)"
            if (-not $smbObservations.ContainsKey($observationKey)) {
                $smbObservations[$observationKey] = [pscustomobject]@{
                    ServerName = $smbConnection.ServerName
                    ShareName  = $smbConnection.ShareName
                    UserName   = $smbConnection.UserName
                    FirstSeen  = $sampleTime
                    LastSeen   = $sampleTime
                    SampleHits = 0
                }
            }
            $smbObservations[$observationKey].LastSeen = $sampleTime
            $smbObservations[$observationKey].SampleHits++
        }

        # State 5 is Established. Process 4 is the kernel SMB client, already covered by Get-SmbConnection.
        $criticalTcpConnections = Get-CimInstance -Namespace 'root/StandardCimv2' -ClassName MSFT_NetTCPConnection -Filter 'State = 5' |
            Where-Object {
                $_.OwningProcess -ne 4 -and
                $CriticalAddress -contains $_.RemoteAddress -and
                $CriticalPort -contains $_.RemotePort
            }
        foreach ($tcpConnection in $criticalTcpConnections) {
            $ownerProcess = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($tcpConnection.OwningProcess)"
            # Short-lived jobs can exit between the two queries, leaving no process to describe.
            if ($null -eq $ownerProcess) {
                continue
            }
            $observationKey = "$($ownerProcess.Name)|$($tcpConnection.RemoteAddress)|$($tcpConnection.RemotePort)|$($ownerProcess.CommandLine)"
            if (-not $tcpObservations.ContainsKey($observationKey)) {
                $tcpObservations[$observationKey] = [pscustomobject]@{
                    ProcessName   = $ownerProcess.Name
                    ProcessPath   = $ownerProcess.ExecutablePath
                    CommandLine   = $ownerProcess.CommandLine
                    RemoteAddress = $tcpConnection.RemoteAddress
                    RemotePort    = $tcpConnection.RemotePort
                    FirstSeen     = $sampleTime
                    LastSeen      = $sampleTime
                    SampleHits    = 0
                }
            }
            $tcpObservations[$observationKey].LastSeen = $sampleTime
            $tcpObservations[$observationKey].SampleHits++
        }

        if ($sampleIndex -lt $sampleCount - 1) {
            Start-Sleep -Seconds $SampleIntervalSeconds
        }
    }

    [pscustomobject]@{
        ScheduledTasks = @($taskFindings)
        SmbSessions    = @($smbObservations.Values)
        TcpSessions    = @($tcpObservations.Values)
    }
}

$hostReports = Invoke-Command -ComputerName $ComputerName -ScriptBlock $collectionScript -ErrorAction Stop -ArgumentList $CriticalServer, $criticalAddress, $CriticalPort, $ObservationMinutes, $SampleIntervalSeconds

$inventory = foreach ($hostReport in $hostReports) {
    [pscustomobject]@{
        ComputerName   = $hostReport.PSComputerName
        ScheduledTasks = $hostReport.ScheduledTasks
        SmbSessions    = $hostReport.SmbSessions
        TcpSessions    = $hostReport.TcpSessions
    }
}

$inventory

if ($Apply) {
    ConvertTo-Json -InputObject @($inventory) -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding utf8
    Write-Verbose "Inventory written to $OutputPath"
}
