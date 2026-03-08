param(
    [Parameter(Mandatory = $true)]
    [string]$ConfigPath,

    [string]$LauncherPath = (Join-Path $PSScriptRoot "start-codex-subagent-team.ps1"),

    [string]$CodexExecutable = "codex",

    [int]$MaxPolls = 0,

    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-OptionalProperty {
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

function Get-BoolValue {
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

function Get-StringList {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }

    if ($Value -is [string]) {
        return @([string]$Value)
    }

    $items = @()
    foreach ($entry in $Value) {
        if ($null -ne $entry) {
            $items += [string]$entry
        }
    }

    return $items
}

function Get-UniqueStringList {
    param($Value)

    $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    $items = New-Object System.Collections.Generic.List[string]

    foreach ($entry in @(Get-StringList $Value)) {
        if ([string]::IsNullOrWhiteSpace($entry)) {
            continue
        }

        if ($seen.Add($entry)) {
            $items.Add($entry)
        }
    }

    return [string[]]$items.ToArray()
}

function Normalize-PathInput {
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

function Resolve-AbsolutePath {
    param(
        [string]$Path,
        [string]$BaseDirectory,
        [switch]$AllowMissing
    )

    $inputPath = Normalize-PathInput $Path
    if ([string]::IsNullOrWhiteSpace($inputPath)) {
        throw "Path value cannot be empty."
    }

    $normalizedBaseDirectory = Normalize-PathInput $BaseDirectory
    if ([string]::IsNullOrWhiteSpace($normalizedBaseDirectory)) {
        $normalizedBaseDirectory = (Get-Location).Path
    }

    $candidate = if ([System.IO.Path]::IsPathRooted($inputPath)) {
        [System.IO.Path]::GetFullPath($inputPath)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path -Path $normalizedBaseDirectory -ChildPath $inputPath))
    }

    if ($AllowMissing) {
        return [string]$candidate
    }

    if (-not (Test-Path -LiteralPath $candidate)) {
        throw "Resolved path does not exist: $candidate"
    }

    return [string]$candidate
}

function Resolve-CommandPath {
    param([string]$Executable)

    $normalized = Normalize-PathInput $Executable
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        throw "Executable value cannot be empty."
    }

    if ([System.IO.Path]::IsPathRooted($normalized) -or $normalized.Contains("\") -or $normalized.Contains("/")) {
        return Resolve-AbsolutePath -Path $normalized -BaseDirectory (Get-Location).Path -AllowMissing
    }

    $command = Get-Command $normalized -ErrorAction Stop | Select-Object -First 1
    if ($command.Path) {
        return $command.Path
    }

    return $normalized
}

function Get-SafePathSegment {
    param(
        [string]$Value,
        [string]$Default = "item"
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $Default
    }

    $safe = $Value
    foreach ($invalid in [System.IO.Path]::GetInvalidFileNameChars()) {
        $safe = $safe.Replace([string]$invalid, "-")
    }

    $safe = $safe -replace '\s+', '-'
    $safe = $safe -replace '-{2,}', '-'
    $safe = $safe.Trim(" ", ".", "-")
    if ([string]::IsNullOrWhiteSpace($safe)) {
        return $Default
    }

    return $safe
}

function Quote-Arg {
    param([string]$Value)

    if ($null -eq $Value -or $Value -eq "") {
        return '""'
    }

    if ($Value -match '[\s"]') {
        $escaped = $Value -replace '(\\*)"', '$1$1\"'
        $escaped = $escaped -replace '(\\+)$', '$1$1'
        return '"' + $escaped + '"'
    }

    return $Value
}

function Join-ArgLine {
    param([string[]]$Items)

    return ($Items | ForEach-Object { Quote-Arg $_ }) -join " "
}

function ConvertTo-NormalizedValue {
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
            $map[[string]$key] = ConvertTo-NormalizedValue $Value[$key]
        }

        return $map
    }

    if ($Value -is [pscustomobject]) {
        $map = [ordered]@{}
        foreach ($property in $Value.PSObject.Properties) {
            $map[[string]$property.Name] = ConvertTo-NormalizedValue $property.Value
        }

        return $map
    }

    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        $items = New-Object System.Collections.Generic.List[object]
        foreach ($entry in $Value) {
            $items.Add((ConvertTo-NormalizedValue $entry))
        }

        return @($items.ToArray())
    }

    return $Value
}

function ConvertTo-NormalizedMap {
    param($Value)

    if ($null -eq $Value) {
        return [ordered]@{}
    }

    $normalized = ConvertTo-NormalizedValue $Value
    if ($normalized -isnot [System.Collections.IDictionary]) {
        throw "Expected an object value."
    }

    return $normalized
}

function Merge-NormalizedMaps {
    param(
        [System.Collections.IDictionary]$Base,
        [System.Collections.IDictionary]$Overlay
    )

    if ($null -eq $Base -or $Base.Count -eq 0) {
        return ConvertTo-NormalizedMap $Overlay
    }

    if ($null -eq $Overlay -or $Overlay.Count -eq 0) {
        return ConvertTo-NormalizedMap $Base
    }

    $merged = [ordered]@{}
    foreach ($key in $Base.Keys) {
        $merged[[string]$key] = ConvertTo-NormalizedValue $Base[$key]
    }

    foreach ($key in $Overlay.Keys) {
        $stringKey = [string]$key
        $overlayValue = ConvertTo-NormalizedValue $Overlay[$key]
        if ($merged.Contains($stringKey) -and
            $merged[$stringKey] -is [System.Collections.IDictionary] -and
            $overlayValue -is [System.Collections.IDictionary]) {
            $merged[$stringKey] = Merge-NormalizedMaps -Base $merged[$stringKey] -Overlay $overlayValue
            continue
        }

        $merged[$stringKey] = $overlayValue
    }

    return $merged
}

function Get-TimestampUtc {
    return (Get-Date).ToUniversalTime().ToString("o")
}

function Get-FirstNonEmptyString {
    param([object[]]$Values)

    foreach ($value in $Values) {
        if ($null -eq $value) {
            continue
        }

        $text = [string]$value
        if (-not [string]::IsNullOrWhiteSpace($text)) {
            return $text
        }
    }

    return $null
}

function Get-FrontMatterStringList {
    param(
        $FrontMatter,
        [string]$Name
    )

    $value = Get-OptionalProperty $FrontMatter $Name
    if ($null -eq $value) {
        return @()
    }

    if ($value -is [string]) {
        $trimmed = $value.Trim()
        if ($trimmed.StartsWith("[") -and $trimmed.EndsWith("]")) {
            try {
                $decoded = $trimmed | ConvertFrom-Json -ErrorAction Stop
                return ,([string[]](Get-UniqueStringList $decoded))
            } catch {
            }
        }

        return ,([string[]](Get-UniqueStringList ($trimmed -split '\s*,\s*')))
    }

    return ,([string[]](Get-UniqueStringList $value))
}

function ConvertFrom-FrontMatterScalar {
    param([string]$Value)

    if ($null -eq $Value) {
        return $null
    }

    $trimmed = $Value.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        return ""
    }

    if (($trimmed.StartsWith('"') -and $trimmed.EndsWith('"')) -or ($trimmed.StartsWith("'") -and $trimmed.EndsWith("'"))) {
        return $trimmed.Substring(1, $trimmed.Length - 2)
    }

    if ($trimmed -match '^(?i:true|false)$') {
        return [bool]::Parse($trimmed)
    }

    $intValue = 0
    if ([int]::TryParse($trimmed, [ref]$intValue)) {
        return $intValue
    }

    if ($trimmed.StartsWith("[") -and $trimmed.EndsWith("]")) {
        try {
            return $trimmed | ConvertFrom-Json -ErrorAction Stop
        } catch {
        }
    }

    return $trimmed
}

