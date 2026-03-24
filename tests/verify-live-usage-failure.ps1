Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$launcherPath = Join-Path $workspaceRoot "skills\codex-subagent-orchestrator\scripts\start-codex-subagent-team.ps1"
$mockCodexPath = Join-Path $workspaceRoot "tests\fixtures\mock-codex-fail.cmd"
$usageHelperPath = Join-Path $workspaceRoot "usage.ps1"
$artifactRoot = Join-Path $workspaceRoot ("tests\artifacts\live-usage-failure-" + ([guid]::NewGuid().ToString("N")))
$outputDir = Join-Path $artifactRoot "run"
$specPath = Join-Path $artifactRoot "live-usage-failure-spec.json"
$statusFile = Join-Path $outputDir "orchestration-usage.json"
$manifestFile = Join-Path $outputDir "orchestration-manifest.json"
$launcherStdout = Join-Path $artifactRoot "launcher.stdout.txt"
$launcherStderr = Join-Path $artifactRoot "launcher.stderr.txt"
$expectedMessage = "stream disconnected before completion: error sending request for url (https://api.openai.com/v1/responses)"

New-Item -ItemType Directory -Path $artifactRoot -Force | Out-Null

$spec = [ordered]@{
    cwd = $workspaceRoot
    output_dir = $outputDir
    manifest_file = $manifestFile
    skip_git_repo_check = $true
    execution_mode = "sequential"
    write_run_archive = $false
    write_summary_file = $false
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
            name = "failing-worker"
            task = "Emit a semantic turn failure."
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

$snapshot = Get-Content -LiteralPath $statusFile -Raw | ConvertFrom-Json
if ($snapshot.completed_workers -ne 0) {
    throw "Expected no completed workers, got $($snapshot.completed_workers)."
}
if ($snapshot.failed_workers -ne 1) {
    throw "Expected one failed worker, got $($snapshot.failed_workers)."
}
if ($snapshot.workers[0].status -ne "failed") {
    throw "Expected worker status=failed, got $($snapshot.workers[0].status)."
}
if ($snapshot.workers[0].last_error -ne $expectedMessage) {
    throw "Expected live usage last_error to match semantic failure, got '$($snapshot.workers[0].last_error)'."
}

$manifest = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
if ($manifest.results[0].succeeded) {
    throw "Expected semantic failure to produce succeeded=false."
}
if (-not $manifest.results[0].turn_failed) {
    throw "Expected manifest result turn_failed=true."
}
if ($manifest.results[0].failure_message -ne $expectedMessage) {
    throw "Expected manifest failure_message to match semantic failure, got '$($manifest.results[0].failure_message)'."
}
if (@($manifest.results[0].validation_failures) -notcontains "worker reported turn.failed: $expectedMessage") {
    throw "Expected validation_failures to include the turn.failed message."
}

$usageOutput = @(
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File $usageHelperPath -StatusFile $statusFile -Once
)
$usageText = $usageOutput -join [Environment]::NewLine
if ($usageText -notmatch 'failing-worker status=failed tokens=n/a') {
    throw "usage helper did not report the expected failed worker line. Output: $usageText"
}
if ($usageText -notmatch [regex]::Escape($expectedMessage)) {
    throw "usage helper did not report the semantic failure message. Output: $usageText"
}

Write-Output "Live usage failure verification passed."
