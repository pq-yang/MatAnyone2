param(
    [string]$ServiceRoot = "",
    [string]$RuntimeRoot = "",
    [int]$Port = 8010,
    [switch]$DryRun
)

. (Join-Path $PSScriptRoot "internal_webapp_common.ps1")

$config = Get-InternalWebAppServiceConfig `
    -ScriptRoot $PSScriptRoot `
    -ServiceRoot $ServiceRoot `
    -RuntimeRoot $RuntimeRoot `
    -Port $Port

$state = Read-InternalWebAppState -StateFile $config.state_file
$stoppedPids = @()

if ($null -eq $state) {
    $fallbackPids = @(Get-InternalWebAppManagedProcesses -RepoRoot $config.repo_root | Select-Object -ExpandProperty ProcessId -Unique)
    if ($DryRun) {
        Write-InternalWebAppJson @{
            status = if ($fallbackPids.Count -gt 0) { "dry_run" } else { "not_running" }
            service_root = $config.service_root
            state_file = $config.state_file
            candidate_pids = $fallbackPids
        }
        exit 0
    }

    foreach ($processId in $fallbackPids) {
        if (Stop-InternalWebAppProcessTree -ProcessId $processId) {
            $stoppedPids += $processId
        }
    }

    Write-InternalWebAppJson @{
        status = if ($stoppedPids.Count -gt 0) { "stopped" } else { "not_running" }
        service_root = $config.service_root
        state_file = $config.state_file
        stopped_pids = $stoppedPids
    }
    exit 0
}

$candidatePids = @([int]$state.webapp_pid, [int]$state.worker_pid) | Where-Object { $_ -gt 0 } | Select-Object -Unique
if ($DryRun) {
    Write-InternalWebAppJson @{
        status = if ($candidatePids.Count -gt 0) { "dry_run" } else { "not_running" }
        service_root = $config.service_root
        state_file = $config.state_file
        candidate_pids = $candidatePids
    }
    exit 0
}

foreach ($processId in $candidatePids) {
    if (Stop-InternalWebAppProcessTree -ProcessId $processId) {
        $stoppedPids += $processId
    }
}

Remove-Item -LiteralPath $config.state_file -Force -ErrorAction SilentlyContinue
Write-InternalWebAppJson @{
    status = "stopped"
    service_root = $config.service_root
    state_file = $config.state_file
    stopped_pids = $stoppedPids
}