function ConvertFrom-SimpleFrontMatter {
    param([string]$FrontMatterText)

    $frontMatter = [ordered]@{}
    $currentListKey = $null

    foreach ($rawLine in ($FrontMatterText -split "`r?`n")) {
        $line = $rawLine.TrimEnd()
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        if ($line.TrimStart().StartsWith("#")) {
            continue
        }

        if ($line -match '^\s*([A-Za-z0-9_.-]+)\s*:\s*(.*)$') {
            $key = [string]$matches[1]
            $rawValue = [string]$matches[2]

            if ([string]::IsNullOrWhiteSpace($rawValue)) {
                $frontMatter[$key] = @()
                $currentListKey = $key
            } else {
                $frontMatter[$key] = ConvertFrom-FrontMatterScalar -Value $rawValue
                $currentListKey = $null
            }

            continue
        }

        if ($null -ne $currentListKey -and $line -match '^\s*-\s*(.+)$') {
            $values = @()
            foreach ($entry in @($frontMatter[$currentListKey])) {
                if ($null -ne $entry) {
                    $values += $entry
                }
            }

            $values += (ConvertFrom-FrontMatterScalar -Value ([string]$matches[1]))
            $frontMatter[$currentListKey] = $values
        }
    }

    return $frontMatter
}

function Split-MarkdownTaskDocument {
    param([string]$Content)

    $body = $Content
    $frontMatter = [ordered]@{}
    $match = [regex]::Match(
        $Content,
        '^---\r?\n(?<front>.*?)\r?\n---\r?\n?(?<body>[\s\S]*)$',
        [System.Text.RegularExpressions.RegexOptions]::Singleline
    )

    if ($match.Success) {
        $frontMatter = ConvertFrom-SimpleFrontMatter -FrontMatterText ([string]$match.Groups["front"].Value)
        $body = [string]$match.Groups["body"].Value
    }

    return [pscustomobject]@{
        front_matter = $frontMatter
        body = $body
    }
}

function Get-FileTimestampUtc {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    return (Get-Item -LiteralPath $Path).LastWriteTimeUtc.ToString("o")
}

function New-DefaultAgentsTemplate {
    return @(
        [ordered]@{
            name = "issue-implementer"
            kind = "implementer"
            stage = 1
            role = "issue implementer"
            mission = "Execute the current issue in the assigned workspace while respecting repository rules and declared scope."
            task = "Implement the current issue in this workspace, validate the result, and stop when the workflow-defined handoff state has been reached."
            return_contract = @(
                "Return a concise implementation summary and concrete validation notes only."
            )
        },
        [ordered]@{
            name = "issue-reviewer"
            kind = "reviewer"
            stage = 2
            sandbox = "read-only"
            role = "final reviewer"
            mission = "Review the final workspace state after implementation."
            task = "Review the final workspace state for correctness, scope compliance, and readiness for handoff."
            return_contract = @(
                "Return a concise review verdict and only the material issues."
            )
        }
    )
}

