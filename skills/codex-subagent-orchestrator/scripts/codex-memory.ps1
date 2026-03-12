function Get-MemoryOptionalProperty {
    param(
        $Object,
        [string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }

    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) {
            return $Object[$Name]
        }

        return $null
    }

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }

    return $property.Value
}

function Get-MemoryBoolValue {
    param(
        $Primary,
        $Fallback
    )

    if ($null -ne $Primary) {
        return [bool]$Primary
    }

    if ($null -ne $Fallback) {
        return [bool]$Fallback
    }

    return $false
}

function Get-MemoryStringList {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }

    if ($Value -is [string]) {
        return @([string]$Value)
    }

    $items = New-Object System.Collections.Generic.List[string]
    foreach ($entry in $Value) {
        if ($null -eq $entry) {
            continue
        }

        $items.Add([string]$entry)
    }

    return [string[]]$items.ToArray()
}

function ConvertTo-MemoryNormalizedValue {
    param($Value)

    if ($null -eq $Value) {
        return $null
    }

    if ($Value -is [DateTime]) {
        return $Value.ToUniversalTime().ToString("o")
    }

    if ($Value -is [DateTimeOffset]) {
        return $Value.ToUniversalTime().ToString("o")
    }

    if ($Value -is [System.Collections.IDictionary]) {
        $map = [ordered]@{}
        foreach ($key in $Value.Keys) {
            $map[[string]$key] = ConvertTo-MemoryNormalizedValue $Value[$key]
        }

        return $map
    }

    if ($Value -is [pscustomobject]) {
        $map = [ordered]@{}
        foreach ($property in $Value.PSObject.Properties) {
            $map[[string]$property.Name] = ConvertTo-MemoryNormalizedValue $property.Value
        }

        return $map
    }

    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        $items = New-Object System.Collections.Generic.List[object]
        foreach ($entry in $Value) {
            $items.Add((ConvertTo-MemoryNormalizedValue $entry))
        }

        return @($items.ToArray())
    }

    return $Value
}

function Get-MemorySpecValue {
    param($Object)

    $memory = Get-MemoryOptionalProperty -Object $Object -Name "memory"
    if ($null -eq $memory) {
        return $null
    }

    return ConvertTo-MemoryNormalizedValue $memory
}

function Get-MemoryNormalizedChoice {
    param(
        $Primary,
        [string]$Default,
        [string[]]$AllowedValues,
        [string]$FieldName
    )

    $selected = if ($null -ne $Primary) {
        [string]$Primary
    } else {
        $Default
    }

    if ([string]::IsNullOrWhiteSpace($selected)) {
        $selected = $Default
    }

    $normalized = $selected.ToLowerInvariant()
    if ($AllowedValues -and $normalized -notin $AllowedValues) {
        throw "Unsupported value '$selected' for '$FieldName'. Allowed values: $($AllowedValues -join ', ')"
    }

    return $normalized
}

function Normalize-MemoryPathInput {
    param([string]$Value)

    if ($null -eq $Value) {
        return $null
    }

    $trimmed = $Value.Trim()
    if ($trimmed.Length -ge 2) {
        $first = $trimmed[0]
        $last = $trimmed[$trimmed.Length - 1]
        if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
            $trimmed = $trimmed.Substring(1, $trimmed.Length - 2)
        }
    }

    return $trimmed
}

function Resolve-MemoryAbsolutePath {
    param(
        [string]$Path,
        [string]$BaseDirectory,
        [switch]$AllowMissing
    )

    $inputPath = Normalize-MemoryPathInput $Path
    if ([string]::IsNullOrWhiteSpace($inputPath)) {
        throw "Path value cannot be empty."
    }

    $base = Normalize-MemoryPathInput $BaseDirectory
    if ([string]::IsNullOrWhiteSpace($base)) {
        $base = (Get-Location).Path
    }

    $candidate = if ([System.IO.Path]::IsPathRooted($inputPath)) {
        [System.IO.Path]::GetFullPath($inputPath)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path -Path $base -ChildPath $inputPath))
    }

    if ($AllowMissing) {
        return [string]$candidate
    }

    if (-not (Test-Path -LiteralPath $candidate)) {
        throw "Resolved path does not exist: $candidate"
    }

    return [string]$candidate
}

function Test-MemoryPathWithinRoot {
    param(
        [string]$CandidatePath,
        [string]$RootPath
    )

    $candidate = [System.IO.Path]::GetFullPath($CandidatePath)
    $root = [System.IO.Path]::GetFullPath($RootPath)
    $comparison = [System.StringComparison]::OrdinalIgnoreCase
    if ($candidate.Equals($root, $comparison)) {
        return $true
    }

    $prefix = $root.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    return $candidate.StartsWith($prefix, $comparison)
}

