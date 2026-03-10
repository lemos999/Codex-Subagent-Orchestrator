param(
    [Parameter(Mandatory = $true)]
    [string]$SpecPath,

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

    return [string[]]$items
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

    $normalized = Normalize-PathInput -Value $Path
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return $null
    }

    if ([System.IO.Path]::IsPathRooted($normalized)) {
        $candidate = [System.IO.Path]::GetFullPath($normalized)
    } else {
        $candidate = [System.IO.Path]::GetFullPath((Join-Path $BaseDirectory $normalized))
    }

    if (-not $AllowMissing -and -not (Test-Path -LiteralPath $candidate)) {
        throw "Path does not exist: $candidate"
    }

    return $candidate
}

function Get-NormalizedChoice {
    param(
        $Primary,
        $Fallback,
        [string]$Default,
        [string[]]$AllowedValues,
        [string]$FieldName
    )

    $candidate = if ($null -ne $Primary) {
        [string]$Primary
    } elseif ($null -ne $Fallback) {
        [string]$Fallback
    } else {
        $Default
    }

    $normalized = $candidate.Trim().ToLowerInvariant()
    if ($normalized -notin $AllowedValues) {
        throw "Invalid value '$candidate' for $FieldName. Allowed values: $($AllowedValues -join ', ')."
    }

    return $normalized
}

function Add-SectionLines {
    param(
        [System.Collections.Generic.List[string]]$Lines,
        [string]$Title,
        [string[]]$Items
    )

    if (-not $Items -or $Items.Count -eq 0) {
        return
    }

    $Lines.Add("")
    $Lines.Add($Title)
    foreach ($item in $Items) {
        if (-not [string]::IsNullOrWhiteSpace($item)) {
            $Lines.Add("- $item")
        }
    }
}

function Get-CompactDirectiveText {
    param(
        [string]$SourceText,
        [string]$Source
    )

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("Follow workspace rules, keep scope narrow, prefer explicit validation, and leave compact checkpoint updates.")

    if (-not [string]::IsNullOrWhiteSpace($SourceText)) {
        $leaf = if ([string]::IsNullOrWhiteSpace($Source)) { "" } else { Split-Path -Leaf $Source }
        if ($leaf -eq "AGENTS.md") {
            $lines.Add("Inspect AGENTS.md only if local rules or workflow boundaries are unclear.")
        } elseif (-not [string]::IsNullOrWhiteSpace($leaf)) {
            $lines.Add("Inspect $leaf only if local rules or workflow boundaries are unclear.")
        }
    }

    return ($lines -join [Environment]::NewLine)
}

function Get-DirectiveReferenceText {
    param([string]$Source)

    if ([string]::IsNullOrWhiteSpace($Source)) {
        return "Read and follow AGENTS.md in the working directory. Do not restate it."
    }

    $leaf = Split-Path -Leaf $Source
    if ($leaf -eq "AGENTS.md") {
        return "Read and follow AGENTS.md in the working directory. Do not restate it."
    }

    return "Read and follow the shared directive file before editing: $Source"
}