function Get-QueueConfig {
    param(
        $RawConfig,
        [string]$ConfigDirectory,
        [string]$LauncherScriptPath
    )

    $tracker = ConvertTo-NormalizedMap (Get-OptionalProperty $RawConfig "tracker")
    $polling = ConvertTo-NormalizedMap (Get-OptionalProperty $RawConfig "polling")
    $workspace = ConvertTo-NormalizedMap (Get-OptionalProperty $RawConfig "workspace")
    $output = ConvertTo-NormalizedMap (Get-OptionalProperty $RawConfig "output")
    $launcher = ConvertTo-NormalizedMap (Get-OptionalProperty $RawConfig "launcher")
    $hooks = ConvertTo-NormalizedMap (Get-OptionalProperty $RawConfig "hooks")

    $trackerKind = [string](Get-OptionalProperty $tracker "kind")
    if ([string]::IsNullOrWhiteSpace($trackerKind)) {
        throw "Queue config must define tracker.kind."
    }

    $workspaceRootValue = Get-OptionalProperty $workspace "root"
    if (-not $workspaceRootValue) {
        throw "Queue config must define workspace.root."
    }

    $outputRootValue = Get-OptionalProperty $output "root"
    if (-not $outputRootValue) {
        $outputRootValue = "queue-runs"
    }

    $outputRoot = Resolve-AbsolutePath -Path ([string]$outputRootValue) -BaseDirectory $ConfigDirectory -AllowMissing
    $workspaceRoot = Resolve-AbsolutePath -Path ([string]$workspaceRootValue) -BaseDirectory $ConfigDirectory -AllowMissing
    $stateFileValue = Get-OptionalProperty $output "state_file"
    $stateFile = if ($stateFileValue) {
        Resolve-AbsolutePath -Path ([string]$stateFileValue) -BaseDirectory $ConfigDirectory -AllowMissing
    } else {
        Resolve-AbsolutePath -Path (Join-Path $outputRoot "queue-state.json") -BaseDirectory $ConfigDirectory -AllowMissing
    }

    $workflowFileValue = Get-OptionalProperty $RawConfig "workflow_file"
    $workflowFile = if ($workflowFileValue) {
        Resolve-AbsolutePath -Path ([string]$workflowFileValue) -BaseDirectory $ConfigDirectory -AllowMissing
    } else {
        $null
    }

    $maxConcurrentIssuesValue = Get-OptionalProperty $launcher "max_concurrent_issues"
    $maxConcurrentIssues = if ($maxConcurrentIssuesValue) { [int]$maxConcurrentIssuesValue } else { 1 }
    if ($maxConcurrentIssues -lt 1) {
        throw "launcher.max_concurrent_issues must be at least 1."
    }

    $pollIntervalSecondsValue = Get-OptionalProperty $polling "interval_seconds"
    $pollIntervalSeconds = if ($pollIntervalSecondsValue) { [int]$pollIntervalSecondsValue } else { 5 }
    if ($pollIntervalSeconds -lt 1) {
        $pollIntervalSeconds = 1
    }

    $configuredMaxPollsValue = Get-OptionalProperty $polling "max_polls"
    $configuredMaxPolls = if ($configuredMaxPollsValue) { [int]$configuredMaxPollsValue } else { 0 }
    $drainOnExit = Get-BoolValue (Get-OptionalProperty $polling "drain_on_exit") $true

    $retry = ConvertTo-NormalizedMap (Get-OptionalProperty $RawConfig "retry")
    $baseBackoffSecondsValue = Get-OptionalProperty $retry "base_backoff_seconds"
    $maxBackoffSecondsValue = Get-OptionalProperty $retry "max_backoff_seconds"
    $baseBackoffSeconds = if ($baseBackoffSecondsValue) { [int]$baseBackoffSecondsValue } else { 30 }
    $maxBackoffSeconds = if ($maxBackoffSecondsValue) { [int]$maxBackoffSecondsValue } else { 300 }

    $generatedSpecsRoot = Resolve-AbsolutePath -Path (Join-Path $outputRoot "generated-specs") -BaseDirectory $ConfigDirectory -AllowMissing
    $issueRunsRoot = Resolve-AbsolutePath -Path (Join-Path $outputRoot "issue-runs") -BaseDirectory $ConfigDirectory -AllowMissing
    $queueLogsRoot = Resolve-AbsolutePath -Path (Join-Path $outputRoot "queue-logs") -BaseDirectory $ConfigDirectory -AllowMissing

    $defaults = ConvertTo-NormalizedMap (Get-OptionalProperty $launcher "defaults")
    $agentsTemplate = Get-OptionalProperty $launcher "agents_template"
    if ($null -eq $agentsTemplate -or @($agentsTemplate).Count -eq 0) {
        $agentsTemplate = New-DefaultAgentsTemplate
    }

    $sourceFileValue = Get-OptionalProperty $tracker "source_file"
    $sourceFile = if ($sourceFileValue) {
        Resolve-AbsolutePath -Path ([string]$sourceFileValue) -BaseDirectory $ConfigDirectory -AllowMissing
    } else {
        $null
    }

    $sourceDirectoryValue = Get-OptionalProperty $tracker "source_dir"
    $sourceDirectory = if ($sourceDirectoryValue) {
        Resolve-AbsolutePath -Path ([string]$sourceDirectoryValue) -BaseDirectory $ConfigDirectory -AllowMissing
    } else {
        $null
    }

    $reportFileValue = Get-OptionalProperty $output "report_file"
    $reportFile = if ($reportFileValue) {
        Resolve-AbsolutePath -Path ([string]$reportFileValue) -BaseDirectory $ConfigDirectory -AllowMissing
    } else {
        Resolve-AbsolutePath -Path (Join-Path $outputRoot "queue-report.md") -BaseDirectory $ConfigDirectory -AllowMissing
    }

    return [pscustomobject]@{
        config_directory = $ConfigDirectory
        launcher_script = Resolve-AbsolutePath -Path $LauncherScriptPath -BaseDirectory $ConfigDirectory
        workflow_file = $workflowFile
        workflow_auto_detect = Get-BoolValue (Get-OptionalProperty $RawConfig "workflow_auto_detect") $true
        workflow_prompt_mode = if (Get-OptionalProperty $RawConfig "workflow_prompt_mode") { [string](Get-OptionalProperty $RawConfig "workflow_prompt_mode") } else { "prepend" }
        workflow_render_strict = Get-BoolValue (Get-OptionalProperty $RawConfig "workflow_render_strict") $true
        tracker = [pscustomobject]@{
            kind = $trackerKind.ToLowerInvariant()
            active_states = [string[]](Get-UniqueStringList (Get-OptionalProperty $tracker "active_states"))
            terminal_states = [string[]](Get-UniqueStringList (Get-OptionalProperty $tracker "terminal_states"))
            project_slug = [string](Get-OptionalProperty $tracker "project_slug")
            source_file = $sourceFile
            source_dir = $sourceDirectory
            include_globs = [string[]](Get-UniqueStringList (Get-OptionalProperty $tracker "include_globs"))
            recurse = Get-BoolValue (Get-OptionalProperty $tracker "recurse") $true
            endpoint = if (Get-OptionalProperty $tracker "endpoint") { [string](Get-OptionalProperty $tracker "endpoint") } else { "https://api.linear.app/graphql" }
            api_key_env = if (Get-OptionalProperty $tracker "api_key_env") { [string](Get-OptionalProperty $tracker "api_key_env") } else { "LINEAR_API_KEY" }
        }
        polling = [pscustomobject]@{
            interval_seconds = $pollIntervalSeconds
            max_polls = if ($MaxPolls -gt 0) { $MaxPolls } else { $configuredMaxPolls }
            drain_on_exit = $drainOnExit
        }
        retry = [pscustomobject]@{
            base_backoff_seconds = $baseBackoffSeconds
            max_backoff_seconds = $maxBackoffSeconds
        }
        workspace = [pscustomobject]@{
            root = $workspaceRoot
        }
        output = [pscustomobject]@{
            root = $outputRoot
            state_file = $stateFile
            report_file = $reportFile
            generated_specs_root = $generatedSpecsRoot
            issue_runs_root = $issueRunsRoot
            queue_logs_root = $queueLogsRoot
        }
        launcher = [pscustomobject]@{
            execution_mode = if (Get-OptionalProperty $launcher "execution_mode") { [string](Get-OptionalProperty $launcher "execution_mode") } else { "sequential" }
            write_prompt_files = Get-BoolValue (Get-OptionalProperty $launcher "write_prompt_files") $true
            write_summary_file = Get-BoolValue (Get-OptionalProperty $launcher "write_summary_file") $true
            write_run_archive = Get-BoolValue (Get-OptionalProperty $launcher "write_run_archive") $true
            shared_directive_mode = if (Get-OptionalProperty $launcher "shared_directive_mode") { [string](Get-OptionalProperty $launcher "shared_directive_mode") } else { "reference" }
            requested_deliverables = [string[]](Get-UniqueStringList (Get-OptionalProperty $launcher "requested_deliverables"))
            supervisor_only = Get-BoolValue (Get-OptionalProperty $launcher "supervisor_only") $true
            require_final_read_only_review = Get-BoolValue (Get-OptionalProperty $launcher "require_final_read_only_review") $true
            material_issue_strategy = if (Get-OptionalProperty $launcher "material_issue_strategy") { [string](Get-OptionalProperty $launcher "material_issue_strategy") } else { "fixer_then_rereview" }
            defaults = $defaults
            max_concurrent_issues = $maxConcurrentIssues
            agents_template = ConvertTo-NormalizedValue $agentsTemplate
        }
        hooks = $hooks
    }
}

function Get-NormalizedIssue {
    param($RawIssue)

    $issue = ConvertTo-NormalizedMap $RawIssue
    $identifier = Get-FirstNonEmptyString @(
        (Get-OptionalProperty $issue "identifier"),
        (Get-OptionalProperty $issue "id"),
        (Get-OptionalProperty $issue "key")
    )
    $title = Get-FirstNonEmptyString @(
        (Get-OptionalProperty $issue "title"),
        (Get-OptionalProperty $issue "name"),
        $identifier
    )

    return [pscustomobject]@{
        id = Get-FirstNonEmptyString @((Get-OptionalProperty $issue "id"), $identifier)
        identifier = $identifier
        title = $title
        description = Get-FirstNonEmptyString @((Get-OptionalProperty $issue "description"), (Get-OptionalProperty $issue "body"), "")
        priority = Get-OptionalProperty $issue "priority"
        state = Get-FirstNonEmptyString @((Get-OptionalProperty $issue "state"), "Todo")
        branch_name = [string](Get-OptionalProperty $issue "branch_name")
        url = [string](Get-OptionalProperty $issue "url")
        labels = [string[]](Get-UniqueStringList (Get-OptionalProperty $issue "labels"))
        blocked_by = @(ConvertTo-NormalizedValue (Get-OptionalProperty $issue "blocked_by"))
        created_at = Get-FirstNonEmptyString @((Get-OptionalProperty $issue "created_at"), (Get-OptionalProperty $issue "updated_at"))
        updated_at = Get-FirstNonEmptyString @((Get-OptionalProperty $issue "updated_at"), (Get-OptionalProperty $issue "created_at"))
        requested_deliverables = [string[]](Get-UniqueStringList @((Get-OptionalProperty $issue "requested_deliverables"), (Get-OptionalProperty $issue "deliverables")))
        mode_hint = [string](Get-OptionalProperty $issue "mode_hint")
        auto_run = Get-OptionalProperty $issue "auto_run"
        source_path = [string](Get-OptionalProperty $issue "source_path")
        source_kind = [string](Get-OptionalProperty $issue "source_kind")
    }
}

