function Get-InternalWebAppRepoRoot {
    param(
        [string]$ScriptRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path $ScriptRoot ".."))
}

function Get-InternalWebAppPythonPath {
    param(
        [string]$RepoRoot
    )

    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot ".venv\Scripts\python.exe"))
}

function Get-InternalWebAppServiceConfig {
    param(
        [string]$ScriptRoot,
        [string]$ServiceRoot,
        [string]$RuntimeRoot,
        [int]$Port
    )

    $repoRoot = Get-InternalWebAppRepoRoot -ScriptRoot $ScriptRoot
    $resolvedServiceRoot = if ($ServiceRoot) {
        [System.IO.Path]::GetFullPath($ServiceRoot)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot "runtime\webapp-service"))
    }
    $resolvedRuntimeRoot = if ($RuntimeRoot) {
        [System.IO.Path]::GetFullPath($RuntimeRoot)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $resolvedServiceRoot "runtime"))
    }
    $logsDir = [System.IO.Path]::GetFullPath((Join-Path $resolvedServiceRoot "logs"))

    return @{
        repo_root = $repoRoot
        service_root = $resolvedServiceRoot
        runtime_root = $resolvedRuntimeRoot
        logs_dir = $logsDir
        state_file = [System.IO.Path]::GetFullPath((Join-Path $resolvedServiceRoot "service.json"))
        database_path = [System.IO.Path]::GetFullPath((Join-Path $resolvedRuntimeRoot "jobs.db"))
        base_url = "http://127.0.0.1:$Port"
        port = $Port
        python_path = Get-InternalWebAppPythonPath -RepoRoot $repoRoot
        webapp_stdout = [System.IO.Path]::GetFullPath((Join-Path $logsDir "webapp.out.log"))
        webapp_stderr = [System.IO.Path]::GetFullPath((Join-Path $logsDir "webapp.err.log"))
        worker_stdout = [System.IO.Path]::GetFullPath((Join-Path $logsDir "worker.out.log"))
        worker_stderr = [System.IO.Path]::GetFullPath((Join-Path $logsDir "worker.err.log"))
    }
}

function ConvertTo-CompactJson {
    param(
        [Parameter(ValueFromPipeline = $true)]
        [object]$InputObject
    )

    process {
        return $InputObject | ConvertTo-Json -Depth 8 -Compress
    }
}

function Write-InternalWebAppJson {
    param(
        [hashtable]$Payload
    )

    $Payload | ConvertTo-CompactJson | Write-Output
}

function Ensure-InternalWebAppDirectories {
    param(
        [hashtable]$Config
    )

    foreach ($path in @($Config.service_root, $Config.runtime_root, $Config.logs_dir)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

function Read-InternalWebAppState {
    param(
        [string]$StateFile
    )

    if (-not (Test-Path -LiteralPath $StateFile)) {
        return $null
    }
    return Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
}

function Write-InternalWebAppState {
    param(
        [string]$StateFile,
        [hashtable]$Payload
    )

    $json = $Payload | ConvertTo-Json -Depth 8
    Set-Content -LiteralPath $StateFile -Value $json -Encoding UTF8
}

function Test-InternalWebAppProcess {
    param(
        [int]$ProcessId
    )

    if ($ProcessId -le 0) {
        return $false
    }
    return $null -ne (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function Get-InternalWebAppManagedProcesses {
    param(
        [string]$RepoRoot
    )

    return Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and (
                $_.CommandLine -like "*$RepoRoot*" -and (
                    $_.CommandLine -like "*scripts.run_internal_webapp:app*" -or
                    $_.CommandLine -like "*scripts/run_internal_worker.py*" -or
                    $_.CommandLine -like "*scripts\\run_internal_worker.py*"
                )
            )
        }
}

function Stop-InternalWebAppProcessTree {
    param(
        [int]$ProcessId
    )

    if (-not (Test-InternalWebAppProcess -ProcessId $ProcessId)) {
        return $false
    }

    & taskkill /PID $ProcessId /T /F | Out-Null
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if (-not (Test-InternalWebAppProcess -ProcessId $ProcessId)) {
            return $true
        }
        Start-Sleep -Milliseconds 200
    }
    return -not (Test-InternalWebAppProcess -ProcessId $ProcessId)
}

function ConvertTo-PowerShellLiteral {
    param(
        [string]$Value
    )

    return "'" + $Value.Replace("'", "''") + "'"
}

function New-InternalWebAppCommand {
    param(
        [string]$PythonPath,
        [string[]]$PythonArguments,
        [string]$RepoRoot,
        [hashtable]$Environment,
        [string]$StdoutPath,
        [string]$StderrPath
    )

    $segments = @()
    foreach ($entry in $Environment.GetEnumerator()) {
        $segments += '$env:' + $entry.Key + ' = ' + (ConvertTo-PowerShellLiteral -Value $entry.Value)
    }
    $segments += 'Set-Location ' + (ConvertTo-PowerShellLiteral -Value $RepoRoot)

    $joinedArguments = ($PythonArguments | ForEach-Object {
        ConvertTo-PowerShellLiteral -Value $_
    }) -join ' '
    $command = '& ' + (ConvertTo-PowerShellLiteral -Value $PythonPath) + ' ' + $joinedArguments
    $command += ' 1>> ' + (ConvertTo-PowerShellLiteral -Value $StdoutPath)
    $command += ' 2>> ' + (ConvertTo-PowerShellLiteral -Value $StderrPath)
    $segments += $command

    return '& { ' + ($segments -join '; ') + ' }'
}
