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

$webappArgs = @(
    "-m",
    "uvicorn",
    "scripts.run_internal_webapp:app",
    "--host",
    "127.0.0.1",
    "--port",
    "$Port"
)
$workerArgs = @("scripts/run_internal_worker.py")

if ($DryRun) {
    Write-InternalWebAppJson @{
        status = "dry_run"
        service_root = $config.service_root
        runtime_root = $config.runtime_root
        state_file = $config.state_file
        python_path = $config.python_path
        base_url = $config.base_url
        webapp_args = $webappArgs
        worker_args = $workerArgs
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $config.python_path)) {
    throw "Missing python executable: $($config.python_path)"
}

Ensure-InternalWebAppDirectories -Config $config
$existingState = Read-InternalWebAppState -StateFile $config.state_file
if ($null -ne $existingState) {
    $webappAlive = Test-InternalWebAppProcess -ProcessId ([int]$existingState.webapp_pid)
    $workerAlive = Test-InternalWebAppProcess -ProcessId ([int]$existingState.worker_pid)
    if ($webappAlive -and $workerAlive) {
        Write-InternalWebAppJson @{
            status = "already_running"
            base_url = $existingState.base_url
            service_root = $config.service_root
            state_file = $config.state_file
            webapp_pid = [int]$existingState.webapp_pid
            worker_pid = [int]$existingState.worker_pid
        }
        exit 0
    }
}

$environment = @{
    MATANYONE2_WEBAPP_RUNTIME_ROOT = $config.runtime_root
    MATANYONE2_WEBAPP_DATABASE_PATH = $config.database_path
    MATANYONE2_WEBAPP_ENABLE_PRORES = "1"
    PYTHONIOENCODING = "utf-8"
}
if ($env:MATANYONE2_WEBAPP_SAM_MODEL_TYPE) {
    $environment["MATANYONE2_WEBAPP_SAM_MODEL_TYPE"] = $env:MATANYONE2_WEBAPP_SAM_MODEL_TYPE
}
if ($env:MATANYONE2_WEBAPP_SAM_BACKEND) {
    $environment["MATANYONE2_WEBAPP_SAM_BACKEND"] = $env:MATANYONE2_WEBAPP_SAM_BACKEND
}
if ($env:MATANYONE2_WEBAPP_SAM2_VARIANT) {
    $environment["MATANYONE2_WEBAPP_SAM2_VARIANT"] = $env:MATANYONE2_WEBAPP_SAM2_VARIANT
}
if ($env:MATANYONE2_WEBAPP_SAM2_CHECKPOINT_PATH) {
    $environment["MATANYONE2_WEBAPP_SAM2_CHECKPOINT_PATH"] = $env:MATANYONE2_WEBAPP_SAM2_CHECKPOINT_PATH
}

$webappCommand = New-InternalWebAppCommand `
    -PythonPath $config.python_path `
    -PythonArguments $webappArgs `
    -RepoRoot $config.repo_root `
    -Environment $environment `
    -StdoutPath $config.webapp_stdout `
    -StderrPath $config.webapp_stderr
$workerCommand = New-InternalWebAppCommand `
    -PythonPath $config.python_path `
    -PythonArguments $workerArgs `
    -RepoRoot $config.repo_root `
    -Environment $environment `
    -StdoutPath $config.worker_stdout `
    -StderrPath $config.worker_stderr

$webappProcess = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $webappCommand) `
    -WorkingDirectory $config.repo_root `
    -PassThru `
    -WindowStyle Hidden
$workerProcess = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $workerCommand) `
    -WorkingDirectory $config.repo_root `
    -PassThru `
    -WindowStyle Hidden

$state = @{
    repo_root = $config.repo_root
    service_root = $config.service_root
    runtime_root = $config.runtime_root
    logs_dir = $config.logs_dir
    state_file = $config.state_file
    base_url = $config.base_url
    port = $config.port
    python_path = $config.python_path
    webapp_pid = $webappProcess.Id
    worker_pid = $workerProcess.Id
    webapp_stdout = $config.webapp_stdout
    webapp_stderr = $config.webapp_stderr
    worker_stdout = $config.worker_stdout
    worker_stderr = $config.worker_stderr
}
Write-InternalWebAppState -StateFile $config.state_file -Payload $state
Write-InternalWebAppJson @{
    status = "started"
    base_url = $config.base_url
    service_root = $config.service_root
    state_file = $config.state_file
    webapp_pid = $webappProcess.Id
    worker_pid = $workerProcess.Id
}