function Get-JsonBackedIssues {
    param(
        [string]$SourceFile,
        [string]$SourceKind = "json-file"
    )

    $rawText = Get-Content -LiteralPath $SourceFile -Raw
    $decoded = $rawText | ConvertFrom-Json -ErrorAction Stop
    $rawIssues = if ($decoded -is [System.Collections.IEnumerable] -and -not ($decoded -is [string])) {
        $decoded
    } else {
        $containerIssues = Get-OptionalProperty $decoded "issues"
        if ($null -ne $containerIssues) {
            $containerIssues
        } else {
            $containerTasks = Get-OptionalProperty $decoded "tasks"
            if ($null -ne $containerTasks) {
                $containerTasks
            } else {
                @($decoded)
            }
        }
    }

    if ($null -eq $rawIssues) {
        return @()
    }

    $sourceUpdatedAt = Get-FileTimestampUtc -Path $SourceFile
    $issues = @()
    foreach ($entry in @($rawIssues)) {
        $issueMap = ConvertTo-NormalizedMap $entry
        $embeddedIssue = Get-OptionalProperty $issueMap "issue"
        if ($null -ne $embeddedIssue) {
            $issueMap = ConvertTo-NormalizedMap $embeddedIssue
        }

        $embeddedTask = Get-OptionalProperty $issueMap "task"
        if ($null -ne $embeddedTask) {
            $issueMap = ConvertTo-NormalizedMap $embeddedTask
        }

        if (-not (Get-OptionalProperty $issueMap "source_path")) {
            $issueMap["source_path"] = $SourceFile
        }

        if (-not (Get-OptionalProperty $issueMap "source_kind")) {
            $issueMap["source_kind"] = $SourceKind
        }

        if (-not (Get-OptionalProperty $issueMap "updated_at") -and $sourceUpdatedAt) {
            $issueMap["updated_at"] = $sourceUpdatedAt
        }

        $issues += Get-NormalizedIssue $issueMap
    }

    return @($issues)
}

function Get-MockTrackerIssues {
    param([string]$SourceFile)

    return Get-JsonBackedIssues -SourceFile $SourceFile -SourceKind "mock-json"
}

function Get-LocalJsonTrackerIssues {
    param([string]$SourceFile)

    if (-not (Test-Path -LiteralPath $SourceFile)) {
        return @()
    }

    return Get-JsonBackedIssues -SourceFile $SourceFile -SourceKind "local-json"
}

function Get-MarkdownTaskIssue {
    param([string]$SourceFile)

    $fileInfo = Get-Item -LiteralPath $SourceFile
    $content = Get-Content -LiteralPath $SourceFile -Raw
    $document = Split-MarkdownTaskDocument -Content $content
    $frontMatter = ConvertTo-NormalizedMap $document.front_matter
    $body = [string]$document.body

    $bodyLines = @($body -split "`r?`n")
    $headingTitle = $null
    $descriptionLines = $bodyLines
    for ($lineIndex = 0; $lineIndex -lt $bodyLines.Count; $lineIndex += 1) {
        $line = $bodyLines[$lineIndex]
        if ($line -match '^\s*#\s+(.+?)\s*$') {
            $headingTitle = [string]$matches[1].Trim()
            $descriptionLines = if ($lineIndex + 1 -lt $bodyLines.Count) {
                @($bodyLines[($lineIndex + 1)..($bodyLines.Count - 1)])
            } else {
                @()
            }
            break
        }
    }

    $descriptionBody = ([string]::Join([Environment]::NewLine, $descriptionLines)).Trim()

    $blockedBy = @(Get-FrontMatterStringList -FrontMatter $frontMatter -Name "blocked_by")
    $requestedDeliverables = @(Get-FrontMatterStringList -FrontMatter $frontMatter -Name "requested_deliverables")
    if ($requestedDeliverables.Count -eq 0) {
        $requestedDeliverables = @(Get-FrontMatterStringList -FrontMatter $frontMatter -Name "deliverables")
    }

    $issueMap = [ordered]@{
        id = Get-FirstNonEmptyString @((Get-OptionalProperty $frontMatter "id"), (Get-OptionalProperty $frontMatter "identifier"), $fileInfo.BaseName)
        identifier = Get-FirstNonEmptyString @((Get-OptionalProperty $frontMatter "identifier"), $fileInfo.BaseName)
        title = Get-FirstNonEmptyString @((Get-OptionalProperty $frontMatter "title"), $headingTitle, $fileInfo.BaseName)
        description = Get-FirstNonEmptyString @((Get-OptionalProperty $frontMatter "description"), $descriptionBody, "")
        priority = Get-OptionalProperty $frontMatter "priority"
        state = Get-FirstNonEmptyString @((Get-OptionalProperty $frontMatter "state"), "Todo")
        branch_name = [string](Get-OptionalProperty $frontMatter "branch_name")
        url = [string](Get-OptionalProperty $frontMatter "url")
        labels = @(Get-FrontMatterStringList -FrontMatter $frontMatter -Name "labels")
        blocked_by = @($blockedBy)
        created_at = Get-FirstNonEmptyString @((Get-OptionalProperty $frontMatter "created_at"), $fileInfo.CreationTimeUtc.ToString("o"))
        updated_at = Get-FirstNonEmptyString @((Get-OptionalProperty $frontMatter "updated_at"), $fileInfo.LastWriteTimeUtc.ToString("o"))
        requested_deliverables = @($requestedDeliverables)
        mode_hint = [string](Get-OptionalProperty $frontMatter "mode_hint")
        auto_run = Get-OptionalProperty $frontMatter "auto_run"
        source_path = $fileInfo.FullName
        source_kind = "local-file-markdown"
    }

    return Get-NormalizedIssue $issueMap
}

