# setup_weekly_clean_windows.ps1
# Registers a weekly Task Scheduler job that runs 'cull' on your dev folder.
# Run this script once, then forget about it.
#
# Usage:
#   .\setup_weekly_clean_windows.ps1 [-Path C:\dev] [-OlderThan 60] [-MinSize 50]
#
# Defaults: scans $HOME\IdeaProjects, removes caches older than 90 days, no size filter.

param(
    [string]$Path       = "$env:USERPROFILE\IdeaProjects",
    [int]$OlderThan     = 90,
    [int]$MinSize       = 0,
    [string]$TaskName   = "devcull-weekly"
)

$ErrorActionPreference = "Stop"

# find cull.exe (installed with 'pip install devcull')
$cull = Get-Command cull -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $cull) {
    Write-Error "cull not found. Run: pip install devcull"
    exit 1
}

$args = @("--older-than", $OlderThan, "--delete")
if ($MinSize -gt 0) { $args += @("--min-size", $MinSize) }
$args += $Path

$action = New-ScheduledTaskAction -Execute $cull -Argument ($args -join " ")
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "9:00AM"
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) -RunOnlyIfIdle $false

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Task '$TaskName' registered. cull will run every Sunday at 9am on $Path"
Write-Host "To remove: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
