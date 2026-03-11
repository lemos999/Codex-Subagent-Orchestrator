param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutputRoot = (Split-Path -Parent (Resolve-Path (Join-Path $PSScriptRoot "..")).Path),
    [string]$RunLabel = ("deploy-" + (Get-Date -Format "yyyyMMdd-HHmmss")),
    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-Directory {
    param([string]$Path)

    New-Item -ItemType Directory -Path $Path -Force | Out-Null
    return $Path
}

function Assert-RequiredPath {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Required packaging input is missing: $Path"
    }
}

function Copy-AllowedPath {
    param(
        [string]$SourceRoot,
        [string]$RelativePath,
        [string]$DestinationRoot
    )

    $sourcePath = Join-Path $SourceRoot $RelativePath
    $destinationPath = Join-Path $DestinationRoot $RelativePath
    Assert-RequiredPath -Path $sourcePath
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Recurse -Force
}

$resolvedWorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$resolvedOutputRoot = New-Directory -Path $OutputRoot
$repoName = Split-Path -Leaf $resolvedWorkspaceRoot
$stageRoot = Join-Path $resolvedOutputRoot ("_package_stage_" + $RunLabel)
$stageRepoRoot = Join-Path $stageRoot $repoName
$zipPath = Join-Path $resolvedOutputRoot ("{0}-{1}.zip" -f $repoName, $RunLabel)

$allowedRelativePaths = @(
    "AGENTS.md",
    "README.md",
    "skills",
    "scripts"
)

$forbiddenPatterns = @(
    '(^|\\)examples(\\|$)',
    '(^|\\)prompt-benchmarks(\\|$)',
    '(^|\\)parent-session-runs(\\|$)',
    '(^|\\)subagent-benchmarks(\\|$)',
    '(^|\\)subagent-records(\\|$)',
    '(^|\\)minesweeper-parent-session\.json$'
)

New-Directory -Path $stageRepoRoot | Out-Null

foreach ($relativePath in $allowedRelativePaths) {
    Copy-AllowedPath -SourceRoot $resolvedWorkspaceRoot -RelativePath $relativePath -DestinationRoot $stageRepoRoot
}

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Compress-Archive -LiteralPath $stageRepoRoot -DestinationPath $zipPath -Force

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
$entries = @($zip.Entries | Select-Object -ExpandProperty FullName)
$zip.Dispose()

$forbiddenMatches = New-Object System.Collections.Generic.List[string]
foreach ($entry in $entries) {
    foreach ($pattern in $forbiddenPatterns) {
        if ($entry -match $pattern) {
            $forbiddenMatches.Add($entry)
            break
        }
    }
}

if ($forbiddenMatches.Count -gt 0) {
    throw ("Packaging validation failed. Forbidden entries found: {0}" -f ($forbiddenMatches -join ", "))
}

$result = [pscustomobject]@{
    zip = $zipPath
    size_bytes = (Get-Item -LiteralPath $zipPath).Length
    stage = $stageRoot
    included_paths = [string[]]$allowedRelativePaths
    excluded_checks = [string[]]$forbiddenPatterns
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 5
} else {
    $result
}