function Get-LocalFilesTrackerIssues {
    param(
        [string]$SourceDirectory,
        [string[]]$IncludeGlobs,
        [bool]$Recurse
    )

    if (-not (Test-Path -LiteralPath $SourceDirectory)) {
        return @()
    }

    $patterns = @($IncludeGlobs | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($patterns.Count -eq 0) {
        $patterns = @("*.json", "*.md", "*.txt")
    }

    $files = @()
    foreach ($pattern in $patterns) {
        $childItems = Get-ChildItem -LiteralPath $SourceDirectory -File -Filter $pattern -Recurse:$Recurse
        foreach ($item in @($childItems)) {
            $files += $item
        }
    }

    $issues = @()
    foreach ($file in @($files | Sort-Object -Property FullName -Unique)) {
        switch ($file.Extension.ToLowerInvariant()) {
            ".json" {
                $issues += Get-JsonBackedIssues -SourceFile $file.FullName -SourceKind "local-file-json"
            }
            ".md" {
                $issues += Get-MarkdownTaskIssue -SourceFile $file.FullName
            }
            ".txt" {
                $issues += Get-MarkdownTaskIssue -SourceFile $file.FullName
            }
        }
    }

    return @($issues)
}

function Invoke-LinearGraphQl {
    param(
        [string]$Endpoint,
        [string]$ApiToken,
        [string]$Query,
        [hashtable]$Variables
    )

    $headers = @{
        Authorization = $ApiToken
        "Content-Type" = "application/json"
    }
    $body = @{
        query = $Query
        variables = $Variables
    } | ConvertTo-Json -Depth 8

    $response = Invoke-RestMethod -Uri $Endpoint -Method Post -Headers $headers -Body $body -TimeoutSec 30
    if ($response.errors) {
        throw ("Linear GraphQL returned errors: {0}" -f (($response.errors | ConvertTo-Json -Depth 8 -Compress)))
    }

    return $response
}

function Get-LinearTrackerIssues {
    param($TrackerConfig)

    $apiKey = [Environment]::GetEnvironmentVariable($TrackerConfig.api_key_env)
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        throw "Linear API key env var is not set: $($TrackerConfig.api_key_env)"
    }

    if ([string]::IsNullOrWhiteSpace($TrackerConfig.project_slug)) {
        throw "tracker.project_slug is required for tracker.kind=linear."
    }

    $query = @'
query CodexSubagentQueuePoll($projectSlug: String!, $stateNames: [String!]!, $first: Int!) {
  issues(filter: {project: {slugId: {eq: $projectSlug}}, state: {name: {in: $stateNames}}}, first: $first) {
    nodes {
      id
      identifier
      title
      description
      priority
      state { name }
      branchName
      url
      labels { nodes { name } }
      inverseRelations(first: 50) {
        nodes {
          type
          issue {
            id
            identifier
            state { name }
          }
        }
      }
      createdAt
      updatedAt
    }
  }
}
'@

    $response = Invoke-LinearGraphQl `
        -Endpoint $TrackerConfig.endpoint `
        -ApiToken $apiKey `
        -Query $query `
        -Variables @{
            projectSlug = $TrackerConfig.project_slug
            stateNames = @($TrackerConfig.active_states)
            first = 50
        }

    $issues = @()
    foreach ($node in @($response.data.issues.nodes)) {
        $blockers = @()
        foreach ($relation in @($node.inverseRelations.nodes)) {
            if ([string]$relation.type -eq "blocks" -and $relation.issue) {
                $blockers += [ordered]@{
                    id = [string]$relation.issue.id
                    identifier = [string]$relation.issue.identifier
                    state = [string]$relation.issue.state.name
                }
            }
        }

        $issues += [pscustomobject]@{
            id = [string]$node.id
            identifier = [string]$node.identifier
            title = [string]$node.title
            description = [string]$node.description
            priority = $node.priority
            state = [string]$node.state.name
            branch_name = [string]$node.branchName
            url = [string]$node.url
            labels = @($node.labels.nodes | ForEach-Object { [string]$_.name.ToLowerInvariant() })
            blocked_by = @($blockers)
            created_at = [string]$node.createdAt
            updated_at = [string]$node.updatedAt
        }
    }

    return @($issues)
}

