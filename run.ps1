# Open Transfer — one-command launcher for Windows (PowerShell).
#
#   .\run.ps1                  share .\uploads on port 5000
#   .\run.ps1 C:\Share --pin   any open-transfer option works
#
# If scripts are blocked, run once:  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$venv = ".venv"
$stamp = Join-Path $venv ".open-transfer-installed"
# Windows venvs use Scripts\*.exe; PowerShell on macOS/Linux gets bin/*.
$onWindows = $env:OS -eq "Windows_NT"
$bin = if ($onWindows) { Join-Path $venv "Scripts" } else { Join-Path $venv "bin" }
$exe = if ($onWindows) { ".exe" } else { "" }
$python = Join-Path $bin "python$exe"

$needsInstall = -not (Test-Path $stamp) -or ((Get-Item "pyproject.toml").LastWriteTime -gt (Get-Item $stamp).LastWriteTime)
if ($needsInstall) {
    Write-Host "  Setting up Open Transfer (first run only)..."
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        if (-not (Test-Path $python)) { uv venv -q --python ">=3.10" $venv }
        uv pip install -q --python $python -e .
    } else {
        $py = $null
        # "python" first: the "py" launcher can stop on an interactive first-run prompt.
        foreach ($candidate in @("python", "python3", "py -3")) {
            $cmd, $rest = $candidate.Split(" ")
            if (Get-Command $cmd -ErrorAction SilentlyContinue) {
                & $cmd @rest -c "import sys; sys.exit(sys.version_info < (3, 10))" 2>$null
                if ($LASTEXITCODE -eq 0) { $py = $candidate; break }
            }
        }
        if (-not $py) {
            Write-Host "  Open Transfer needs Python 3.10 or newer: https://www.python.org/downloads/"
            exit 1
        }
        $cmd, $rest = $py.Split(" ")
        if (-not (Test-Path $python)) { & $cmd @rest -m venv $venv }
        & $python -m pip install -q --disable-pip-version-check -e .
    }
    New-Item -ItemType File -Force -Path $stamp | Out-Null
}

& (Join-Path $bin "open-transfer$exe") @args
exit $LASTEXITCODE
