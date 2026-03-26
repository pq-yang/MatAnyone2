param(
    [string]$ServiceRoot = "",
    [string]$RuntimeRoot = "",
    [int]$Port = 8010
)

. (Join-Path $PSScriptRoot "internal_webapp_common.ps1")

$config = Get-InternalWebAppServiceConfig `
    -ScriptRoot $PSScriptRoot `
    -ServiceRoot $ServiceRoot `
    -RuntimeRoot $RuntimeRoot `
    -Port $Port

$state = Read-InternalWebAppState -StateFile $config.state_file
if ($null -eq $state) {
    Write-InternalWebAppJson @{
        status = "not_running"
        service_root = $config.service_root
        state_file = $config.state_file
    }
    exit 1
}

$webappAlive = Test-InternalWebAppProcess -ProcessId ([int]$state.webapp_pid)
$workerAlive = Test-InternalWebAppProcess -ProcessId ([int]$state.worker_pid)
$httpOk = $false
$httpStatus = $null
try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $state.base_url -TimeoutSec 10
    $httpStatus = [int]$response.StatusCode
    $httpOk = ($httpStatus -eq 200)
} catch {
    $httpStatus = $null
}

if ($webappAlive -and $workerAlive -and $httpOk) {
    Write-InternalWebAppJson @{
        status = "running"
        base_url = $state.base_url
        service_root = $state.service_root
        state_file = $config.state_file
        webapp_pid = [int]$state.webapp_pid
        worker_pid = [int]$state.worker_pid
        http_status = $httpStatus
    }
    exit 0
}

Write-InternalWebAppJson @{
    status = "degraded"
    base_url = $state.base_url
    service_root = $state.service_root
    state_file = $config.state_file
    webapp_pid = [int]$state.webapp_pid
    worker_pid = [int]$state.worker_pid
    webapp_alive = $webappAlive
    worker_alive = $workerAlive
    http_status = $httpStatus
}
exit 1