function ConvertTo-MemoryRelativePath {
    param(
        [string]$RootPath,
        [string]$TargetPath
    )

    $root = [System.IO.Path]::GetFullPath($RootPath).TrimEnd('\', '/')
    $target = [System.IO.Path]::GetFullPath($TargetPath)
    if ($target.Equals($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        return "."
    }

    if (-not (Test-MemoryPathWithinRoot -CandidatePath $target -RootPath $root)) {
        return $target.Replace('\', '/')
    }

    $relative = $target.Substring($root.Length).TrimStart('\', '/')
    if ([string]::IsNullOrWhiteSpace($relative)) {
        return "."
    }

    return $relative.Replace('\', '/')
}

function Get-MemoryHash {
    param([string]$Text)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes([string]$Text)
        $hash = $sha.ComputeHash($bytes)
        return ([BitConverter]::ToString($hash)).Replace("-", "").ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Get-MemoryFileText {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return ""
    }

    return Get-Content -LiteralPath $Path -Raw
}

function Get-RollbackSafeBackupPath {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }

    return "$Path.bak"
}

function Write-RollbackSafeFile {
    param(
        [string]$Path,
        [string]$Content,
        [switch]$OnlyIfMissing,
        [int]$RetryCount = 4,
        [int]$RetryDelayMilliseconds = 40
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "Path value cannot be empty."
    }

    $directory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    $tempDirectory = if ([string]::IsNullOrWhiteSpace($directory)) {
        (Get-Location).Path
    } else {
        $directory
    }
    $tempPath = Join-Path $tempDirectory ("{0}.tmp" -f [System.IO.Path]::GetRandomFileName())
    $backupPath = Get-RollbackSafeBackupPath -Path $Path
    $maxAttempts = [math]::Max(1, $RetryCount)
    if ($null -eq $Content) {
        $Content = ""
    }

    Set-Content -LiteralPath $tempPath -Value $Content -Encoding utf8

    try {
        $attempt = 0
        while ($true) {
            try {
                if ($OnlyIfMissing) {
                    if (Test-Path -LiteralPath $Path) {
                        return $false
                    }

                    [System.IO.File]::Move($tempPath, $Path)
                    return $true
                }

                if (Test-Path -LiteralPath $Path) {
                    [System.IO.File]::Replace($tempPath, $Path, $backupPath, $true)
                } else {
                    try {
                        [System.IO.File]::Move($tempPath, $Path)
                    } catch [System.IO.IOException] {
                        if (-not (Test-Path -LiteralPath $Path)) {
                            throw
                        }

                        [System.IO.File]::Replace($tempPath, $Path, $backupPath, $true)
                    }
                }

                return $true
            } catch {
                if ($OnlyIfMissing -and (Test-Path -LiteralPath $Path)) {
                    return $false
                }

                $isRetryable = ($_.Exception -is [System.IO.IOException]) -or ($_.Exception -is [System.UnauthorizedAccessException])
                $attempt += 1
                if ((-not $isRetryable) -or $attempt -ge $maxAttempts) {
                    throw
                }

                Start-Sleep -Milliseconds ($RetryDelayMilliseconds * $attempt)
            }
        }
    } finally {
        if (Test-Path -LiteralPath $tempPath) {
            Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Read-RollbackSafeJsonFile {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    foreach ($candidate in @(
            $Path,
            (Get-RollbackSafeBackupPath -Path $Path)
        )) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }

        if ($candidates.Contains($candidate)) {
            continue
        }

        $candidates.Add($candidate)
    }

    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate)) {
            continue
        }

        try {
            $raw = Get-Content -LiteralPath $candidate -Raw -ErrorAction Stop
            if ([string]::IsNullOrWhiteSpace($raw)) {
                continue
            }

            return $raw | ConvertFrom-Json -ErrorAction Stop
        } catch {
            continue
        }
    }

    return $null
}

function Get-MemoryDefaultState {
    return [ordered]@{
        completed_runs = 0
        last_run_at_utc = $null
        last_optimized_at_utc = $null
        last_optimize_reason = @()
    }
}

function Get-MemoryState {
    param($MemoryConfig)

    if (-not $MemoryConfig.state_file) {
        return [pscustomobject](Get-MemoryDefaultState)
    }

    if (-not (Test-Path -LiteralPath $MemoryConfig.state_file)) {
        return [pscustomobject](Get-MemoryDefaultState)
    }

    $state = Read-RollbackSafeJsonFile -Path $MemoryConfig.state_file
    if ($null -ne $state) {
        return [pscustomobject]@{
            completed_runs = if ($null -ne (Get-MemoryOptionalProperty $state "completed_runs")) { [int](Get-MemoryOptionalProperty $state "completed_runs") } else { 0 }
            last_run_at_utc = [string](Get-MemoryOptionalProperty $state "last_run_at_utc")
            last_optimized_at_utc = [string](Get-MemoryOptionalProperty $state "last_optimized_at_utc")
            last_optimize_reason = [string[]](Get-MemoryStringList (Get-MemoryOptionalProperty $state "last_optimize_reason"))
        }
    }

    return [pscustomobject](Get-MemoryDefaultState)
}

function Save-MemoryState {
    param(
        $MemoryConfig,
        $State
    )

    if (-not $MemoryConfig.state_file) {
        return
    }

    $directory = Split-Path -Parent $MemoryConfig.state_file
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    Write-RollbackSafeFile -Path $MemoryConfig.state_file -Content ($State | ConvertTo-Json -Depth 6) | Out-Null
}

function Ensure-MemoryFile {
    param(
        [string]$Path,
        [string]$Content
    )

    if (Test-Path -LiteralPath $Path) {
        return
    }

    $directory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    Write-RollbackSafeFile -Path $Path -Content $Content -OnlyIfMissing | Out-Null
}

function Get-MemoryConfig {
    param(
        $Spec,
        [string]$WorkspaceRoot
    )

    $workspaceRootResolved = Resolve-MemoryAbsolutePath -Path $WorkspaceRoot -BaseDirectory (Get-Location).Path
    $memoryBlock = Get-MemoryOptionalProperty -Object $Spec -Name "memory"
    if ($null -eq $memoryBlock) {
        return [pscustomobject]@{
            configured = $false
            enabled = $false
            active = $false
            requested_mode = "off"
            mode = "off"
            workspace_root = $workspaceRootResolved
            relative_root = ".codex-memory"
            root = $null
            memory_file = $null
            active_file = $null
            daily_root = $null
            inbox_root = $null
            bank_root = $null
            index_root = $null
            runtime_root = $null
            worker_runtime_root = $null
            index_file = $null
            stats_file = $null
            state_file = $null
            core = [pscustomobject]@{ max_chars = 500 }
            retrieval = [pscustomobject]@{
                max_snippets = 4
                max_chars = 1400
                min_score = 0.18
                attach_as_read_first = $true
                write_runtime_file = $true
            }
            search = [pscustomobject]@{
                candidate_limit = 12
                recency = [pscustomobject]@{
                    enabled = $true
                    half_life_days = 21
                }
                dedupe = [pscustomobject]@{
                    enabled = $true
                    jaccard_threshold = 0.75
                }
            }
            retain = [pscustomobject]@{
                enabled = $true
                max_entry_chars = 500
            }
            optimize = [pscustomobject]@{
                enabled = $true
                every_completed_runs = 5
                memory_max_chars = 4000
                active_max_chars = 2500
                daily_max_chars = 12000
                prune_ttl_days = 45
            }
            guardrails = [pscustomobject]@{
                deny_instruction_like_content = $true
                deny_secrets = $true
                deny_large_logs = $true
                promote_only_verified = $true
            }
        }
    }

    $enabled = Get-MemoryBoolValue (Get-MemoryOptionalProperty $memoryBlock "enabled") $false
    $requestedMode = Get-MemoryNormalizedChoice `
        -Primary (Get-MemoryOptionalProperty $memoryBlock "mode") `
        -Default $(if ($enabled) { "hybrid" } else { "off" }) `
        -AllowedValues @("off", "reference", "core", "retrieval", "hybrid") `
        -FieldName "memory.mode"
    $active = ($enabled -and $requestedMode -ne "off")
    $rootValue = Get-MemoryOptionalProperty $memoryBlock "root"
    if (-not $rootValue) {
        $rootValue = ".codex-memory"
    }
    $relativeRoot = ([string]$rootValue).Replace('\', '/')
    $coreBlock = Get-MemoryOptionalProperty $memoryBlock "core"
    $retrievalBlock = Get-MemoryOptionalProperty $memoryBlock "retrieval"
    $searchBlock = Get-MemoryOptionalProperty $memoryBlock "search"
    $retainBlock = Get-MemoryOptionalProperty $memoryBlock "retain"
    $optimizeBlock = Get-MemoryOptionalProperty $memoryBlock "optimize"
    $guardrailBlock = Get-MemoryOptionalProperty $memoryBlock "guardrails"
    $recencyBlock = Get-MemoryOptionalProperty $searchBlock "recency"
    $dedupeBlock = Get-MemoryOptionalProperty $searchBlock "dedupe"
    $root = $null
    $memoryFile = $null
    $activeFile = $null
    $dailyRoot = $null
    $inboxRoot = $null
    $bankRoot = $null
    $indexRoot = $null
    $runtimeRoot = $null
    $workerRuntimeRoot = $null
    $indexFile = $null
    $statsFile = $null
    $stateFile = $null

    if ($active) {
        $root = Resolve-MemoryAbsolutePath -Path ([string]$rootValue) -BaseDirectory $workspaceRootResolved -AllowMissing
        if (-not (Test-MemoryPathWithinRoot -CandidatePath $root -RootPath $workspaceRootResolved)) {
            throw "memory.root must stay inside the workspace root: $root"
        }

        $relativeRoot = ConvertTo-MemoryRelativePath -RootPath $workspaceRootResolved -TargetPath $root
        $memoryFile = Join-Path $root "MEMORY.md"
        $activeFile = Join-Path $root "active.md"
        $dailyRoot = Join-Path $root "daily"
        $inboxRoot = Join-Path $root "inbox"
        $bankRoot = Join-Path $root "bank"
        $indexRoot = Join-Path $root "index"
        $runtimeRoot = Join-Path $root "runtime"
        $workerRuntimeRoot = Join-Path (Join-Path $root "runtime") "worker-memory"
        $indexFile = Join-Path (Join-Path $root "index") "memory-index.json"
        $statsFile = Join-Path (Join-Path $root "index") "memory-stats.json"
        $stateFile = Join-Path $root "state.json"
    }

    return [pscustomobject]@{
        configured = $true
        enabled = $enabled
        active = $active
        requested_mode = $requestedMode
        mode = $requestedMode
        workspace_root = $workspaceRootResolved
        relative_root = $relativeRoot
        root = $root
        memory_file = $memoryFile
        active_file = $activeFile
        daily_root = $dailyRoot
        inbox_root = $inboxRoot
        bank_root = $bankRoot
        index_root = $indexRoot
        runtime_root = $runtimeRoot
        worker_runtime_root = $workerRuntimeRoot
        index_file = $indexFile
        stats_file = $statsFile
        state_file = $stateFile
        core = [pscustomobject]@{
            max_chars = if ($null -ne (Get-MemoryOptionalProperty $coreBlock "max_chars")) { [int](Get-MemoryOptionalProperty $coreBlock "max_chars") } else { 500 }
        }
        retrieval = [pscustomobject]@{
            max_snippets = if ($null -ne (Get-MemoryOptionalProperty $retrievalBlock "max_snippets")) { [int](Get-MemoryOptionalProperty $retrievalBlock "max_snippets") } else { 4 }
            max_chars = if ($null -ne (Get-MemoryOptionalProperty $retrievalBlock "max_chars")) { [int](Get-MemoryOptionalProperty $retrievalBlock "max_chars") } else { 1400 }
            min_score = if ($null -ne (Get-MemoryOptionalProperty $retrievalBlock "min_score")) { [double](Get-MemoryOptionalProperty $retrievalBlock "min_score") } else { 0.18 }
            attach_as_read_first = (Get-MemoryBoolValue (Get-MemoryOptionalProperty $retrievalBlock "attach_as_read_first") $true)
            write_runtime_file = (Get-MemoryBoolValue (Get-MemoryOptionalProperty $retrievalBlock "write_runtime_file") $true)
        }
        search = [pscustomobject]@{
            candidate_limit = if ($null -ne (Get-MemoryOptionalProperty $searchBlock "candidate_limit")) { [int](Get-MemoryOptionalProperty $searchBlock "candidate_limit") } else { 12 }
            recency = [pscustomobject]@{
                enabled = (Get-MemoryBoolValue (Get-MemoryOptionalProperty $recencyBlock "enabled") $true)
                half_life_days = if ($null -ne (Get-MemoryOptionalProperty $recencyBlock "half_life_days")) { [int](Get-MemoryOptionalProperty $recencyBlock "half_life_days") } else { 21 }
            }
            dedupe = [pscustomobject]@{
                enabled = (Get-MemoryBoolValue (Get-MemoryOptionalProperty $dedupeBlock "enabled") $true)
                jaccard_threshold = if ($null -ne (Get-MemoryOptionalProperty $dedupeBlock "jaccard_threshold")) { [double](Get-MemoryOptionalProperty $dedupeBlock "jaccard_threshold") } else { 0.75 }
            }
        }
        retain = [pscustomobject]@{
            enabled = (Get-MemoryBoolValue (Get-MemoryOptionalProperty $retainBlock "enabled") $true)
            max_entry_chars = if ($null -ne (Get-MemoryOptionalProperty $retainBlock "max_entry_chars")) { [int](Get-MemoryOptionalProperty $retainBlock "max_entry_chars") } else { 500 }
        }
        optimize = [pscustomobject]@{
            enabled = (Get-MemoryBoolValue (Get-MemoryOptionalProperty $optimizeBlock "enabled") $true)
            every_completed_runs = if ($null -ne (Get-MemoryOptionalProperty $optimizeBlock "every_completed_runs")) { [int](Get-MemoryOptionalProperty $optimizeBlock "every_completed_runs") } else { 5 }
            memory_max_chars = if ($null -ne (Get-MemoryOptionalProperty $optimizeBlock "memory_max_chars")) { [int](Get-MemoryOptionalProperty $optimizeBlock "memory_max_chars") } else { 4000 }
            active_max_chars = if ($null -ne (Get-MemoryOptionalProperty $optimizeBlock "active_max_chars")) { [int](Get-MemoryOptionalProperty $optimizeBlock "active_max_chars") } else { 2500 }
            daily_max_chars = if ($null -ne (Get-MemoryOptionalProperty $optimizeBlock "daily_max_chars")) { [int](Get-MemoryOptionalProperty $optimizeBlock "daily_max_chars") } else { 12000 }
            prune_ttl_days = if ($null -ne (Get-MemoryOptionalProperty $optimizeBlock "prune_ttl_days")) { [int](Get-MemoryOptionalProperty $optimizeBlock "prune_ttl_days") } else { 45 }
        }
        guardrails = [pscustomobject]@{
            deny_instruction_like_content = (Get-MemoryBoolValue (Get-MemoryOptionalProperty $guardrailBlock "deny_instruction_like_content") $true)
            deny_secrets = (Get-MemoryBoolValue (Get-MemoryOptionalProperty $guardrailBlock "deny_secrets") $true)
            deny_large_logs = (Get-MemoryBoolValue (Get-MemoryOptionalProperty $guardrailBlock "deny_large_logs") $true)
            promote_only_verified = (Get-MemoryBoolValue (Get-MemoryOptionalProperty $guardrailBlock "promote_only_verified") $true)
        }
    }
}

function Initialize-MemoryStore {
    param($MemoryConfig)

    if (-not $MemoryConfig.active) {
        return [pscustomobject]@{
            initialized = $false
            index = [pscustomobject]@{
                chunk_count = 0
                file_count = 0
            }
        }
    }

    foreach ($directory in @(
            $MemoryConfig.root,
            $MemoryConfig.daily_root,
            $MemoryConfig.inbox_root,
            $MemoryConfig.bank_root,
            $MemoryConfig.index_root,
            $MemoryConfig.runtime_root,
            $MemoryConfig.worker_runtime_root
        )) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    Ensure-MemoryFile -Path $MemoryConfig.memory_file -Content @'
# Workspace Memory

## Core
- Add short, verified project facts here.
'@
    Ensure-MemoryFile -Path $MemoryConfig.active_file -Content @'
# Active Memory

## Current Focus
- Keep only short-lived notes that help the next related run.
'@
    if (-not (Test-Path -LiteralPath $MemoryConfig.state_file)) {
        Save-MemoryState -MemoryConfig $MemoryConfig -State (Get-MemoryDefaultState)
    }

    $indexInfo = Rebuild-MemoryIndex -MemoryConfig $MemoryConfig
    return [pscustomobject]@{
        initialized = $true
        index = $indexInfo
    }
}

function Get-MemorySourceKind {
    param(
        [string]$RelativePath,
        $MemoryConfig
    )

    $rootPrefix = $MemoryConfig.relative_root.TrimEnd('/')
    if ($RelativePath -eq "$rootPrefix/MEMORY.md") {
        return "memory"
    }

    if ($RelativePath -eq "$rootPrefix/active.md") {
        return "active"
    }

    if ($RelativePath -like "$rootPrefix/bank/*") {
        return "bank"
    }

    if ($RelativePath -like "$rootPrefix/inbox/*") {
        return "inbox"
    }

    if ($RelativePath -like "$rootPrefix/daily/*") {
        return "daily"
    }

    return "other"
}

function Test-MemoryIndexableContent {
    param(
        [string]$Content,
        [string]$SourceKind
    )

    if ($SourceKind -eq "inbox" -and $Content -match '(?im)^- verified:\s*false\s*$') {
        return $false
    }

    return $true
}

function Get-MemoryDurabilityWeight {
    param([string]$SourceKind)

    switch ($SourceKind) {
        "memory" { return 1.0 }
        "bank" { return 0.95 }
        "active" { return 0.8 }
        "inbox" { return 0.6 }
        "daily" { return 0.5 }
        default { return 0.4 }
    }
}

function Get-MemoryDurabilityName {
    param([string]$SourceKind)

    switch ($SourceKind) {
        "memory" { return "durable" }
        "bank" { return "durable" }
        "active" { return "active" }
        "inbox" { return "candidate" }
        "daily" { return "daily" }
        default { return "other" }
    }
}

function ConvertTo-MemoryTokens {
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return @()
    }

    $normalized = $Text.ToLowerInvariant()
    $normalized = $normalized -replace '[^a-z0-9_./\\-]', ' '
    $parts = @($normalized -split '\s+' | Where-Object { $_ -and $_.Length -ge 2 })
    if (@($parts).Count -eq 0) {
        return @()
    }

    return [string[]]($parts | Select-Object -Unique)
}

function Get-MemoryPathMentions {
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return @()
    }

    $matches = [regex]::Matches($Text, '(?i)([A-Za-z0-9_.\\/\-]+(?:\.[A-Za-z0-9_.\-]+)+)')
    $paths = New-Object System.Collections.Generic.List[string]
    foreach ($match in $matches) {
        $value = [string]$match.Groups[1].Value
        if ([string]::IsNullOrWhiteSpace($value)) {
            continue
        }

        $paths.Add($value.Replace('\', '/'))
    }

    return [string[]]($paths.ToArray() | Select-Object -Unique)
}

function Get-MarkdownChunks {
    param(
        [string]$Path,
        $MemoryConfig
    )

    $raw = Get-MemoryFileText -Path $Path
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return @()
    }

    $relativePath = ConvertTo-MemoryRelativePath -RootPath $MemoryConfig.workspace_root -TargetPath $Path
    $sourceKind = Get-MemorySourceKind -RelativePath $relativePath -MemoryConfig $MemoryConfig
    if (-not (Test-MemoryIndexableContent -Content $raw -SourceKind $sourceKind)) {
        return @()
    }

    $defaultHeading = [System.IO.Path]::GetFileNameWithoutExtension($Path)
    $updatedAt = (Get-Item -LiteralPath $Path).LastWriteTimeUtc.ToString("o")
    $lines = @([regex]::Split($raw, "\r?\n"))
    $chunks = New-Object System.Collections.Generic.List[object]
    $heading = $defaultHeading
    $bodyLines = New-Object System.Collections.Generic.List[string]
    $headingIndex = 0

    foreach ($line in $lines) {
        if ($line -match '^\s{0,3}#{1,6}\s+(.+?)\s*$') {
            $body = ($bodyLines -join [Environment]::NewLine).Trim()
            if (-not [string]::IsNullOrWhiteSpace($body)) {
                $chunkText = "$heading`n$body".Trim()
                $chunkPaths = @(
                    @(Get-MemoryPathMentions -Text $heading)
                    @(Get-MemoryPathMentions -Text $body)
                ) | Select-Object -Unique
                $chunkTags = @(
                    ConvertTo-MemoryTokens -Text $heading
                    ConvertTo-MemoryTokens -Text $body
                ) | Select-Object -Unique

                $chunks.Add([pscustomobject]@{
                        id = ("{0}:{1}" -f $relativePath, $headingIndex)
                        path = $relativePath
                        heading = $heading
                        body = $body
                        text = $chunkText
                        tags = [string[]]$chunkTags
                        paths = [string[]]$chunkPaths
                        source_kind = $sourceKind
                        durability = (Get-MemoryDurabilityName -SourceKind $sourceKind)
                        durability_weight = (Get-MemoryDurabilityWeight -SourceKind $sourceKind)
                        updated_at_utc = $updatedAt
                        fingerprint = (Get-MemoryHash -Text ("{0}`n{1}`n{2}" -f $relativePath, $heading, $body))
                        char_count = $chunkText.Length
                    })
                $headingIndex += 1
            }

            $heading = [string]$Matches[1].Trim()
            $bodyLines = New-Object System.Collections.Generic.List[string]
            continue
        }

        $bodyLines.Add($line)
    }

    $finalBody = ($bodyLines -join [Environment]::NewLine).Trim()
    if (-not [string]::IsNullOrWhiteSpace($finalBody)) {
        $chunkText = "$heading`n$finalBody".Trim()
        $chunkPaths = @(
            @(Get-MemoryPathMentions -Text $heading)
            @(Get-MemoryPathMentions -Text $finalBody)
        ) | Select-Object -Unique
        $chunkTags = @(
            ConvertTo-MemoryTokens -Text $heading
            ConvertTo-MemoryTokens -Text $finalBody
        ) | Select-Object -Unique

        $chunks.Add([pscustomobject]@{
                id = ("{0}:{1}" -f $relativePath, $headingIndex)
                path = $relativePath
                heading = $heading
                body = $finalBody
                text = $chunkText
                tags = [string[]]$chunkTags
                paths = [string[]]$chunkPaths
                source_kind = $sourceKind
                durability = (Get-MemoryDurabilityName -SourceKind $sourceKind)
                durability_weight = (Get-MemoryDurabilityWeight -SourceKind $sourceKind)
                updated_at_utc = $updatedAt
                fingerprint = (Get-MemoryHash -Text ("{0}`n{1}`n{2}" -f $relativePath, $heading, $finalBody))
                char_count = $chunkText.Length
            })
    }

    return @($chunks.ToArray())
}

function Rebuild-MemoryIndex {
    param($MemoryConfig)

    if (-not $MemoryConfig.active) {
        return [pscustomobject]@{
            chunk_count = 0
            file_count = 0
            chunks = @()
            stats = $null
        }
    }

    $files = New-Object System.Collections.Generic.List[string]
    foreach ($path in @(
            $MemoryConfig.memory_file,
            $MemoryConfig.active_file
        )) {
        if (Test-Path -LiteralPath $path) {
            $files.Add($path)
        }
    }

    foreach ($pattern in @(
            (Join-Path $MemoryConfig.bank_root "*.md"),
            (Join-Path $MemoryConfig.inbox_root "*.md"),
            (Join-Path $MemoryConfig.daily_root "*.md")
        )) {
        foreach ($file in @(Get-ChildItem -LiteralPath (Split-Path -Parent $pattern) -Filter ([System.IO.Path]::GetFileName($pattern)) -File -ErrorAction SilentlyContinue)) {
            $files.Add($file.FullName)
        }
    }

    $chunks = New-Object System.Collections.Generic.List[object]
    foreach ($file in @($files.ToArray() | Select-Object -Unique)) {
        foreach ($chunk in @(Get-MarkdownChunks -Path $file -MemoryConfig $MemoryConfig)) {
            $chunks.Add($chunk)
        }
    }

    $chunkArray = @($chunks.ToArray())
    $chunkCount = @($chunkArray).Count
    $sourceCounts = [ordered]@{}
    foreach ($kind in @("memory", "active", "bank", "inbox", "daily", "other")) {
        $sourceCounts[$kind] = @($chunkArray | Where-Object { $_.source_kind -eq $kind }).Count
    }

    $index = [ordered]@{
        created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        root = $MemoryConfig.relative_root
        chunk_count = $chunkCount
        file_count = @($files.ToArray() | Select-Object -Unique).Count
        chunks = $chunkArray
    }
    $stats = [ordered]@{
        created_at_utc = $index.created_at_utc
        root = $MemoryConfig.relative_root
        chunk_count = $chunkCount
        file_count = $index.file_count
        source_counts = $sourceCounts
    }

    Write-RollbackSafeFile -Path $MemoryConfig.index_file -Content ($index | ConvertTo-Json -Depth 8) | Out-Null
    Write-RollbackSafeFile -Path $MemoryConfig.stats_file -Content ($stats | ConvertTo-Json -Depth 6) | Out-Null

    return [pscustomobject]@{
        chunk_count = $chunkCount
        file_count = $index.file_count
        chunks = $chunkArray
        stats = [pscustomobject]$stats
    }
}

function Get-MemoryIndex {
    param($MemoryConfig)

    if (-not $MemoryConfig.active) {
        return [pscustomobject]@{
            chunk_count = 0
            file_count = 0
            chunks = @()
        }
    }

    if (-not (Test-Path -LiteralPath $MemoryConfig.index_file)) {
        return Rebuild-MemoryIndex -MemoryConfig $MemoryConfig
    }

    $index = Read-RollbackSafeJsonFile -Path $MemoryConfig.index_file
    if ($null -ne $index) {
        if ($null -eq (Get-MemoryOptionalProperty $index "chunks")) {
            return Rebuild-MemoryIndex -MemoryConfig $MemoryConfig
        }

        return [pscustomobject]@{
            chunk_count = if ($null -ne (Get-MemoryOptionalProperty $index "chunk_count")) { [int](Get-MemoryOptionalProperty $index "chunk_count") } else { @($index.chunks).Count }
            file_count = if ($null -ne (Get-MemoryOptionalProperty $index "file_count")) { [int](Get-MemoryOptionalProperty $index "file_count") } else { 0 }
            chunks = @($index.chunks)
        }
    }

    return Rebuild-MemoryIndex -MemoryConfig $MemoryConfig
}

function Get-WorkerMemoryMode {
    param(
        $Agent,
        [string]$WorkerKind,
        [bool]$IsReadOnly,
        $MemoryConfig
    )

    if (-not $MemoryConfig.active) {
        return "off"
    }

    $agentMode = Get-MemoryOptionalProperty -Object $Agent -Name "memory_mode"
    if ($agentMode) {
        return Get-MemoryNormalizedChoice `
            -Primary $agentMode `
            -Default $MemoryConfig.mode `
            -AllowedValues @("off", "reference", "core", "retrieval", "hybrid") `
            -FieldName "memory_mode"
    }

    if ($MemoryConfig.mode -ne "hybrid") {
        return $MemoryConfig.mode
    }

    switch ($WorkerKind) {
        "implementer" { return "retrieval" }
        "fixer" { return "retrieval" }
        "planner" { return "retrieval" }
        "reviewer" { return "core" }
        "validator" { return "core" }
        "custom" {
            if ($IsReadOnly) {
                return "core"
            }

            return "retrieval"
        }
        default {
            if ($IsReadOnly) {
                return "core"
            }

            return "retrieval"
        }
    }
}

function Get-MemoryQueryText {
    param(
        $Agent,
        [string]$WorkerKind,
        [string[]]$RequestedDeliverables,
        $WorkflowContext
    )

    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($label in @(
            [string](Get-MemoryOptionalProperty $Agent "role"),
            [string](Get-MemoryOptionalProperty $Agent "mission"),
            [string](Get-MemoryOptionalProperty $Agent "task"),
            [string](Get-MemoryOptionalProperty $Agent "prompt"),
            [string]$WorkerKind
        )) {
        if (-not [string]::IsNullOrWhiteSpace($label)) {
            $parts.Add($label)
        }
    }

    foreach ($entry in @(Get-MemoryStringList (Get-MemoryOptionalProperty $Agent "read_first"))) {
        $parts.Add($entry)
    }
    foreach ($entry in @(Get-MemoryStringList (Get-MemoryOptionalProperty $Agent "writable_scope"))) {
        $parts.Add($entry)
    }
    foreach ($entry in @(Get-MemoryStringList $RequestedDeliverables)) {
        $parts.Add($entry)
    }

    if ($WorkflowContext) {
        $issue = Get-MemoryOptionalProperty -Object $WorkflowContext -Name "issue"
        if ($issue) {
            foreach ($entry in @(
                    [string](Get-MemoryOptionalProperty $issue "identifier"),
                    [string](Get-MemoryOptionalProperty $issue "title"),
                    [string](Get-MemoryOptionalProperty $issue "description")
                )) {
                if (-not [string]::IsNullOrWhiteSpace($entry)) {
                    $parts.Add($entry)
                }
            }

            foreach ($label in @(Get-MemoryStringList (Get-MemoryOptionalProperty $issue "labels"))) {
                $parts.Add($label)
            }
            foreach ($deliverable in @(Get-MemoryStringList (Get-MemoryOptionalProperty $issue "requested_deliverables"))) {
                $parts.Add($deliverable)
            }
        }
    }

    return (($parts.ToArray() | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join [Environment]::NewLine).Trim()
}

function Get-MemoryOverlapScore {
    param(
        [string[]]$QueryTokens,
        [string[]]$CandidateTokens
    )

    if (@($QueryTokens).Count -eq 0 -or @($CandidateTokens).Count -eq 0) {
        return 0.0
    }

    $querySet = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($token in $QueryTokens) {
        [void]$querySet.Add($token)
    }

    $hitCount = 0
    $candidateSet = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($token in $CandidateTokens) {
        if ($candidateSet.Add($token) -and $querySet.Contains($token)) {
            $hitCount += 1
        }
    }

    return [double]$hitCount / [double]$querySet.Count
}

function Get-MemoryRecencyScore {
    param(
        $Chunk,
        $MemoryConfig
    )

    if (-not $MemoryConfig.search.recency.enabled) {
        return 1.0
    }

    if ($Chunk.source_kind -in @("memory", "bank")) {
        return 1.0
    }

    $updatedAtValue = [string](Get-MemoryOptionalProperty $Chunk "updated_at_utc")
    if ([string]::IsNullOrWhiteSpace($updatedAtValue)) {
        return 0.5
    }

    $updatedAt = [datetime]::MinValue
    if (-not [DateTime]::TryParse($updatedAtValue, [ref]$updatedAt)) {
        return 0.5
    }

    $ageDays = [math]::Max(0.0, ((Get-Date).ToUniversalTime() - $updatedAt.ToUniversalTime()).TotalDays)
    $halfLife = [double][math]::Max(1, $MemoryConfig.search.recency.half_life_days)
    return [math]::Pow(0.5, ($ageDays / $halfLife))
}

function Get-MemoryJaccardSimilarity {
    param(
        [string[]]$First,
        [string[]]$Second
    )

    if (@($First).Count -eq 0 -or @($Second).Count -eq 0) {
        return 0.0
    }

    $firstSet = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    $secondSet = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($item in $First) {
        [void]$firstSet.Add($item)
    }
    foreach ($item in $Second) {
        [void]$secondSet.Add($item)
    }

    $intersection = 0
    foreach ($item in $firstSet) {
        if ($secondSet.Contains($item)) {
            $intersection += 1
        }
    }

    $union = $firstSet.Count + $secondSet.Count - $intersection
    if ($union -le 0) {
        return 0.0
    }

    return [double]$intersection / [double]$union
}

function Search-MemoryIndex {
    param(
        $MemoryConfig,
        [string]$QueryText,
        [string[]]$WorkerPaths
    )

    if (-not $MemoryConfig.active) {
        return @()
    }

    $index = Get-MemoryIndex -MemoryConfig $MemoryConfig
    $queryTokens = ConvertTo-MemoryTokens -Text $QueryText
    $workerPathTokens = @(
        foreach ($path in @(Get-MemoryStringList $WorkerPaths)) {
            ConvertTo-MemoryTokens -Text $path
        }
    ) | Select-Object -Unique

    $scored = New-Object System.Collections.Generic.List[object]
    foreach ($chunk in @($index.chunks)) {
        $chunkTokens = @(
            @(Get-MemoryStringList (Get-MemoryOptionalProperty $chunk "tags"))
            ConvertTo-MemoryTokens -Text ([string](Get-MemoryOptionalProperty $chunk "text"))
        ) | Select-Object -Unique
        $chunkPathTokens = @(
            foreach ($path in @(Get-MemoryStringList (Get-MemoryOptionalProperty $chunk "paths"))) {
                ConvertTo-MemoryTokens -Text $path
            }
            ConvertTo-MemoryTokens -Text ([string](Get-MemoryOptionalProperty $chunk "path"))
        ) | Select-Object -Unique

        $lexicalScore = Get-MemoryOverlapScore -QueryTokens $queryTokens -CandidateTokens $chunkTokens
        $pathScore = Get-MemoryOverlapScore -QueryTokens $workerPathTokens -CandidateTokens $chunkPathTokens
        $durabilityScore = [double](Get-MemoryOptionalProperty $chunk "durability_weight")
        $recencyScore = Get-MemoryRecencyScore -Chunk $chunk -MemoryConfig $MemoryConfig
        $score = (0.45 * $lexicalScore) + (0.25 * $pathScore) + (0.15 * $durabilityScore) + (0.15 * $recencyScore)

        if ($score -lt $MemoryConfig.retrieval.min_score) {
            continue
        }

        $scored.Add([pscustomobject]@{
                score = [math]::Round($score, 6)
                lexical_score = [math]::Round($lexicalScore, 6)
                path_score = [math]::Round($pathScore, 6)
                recency_score = [math]::Round($recencyScore, 6)
                chunk = $chunk
                comparison_tokens = [string[]]$chunkTokens
            })
    }

    $sorted = @($scored.ToArray() | Sort-Object -Property @{ Expression = { $_.score }; Descending = $true }, @{ Expression = { $_.chunk.updated_at_utc }; Descending = $true })
    if (-not $MemoryConfig.search.dedupe.enabled) {
        return @($sorted | Select-Object -First $MemoryConfig.search.candidate_limit)
    }

    $selected = New-Object System.Collections.Generic.List[object]
    foreach ($candidate in $sorted) {
        $isDuplicate = $false
        foreach ($existing in $selected) {
            $similarity = Get-MemoryJaccardSimilarity -First $candidate.comparison_tokens -Second $existing.comparison_tokens
            if ($similarity -ge $MemoryConfig.search.dedupe.jaccard_threshold) {
                $isDuplicate = $true
                break
            }
        }

        if ($isDuplicate) {
            continue
        }

        $selected.Add($candidate)
        if ($selected.Count -ge $MemoryConfig.search.candidate_limit) {
            break
        }
    }

    return @($selected.ToArray())
}

function Get-MemoryCoreText {
    param($MemoryConfig)

    if (-not $MemoryConfig.active) {
        return ""
    }

    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($path in @($MemoryConfig.memory_file, $MemoryConfig.active_file)) {
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }

        $relative = ConvertTo-MemoryRelativePath -RootPath $MemoryConfig.workspace_root -TargetPath $path
        $content = (Get-MemoryFileText -Path $path).Trim()
        if ([string]::IsNullOrWhiteSpace($content)) {
            continue
        }

        $parts.Add("### $relative")
        $parts.Add($content)
    }

    $combined = ($parts.ToArray() -join ([Environment]::NewLine + [Environment]::NewLine)).Trim()
    if ([string]::IsNullOrWhiteSpace($combined)) {
        return ""
    }

    if ($combined.Length -le $MemoryConfig.core.max_chars) {
        return $combined
    }

    return ($combined.Substring(0, $MemoryConfig.core.max_chars).Trim() + "...")
}

function Select-MemorySnippets {
    param(
        $MemoryConfig,
        [string]$Mode,
        $Hits
    )

    $sections = New-Object System.Collections.Generic.List[string]
    $hitPaths = New-Object System.Collections.Generic.List[string]
    $snippetCount = 0

    if ($Mode -eq "reference") {
        $referenceLines = New-Object System.Collections.Generic.List[string]
        foreach ($path in @($MemoryConfig.memory_file, $MemoryConfig.active_file)) {
            if (Test-Path -LiteralPath $path) {
                $referenceLines.Add("- " + (ConvertTo-MemoryRelativePath -RootPath $MemoryConfig.workspace_root -TargetPath $path))
            }
        }
        foreach ($file in @(Get-ChildItem -LiteralPath $MemoryConfig.bank_root -Filter "*.md" -File -ErrorAction SilentlyContinue | Sort-Object Name)) {
            $referenceLines.Add("- " + (ConvertTo-MemoryRelativePath -RootPath $MemoryConfig.workspace_root -TargetPath $file.FullName))
        }
        if (@($referenceLines).Count -gt 0) {
            $sections.Add("## Memory references")
            $sections.Add(($referenceLines.ToArray() -join [Environment]::NewLine))
        }
    }

    if ($Mode -in @("core", "hybrid")) {
        $coreText = Get-MemoryCoreText -MemoryConfig $MemoryConfig
        if (-not [string]::IsNullOrWhiteSpace($coreText)) {
            $sections.Add("## Core memory")
            $sections.Add($coreText)
        }
    }

    if ($Mode -in @("retrieval", "hybrid")) {
        $retrievalLines = New-Object System.Collections.Generic.List[string]
        $usedChars = 0
        foreach ($hit in @($Hits | Select-Object -First $MemoryConfig.retrieval.max_snippets)) {
            $chunk = $hit.chunk
            $excerpt = [string](Get-MemoryOptionalProperty $chunk "body")
            if ([string]::IsNullOrWhiteSpace($excerpt)) {
                continue
            }

            $budgetRemaining = $MemoryConfig.retrieval.max_chars - $usedChars
            if ($budgetRemaining -le 80) {
                break
            }

            $maxPerSnippet = [math]::Min(400, $budgetRemaining)
            if ($excerpt.Length -gt $maxPerSnippet) {
                $excerpt = $excerpt.Substring(0, $maxPerSnippet).Trim() + "..."
            }

            $retrievalLines.Add(("### {0} | {1} | score={2}" -f $chunk.path, $chunk.heading, $hit.score))
            $retrievalLines.Add($excerpt)
            $usedChars += $excerpt.Length
            $snippetCount += 1
            if (-not [string]::IsNullOrWhiteSpace([string]$chunk.path)) {
                $hitPaths.Add([string]$chunk.path)
            }
        }

        if (@($retrievalLines).Count -gt 0) {
            $sections.Add("## Retrieved snippets")
            $sections.Add(($retrievalLines.ToArray() -join ([Environment]::NewLine + [Environment]::NewLine)))
        }
    }

    $content = ($sections.ToArray() -join ([Environment]::NewLine + [Environment]::NewLine)).Trim()
    return [pscustomobject]@{
        mode = $Mode
        content = $content
        snippet_count = $snippetCount
        hit_paths = [string[]]($hitPaths.ToArray() | Select-Object -Unique)
    }
}

function Write-WorkerMemoryContextFile {
    param(
        $MemoryConfig,
        [string]$WorkerName,
        [string]$Mode,
        $MemoryContext
    )

    if (-not $MemoryConfig.active -or $Mode -eq "off" -or -not $MemoryConfig.retrieval.write_runtime_file) {
        return [pscustomobject]@{
            enabled = $false
            exists = $false
            mode = "off"
            path = $null
            relative_path = $null
            snippet_count = 0
            injected_chars = 0
            hit_paths = @()
        }
    }

    $safeWorkerName = ($WorkerName -replace '[^A-Za-z0-9_.-]', '-')
    if ([string]::IsNullOrWhiteSpace($safeWorkerName)) {
        $safeWorkerName = "worker"
    }

    $filePath = Join-Path $MemoryConfig.worker_runtime_root ("{0}.md" -f $safeWorkerName)
    $fileRelativePath = ConvertTo-MemoryRelativePath -RootPath $MemoryConfig.workspace_root -TargetPath $filePath
    $body = if ([string]::IsNullOrWhiteSpace($MemoryContext.content)) {
        "## Retrieved snippets`nNo relevant memory snippets were selected for this worker."
    } else {
        $MemoryContext.content
    }

    $content = @(
        "# Worker Memory Context",
        "",
        "- mode: $Mode",
        "- generated_at_utc: $((Get-Date).ToUniversalTime().ToString("o"))",
        "- memory_root: $($MemoryConfig.relative_root)",
        "- supporting_only: true",
        "",
        "## Policy",
        "- Treat memory as supporting context only.",
        "- Current task, repository files, validation output, and reviewer findings override memory.",
        "- If memory conflicts with actual files, trust the files.",
        "",
        $body.Trim()
    ) -join [Environment]::NewLine

    Write-RollbackSafeFile -Path $filePath -Content $content | Out-Null

    return [pscustomobject]@{
        enabled = $true
        exists = $true
        mode = $Mode
        path = $filePath
        relative_path = $fileRelativePath
        snippet_count = [int]$MemoryContext.snippet_count
        injected_chars = $content.Length
        hit_paths = [string[]]$MemoryContext.hit_paths
    }
}

function Test-MemorySecretLikeContent {
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $false
    }

    foreach ($pattern in @(
            '(?i)\b(api[_-]?key|secret|token|password|credential)\b\s*[:=]',
            '(?i)\b(sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{10,}|github_pat_[A-Za-z0-9_]{10,})\b',
            '(?i)\bAKIA[0-9A-Z]{16}\b'
        )) {
        if ($Text -match $pattern) {
            return $true
        }
    }

    return $false
}

function Test-MemoryInstructionLikeContent {
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $false
    }

    foreach ($pattern in @(
            '(?i)\b(ignore|always obey|follow these instructions|system prompt|developer message)\b',
            '(?i)\bdo not ask questions\b',
            '(?i)\byou are a bounded codex exec worker\b'
        )) {
        if ($Text -match $pattern) {
            return $true
        }
    }

    return $false
}