function Get-TrackerIssues {
    param($TrackerConfig)

    switch ($TrackerConfig.kind) {
        "mock-json" {
            if ([string]::IsNullOrWhiteSpace($TrackerConfig.source_file)) {
                throw "tracker.source_file is required for tracker.kind=mock-json."
            }

            if (-not (Test-Path -LiteralPath $TrackerConfig.source_file)) {
                throw "tracker.source_file does not exist for tracker.kind=mock-json: $($TrackerConfig.source_file)"
            }

            return Get-MockTrackerIssues -SourceFile $TrackerConfig.source_file
        }
        "local-json" {
            if ([string]::IsNullOrWhiteSpace($TrackerConfig.source_file)) {
                throw "tracker.source_file is required for tracker.kind=local-json."
            }

            return Get-LocalJsonTrackerIssues -SourceFile $TrackerConfig.source_file
        }
        "local-files" {
            if ([string]::IsNullOrWhiteSpace($TrackerConfig.source_dir)) {
                throw "tracker.source_dir is required for tracker.kind=local-files."
            }

            return Get-LocalFilesTrackerIssues `
                -SourceDirectory $TrackerConfig.source_dir `
                -IncludeGlobs $TrackerConfig.include_globs `
                -Recurse ([bool]$TrackerConfig.recurse)
        }
        "linear" {
            return Get-LinearTrackerIssues -TrackerConfig $TrackerConfig
        }
        default {
            throw "Unsupported tracker.kind '$($TrackerConfig.kind)'."
        }
    }
}

function Test-IssueBlocked {
    param(
        $Issue,
        [string[]]$ActiveStates,
        [System.Collections.IDictionary]$IssueMap,
        [System.Collections.IDictionary]$State
    )

    foreach ($blocker in @($Issue.blocked_by)) {
        $blockerIdentifier = $null
        if ($blocker -is [string]) {
            $blockerIdentifier = [string]$blocker
        } else {
            $blockerIdentifier = Get-FirstNonEmptyString @(
                (Get-OptionalProperty $blocker "identifier"),
                (Get-OptionalProperty $blocker "id"),
                (Get-OptionalProperty $blocker "key")
            )
        }

        $blockerIssue = if (-not [string]::IsNullOrWhiteSpace($blockerIdentifier)) {
            Get-OptionalProperty $IssueMap $blockerIdentifier
        } else {
            $null
        }

        if ($null -ne $blockerIssue) {
            $blockerStateRecord = Get-IssueStateRecord -State $State -IssueKey ([string]$blockerIssue.identifier)
            $blockerFingerprint = Get-IssueFingerprint -Issue $blockerIssue
            if ([string](Get-OptionalProperty $blockerStateRecord "last_success_fingerprint") -eq $blockerFingerprint) {
                continue
            }

            if ([string]$blockerIssue.state -in $ActiveStates) {
                return $true
            }

            continue
        }

        if (-not [string]::IsNullOrWhiteSpace($blockerIdentifier)) {
            $blockerStateRecord = Get-IssueStateRecord -State $State -IssueKey $blockerIdentifier
            if ([string](Get-OptionalProperty $blockerStateRecord "status") -eq "completed") {
                continue
            }
        }

        $blockerState = [string](Get-OptionalProperty $blocker "state")
        if (-not [string]::IsNullOrWhiteSpace($blockerState) -and $blockerState -in $ActiveStates) {
            return $true
        }
    }

    return $false
}

function Get-IssueSortKey {
    param($Issue)

    $priority = Get-OptionalProperty $Issue "priority"
    $prioritySort = if ($priority -is [int] -or $priority -as [int]) { [int]$priority } else { 999 }
    $updatedAt = [string](Get-OptionalProperty $Issue "updated_at")

    return [pscustomobject]@{
        priority = $prioritySort
        updated_at = if ([string]::IsNullOrWhiteSpace($updatedAt)) { "9999-12-31T23:59:59Z" } else { $updatedAt }
        identifier = [string]$Issue.identifier
    }
}

function Test-IssueAutoRunnable {
    param($Issue)

    $autoRun = Get-OptionalProperty $Issue "auto_run"
    if ($null -eq $autoRun) {
        return $true
    }

    return [bool]$autoRun
}

function Get-IssueFingerprint {
    param($Issue)

    $fingerprintSource = [ordered]@{
        identifier = [string](Get-OptionalProperty $Issue "identifier")
        title = [string](Get-OptionalProperty $Issue "title")
        description = [string](Get-OptionalProperty $Issue "description")
        priority = Get-OptionalProperty $Issue "priority"
        state = [string](Get-OptionalProperty $Issue "state")
        branch_name = [string](Get-OptionalProperty $Issue "branch_name")
        url = [string](Get-OptionalProperty $Issue "url")
        labels = [string[]](Get-UniqueStringList (Get-OptionalProperty $Issue "labels"))
        blocked_by = ConvertTo-NormalizedValue (Get-OptionalProperty $Issue "blocked_by")
        created_at = [string](Get-OptionalProperty $Issue "created_at")
        updated_at = [string](Get-OptionalProperty $Issue "updated_at")
        requested_deliverables = [string[]](Get-UniqueStringList (Get-OptionalProperty $Issue "requested_deliverables"))
        mode_hint = [string](Get-OptionalProperty $Issue "mode_hint")
        auto_run = Get-OptionalProperty $Issue "auto_run"
        source_path = [string](Get-OptionalProperty $Issue "source_path")
        source_kind = [string](Get-OptionalProperty $Issue "source_kind")
    }

    return ($fingerprintSource | ConvertTo-Json -Depth 12 -Compress)
}

function Load-StateFile {
    param([string]$StateFile)

    if (-not (Test-Path -LiteralPath $StateFile)) {
        return [ordered]@{
            updated_at_utc = $null
            issues = [ordered]@{}
        }
    }

    $decoded = (Get-Content -LiteralPath $StateFile -Raw) | ConvertFrom-Json -ErrorAction Stop
    $issues = ConvertTo-NormalizedMap (Get-OptionalProperty $decoded "issues")
    return [ordered]@{
        updated_at_utc = [string](Get-OptionalProperty $decoded "updated_at_utc")
        issues = $issues
    }
}

function Save-StateFile {
    param(
        [string]$StateFile,
        [System.Collections.IDictionary]$State
    )

    $directory = Split-Path -Parent $StateFile
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    $State.updated_at_utc = Get-TimestampUtc
    $State | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $StateFile -Encoding utf8
}

function Get-IssueStateRecord {
    param(
        [System.Collections.IDictionary]$State,
        [string]$IssueKey
    )

    if (-not $State.issues.Contains($IssueKey)) {
        $State.issues[$IssueKey] = [ordered]@{
            issue_key = $IssueKey
            status = "idle"
            dispatch_count = 0
            consecutive_failures = 0
            next_eligible_at_utc = $null
            workspace_path = $null
            last_state = $null
            last_manifest = $null
            last_summary = $null
            last_stdout = $null
            last_stderr = $null
            last_exit_code = $null
            last_started_at_utc = $null
            last_finished_at_utc = $null
            last_seen_at_utc = $null
            last_issue_fingerprint = $null
            last_success_fingerprint = $null
            last_success_at_utc = $null
            source_path = $null
            stop_reason = $null
        }
    }

    return $State.issues[$IssueKey]
}

function Get-EffectiveWorkflowAttempt {
    param($IssueState)

    $dispatchCount = [int](Get-OptionalProperty $IssueState "dispatch_count")
    if ($dispatchCount -lt 1) {
        return $null
    }

    return $dispatchCount
}

function New-IssueLauncherSpec {
    param(
        $QueueConfig,
        $Issue,
        $IssueState,
        [string]$WorkspacePath
    )

    $issueKey = Get-SafePathSegment -Value ([string]$Issue.identifier) -Default "issue"
    $timestamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
    $runRoot = Resolve-AbsolutePath -Path (Join-Path $QueueConfig.output.issue_runs_root $issueKey) -BaseDirectory $WorkspacePath -AllowMissing
    $runOutputDir = Resolve-AbsolutePath -Path (Join-Path $runRoot $timestamp) -BaseDirectory $WorkspacePath -AllowMissing
    $generatedSpecPath = Resolve-AbsolutePath -Path (Join-Path $QueueConfig.output.generated_specs_root ("{0}.json" -f $issueKey)) -BaseDirectory $WorkspacePath -AllowMissing
    $workflowContext = [ordered]@{
        issue = ConvertTo-NormalizedValue $Issue
        attempt = Get-EffectiveWorkflowAttempt -IssueState $IssueState
    }
    $requestedDeliverables = [string[]](Get-UniqueStringList @(
            $QueueConfig.launcher.requested_deliverables,
            (Get-OptionalProperty $Issue "requested_deliverables")
        ))

    $spec = [ordered]@{
        cwd = $WorkspacePath
        output_dir = $runOutputDir
        manifest_file = Join-Path $runOutputDir "orchestration-manifest.json"
        summary_file = Join-Path $runOutputDir "orchestration-summary.md"
        debug_log_file = Join-Path $runOutputDir "launcher-debug.log"
        archive_root = Resolve-AbsolutePath -Path (Join-Path $QueueConfig.output.root "archives") -BaseDirectory $WorkspacePath -AllowMissing
        write_run_archive = [bool]$QueueConfig.launcher.write_run_archive
        archive_run_label = $Issue.identifier
        skip_git_repo_check = $true
        execution_mode = $QueueConfig.launcher.execution_mode
        write_prompt_files = [bool]$QueueConfig.launcher.write_prompt_files
        write_summary_file = [bool]$QueueConfig.launcher.write_summary_file
        requested_deliverables = $requestedDeliverables
        supervisor_only = [bool]$QueueConfig.launcher.supervisor_only
        require_final_read_only_review = [bool]$QueueConfig.launcher.require_final_read_only_review
        material_issue_strategy = $QueueConfig.launcher.material_issue_strategy
        shared_directive_mode = $QueueConfig.launcher.shared_directive_mode
        workflow_prompt_mode = $QueueConfig.workflow_prompt_mode
        workflow_render_strict = [bool]$QueueConfig.workflow_render_strict
        workflow_auto_detect = [bool]$QueueConfig.workflow_auto_detect
        workflow_context = $workflowContext
        defaults = $QueueConfig.launcher.defaults
        hooks = $QueueConfig.hooks
        agents = $QueueConfig.launcher.agents_template
    }

    if ($QueueConfig.workflow_file) {
        $spec.workflow_file = $QueueConfig.workflow_file
    }

    $directory = Split-Path -Parent $generatedSpecPath
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    $spec | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $generatedSpecPath -Encoding utf8

    return [pscustomobject]@{
        spec_path = $generatedSpecPath
        output_dir = $runOutputDir
    }
}

function Start-IssueProcess {
    param(
        $QueueConfig,
        $Issue,
        [string]$SpecPath,
        [string]$CodexExecutablePath,
        [string]$IssueFingerprint
    )

    $issueKey = Get-SafePathSegment -Value ([string]$Issue.identifier) -Default "issue"
    $logRoot = Resolve-AbsolutePath -Path (Join-Path $QueueConfig.output.queue_logs_root $issueKey) -BaseDirectory $QueueConfig.output.root -AllowMissing
    New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
    $stdoutPath = Resolve-AbsolutePath -Path (Join-Path $logRoot "launcher.stdout.log") -BaseDirectory $logRoot -AllowMissing
    $stderrPath = Resolve-AbsolutePath -Path (Join-Path $logRoot "launcher.stderr.log") -BaseDirectory $logRoot -AllowMissing

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $QueueConfig.launcher_script,
        "-SpecPath",
        $SpecPath,
        "-CodexExecutable",
        $CodexExecutablePath,
        "-AsJson"
    )

    $process = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList (Join-ArgLine -Items $args) `
        -WorkingDirectory $QueueConfig.config_directory `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -PassThru `
        -NoNewWindow

    return [pscustomobject]@{
        issue_id = $Issue.id
        issue_identifier = $Issue.identifier
        issue_fingerprint = $IssueFingerprint
        stdout = $stdoutPath
        stderr = $stderrPath
        process = $process
        started_at_utc = Get-TimestampUtc
        spec_path = $SpecPath
    }
}

function Read-LauncherResult {
    param([string]$StdoutPath)

    if (-not (Test-Path -LiteralPath $StdoutPath)) {
        return $null
    }

    $raw = Get-Content -LiteralPath $StdoutPath -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $null
    }

    try {
        return $raw | ConvertFrom-Json -ErrorAction Stop
    } catch {
        return $null
    }
}

function Get-BackoffSeconds {
    param(
        $QueueConfig,
        [int]$ConsecutiveFailures
    )

    if ($ConsecutiveFailures -lt 1) {
        return 0
    }

    $value = [math]::Pow(2, ($ConsecutiveFailures - 1)) * $QueueConfig.retry.base_backoff_seconds
    return [int][math]::Min($value, $QueueConfig.retry.max_backoff_seconds)
}

function Set-NextEligibleAt {
    param(
        $IssueState,
        [int]$SecondsFromNow
    )

    if ($SecondsFromNow -le 0) {
        $IssueState.next_eligible_at_utc = $null
        return
    }

    $IssueState.next_eligible_at_utc = (Get-Date).ToUniversalTime().AddSeconds($SecondsFromNow).ToString("o")
}

function Test-IssueEligibleNow {
    param($IssueState)

    $nextEligibleAt = [string](Get-OptionalProperty $IssueState "next_eligible_at_utc")
    if ([string]::IsNullOrWhiteSpace($nextEligibleAt)) {
        return $true
    }

    $parsed = $null
    if (-not [DateTime]::TryParse($nextEligibleAt, [ref]$parsed)) {
        return $true
    }

    return ($parsed.ToUniversalTime() -le (Get-Date).ToUniversalTime())
}

function Update-CompletedRun {
    param(
        [System.Collections.IDictionary]$State,
        $RunningRecord
    )

    $IssueState = Get-IssueStateRecord -State $State -IssueKey ([string]$RunningRecord.issue_identifier)
    $exitCode = if ($RunningRecord.process.HasExited) { [int]$RunningRecord.process.ExitCode } else { -1 }
    $IssueState.status = if ($exitCode -eq 0) { "completed" } else { "failed" }
    $IssueState.last_exit_code = $exitCode
    $IssueState.last_finished_at_utc = Get-TimestampUtc
    $IssueState.last_stdout = $RunningRecord.stdout
    $IssueState.last_stderr = $RunningRecord.stderr

    $launcherResult = Read-LauncherResult -StdoutPath $RunningRecord.stdout
    if ($launcherResult) {
        $IssueState.last_manifest = [string](Get-OptionalProperty $launcherResult "manifest")
        $IssueState.last_summary = [string](Get-OptionalProperty $launcherResult "summary")
    }

    if ($exitCode -eq 0) {
        $IssueState.consecutive_failures = 0
        $IssueState.last_success_fingerprint = [string](Get-OptionalProperty $RunningRecord "issue_fingerprint")
        $IssueState.last_success_at_utc = $IssueState.last_finished_at_utc
        Set-NextEligibleAt -IssueState $IssueState -SecondsFromNow 0
    } else {
        $IssueState.consecutive_failures = [int](Get-OptionalProperty $IssueState "consecutive_failures") + 1
        $backoffSeconds = Get-BackoffSeconds -QueueConfig $script:QueueConfig -ConsecutiveFailures ([int]$IssueState.consecutive_failures)
        Set-NextEligibleAt -IssueState $IssueState -SecondsFromNow $backoffSeconds
    }
}

function Stop-RunningIssue {
    param(
        [System.Collections.IDictionary]$State,
        $RunningRecord,
        [string]$Reason
    )

    if (-not $RunningRecord.process.HasExited) {
        Stop-Process -Id $RunningRecord.process.Id -Force -ErrorAction SilentlyContinue
    }

    $IssueState = Get-IssueStateRecord -State $State -IssueKey ([string]$RunningRecord.issue_identifier)
    $IssueState.status = "stopped"
    $IssueState.stop_reason = $Reason
    $IssueState.last_finished_at_utc = Get-TimestampUtc
    $IssueState.last_stdout = $RunningRecord.stdout
    $IssueState.last_stderr = $RunningRecord.stderr
}

function Write-QueueReport {
    param(
        $QueueConfig,
        [System.Collections.IDictionary]$State,
        [int]$PollCount,
        [int]$DispatchCount,
        [int]$CompletedCount,
        [int]$RunningCount
    )

    $reportPath = $QueueConfig.output.report_file
    $directory = Split-Path -Parent $reportPath
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Queue Report")
    $lines.Add("")
    $lines.Add("- Updated: $(Get-TimestampUtc)")
    $lines.Add("- Tracker kind: $($QueueConfig.tracker.kind)")
    $lines.Add("- Poll count: $PollCount")
    $lines.Add("- Dispatch count: $DispatchCount")
    $lines.Add("- Completed count: $CompletedCount")
    $lines.Add("- Running count: $RunningCount")
    $lines.Add("")
    $lines.Add("## Issues")
    $lines.Add("")

    $issueKeys = @($State.issues.Keys | Sort-Object)
    if ($issueKeys.Count -eq 0) {
        $lines.Add("No issues have been observed yet.")
    } else {
        foreach ($issueKey in $issueKeys) {
            $issueState = $State.issues[$issueKey]
            $status = [string](Get-OptionalProperty $issueState "status")
            $lastState = [string](Get-OptionalProperty $issueState "last_state")
            $workspacePath = [string](Get-OptionalProperty $issueState "workspace_path")
            $lastSummary = [string](Get-OptionalProperty $issueState "last_summary")
            $nextEligibleAt = [string](Get-OptionalProperty $issueState "next_eligible_at_utc")
            $stopReason = [string](Get-OptionalProperty $issueState "stop_reason")
            $lines.Add(("- {0}: status={1}, tracker_state={2}, dispatches={3}, failures={4}" -f `
                        $issueKey, `
                        $status, `
                        $lastState, `
                        ([int](Get-OptionalProperty $issueState "dispatch_count")), `
                        ([int](Get-OptionalProperty $issueState "consecutive_failures"))))
            if (-not [string]::IsNullOrWhiteSpace($workspacePath)) {
                $lines.Add("  workspace: $workspacePath")
            }

            if (-not [string]::IsNullOrWhiteSpace($lastSummary)) {
                $lines.Add("  last_summary: $lastSummary")
            }

            if (-not [string]::IsNullOrWhiteSpace($nextEligibleAt)) {
                $lines.Add("  next_eligible_at_utc: $nextEligibleAt")
            }

            if (-not [string]::IsNullOrWhiteSpace($stopReason)) {
                $lines.Add("  stop_reason: $stopReason")
            }
        }
    }

    [string]::Join([Environment]::NewLine, $lines) | Set-Content -LiteralPath $reportPath -Encoding utf8
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Queue config file not found: $ConfigPath"
}

$configPathResolved = Resolve-AbsolutePath -Path $ConfigPath -BaseDirectory (Get-Location).Path
$configDirectory = Split-Path -Parent $configPathResolved
$rawConfig = (Get-Content -LiteralPath $configPathResolved -Raw) | ConvertFrom-Json -ErrorAction Stop
$script:QueueConfig = Get-QueueConfig -RawConfig $rawConfig -ConfigDirectory $configDirectory -LauncherScriptPath $LauncherPath
$resolvedCodexExecutable = Resolve-CommandPath -Executable $CodexExecutable

foreach ($directory in @(
        $script:QueueConfig.workspace.root,
        $script:QueueConfig.output.root,
        $script:QueueConfig.output.generated_specs_root,
        $script:QueueConfig.output.issue_runs_root,
        $script:QueueConfig.output.queue_logs_root
    )) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}

$state = Load-StateFile -StateFile $script:QueueConfig.output.state_file
$running = [ordered]@{}
$pollCount = 0
$dispatchCount = 0
$completedCount = 0

while ($true) {
    $pollCount += 1
    $issues = @(
        Get-TrackerIssues -TrackerConfig $script:QueueConfig.tracker |
            Where-Object {
                -not [string]::IsNullOrWhiteSpace([string]$_.identifier) -and
                -not [string]::IsNullOrWhiteSpace([string]$_.state)
            }
    )

    $issueMap = [ordered]@{}
    foreach ($issue in $issues) {
        $issueMap[[string]$issue.identifier] = $issue
        $issueState = Get-IssueStateRecord -State $state -IssueKey ([string]$issue.identifier)
        $issueState.last_state = [string]$issue.state
        $issueState.last_seen_at_utc = Get-TimestampUtc
        $issueState.last_issue_fingerprint = Get-IssueFingerprint -Issue $issue
        $issueState.source_path = [string](Get-OptionalProperty $issue "source_path")
    }

    foreach ($key in @($running.Keys)) {
        $run = $running[$key]
        if ($run.process.HasExited) {
            Update-CompletedRun -State $state -RunningRecord $run
            $run.process.Dispose()
            $running.Remove($key)
            $completedCount += 1
            continue
        }

        $currentIssue = Get-OptionalProperty $issueMap $key
        if ($null -eq $currentIssue) {
            Stop-RunningIssue -State $state -RunningRecord $run -Reason "issue_missing_from_tracker"
            $run.process.Dispose()
            $running.Remove($key)
            continue
        }

        if ([string]$currentIssue.state -in $script:QueueConfig.tracker.terminal_states) {
            Stop-RunningIssue -State $state -RunningRecord $run -Reason ("terminal_state:{0}" -f $currentIssue.state)
            $run.process.Dispose()
            $running.Remove($key)
            continue
        }

        if ([string]$currentIssue.state -notin $script:QueueConfig.tracker.active_states) {
            Stop-RunningIssue -State $state -RunningRecord $run -Reason ("inactive_state:{0}" -f $currentIssue.state)
            $run.process.Dispose()
            $running.Remove($key)
        }
    }

    $dispatchable = @(
        $issues |
            Where-Object {
                $_.state -in $script:QueueConfig.tracker.active_states -and
                (Test-IssueAutoRunnable -Issue $_) -and
                -not (Test-IssueBlocked -Issue $_ -ActiveStates $script:QueueConfig.tracker.active_states -IssueMap $issueMap -State $state)
            } |
            Sort-Object `
                @{ Expression = { (Get-IssueSortKey $_).priority } }, `
                @{ Expression = { (Get-IssueSortKey $_).updated_at } }, `
                @{ Expression = { (Get-IssueSortKey $_).identifier } }
    )

    foreach ($issue in $dispatchable) {
        if ($running.Count -ge $script:QueueConfig.launcher.max_concurrent_issues) {
            break
        }

        $issueKey = [string]$issue.identifier
        if ($running.Contains($issueKey)) {
            continue
        }

        $issueState = Get-IssueStateRecord -State $state -IssueKey $issueKey
        if (-not (Test-IssueEligibleNow -IssueState $issueState)) {
            continue
        }

        $issueFingerprint = Get-IssueFingerprint -Issue $issue
        if ([string](Get-OptionalProperty $issueState "status") -eq "completed" -and
            [string](Get-OptionalProperty $issueState "last_success_fingerprint") -eq $issueFingerprint) {
            continue
        }

        $workspacePath = Resolve-AbsolutePath -Path (Join-Path $script:QueueConfig.workspace.root (Get-SafePathSegment -Value $issueKey -Default "issue")) -BaseDirectory $script:QueueConfig.workspace.root -AllowMissing
        New-Item -ItemType Directory -Path $workspacePath -Force | Out-Null

        $issueState.workspace_path = $workspacePath
        $issueState.status = "running"
        $issueState.last_started_at_utc = Get-TimestampUtc
        $issueState.dispatch_count = [int](Get-OptionalProperty $issueState "dispatch_count") + 1
        $issueState.stop_reason = $null

        $specInfo = New-IssueLauncherSpec `
            -QueueConfig $script:QueueConfig `
            -Issue $issue `
            -IssueState $issueState `
            -WorkspacePath $workspacePath
        $run = Start-IssueProcess `
            -QueueConfig $script:QueueConfig `
            -Issue $issue `
            -SpecPath $specInfo.spec_path `
            -CodexExecutablePath $resolvedCodexExecutable `
            -IssueFingerprint $issueFingerprint

        $running[$issueKey] = $run
        $dispatchCount += 1
    }

    Save-StateFile -StateFile $script:QueueConfig.output.state_file -State $state
    Write-QueueReport `
        -QueueConfig $script:QueueConfig `
        -State $state `
        -PollCount $pollCount `
        -DispatchCount $dispatchCount `
        -CompletedCount $completedCount `
        -RunningCount $running.Count

    if ($script:QueueConfig.polling.max_polls -gt 0 -and $pollCount -ge $script:QueueConfig.polling.max_polls) {
        break
    }

    Start-Sleep -Seconds $script:QueueConfig.polling.interval_seconds
}

if ($script:QueueConfig.polling.drain_on_exit) {
    while ($running.Count -gt 0) {
        Start-Sleep -Milliseconds 500
        foreach ($key in @($running.Keys)) {
            $run = $running[$key]
            if ($run.process.HasExited) {
                Update-CompletedRun -State $state -RunningRecord $run
                $run.process.Dispose()
                $running.Remove($key)
                $completedCount += 1
            }
        }

        Save-StateFile -StateFile $script:QueueConfig.output.state_file -State $state
        Write-QueueReport `
            -QueueConfig $script:QueueConfig `
            -State $state `
            -PollCount $pollCount `
            -DispatchCount $dispatchCount `
            -CompletedCount $completedCount `
            -RunningCount $running.Count
    }
}

$finalOutput = [pscustomobject]@{
    config_path = $configPathResolved
    state_file = $script:QueueConfig.output.state_file
    report_file = $script:QueueConfig.output.report_file
    poll_count = $pollCount
    dispatch_count = $dispatchCount
    completed_count = $completedCount
    running_count = $running.Count
    workspace_root = $script:QueueConfig.workspace.root
    output_root = $script:QueueConfig.output.root
    tracker_kind = $script:QueueConfig.tracker.kind
    issues = $state.issues
}

if ($AsJson) {
    $finalOutput | ConvertTo-Json -Depth 12
} else {
    $state.issues.GetEnumerator() |
        ForEach-Object { [pscustomobject]$_ } |
        Select-Object Name, @{ Name = "status"; Expression = { $_.Value.status } }, @{ Name = "dispatch_count"; Expression = { $_.Value.dispatch_count } }, @{ Name = "last_state"; Expression = { $_.Value.last_state } }, @{ Name = "last_exit_code"; Expression = { $_.Value.last_exit_code } }, @{ Name = "workspace_path"; Expression = { $_.Value.workspace_path } } |
        Format-Table -AutoSize
    Write-Output ""
    Write-Output ("State file: {0}" -f $script:QueueConfig.output.state_file)
}