function Get-SharedDirectiveInfo {
    param(
        $Spec,
        [string]$WorkspaceRoot,
        [string]$SpecDirectory
    )

    $requestedMode = Get-NormalizedChoice `
        -Primary (Get-OptionalProperty $Spec "shared_directive_mode") `
        -Fallback $null `
        -Default "reference" `
        -AllowedValues @("full", "compact", "reference", "disabled") `
        -FieldName "shared_directive_mode"

    $injectDirective = Get-OptionalProperty $Spec "inject_shared_directive"
    if (($null -ne $injectDirective -and -not [bool]$injectDirective) -or $requestedMode -eq "disabled") {
        return [pscustomobject]@{
            text = $null
            source = "disabled"
            requested_mode = $requestedMode
            effective_mode = "disabled"
            original_char_count = 0
            effective_char_count = 0
        }
    }

    $rawText = $null
    $source = $null

    $inlineDirective = Get-OptionalProperty $Spec "shared_directive_text"
    if ($inlineDirective) {
        $rawText = ([string]$inlineDirective).Trim()
        $source = "spec.shared_directive_text"
    }

    if ($null -eq $rawText) {
        $directiveFileValue = Get-OptionalProperty $Spec "shared_directive_file"
        if ($directiveFileValue) {
            $directivePath = Resolve-AbsolutePath -Path ([string]$directiveFileValue) -BaseDirectory $SpecDirectory
            $rawText = (Get-Content -LiteralPath $directivePath -Raw).Trim()
            $source = $directivePath
        }
    }

    if ($null -eq $rawText) {
        $workspaceAgentsPath = Join-Path $WorkspaceRoot "AGENTS.md"
        if (Test-Path -LiteralPath $workspaceAgentsPath) {
            $rawText = (Get-Content -LiteralPath $workspaceAgentsPath -Raw).Trim()
            $source = $workspaceAgentsPath
        }
    }

    if ($null -eq $rawText) {
        $rawText = "Follow the workspace rules and keep the workflow compact."
        $source = "parent-session fallback directive"
    }

    $effectiveMode = $requestedMode
    $effectiveText = switch ($requestedMode) {
        "full" { $rawText; break }
        "compact" { Get-CompactDirectiveText -SourceText $rawText -Source $source; break }
        "reference" {
            if ($source -eq "spec.shared_directive_text") {
                $effectiveMode = "compact"
                Get-CompactDirectiveText -SourceText $rawText -Source $source
            } else {
                Get-DirectiveReferenceText -Source $source
            }
            break
        }
    }

    return [pscustomobject]@{
        text = $effectiveText
        source = $source
        requested_mode = $requestedMode
        effective_mode = $effectiveMode
        original_char_count = if ($rawText) { $rawText.Length } else { 0 }
        effective_char_count = if ($effectiveText) { $effectiveText.Length } else { 0 }
    }
}

function New-TaskBriefText {
    param(
        [string]$Task,
        [string[]]$Context,
        [string[]]$Constraints,
        [string[]]$AcceptanceCriteria,
        [string[]]$RequestedDeliverables
    )

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Task Brief")
    $lines.Add("")
    $lines.Add("## Task")
    $lines.Add("")
    $lines.Add($Task)
    Add-SectionLines -Lines $lines -Title "## Context" -Items $Context
    Add-SectionLines -Lines $lines -Title "## Constraints" -Items $Constraints
    Add-SectionLines -Lines $lines -Title "## Acceptance Criteria" -Items $AcceptanceCriteria
    Add-SectionLines -Lines $lines -Title "## Requested Deliverables" -Items $RequestedDeliverables
    return ($lines -join [Environment]::NewLine)
}

function New-ActiveContextText {
    param(
        [string]$Task,
        $SharedDirectiveInfo,
        [string[]]$RequestedDeliverables,
        [string]$FirstPhaseName
    )

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Active Context")
    $lines.Add("")
    $lines.Add("## Shared Contract")
    $lines.Add("")
    if ([string]::IsNullOrWhiteSpace($SharedDirectiveInfo.text)) {
        $lines.Add("Shared directive injection is disabled for this run.")
    } else {
        $lines.Add($SharedDirectiveInfo.text)
    }
    $lines.Add("")
    $lines.Add("## Task")
    $lines.Add("")
    $lines.Add($Task)
    Add-SectionLines -Lines $lines -Title "## Deliverables" -Items $RequestedDeliverables
    $lines.Add("")
    $lines.Add("## Session Rules")
    $lines.Add("")
    $lines.Add("- Execute the workflow inside the current parent session only.")
    $lines.Add("- Use the current phase file and session-summary.md as the only durable handoff surfaces.")
    $lines.Add("- Avoid replaying full chat history, full AGENTS text, and full logs.")
    $lines.Add("- Read only the files listed for the current phase before broadening scope.")
    $lines.Add("- Keep parent-facing summaries compact and delta-oriented.")
    $lines.Add("")
    $lines.Add("## Current Phase")
    $lines.Add("")
    $lines.Add($FirstPhaseName)
    return ($lines -join [Environment]::NewLine)
}

function New-CheckpointTemplateText {
    param([string]$FirstPhaseName)

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Session Summary")
    $lines.Add("")
    $lines.Add("## Current Status")
    $lines.Add("")
    $lines.Add("- Current phase: $FirstPhaseName")
    $lines.Add("- Status: not started")
    $lines.Add("")
    $lines.Add("## Touched Files")
    $lines.Add("")
    $lines.Add("- None yet.")
    $lines.Add("")
    $lines.Add("## Commands Run")
    $lines.Add("")
    $lines.Add("- None yet.")
    $lines.Add("")
    $lines.Add("## Risks Or Failures")
    $lines.Add("")
    $lines.Add("- None yet.")
    $lines.Add("")
    $lines.Add("## Next Step")
    $lines.Add("")
    $lines.Add("- Start phase: $FirstPhaseName")
    return ($lines -join [Environment]::NewLine)
}

function New-PhaseChecklistText {
    param($ResolvedPhases)

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Phase Checklist")
    $lines.Add("")

    foreach ($phase in $ResolvedPhases) {
        $lines.Add("- [ ] $($phase.display_name) [$($phase.mode)]")
    }

    return ($lines -join [Environment]::NewLine)
}

function New-PhasePromptText {
    param(
        $Phase,
        [int]$Index,
        [int]$TotalCount,
        $SharedDirectiveInfo
    )

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Phase $Index of ${TotalCount}: $($Phase.display_name)")
    $lines.Add("")
    $lines.Add("- role: $($Phase.role)")
    $lines.Add("- mode: $($Phase.mode)")
    $lines.Add("- reasoning_effort: $($Phase.reasoning_effort)")
    $lines.Add("- response_style: $($Phase.response_style)")
    $lines.Add("- max_response_lines: $($Phase.max_response_lines)")

    if (-not [string]::IsNullOrWhiteSpace($SharedDirectiveInfo.text)) {
        $lines.Add("")
        $lines.Add("## Shared Contract")
        $lines.Add("")
        $lines.Add($SharedDirectiveInfo.text)
    }

    $taskText = if (-not [string]::IsNullOrWhiteSpace($Phase.task)) {
        $Phase.task
    } else {
        $Phase.goal
    }

    $lines.Add("")
    $lines.Add("## Goal")
    $lines.Add("")
    $lines.Add($taskText)

    if (-not [string]::IsNullOrWhiteSpace($Phase.mission)) {
        $lines.Add("")
        $lines.Add("## Mission")
        $lines.Add("")
        $lines.Add($Phase.mission)
    }

    Add-SectionLines -Lines $lines -Title "## Read First" -Items $Phase.read_first
    Add-SectionLines -Lines $lines -Title "## Focus Paths" -Items $Phase.focus_paths
    Add-SectionLines -Lines $lines -Title "## Writable Scope" -Items $Phase.writable_scope
    Add-SectionLines -Lines $lines -Title "## Outputs" -Items $Phase.outputs
    Add-SectionLines -Lines $lines -Title "## Success Criteria" -Items $Phase.success_criteria
    Add-SectionLines -Lines $lines -Title "## Validation" -Items $Phase.validation
    Add-SectionLines -Lines $lines -Title "## Stop When" -Items $Phase.stop_when

    $lines.Add("")
    $lines.Add("## Token Discipline")
    $lines.Add("")
    $lines.Add("- Use only the files needed for this phase.")
    $lines.Add("- Update session-summary.md with deltas instead of retelling history.")
    $lines.Add("- Do not paste full logs, full diffs, or unchanged file contents.")
    $lines.Add("- If you need more context, add it to session-summary.md first and then continue.")

    return ($lines -join [Environment]::NewLine)
}

$specPathResolved = Resolve-AbsolutePath -Path $SpecPath -BaseDirectory (Get-Location).Path
$specDirectory = Split-Path -Parent $specPathResolved
$specText = Get-Content -LiteralPath $specPathResolved -Raw
$spec = $specText | ConvertFrom-Json

if (-not $spec) {
    throw "Failed to parse spec JSON."
}

if ([string]::IsNullOrWhiteSpace([string](Get-OptionalProperty $spec "task"))) {
    throw "Spec must define a non-empty 'task'."
}

$phases = @($spec.phases)
if (-not $phases -or $phases.Count -lt 1) {
    throw "Spec must define at least one phase."
}

$invocationCwd = (Get-Location).Path
$cwdResolutionMode = Get-NormalizedChoice `
    -Primary (Get-OptionalProperty $spec "cwd_resolution") `
    -Fallback $null `
    -Default "invocation" `
    -AllowedValues @("invocation", "spec") `
    -FieldName "cwd_resolution"

$cwdBaseDirectory = if ($cwdResolutionMode -eq "spec") { $specDirectory } else { $invocationCwd }
$workspaceRoot = Resolve-AbsolutePath -Path ([string]$spec.cwd) -BaseDirectory $cwdBaseDirectory
$outputDirValue = Get-OptionalProperty $spec "output_dir"
$outputDir = if ($outputDirValue) {
    Resolve-AbsolutePath -Path ([string]$outputDirValue) -BaseDirectory $workspaceRoot -AllowMissing
} else {
    Resolve-AbsolutePath -Path "parent-session-runs" -BaseDirectory $workspaceRoot -AllowMissing
}

$taskBriefFile = if (Get-OptionalProperty $spec "task_brief_file") {
    Resolve-AbsolutePath -Path ([string](Get-OptionalProperty $spec "task_brief_file")) -BaseDirectory $workspaceRoot -AllowMissing
} else {
    Resolve-AbsolutePath -Path (Join-Path $outputDir "task-brief.md") -BaseDirectory $workspaceRoot -AllowMissing
}

$activeContextFile = if (Get-OptionalProperty $spec "active_context_file") {
    Resolve-AbsolutePath -Path ([string](Get-OptionalProperty $spec "active_context_file")) -BaseDirectory $workspaceRoot -AllowMissing
} else {
    Resolve-AbsolutePath -Path (Join-Path $outputDir "active-context.md") -BaseDirectory $workspaceRoot -AllowMissing
}

$checkpointFile = if (Get-OptionalProperty $spec "checkpoint_file") {
    Resolve-AbsolutePath -Path ([string](Get-OptionalProperty $spec "checkpoint_file")) -BaseDirectory $workspaceRoot -AllowMissing
} else {
    Resolve-AbsolutePath -Path (Join-Path $outputDir "session-summary.md") -BaseDirectory $workspaceRoot -AllowMissing
}

$phaseChecklistFile = if (Get-OptionalProperty $spec "phase_checklist_file") {
    Resolve-AbsolutePath -Path ([string](Get-OptionalProperty $spec "phase_checklist_file")) -BaseDirectory $workspaceRoot -AllowMissing
} else {
    Resolve-AbsolutePath -Path (Join-Path $outputDir "phase-checklist.md") -BaseDirectory $workspaceRoot -AllowMissing
}

$manifestFile = if (Get-OptionalProperty $spec "manifest_file") {
    Resolve-AbsolutePath -Path ([string](Get-OptionalProperty $spec "manifest_file")) -BaseDirectory $workspaceRoot -AllowMissing
} else {
    Resolve-AbsolutePath -Path (Join-Path $outputDir "parent-session-manifest.json") -BaseDirectory $workspaceRoot -AllowMissing
}

$phaseDirectory = if (Get-OptionalProperty $spec "phase_directory") {
    Resolve-AbsolutePath -Path ([string](Get-OptionalProperty $spec "phase_directory")) -BaseDirectory $workspaceRoot -AllowMissing
} else {
    Resolve-AbsolutePath -Path (Join-Path $outputDir "phases") -BaseDirectory $workspaceRoot -AllowMissing
}

New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
New-Item -ItemType Directory -Path $phaseDirectory -Force | Out-Null

$sharedDirectiveInfo = Get-SharedDirectiveInfo -Spec $spec -WorkspaceRoot $workspaceRoot -SpecDirectory $specDirectory
$defaults = Get-OptionalProperty $spec "defaults"
$resolvedPhases = @()

for ($index = 0; $index -lt $phases.Count; $index++) {
    $phase = $phases[$index]
    $name = [string](Get-OptionalProperty $phase "name")
    if ([string]::IsNullOrWhiteSpace($name)) {
        throw "Each phase must define a non-empty 'name'."
    }

    $goal = [string](Get-OptionalProperty $phase "goal")
    $task = [string](Get-OptionalProperty $phase "task")
    if ([string]::IsNullOrWhiteSpace($goal) -and [string]::IsNullOrWhiteSpace($task)) {
        throw "Phase '$name' must define either 'goal' or 'task'."
    }

    $mode = Get-NormalizedChoice `
        -Primary (Get-OptionalProperty $phase "mode") `
        -Fallback (Get-OptionalProperty $defaults "mode") `
        -Default $(if ($name.ToLowerInvariant() -in @("implement", "fix")) { "write" } else { "read-only" }) `
        -AllowedValues @("read-only", "write") `
        -FieldName "phase.mode"

    $reasoning = if (Get-OptionalProperty $phase "reasoning_effort") {
        [string](Get-OptionalProperty $phase "reasoning_effort")
    } elseif (Get-OptionalProperty $defaults "reasoning_effort") {
        [string](Get-OptionalProperty $defaults "reasoning_effort")
    } else {
        "low"
    }

    $responseStyle = if (Get-OptionalProperty $phase "response_style") {
        [string](Get-OptionalProperty $phase "response_style")
    } elseif (Get-OptionalProperty $defaults "response_style") {
        [string](Get-OptionalProperty $defaults "response_style")
    } else {
        "compact"
    }

    $maxResponseLinesValue = if ($null -ne (Get-OptionalProperty $phase "max_response_lines")) {
        Get-OptionalProperty $phase "max_response_lines"
    } else {
        Get-OptionalProperty $defaults "max_response_lines"
    }
    $maxResponseLines = if ($null -ne $maxResponseLinesValue) { [int]$maxResponseLinesValue } else { 6 }

    $displayName = "{0:D2}-{1}" -f ($index + 1), $name
    $phaseFilePath = Join-Path $phaseDirectory "$displayName.md"

    $resolvedPhase = [pscustomobject]@{
        name = $name
        display_name = $displayName
        role = if (Get-OptionalProperty $phase "role") { [string](Get-OptionalProperty $phase "role") } else { "operator" }
        mission = [string](Get-OptionalProperty $phase "mission")
        mode = $mode
        goal = $goal
        task = $task
        read_first = Get-StringList (Get-OptionalProperty $phase "read_first")
        focus_paths = Get-StringList (Get-OptionalProperty $phase "focus_paths")
        writable_scope = Get-StringList (Get-OptionalProperty $phase "writable_scope")
        outputs = Get-StringList (Get-OptionalProperty $phase "outputs")
        validation = Get-StringList (Get-OptionalProperty $phase "validation")
        success_criteria = Get-StringList (Get-OptionalProperty $phase "success_criteria")
        stop_when = Get-StringList (Get-OptionalProperty $phase "stop_when")
        reasoning_effort = $reasoning
        response_style = $responseStyle
        max_response_lines = $maxResponseLines
        phase_file = $phaseFilePath
    }

    $phaseText = New-PhasePromptText -Phase $resolvedPhase -Index ($index + 1) -TotalCount $phases.Count -SharedDirectiveInfo $sharedDirectiveInfo
    Set-Content -LiteralPath $phaseFilePath -Value $phaseText -Encoding utf8
    $resolvedPhases += $resolvedPhase
}

$task = [string](Get-OptionalProperty $spec "task")
$context = Get-StringList (Get-OptionalProperty $spec "context")
$constraints = Get-StringList (Get-OptionalProperty $spec "constraints")
$acceptanceCriteria = Get-StringList (Get-OptionalProperty $spec "acceptance_criteria")
$requestedDeliverables = Get-StringList (Get-OptionalProperty $spec "requested_deliverables")

Set-Content -LiteralPath $taskBriefFile -Value (New-TaskBriefText -Task $task -Context $context -Constraints $constraints -AcceptanceCriteria $acceptanceCriteria -RequestedDeliverables $requestedDeliverables) -Encoding utf8
Set-Content -LiteralPath $activeContextFile -Value (New-ActiveContextText -Task $task -SharedDirectiveInfo $sharedDirectiveInfo -RequestedDeliverables $requestedDeliverables -FirstPhaseName $resolvedPhases[0].display_name) -Encoding utf8
Set-Content -LiteralPath $checkpointFile -Value (New-CheckpointTemplateText -FirstPhaseName $resolvedPhases[0].display_name) -Encoding utf8
Set-Content -LiteralPath $phaseChecklistFile -Value (New-PhaseChecklistText -ResolvedPhases $resolvedPhases) -Encoding utf8

$manifest = [pscustomobject]@{
    spec_path = $specPathResolved
    workspace_root = $workspaceRoot
    invocation_cwd = $invocationCwd
    cwd_requested = [string]$spec.cwd
    cwd_resolution_mode = $cwdResolutionMode
    output_dir = $outputDir
    task_brief_file = $taskBriefFile
    active_context_file = $activeContextFile
    checkpoint_file = $checkpointFile
    phase_checklist_file = $phaseChecklistFile
    phase_directory = $phaseDirectory
    shared_directive_mode = $sharedDirectiveInfo.effective_mode
    shared_directive_source = $sharedDirectiveInfo.source
    shared_directive_chars = [pscustomobject]@{
        original = $sharedDirectiveInfo.original_char_count
        effective = $sharedDirectiveInfo.effective_char_count
    }
    requested_deliverables = $requestedDeliverables
    task = $task
    phase_count = $resolvedPhases.Count
    read_only_phase_count = @($resolvedPhases | Where-Object { $_.mode -eq "read-only" }).Count
    writable_phase_count = @($resolvedPhases | Where-Object { $_.mode -eq "write" }).Count
    phases = @($resolvedPhases | ForEach-Object {
        [pscustomobject]@{
            name = $_.name
            display_name = $_.display_name
            role = $_.role
            mode = $_.mode
            reasoning_effort = $_.reasoning_effort
            response_style = $_.response_style
            max_response_lines = $_.max_response_lines
            phase_file = $_.phase_file
        }
    })
    generated_files = @(
        $taskBriefFile,
        $activeContextFile,
        $checkpointFile,
        $phaseChecklistFile,
        $manifestFile
    ) + @($resolvedPhases | ForEach-Object { $_.phase_file })
}

$manifestJson = $manifest | ConvertTo-Json -Depth 8
Set-Content -LiteralPath $manifestFile -Value $manifestJson -Encoding utf8

$result = [pscustomobject]@{
    workspace_root = $workspaceRoot
    output_dir = $outputDir
    task_brief_file = $taskBriefFile
    active_context_file = $activeContextFile
    checkpoint_file = $checkpointFile
    phase_checklist_file = $phaseChecklistFile
    manifest_file = $manifestFile
    phase_files = @($resolvedPhases | ForEach-Object { $_.phase_file })
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 8
} else {
    Write-Output "Prepared parent-session run scaffold."
    Write-Output "Workspace root: $workspaceRoot"
    Write-Output "Output dir: $outputDir"
    Write-Output "Manifest: $manifestFile"
}