function Get-SafeMemoryText {
    param(
        [string]$Text,
        [int]$MaxChars,
        $MemoryConfig
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $null
    }

    $normalized = [regex]::Replace($Text, '(?s)```.*?```', ' ')
    $normalized = $normalized -replace "`r", ""
    $lines = @(
        $normalized -split "`n" |
            ForEach-Object { $_.Trim() } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if (@($lines).Count -eq 0) {
        return $null
    }

    $selectedLines = if ($MemoryConfig.guardrails.deny_large_logs) {
        @($lines | Select-Object -First 4)
    } else {
        $lines
    }
    $summary = (($selectedLines -join " ") -replace '\s+', ' ').Trim()
    if ([string]::IsNullOrWhiteSpace($summary)) {
        return $null
    }

    if ($MemoryConfig.guardrails.deny_secrets -and (Test-MemorySecretLikeContent -Text $summary)) {
        return $null
    }

    if ($MemoryConfig.guardrails.deny_instruction_like_content -and (Test-MemoryInstructionLikeContent -Text $summary)) {
        return $null
    }

    if ($summary.Length -gt $MaxChars) {
        $summary = $summary.Substring(0, $MaxChars).Trim() + "..."
    }

    return $summary
}

function New-MemoryInboxEntry {
    param(
        $MemoryConfig,
        [string]$Source,
        [string]$Kind,
        [string]$Text,
        [string[]]$Paths,
        [string[]]$Tags,
        [bool]$Verified = $true,
        [bool]$Promote = $false
    )

    if (-not $MemoryConfig.active -or -not $MemoryConfig.retain.enabled) {
        return [pscustomobject]@{
            written = $false
            path = $null
            relative_path = $null
            text = $null
        }
    }

    if ($Promote -and $MemoryConfig.guardrails.promote_only_verified -and -not $Verified) {
        $Promote = $false
    }

    $safeText = Get-SafeMemoryText -Text $Text -MaxChars $MemoryConfig.retain.max_entry_chars -MemoryConfig $MemoryConfig
    if ([string]::IsNullOrWhiteSpace($safeText)) {
        return [pscustomobject]@{
            written = $false
            path = $null
            relative_path = $null
            text = $null
        }
    }

    $timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffZ")
    $safeSource = if ([string]::IsNullOrWhiteSpace($Source)) { "run" } else { ($Source -replace '[^A-Za-z0-9_.-]', '-') }
    $filePath = Join-Path $MemoryConfig.inbox_root ("{0}-{1}.md" -f $timestamp, $safeSource)
    $relativePath = ConvertTo-MemoryRelativePath -RootPath $MemoryConfig.workspace_root -TargetPath $filePath
    $content = @(
        "# Memory Candidate",
        "",
        "- created_at_utc: $((Get-Date).ToUniversalTime().ToString("o"))",
        "- source: $Source",
        "- kind: $Kind",
        "- verified: $Verified",
        "- promote: $Promote",
        "- paths: $((@(Get-MemoryStringList $Paths) | Select-Object -Unique) -join ', ')",
        "- tags: $((@(Get-MemoryStringList $Tags) | Select-Object -Unique) -join ', ')",
        "- durability: candidate",
        "",
        $safeText
    ) -join [Environment]::NewLine

    Write-RollbackSafeFile -Path $filePath -Content $content | Out-Null

    return [pscustomobject]@{
        written = $true
        path = $filePath
        relative_path = $relativePath
        text = $safeText
    }
}

function Append-DailyMemoryEntry {
    param(
        $MemoryConfig,
        [string]$Source,
        [string]$Kind,
        [string]$Text,
        [string[]]$Paths,
        [string[]]$Tags
    )

    if (-not $MemoryConfig.active -or -not $MemoryConfig.retain.enabled) {
        return [pscustomobject]@{
            written = $false
            path = $null
            relative_path = $null
        }
    }

    $safeText = Get-SafeMemoryText -Text $Text -MaxChars $MemoryConfig.retain.max_entry_chars -MemoryConfig $MemoryConfig
    if ([string]::IsNullOrWhiteSpace($safeText)) {
        return [pscustomobject]@{
            written = $false
            path = $null
            relative_path = $null
        }
    }

    $filePath = Join-Path $MemoryConfig.daily_root ("{0}.md" -f (Get-Date -Format "yyyy-MM-dd"))
    $relativePath = ConvertTo-MemoryRelativePath -RootPath $MemoryConfig.workspace_root -TargetPath $filePath
    $currentContent = if (Test-Path -LiteralPath $filePath) {
        Get-MemoryFileText -Path $filePath
    } else {
        "# {0}" -f (Get-Date -Format "yyyy-MM-dd")
    }

    $entry = @(
        "",
        "## $((Get-Date).ToUniversalTime().ToString("o")) | source:$Source",
        "- kind: $Kind",
        "- paths: $((@(Get-MemoryStringList $Paths) | Select-Object -Unique) -join ', ')",
        "- tags: $((@(Get-MemoryStringList $Tags) | Select-Object -Unique) -join ', ')",
        "",
        $safeText
    ) -join [Environment]::NewLine

    Write-RollbackSafeFile -Path $filePath -Content ($currentContent.TrimEnd() + $entry) | Out-Null

    return [pscustomobject]@{
        written = $true
        path = $filePath
        relative_path = $relativePath
    }
}

function Promote-MemoryCandidates {
    param($MemoryConfig)

    if (-not $MemoryConfig.active) {
        return 0
    }

    $memoryText = Get-MemoryFileText -Path $MemoryConfig.memory_file
    $appended = New-Object System.Collections.Generic.List[string]
    foreach ($file in @(Get-ChildItem -LiteralPath $MemoryConfig.inbox_root -Filter "*.md" -File -ErrorAction SilentlyContinue | Sort-Object Name)) {
        $content = Get-MemoryFileText -Path $file.FullName
        if ($content -notmatch '(?im)^- promote:\s*true\s*$') {
            continue
        }

        $safeText = Get-SafeMemoryText -Text $content -MaxChars $MemoryConfig.retain.max_entry_chars -MemoryConfig $MemoryConfig
        if ([string]::IsNullOrWhiteSpace($safeText)) {
            continue
        }

        if ($memoryText -like "*$safeText*") {
            continue
        }

        $appended.Add("- $safeText")
    }

    if (@($appended).Count -lt 1) {
        return 0
    }

    if ($memoryText -notmatch '(?im)^## Retained Facts\s*$') {
        $memoryText = $memoryText.TrimEnd() + [Environment]::NewLine + [Environment]::NewLine + "## Retained Facts" + [Environment]::NewLine
    }

    $memoryText = $memoryText.TrimEnd() + [Environment]::NewLine + [Environment]::NewLine + (($appended.ToArray()) -join [Environment]::NewLine)
    Write-RollbackSafeFile -Path $MemoryConfig.memory_file -Content $memoryText | Out-Null
    return @($appended).Count
}

function Prune-StaleMemoryEntries {
    param($MemoryConfig)

    if (-not $MemoryConfig.active) {
        return 0
    }

    $pruned = 0
    $cutoff = (Get-Date).ToUniversalTime().AddDays(-1 * [math]::Abs($MemoryConfig.optimize.prune_ttl_days))
    foreach ($file in @(Get-ChildItem -LiteralPath $MemoryConfig.inbox_root -Filter "*.md" -File -ErrorAction SilentlyContinue)) {
        if ($file.LastWriteTimeUtc -lt $cutoff) {
            Remove-Item -LiteralPath $file.FullName -Force
            $pruned += 1
        }
    }

    return $pruned
}

function Test-MemoryOptimizeNeeded {
    param($MemoryConfig)

    if (-not $MemoryConfig.active -or -not $MemoryConfig.optimize.enabled) {
        return [pscustomobject]@{
            should_run = $false
            reasons = @()
        }
    }

    $state = Get-MemoryState -MemoryConfig $MemoryConfig
    $reasons = New-Object System.Collections.Generic.List[string]
    if ($MemoryConfig.optimize.every_completed_runs -gt 0 -and $state.completed_runs -gt 0 -and ($state.completed_runs % $MemoryConfig.optimize.every_completed_runs) -eq 0) {
        $reasons.Add("completed_runs")
    }
    if ((Get-MemoryFileText -Path $MemoryConfig.memory_file).Length -gt $MemoryConfig.optimize.memory_max_chars) {
        $reasons.Add("memory_max_chars")
    }
    if ((Get-MemoryFileText -Path $MemoryConfig.active_file).Length -gt $MemoryConfig.optimize.active_max_chars) {
        $reasons.Add("active_max_chars")
    }

    $todayFile = Join-Path $MemoryConfig.daily_root ("{0}.md" -f (Get-Date -Format "yyyy-MM-dd"))
    if ((Get-MemoryFileText -Path $todayFile).Length -gt $MemoryConfig.optimize.daily_max_chars) {
        $reasons.Add("daily_max_chars")
    }

    return [pscustomobject]@{
        should_run = (@($reasons).Count -gt 0)
        reasons = [string[]]$reasons.ToArray()
    }
}

function Optimize-MemoryStore {
    param($MemoryConfig)

    if (-not $MemoryConfig.active) {
        return [pscustomobject]@{
            ran = $false
            reasons = @()
            promoted_entries = 0
            pruned_entries = 0
            index_chunk_count = 0
        }
    }

    $decision = Test-MemoryOptimizeNeeded -MemoryConfig $MemoryConfig
    if (-not $decision.should_run) {
        return [pscustomobject]@{
            ran = $false
            reasons = @()
            promoted_entries = 0
            pruned_entries = 0
            index_chunk_count = (Get-MemoryIndex -MemoryConfig $MemoryConfig).chunk_count
        }
    }

    $promoted = Promote-MemoryCandidates -MemoryConfig $MemoryConfig
    $pruned = Prune-StaleMemoryEntries -MemoryConfig $MemoryConfig
    $index = Rebuild-MemoryIndex -MemoryConfig $MemoryConfig
    $state = Get-MemoryState -MemoryConfig $MemoryConfig
    $state.last_optimized_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    $state.last_optimize_reason = [string[]]$decision.reasons
    Save-MemoryState -MemoryConfig $MemoryConfig -State $state

    return [pscustomobject]@{
        ran = $true
        reasons = [string[]]$decision.reasons
        promoted_entries = $promoted
        pruned_entries = $pruned
        index_chunk_count = $index.chunk_count
    }
}

function Write-RunMemoryArtifacts {
    param(
        $MemoryConfig,
        $Results,
        [string[]]$RequestedDeliverables
    )

    if (-not $MemoryConfig.active) {
        return $null
    }

    $state = Get-MemoryState -MemoryConfig $MemoryConfig
    $state.completed_runs = [int]$state.completed_runs + 1
    $state.last_run_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    Save-MemoryState -MemoryConfig $MemoryConfig -State $state

    $inboxCount = 0
    $dailyCount = 0
    foreach ($result in @($Results)) {
        if ($result.worker_kind -notin @("reviewer", "validator", "fixer")) {
            continue
        }

        if (-not [bool](Get-MemoryOptionalProperty $result "succeeded")) {
            continue
        }

        $resultText = Get-MemoryFileText -Path ([string](Get-MemoryOptionalProperty $result "last"))
        if ([string]::IsNullOrWhiteSpace($resultText)) {
            $resultText = [string](Get-MemoryOptionalProperty $result "last_message_preview")
        }
        $paths = @(
            @(Get-MemoryStringList (Get-MemoryOptionalProperty $result "required_paths"))
            @(Get-MemoryStringList $RequestedDeliverables)
        ) | Select-Object -Unique
        $tags = @($result.worker_kind, $result.name, "launcher-memory") | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        $entry = New-MemoryInboxEntry `
            -MemoryConfig $MemoryConfig `
            -Source ([string]$result.name) `
            -Kind ([string]$result.worker_kind) `
            -Text $resultText `
            -Paths $paths `
            -Tags $tags `
            -Verified ([bool]$result.succeeded) `
            -Promote $false
        if ($entry.written) {
            $inboxCount += 1
        }
    }

    $successCount = @($Results | Where-Object { $_.succeeded }).Count
    $totalCount = @($Results).Count
    $reviewerPresent = (@($Results | Where-Object { $_.worker_kind -in @("reviewer", "validator") -and $_.is_read_only }).Count -gt 0)
    $deliverableList = @(Get-MemoryStringList $RequestedDeliverables)
    $deliverableText = if ($deliverableList.Count -gt 0) {
        "Deliverables: $($deliverableList -join ', ')."
    } else {
        "No explicit deliverables were declared."
    }
    $dailyEntry = Append-DailyMemoryEntry `
        -MemoryConfig $MemoryConfig `
        -Source "orchestration" `
        -Kind "run-summary" `
        -Text ("Workers succeeded {0}/{1}. Final read-only review present: {2}. {3}" -f $successCount, $totalCount, $reviewerPresent, $deliverableText) `
        -Paths $deliverableList `
        -Tags @("run-summary", "launcher-memory")
    if ($dailyEntry.written) {
        $dailyCount = 1
    }

    $index = Rebuild-MemoryIndex -MemoryConfig $MemoryConfig
    $optimizeResult = Optimize-MemoryStore -MemoryConfig $MemoryConfig
    return [pscustomobject]@{
        inbox_entries_written = $inboxCount
        daily_entries_written = $dailyCount
        optimize_result = $optimizeResult
        index_chunk_count = if ($optimizeResult.ran) { $optimizeResult.index_chunk_count } else { $index.chunk_count }
    }
}

function Get-MemoryMetrics {
    param(
        $MemoryConfig,
        $WorkerContextInfos,
        $RunMemoryArtifacts
    )

    if (-not $MemoryConfig.configured) {
        return $null
    }

    $state = if ($MemoryConfig.active) { Get-MemoryState -MemoryConfig $MemoryConfig } else { [pscustomobject](Get-MemoryDefaultState) }
    $stats = if ($MemoryConfig.active -and (Test-Path -LiteralPath $MemoryConfig.stats_file)) {
        Read-RollbackSafeJsonFile -Path $MemoryConfig.stats_file
    } else {
        $null
    }

    $contexts = @()
    foreach ($context in @($WorkerContextInfos)) {
        $contexts += [pscustomobject]@{
            worker = [string](Get-MemoryOptionalProperty $context "worker")
            mode = [string](Get-MemoryOptionalProperty $context "mode")
            exists = [bool](Get-MemoryOptionalProperty $context "exists")
            relative_path = [string](Get-MemoryOptionalProperty $context "relative_path")
            snippet_count = if ($null -ne (Get-MemoryOptionalProperty $context "snippet_count")) { [int](Get-MemoryOptionalProperty $context "snippet_count") } else { 0 }
            injected_chars = if ($null -ne (Get-MemoryOptionalProperty $context "injected_chars")) { [int](Get-MemoryOptionalProperty $context "injected_chars") } else { 0 }
            hit_paths = [string[]](Get-MemoryStringList (Get-MemoryOptionalProperty $context "hit_paths"))
        }
    }

    return [pscustomobject]@{
        configured = $true
        enabled = [bool]$MemoryConfig.enabled
        active = [bool]$MemoryConfig.active
        root = if ($MemoryConfig.root) { $MemoryConfig.root } else { $null }
        relative_root = $MemoryConfig.relative_root
        requested_mode = $MemoryConfig.requested_mode
        mode = $MemoryConfig.mode
        completed_runs = [int](Get-MemoryOptionalProperty $state "completed_runs")
        last_run_at_utc = [string](Get-MemoryOptionalProperty $state "last_run_at_utc")
        last_optimized_at_utc = [string](Get-MemoryOptionalProperty $state "last_optimized_at_utc")
        last_optimize_reason = [string[]](Get-MemoryStringList (Get-MemoryOptionalProperty $state "last_optimize_reason"))
        runtime_files_written = @($contexts | Where-Object { $_.exists }).Count
        inbox_entries_written = if ($RunMemoryArtifacts) { [int](Get-MemoryOptionalProperty $RunMemoryArtifacts "inbox_entries_written") } else { 0 }
        daily_entries_written = if ($RunMemoryArtifacts) { [int](Get-MemoryOptionalProperty $RunMemoryArtifacts "daily_entries_written") } else { 0 }
        optimize_ran = if ($RunMemoryArtifacts) { [bool](Get-MemoryOptionalProperty (Get-MemoryOptionalProperty $RunMemoryArtifacts "optimize_result") "ran") } else { $false }
        promoted_entries = if ($RunMemoryArtifacts) { [int](Get-MemoryOptionalProperty (Get-MemoryOptionalProperty $RunMemoryArtifacts "optimize_result") "promoted_entries") } else { 0 }
        pruned_entries = if ($RunMemoryArtifacts) { [int](Get-MemoryOptionalProperty (Get-MemoryOptionalProperty $RunMemoryArtifacts "optimize_result") "pruned_entries") } else { 0 }
        optimize_reasons = if ($RunMemoryArtifacts) { [string[]](Get-MemoryStringList (Get-MemoryOptionalProperty (Get-MemoryOptionalProperty $RunMemoryArtifacts "optimize_result") "reasons")) } else { @() }
        index_chunk_count = if ($RunMemoryArtifacts -and $null -ne (Get-MemoryOptionalProperty $RunMemoryArtifacts "index_chunk_count")) { [int](Get-MemoryOptionalProperty $RunMemoryArtifacts "index_chunk_count") } elseif ($stats) { [int](Get-MemoryOptionalProperty $stats "chunk_count") } else { 0 }
        source_counts = if ($stats) { Get-MemoryOptionalProperty $stats "source_counts" } else { $null }
        workers = $contexts
    }
}
