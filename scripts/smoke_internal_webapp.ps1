param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$pythonPath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot ".venv\Scripts\python.exe"))

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Missing python executable: $pythonPath"
}

& $pythonPath (Join-Path $repoRoot "scripts\smoke_internal_webapp.py") @Args
exit $LASTEXITCODE
