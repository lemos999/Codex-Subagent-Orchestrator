$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$MtsRoot = Join-Path $RepoRoot "Projects\Trading Value\MTS-V1"
$UvArchive = Join-Path $env:LOCALAPPDATA "uv\cache\archive-v0"

$PytestPaths = @(
    (Join-Path $UvArchive "ioR2T95oQtbiEEcYZHQsf"),
    (Join-Path $UvArchive "jkcvJfasvWPVO4AT6kZ0y"),
    (Join-Path $UvArchive "7EXsSUAxn9U8TzETknwog"),
    (Join-Path $UvArchive "n2WXXXj1qPcskxoVCqP_z"),
    (Join-Path $UvArchive "nDdym7qhDkC1ihPfOwnaj"),
    (Join-Path $UvArchive "CNSpvPzA-NHsgi5LMHbHI")
)
$MissingPytestPaths = $PytestPaths | Where-Object { -not (Test-Path -LiteralPath $_) }
if ($MissingPytestPaths) {
    throw "Missing cached pytest dependency paths: $($MissingPytestPaths -join ', ')"
}

$RuffExe = Join-Path $UvArchive "BV_ZSK4hjXHOS1vMkUF9r\ruff-0.15.12.data\scripts\ruff.exe"
if (-not (Test-Path -LiteralPath $RuffExe)) {
    throw "Missing cached ruff executable: $RuffExe"
}

$env:PYTHONPATH = ($PytestPaths -join ";")
$env:UV_CACHE_DIR = Join-Path $MtsRoot ".uv-cache"

Push-Location $MtsRoot
try {
    uv run --no-project python -m pytest tests/test_core5_parity_report.py tests/test_btc_parity_diff.py tests/test_btc_parity_trace.py -q -p no:cacheprovider
    & $RuffExe check btc_parity_diff.py btc_parity_trace.py core5_parity_report.py tests/test_btc_parity_diff.py tests/test_core5_parity_report.py tests/test_btc_parity_trace.py
    uv run --no-project python -m py_compile btc_parity_diff.py btc_parity_trace.py core5_parity_report.py
    uv run --no-project python core5_parity_report.py --runs-dir runs --samples-dir samples --report parity_reports/core5_parity.md --bar-seconds 900 --examples 32 --gate baseline
    uv run --no-project python ..\..\..\subagent-runs\mts-v1-parity\sol-state2-diagnosis\verify_task.py
}
finally {
    Pop-Location
}
