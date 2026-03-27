$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PreferredPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$FallbackPython = "D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe"

function Test-DesktopWorkbenchPython {
    param([string]$PythonPath)

    if (-not (Test-Path $PythonPath)) {
        return $false
    }

    & $PythonPath -c "import numpy, cv2, PySide6, torch, fastapi" *> $null
    return ($LASTEXITCODE -eq 0)
}

if (Test-DesktopWorkbenchPython -PythonPath $PreferredPython) {
    $Python = $PreferredPython
} elseif (Test-DesktopWorkbenchPython -PythonPath $FallbackPython) {
    $Python = $FallbackPython
} else {
    throw "No usable Python environment found for the desktop workbench."
}

Start-Process -FilePath $Python -ArgumentList "scripts\run_desktop_workbench.py" -WorkingDirectory $ProjectRoot
