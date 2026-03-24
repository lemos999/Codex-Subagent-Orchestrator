Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$launcherPath = Join-Path $workspaceRoot "skills\codex-subagent-orchestrator\scripts\start-codex-subagent-team.ps1"
$mockCodexPath = Join-Path $workspaceRoot "tests\fixtures\mock-codex.cmd"
$usageHelperPath = Join-Path $workspaceRoot "usage.ps1"
$artifactRoot = Join-Path $workspaceRoot ("tests\artifacts\live-usage-" + ([guid]::NewGuid().ToString("N")))
$outputDir = Join-Path $artifactRoot "run"
$specPath = Join-Path $artifactRoot "live-usage-spec.json"
$statusFile = Join-Path $outputDir "orchestration-usage.json"
$manifestFile = Join-Path $outputDir "orchestration-manifest.json"
$summaryFile = Join-Path $outputDir "orchestration-summary.md"
$launcherStdout = Join-Path $artifactRoot "launcher.stdout.txt"
$launcherStderr = Join-Path $artifactRoot "launcher.stderr.txt"

New-Item -ItemType Directory -Path $artifactRoot -Force | Out-Null

$spec = [ordered]@{
    cwd = $workspaceRoot
    output_dir = $outputDir
    manifest_file = $manifestFile
    summary_file = $summaryFile
    skip_git_repo_check = $true
    execution_mode = "sequential"
    write_run_archive = $false
    write_prompt_files = $true
    write_summary_file = $true
    live_usage = [ordered]@{
        enabled = $true
        display_mode = "file"
        status_file = $statusFile
        poll_interval_ms = 200
    }
    defaults = [ordered]@{
        sandbox = "read-only"
        reasoning_effort = "low"
    }
    agents = @(
        [ordered]@{
            name = "mock-worker"
            task = "Return a bounded mock response."
            validation = @(
                "The mock worker must finish successfully."
            )
        }
    )
}

$spec | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $specPath -Encoding utf8

$process = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $launcherPath,
        "-SpecPath",
        $specPath,
        "-CodexExecutable",
        $mockCodexPath,
        "-AsJson"
    ) `
    -WorkingDirectory $workspaceRoot `
    -RedirectStandardOutput $launcherStdout `
    -RedirectStandardError $launcherStderr `
    -PassThru

$deadline = (Get-Date).AddSeconds(10)
$midRunTokens = $null
while ((Get-Date) -lt $deadline) {
    $process.Refresh()
    if (Test-Path -LiteralPath $statusFile) {
        $snapshot = Get-Content -LiteralPath $statusFile -Raw | ConvertFrom-Json
        if (-not $process.HasExited -and $null -ne $snapshot.total_known_tokens) {
            $midRunTokens = [int64]$snapshot.total_known_tokens
            break
        }
    }

    Start-Sleep -Milliseconds 150
}

if ($null -eq $midRunTokens) {
    throw "Did not observe a live usage snapshot before launcher exit. Stdout: $(Get-Content -LiteralPath $launcherStdout -Raw) Stderr: $(Get-Content -LiteralPath $launcherStderr -Raw)"
}

if ($midRunTokens -ne 65) {
    throw "Expected mid-run live usage total to be 65 tokens, got $midRunTokens."
}

$null = $process.WaitForExit(10000)
if (-not $process.HasExited) {
    Stop-Process -Id $process.Id -Force
    throw "Launcher did not exit within timeout."
}

$process.Refresh()
$exitCode = if ($null -ne $process.ExitCode) { [int]$process.ExitCode } else { 0 }
if ($exitCode -ne 0) {
    throw "Launcher failed with exit code $exitCode. Stdout: $(Get-Content -LiteralPath $launcherStdout -Raw) Stderr: $(Get-Content -LiteralPath $launcherStderr -Raw)"
}

$finalSnapshot = Get-Content -LiteralPath $statusFile -Raw | ConvertFrom-Json
if ([int64]$finalSnapshot.total_known_tokens -ne 321) {
    throw "Expected final live usage total to be 321 tokens, got $($finalSnapshot.total_known_tokens)."
}

$manifest = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
if (-not $manifest.live_usage.enabled) {
    throw "Manifest did not record live usage as enabled."
}
if ($manifest.live_usage.status_file -ne $statusFile) {
    throw "Manifest live usage status file mismatch. Expected '$statusFile' but got '$($manifest.live_usage.status_file)'."
}
if ([int64]$manifest.results[0].footer_tokens_used -ne 321) {
    throw "Manifest footer token count mismatch. Expected 321 but got $($manifest.results[0].footer_tokens_used)."
}
if (-not $manifest.results[0].requested_json_output) {
    throw "Live usage should force JSON worker output, but manifest recorded requested_json_output=false."
}

$summaryText = Get-Content -LiteralPath $summaryFile -Raw
if ($summaryText -notmatch 'live_usage_enabled: True') {
    throw "Summary file is missing live usage status."
}
if ($summaryText -notmatch 'live_usage_status_file:') {
    throw "Summary file is missing live usage status file path."
}

$usageOutput = @(
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File $usageHelperPath -StatusFile $statusFile -Once
)
$usageText = $usageOutput -join [Environment]::NewLine
if ($usageText -notmatch 'Total known tokens: 321') {
    throw "usage helper did not report the expected token total. Output: $usageText"
}
if ($usageText -notmatch 'mock-worker status=completed tokens=321') {
    throw "usage helper did not report the expected worker line. Output: $usageText"
}

Write-Output "Live usage verification passed."
