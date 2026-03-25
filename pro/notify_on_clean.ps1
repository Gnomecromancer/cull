# notify_on_clean.ps1
# Runs cull, then shows a Windows toast notification with how much was freed.
# Use this as the scheduled task action instead of calling cull directly —
# you'll get a "devcull freed 1.2 GB" notification instead of a silent cleanup.
#
# Usage (in Task Scheduler action):
#   powershell.exe -WindowStyle Hidden -File "C:\path\to\notify_on_clean.ps1" -Path "C:\dev"

param(
    [string]$Path       = "$env:USERPROFILE\IdeaProjects",
    [int]$OlderThan     = 90,
    [int]$MinSize       = 0
)

$cull = Get-Command cull -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $cull) { exit 1 }

# capture the report to a temp file so we can read totals
$tmp = [System.IO.Path]::GetTempFileName() + ".json"
$args = @("--older-than", $OlderThan, "--report", $tmp)
if ($MinSize -gt 0) { $args += @("--min-size", $MinSize) }
$args += @("--all", $Path)

# suppress interactive prompt by piping 'y'
echo "y" | & $cull @args 2>&1 | Out-Null

if (-not (Test-Path $tmp)) { exit 0 }

try {
    $report = Get-Content $tmp | ConvertFrom-Json
    $hits = $report.hits.Count
    if ($hits -eq 0) { Remove-Item $tmp; exit 0 }

    $totalBytes = ($report.hits | Measure-Object -Property size_bytes -Sum).Sum
    $totalMB = [math]::Round($totalBytes / 1MB, 1)
    $msg = "Freed $totalMB MB across $hits dirs in $Path"

    # Windows toast via BurntToast if available, else balloon tip fallback
    if (Get-Module -ListAvailable -Name BurntToast -ErrorAction SilentlyContinue) {
        Import-Module BurntToast
        New-BurntToastNotification -Text "devcull", $msg
    } else {
        # fallback: system tray balloon (works without extra deps)
        Add-Type -AssemblyName System.Windows.Forms
        $balloon = New-Object System.Windows.Forms.NotifyIcon
        $balloon.Icon = [System.Drawing.SystemIcons]::Information
        $balloon.BalloonTipIcon = "Info"
        $balloon.BalloonTipTitle = "devcull"
        $balloon.BalloonTipText = $msg
        $balloon.Visible = $true
        $balloon.ShowBalloonTip(5000)
        Start-Sleep -Seconds 6
        $balloon.Dispose()
    }
} finally {
    Remove-Item $tmp -ErrorAction SilentlyContinue
}
