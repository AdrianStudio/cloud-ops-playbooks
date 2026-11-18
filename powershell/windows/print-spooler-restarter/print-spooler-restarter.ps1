<#
.SYNOPSIS
    Restarts the Print Spooler service on a remote computer.

.DESCRIPTION
    This script connects to a specified remote computer and checks the status of the Print Spooler service.
    If the service is running, it can optionally restart it to resolve common printing issues.
    By default, the script only reports the current status. The -Apply switch is required to perform the restart.

.PARAMETER ComputerName
    The hostname or IP address of the remote computer where the Print Spooler service will be managed.

.PARAMETER Apply
    A switch parameter that, when present, instructs the script to restart the Print Spooler service.
    If omitted, the script will only report the current status of the service.

.EXAMPLE
    Restart-PrintSpooler -ComputerName 'ClientPC01'
    Reports the status of the Print Spooler service on 'ClientPC01' without restarting it.

.EXAMPLE
    Restart-PrintSpooler -ComputerName 'ClientPC01' -Apply
    Restarts the Print Spooler service on 'ClientPC01'.

.NOTES
    Requires administrative privileges on the target computer for remote service management.
    Ensure PowerShell Remoting (WinRM) is configured and enabled on the target computer.
#>
function Restart-PrintSpooler {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param (
        [Parameter(Mandatory = $true)]
        [string]$ComputerName,

        [switch]$Apply
    )

    try {
        Write-Host "Checking Print Spooler service on $ComputerName..."
        $service = Get-Service -Name 'Spooler' -ComputerName $ComputerName -ErrorAction Stop

        Write-Host "Current status of Print Spooler on $ComputerName: $($service.Status)"

        if ($Apply) {
            if ($PSCmdlet.ShouldProcess("$ComputerName", "Restart Print Spooler service")) {
                if ($service.Status -eq 'Running') {
                    Write-Host "Stopping Print Spooler service on $ComputerName..."
                    Stop-Service -InputObject $service -ErrorAction Stop
                    $service.WaitForStatus('Stopped', (New-TimeSpan -Seconds 30))
                    Write-Host "Print Spooler service stopped on $ComputerName."
                }

                Write-Host "Starting Print Spooler service on $ComputerName..."
                Start-Service -InputObject $service -ErrorAction Stop
                $service.WaitForStatus('Running', (New-TimeSpan -Seconds 30))
                Write-Host "Print Spooler service started on $ComputerName."

                $updatedService = Get-Service -Name 'Spooler' -ComputerName $ComputerName -ErrorAction Stop
                Write-Host "New status of Print Spooler on $ComputerName: $($updatedService.Status)"
            }
        } else {
            Write-Host "To restart the service, run the command with the -Apply switch."
        }
    }
    catch [System.ServiceProcess.TimeoutException] {
        Write-Error "Service operation timed out on $ComputerName: $($_.Exception.Message)"
    }
    catch [System.Management.Automation.Remoting.PSRemotingTransportException] {
        Write-Error "Failed to connect to $ComputerName. Ensure WinRM is enabled and firewall allows access: $($_.Exception.Message)"
    }
    catch [System.Management.Automation.RuntimeException] {
        Write-Error "An error occurred while managing the Print Spooler service on $ComputerName: $($_.Exception.Message)"
    }
    catch [System.Exception] {
        Write-Error "An unexpected error occurred on $ComputerName: $($_.Exception.Message)"
    }
}
