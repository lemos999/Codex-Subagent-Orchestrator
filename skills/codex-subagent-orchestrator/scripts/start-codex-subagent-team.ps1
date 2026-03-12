param(
    [Parameter(Mandatory = $true)]
    [string]$SpecPath,

    [string]$CodexExecutable = "codex",

    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "codex-memory.ps1")

$FallbackPrincipalEngineerDirective = @'
You are a principal software engineer, reviewer, and production architect whose goal is to turn every request into code that improves code health, not merely code that runs once. For each task, infer the real objective, runtime environment, interfaces, invariants, data model, trust boundaries, failure modes, concurrency risks, performance limits, rollback needs, then choose the smallest design that fully solves problem without decorative abstraction. Favor clear names, explicit control flow, narrow public surfaces, cohesive modules, visible state, boundary validation, safe defaults, precise errors, and behavior that stays predictable under retries, timeouts, malformed input, partial failure, and load. Follow local conventions first, use idiomatic tooling, prefer the standard library and proven dependencies, preserve behavior during refactoring, and separate structural cleanup from behavior change when practical. Build security, observability, and operability into the code through least privilege, secret-safe handling, logs, metrics, traces, health signals, and graceful failure. Write tests around observable behavior, edge cases, regressions, and critical contracts. When details are missing, state the smallest safe assumption and continue. Before finalizing, run a silent senior review for correctness, simplicity, maintainability, security, performance, and rollback safety, then present brief assumptions and design intent, complete code, tests, and concise verification notes.
'@

$CompactPrincipalEngineerDirective = @'
You are a principal engineer, reviewer, and production architect optimizing for long-term code health. Infer the real objective and operating envelope: runtime, interfaces, invariants, model, trust boundaries, failure, concurrency, performance, and rollback. Solve with the smallest complete design, not decorative abstraction. Prefer clear naming, explicit flow, narrow surfaces, cohesive modules, visible state, validated boundaries, safe defaults, precise errors, and predictable behavior under retries, timeouts, malformed input, partial failure, and load. Follow local conventions, idiomatic tooling, standard library first, proven dependencies next; preserve behavior in refactors and separate cleanup from behavior change. Build in least privilege, secret-safe handling, logs, metrics, traces, health signals, and graceful failure. Test observable behavior, edge cases, regressions, and critical contracts. Stay within assigned scope, do not modify unrelated files, state the smallest safe assumption when needed, and finish with concise verification.
'@

$script:LauncherDebugPath = $null

function Write-LauncherDebug {
    param([string]$Message)

    if ([string]::IsNullOrWhiteSpace($script:LauncherDebugPath)) {
        return
    }

    $timestamp = (Get-Date).ToString("o")
    Add-Content -LiteralPath $script:LauncherDebugPath -Value ("[{0}] {1}" -f $timestamp, $Message) -Encoding utf8
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

function Get-NormalizedChoice {
    param(
        $Primary,
        $Fallback,
        [string]$Default,
        [string[]]$AllowedValues,
        [string]$FieldName
    )

    $selected = if ($null -ne $Primary) {
        [string]$Primary
    } elseif ($null -ne $Fallback) {
        [string]$Fallback
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
        throw "Codex executable value cannot be empty."
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

function Quote-Arg {
    param([string]$Value)

    if ($null -eq $Value) {
        return '""'
    }

    if ($Value -eq "") {
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

function Get-OptionalProperty {
    param(
        $Object,
        [string]$Name
    )

    if ($null -eq $Object) {
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

function ConvertTo-TemplateContextValue {
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
            $map[[string]$key] = ConvertTo-TemplateContextValue $Value[$key]
        }

        return $map
    }

    if ($Value -is [pscustomobject]) {
        $map = [ordered]@{}
        foreach ($property in $Value.PSObject.Properties) {
            $map[[string]$property.Name] = ConvertTo-TemplateContextValue $property.Value
        }

        return $map
    }

    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        $items = New-Object System.Collections.Generic.List[object]
        foreach ($entry in $Value) {
            $items.Add((ConvertTo-TemplateContextValue $entry))
        }

        return @($items.ToArray())
    }

    return $Value
}

function ConvertTo-TemplateContextMap {
    param($Value)

    if ($null -eq $Value) {
        return [ordered]@{}
    }

    $converted = ConvertTo-TemplateContextValue $Value
    if ($converted -isnot [System.Collections.IDictionary]) {
        throw "workflow_context must resolve to an object."
    }

    return $converted
}

function Merge-TemplateContextMaps {
    param(
        [System.Collections.IDictionary]$Base,
        [System.Collections.IDictionary]$Overlay
    )

    if ($null -eq $Base -or $Base.Count -eq 0) {
        return ConvertTo-TemplateContextMap $Overlay
    }

    if ($null -eq $Overlay -or $Overlay.Count -eq 0) {
        return ConvertTo-TemplateContextMap $Base
    }

    $merged = [ordered]@{}
    foreach ($key in $Base.Keys) {
        $merged[[string]$key] = ConvertTo-TemplateContextValue $Base[$key]
    }

    foreach ($key in $Overlay.Keys) {
        $stringKey = [string]$key
        $overlayValue = ConvertTo-TemplateContextValue $Overlay[$key]
        if ($merged.Contains($stringKey) -and
            $merged[$stringKey] -is [System.Collections.IDictionary] -and
            $overlayValue -is [System.Collections.IDictionary]) {
            $merged[$stringKey] = Merge-TemplateContextMaps -Base $merged[$stringKey] -Overlay $overlayValue
            continue
        }

        $merged[$stringKey] = $overlayValue
    }

    return $merged
}

function Split-WorkflowDocument {
    param([string]$Content)

    $lines = @([regex]::Split([string]$Content, "\r?\n"))
    if (@($lines).Count -eq 0) {
        return [pscustomobject]@{
            front_matter_text = $null
            prompt_template = ""
        }
    }

    if ($lines[0].Trim() -ne "---") {
        return [pscustomobject]@{
            front_matter_text = $null
            prompt_template = ([string]$Content).Trim()
        }
    }

    $frontMatterLines = New-Object System.Collections.Generic.List[string]
    $promptLines = New-Object System.Collections.Generic.List[string]
    $inFrontMatter = $true

    for ($index = 1; $index -lt $lines.Count; $index += 1) {
        $line = $lines[$index]
        if ($inFrontMatter -and $line.Trim() -eq "---") {
            $inFrontMatter = $false
            continue
        }

        if ($inFrontMatter) {
            $frontMatterLines.Add($line)
        } else {
            $promptLines.Add($line)
        }
    }

    $frontMatterText = if (@($frontMatterLines).Count -gt 0) {
        ($frontMatterLines -join [Environment]::NewLine).Trim()
    } else {
        $null
    }
    $promptTemplate = ($promptLines -join [Environment]::NewLine).Trim()

    return [pscustomobject]@{
        front_matter_text = $frontMatterText
        prompt_template = $promptTemplate
    }
}

function Get-TemplateContextValue {
    param(
        $Context,
        [string]$Path,
        [switch]$AllowMissing
    )

    $current = $Context
    foreach ($segment in @($Path -split '\.')) {
        if ([string]::IsNullOrWhiteSpace($segment)) {
            continue
        }

        if ($current -is [System.Collections.IDictionary]) {
            if (-not $current.Contains($segment)) {
                if ($AllowMissing) {
                    return $null
                }

                throw "workflow template variable not found: $Path"
            }

            $current = $current[$segment]
            continue
        }

        if ($current -is [pscustomobject]) {
            $property = $current.PSObject.Properties[$segment]
            if ($null -eq $property) {
                if ($AllowMissing) {
                    return $null
                }

                throw "workflow template variable not found: $Path"
            }

            $current = $property.Value
            continue
        }

        if ($AllowMissing) {
            return $null
        }

        throw "workflow template variable not found: $Path"
    }

    return $current
}

function Test-TemplateTruthy {
    param($Value)

    if ($null -eq $Value) {
        return $false
    }

    if ($Value -is [bool]) {
        return [bool]$Value
    }

    if ($Value -is [string]) {
        return (-not [string]::IsNullOrWhiteSpace($Value))
    }

    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        foreach ($item in $Value) {
            return $true
        }

        return $false
    }

    return $true
}

function Convert-TemplateValueToString {
    param($Value)

    if ($null -eq $Value) {
        return ""
    }

    if ($Value -is [string]) {
        return $Value
    }

    if ($Value -is [bool]) {
        return $(if ($Value) { "true" } else { "false" })
    }

    if ($Value -is [System.Collections.IDictionary] -or ($Value -is [pscustomobject])) {
        return ((ConvertTo-TemplateContextValue $Value) | ConvertTo-Json -Depth 8 -Compress)
    }

    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        $values = @()
        foreach ($entry in $Value) {
            $values += Convert-TemplateValueToString $entry
        }

        return ($values -join ", ")
    }

    return [string]$Value
}

function Render-WorkflowTemplate {
    param(
        [string]$Template,
        $Context,
        [bool]$StrictVariables = $true
    )

    $pattern = [regex]'(?s)(\{\{\s*([^}]+?)\s*\}\}|\{%\s*(if\s+(.+?)|else|endif)\s*%\})'
    $frames = New-Object System.Collections.Stack
    $builder = New-Object System.Text.StringBuilder
    $lastIndex = 0
    $currentEnabled = $true

    foreach ($match in $pattern.Matches($Template)) {
        if ($currentEnabled -and $match.Index -gt $lastIndex) {
            [void]$builder.Append($Template.Substring($lastIndex, $match.Index - $lastIndex))
        }

        $lastIndex = $match.Index + $match.Length
        $fullToken = $match.Groups[1].Value
        $variablePath = $match.Groups[2].Value
        $ifExpression = $match.Groups[4].Value

        if (-not [string]::IsNullOrWhiteSpace($variablePath)) {
            if (-not $currentEnabled) {
                continue
            }

            $resolvedValue = if ($StrictVariables) {
                Get-TemplateContextValue -Context $Context -Path $variablePath.Trim()
            } else {
                Get-TemplateContextValue -Context $Context -Path $variablePath.Trim() -AllowMissing
            }
            [void]$builder.Append((Convert-TemplateValueToString $resolvedValue))
            continue
        }

        $directive = $fullToken.Trim()
        if ($directive -match '^\{%\s*if\b') {
            $condition = $false
            if ($currentEnabled) {
                $conditionValue = Get-TemplateContextValue -Context $Context -Path $ifExpression.Trim() -AllowMissing
                $condition = Test-TemplateTruthy $conditionValue
            }

            $frames.Push([pscustomobject]@{
                    parent_enabled = $currentEnabled
                    condition = $condition
                    else_seen = $false
                })
            $currentEnabled = ($currentEnabled -and $condition)
            continue
        }

        if ($directive -match '^\{%\s*else\s*%\}$') {
            if ($frames.Count -lt 1) {
                throw "workflow template has unmatched else directive."
            }

            $frame = $frames.Peek()
            if ($frame.else_seen) {
                throw "workflow template has duplicate else directive in the same block."
            }

            $frame.else_seen = $true
            $currentEnabled = ($frame.parent_enabled -and (-not $frame.condition))
            continue
        }

        if ($directive -match '^\{%\s*endif\s*%\}$') {
            if ($frames.Count -lt 1) {
                throw "workflow template has unmatched endif directive."
            }

            $frame = $frames.Pop()
            $currentEnabled = [bool]$frame.parent_enabled
            continue
        }
    }

    if ($currentEnabled -and $lastIndex -lt $Template.Length) {
        [void]$builder.Append($Template.Substring($lastIndex))
    }

    if ($frames.Count -gt 0) {
        throw "workflow template has unterminated if block."
    }

    return $builder.ToString().Trim()
}

function Get-WorkflowInfo {
    param(
        $Spec,
        [string]$WorkspaceRoot,
        [string]$SpecDirectory
    )

    $workflowFileValue = Get-OptionalProperty $Spec "workflow_file"
    $workflowAutoDetect = Get-BoolValue (Get-OptionalProperty $Spec "workflow_auto_detect") $true
    if (-not $workflowFileValue -and $workflowAutoDetect) {
        foreach ($candidate in @(
                (Join-Path $WorkspaceRoot "WORKFLOW.md"),
                (Join-Path $SpecDirectory "WORKFLOW.md")
            )) {
            if (Test-Path -LiteralPath $candidate) {
                $workflowFileValue = $candidate
                break
            }
        }
    }

    if (-not $workflowFileValue) {
        return [pscustomobject]@{
            enabled = $false
            source = $null
            prompt_template = $null
            front_matter_text = $null
            prompt_mode = "disabled"
            strict_render = $true
            auto_detected = $false
            context = [ordered]@{}
        }
    }

    $workflowPath = Resolve-AbsolutePath -Path ([string]$workflowFileValue) -BaseDirectory $SpecDirectory
    $workflowContent = Get-Content -LiteralPath $workflowPath -Raw
    $workflowDocument = Split-WorkflowDocument -Content $workflowContent

    $workflowContext = [ordered]@{}
    $workflowContextFileValue = Get-OptionalProperty $Spec "workflow_context_file"
    if ($workflowContextFileValue) {
        $workflowContextFilePath = Resolve-AbsolutePath -Path ([string]$workflowContextFileValue) -BaseDirectory $SpecDirectory
        $workflowContextFileText = Get-Content -LiteralPath $workflowContextFilePath -Raw
        $workflowContext = Merge-TemplateContextMaps `
            -Base $workflowContext `
            -Overlay (ConvertTo-TemplateContextMap ($workflowContextFileText | ConvertFrom-Json -ErrorAction Stop))
    }

    $workflowContext = Merge-TemplateContextMaps `
        -Base $workflowContext `
        -Overlay (ConvertTo-TemplateContextMap (Get-OptionalProperty $Spec "workflow_context"))
    $workflowContext = Merge-TemplateContextMaps `
        -Base $workflowContext `
        -Overlay ([ordered]@{
                workflow = [ordered]@{
                    source = $workflowPath
                    workspace_root = $WorkspaceRoot
                }
            })

    return [pscustomobject]@{
        enabled = $true
        source = $workflowPath
        prompt_template = $workflowDocument.prompt_template
        front_matter_text = $workflowDocument.front_matter_text
        prompt_mode = Get-NormalizedChoice `
            -Primary (Get-OptionalProperty $Spec "workflow_prompt_mode") `
            -Fallback $null `
            -Default "prepend" `
            -AllowedValues @("prepend", "replace", "disabled") `
            -FieldName "workflow_prompt_mode"
        strict_render = Get-BoolValue (Get-OptionalProperty $Spec "workflow_render_strict") $true
        auto_detected = (-not (Get-OptionalProperty $Spec "workflow_file"))
        context = $workflowContext
    }
}

function Get-AgentWorkflowContext {
    param(
        $WorkflowInfo,
        $Agent,
        [string]$WorkerName,
        [string]$WorkerKind,
        [int]$Stage,
        [string]$WorkerCwd,
        [string]$WorkspaceRoot
    )

    if ($null -eq $WorkflowInfo -or -not $WorkflowInfo.enabled) {
        return [ordered]@{}
    }

    $context = ConvertTo-TemplateContextMap $WorkflowInfo.context
    $agentContextFileValue = Get-OptionalProperty $Agent "workflow_context_file"
    if ($agentContextFileValue) {
        $agentContextFilePath = Resolve-AbsolutePath -Path ([string]$agentContextFileValue) -BaseDirectory $WorkspaceRoot
        $agentContextFileText = Get-Content -LiteralPath $agentContextFilePath -Raw
        $context = Merge-TemplateContextMaps `
            -Base $context `
            -Overlay (ConvertTo-TemplateContextMap ($agentContextFileText | ConvertFrom-Json -ErrorAction Stop))
    }

    $context = Merge-TemplateContextMaps `
        -Base $context `
        -Overlay (ConvertTo-TemplateContextMap (Get-OptionalProperty $Agent "workflow_context"))
    $context = Merge-TemplateContextMaps `
        -Base $context `
        -Overlay ([ordered]@{
                agent = [ordered]@{
                    name = $WorkerName
                    kind = $WorkerKind
                    stage = $Stage
                    cwd = $WorkerCwd
                    role = [string](Get-OptionalProperty $Agent "role")
                    mission = [string](Get-OptionalProperty $Agent "mission")
                }
                run = [ordered]@{
                    worker_name = $WorkerName
                    worker_kind = $WorkerKind
                    stage = $Stage
                    worker_cwd = $WorkerCwd
                    workspace_root = $WorkspaceRoot
                }
            })

    return $context
}

function Get-AgentWorkflowRenderInfo {
    param(
        $WorkflowInfo,
        $Agent,
        [string]$WorkerName,
        [string]$WorkerKind,
        [int]$Stage,
        [string]$WorkerCwd,
        [string]$WorkspaceRoot
    )

    if ($null -eq $WorkflowInfo -or -not $WorkflowInfo.enabled -or $WorkflowInfo.prompt_mode -eq "disabled") {
        return [pscustomobject]@{
            enabled = $false
            mode = "disabled"
            text = $null
            context = [ordered]@{}
        }
    }

    $agentPromptMode = Get-OptionalProperty $Agent "workflow_prompt_mode"
    $effectiveMode = Get-NormalizedChoice `
        -Primary $agentPromptMode `
        -Fallback $WorkflowInfo.prompt_mode `
        -Default "prepend" `
        -AllowedValues @("prepend", "replace", "disabled") `
        -FieldName "workflow_prompt_mode"
    if ($effectiveMode -eq "disabled") {
        return [pscustomobject]@{
            enabled = $false
            mode = "disabled"
            text = $null
            context = [ordered]@{}
        }
    }

    $context = Get-AgentWorkflowContext `
        -WorkflowInfo $WorkflowInfo `
        -Agent $Agent `
        -WorkerName $WorkerName `
        -WorkerKind $WorkerKind `
        -Stage $Stage `
        -WorkerCwd $WorkerCwd `
        -WorkspaceRoot $WorkspaceRoot
    $renderedText = Render-WorkflowTemplate `
        -Template $WorkflowInfo.prompt_template `
        -Context $context `
        -StrictVariables $WorkflowInfo.strict_render

    return [pscustomobject]@{
        enabled = $true
        mode = $effectiveMode
        text = $renderedText
        context = $context
    }
}

function Test-DirectoryIsEmpty {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $true
    }

    return @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue).Count -eq 0
}

function Invoke-PowerShellHook {
    param(
        [string]$Command,
        [string]$RunCwd,
        [string]$StdoutPath,
        [string]$StderrPath
    )

    $stdoutDirectory = Split-Path -Parent $StdoutPath
    $stderrDirectory = Split-Path -Parent $StderrPath
    if (-not [string]::IsNullOrWhiteSpace($stdoutDirectory)) {
        New-Item -ItemType Directory -Path $stdoutDirectory -Force | Out-Null
    }
    if (-not [string]::IsNullOrWhiteSpace($stderrDirectory)) {
        New-Item -ItemType Directory -Path $stderrDirectory -Force | Out-Null
    }

    $encodedCommand = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($Command))
    try {
        $process = Start-Process `
            -FilePath "powershell.exe" `
            -ArgumentList "-NoProfile -ExecutionPolicy Bypass -EncodedCommand $encodedCommand" `
            -WorkingDirectory $RunCwd `
            -RedirectStandardOutput $StdoutPath `
            -RedirectStandardError $StderrPath `
            -PassThru `
            -Wait `
            -NoNewWindow
        $exitCode = [int]$process.ExitCode
    } catch {
        $message = $_ | Out-String
        Add-Content -LiteralPath $StderrPath -Value $message -Encoding utf8
        $exitCode = -1
    }

    return [pscustomobject]@{
        exit_code = $exitCode
        stdout = $StdoutPath
        stderr = $StderrPath
        command = $Command
    }
}

function Get-AfterCreateHookInfo {
    param(
        $Spec,
        [string]$WorkspaceRoot,
        [string]$OutputDir
    )

    $hooks = Get-OptionalProperty $Spec "hooks"
    if ($null -eq $hooks) {
        return [pscustomobject]@{
            enabled = $false
            command = $null
            sentinel_paths = @()
            if_workspace_empty = $false
            stdout = $null
            stderr = $null
        }
    }

    $afterCreateCommand = Get-OptionalProperty $hooks "after_create"
    if (-not $afterCreateCommand) {
        return [pscustomobject]@{
            enabled = $false
            command = $null
            sentinel_paths = @()
            if_workspace_empty = $false
            stdout = $null
            stderr = $null
        }
    }

    $sentinelPaths = @(
        Get-UniqueStringList (Get-OptionalProperty $hooks "after_create_sentinel_paths") |
            ForEach-Object { Resolve-AbsolutePath -Path $_ -BaseDirectory $WorkspaceRoot -AllowMissing }
    )
    $ifWorkspaceEmptyValue = Get-OptionalProperty $hooks "after_create_if_workspace_empty"
    $ifWorkspaceEmpty = if ($null -ne $ifWorkspaceEmptyValue) {
        [bool]$ifWorkspaceEmptyValue
    } elseif (@($sentinelPaths).Count -eq 0) {
        $true
    } else {
        $false
    }

    $stdoutPathValue = Get-OptionalProperty $hooks "after_create_stdout_file"
    $stderrPathValue = Get-OptionalProperty $hooks "after_create_stderr_file"

    return [pscustomobject]@{
        enabled = $true
        command = [string]$afterCreateCommand
        sentinel_paths = [string[]]$sentinelPaths
        if_workspace_empty = $ifWorkspaceEmpty
        stdout = if ($stdoutPathValue) {
            Resolve-AbsolutePath -Path ([string]$stdoutPathValue) -BaseDirectory $WorkspaceRoot -AllowMissing
        } else {
            Resolve-AbsolutePath -Path (Join-Path $OutputDir "workspace-bootstrap.stdout.log") -BaseDirectory $WorkspaceRoot -AllowMissing
        }
        stderr = if ($stderrPathValue) {
            Resolve-AbsolutePath -Path ([string]$stderrPathValue) -BaseDirectory $WorkspaceRoot -AllowMissing
        } else {
            Resolve-AbsolutePath -Path (Join-Path $OutputDir "workspace-bootstrap.stderr.log") -BaseDirectory $WorkspaceRoot -AllowMissing
        }
    }
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
        $Lines.Add("- $item")
    }
}

function Get-TextHash {
    param([string]$Text)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        $hash = $sha.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($hash)).Replace("-", "").ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Get-FileTextSafe {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    return Get-Content -LiteralPath $Path -Raw
}

function Get-PreviewText {
    param(
        [string]$Text,
        [int]$Limit = 400
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $null
    }

    $trimmed = $Text.Trim()
    if ($trimmed.Length -le $Limit) {
        return $trimmed
    }

    return $trimmed.Substring(0, $Limit) + "..."
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

function Copy-ExistingFile {
    param(
        [string]$SourcePath,
        [string]$DestinationPath
    )

    if ([string]::IsNullOrWhiteSpace($SourcePath) -or -not (Test-Path -LiteralPath $SourcePath)) {
        return $false
    }

    $destinationDirectory = Split-Path -Parent $DestinationPath
    if (-not [string]::IsNullOrWhiteSpace($destinationDirectory)) {
        New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    }

    Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath -Force
    return $true
}

function Find-SessionLogPath {
    param([string]$SessionId)

    if ([string]::IsNullOrWhiteSpace($SessionId)) {
        return $null
    }

    $sessionsRoot = Join-Path $HOME ".codex\sessions"
    if (-not (Test-Path -LiteralPath $sessionsRoot)) {
        return $null
    }

    $match = Get-ChildItem -Path $sessionsRoot -Recurse -File -Filter "*$SessionId*.jsonl" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($match) {
        return $match.FullName
    }

    return $null
}

function Test-PathHasContent {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }

    $item = Get-Item -LiteralPath $Path -ErrorAction Stop
    if ($item.PSIsContainer) {
        return @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue).Count -gt 0
    }

    return $item.Length -gt 0
}

function Test-WorkerRequiredPaths {
    param(
        $Run
    )

    $missingPaths = New-Object System.Collections.Generic.List[string]
    $emptyPaths = New-Object System.Collections.Generic.List[string]

    foreach ($path in @($Run.required_paths)) {
        if ([string]::IsNullOrWhiteSpace([string]$path)) {
            continue
        }

        if (-not (Test-Path -LiteralPath $path)) {
            $missingPaths.Add([string]$path)
        }
    }

    foreach ($path in @($Run.required_non_empty_paths)) {
        if ([string]::IsNullOrWhiteSpace([string]$path)) {
            continue
        }

        if (-not (Test-Path -LiteralPath $path)) {
            if ($missingPaths -notcontains [string]$path) {
                $missingPaths.Add([string]$path)
            }
            continue
        }

        if (-not (Test-PathHasContent -Path $path)) {
            $emptyPaths.Add([string]$path)
        }
    }

    return [pscustomobject]@{
        missing_paths = [string[]]$missingPaths.ToArray()
        empty_paths = [string[]]$emptyPaths.ToArray()
        passed = (@($missingPaths).Count -eq 0 -and @($emptyPaths).Count -eq 0)
    }
}

function New-RunArchiveInfo {
    param(
        [bool]$WriteRunArchive,
        [string]$ArchiveRoot,
        [string]$RunLabel
    )

    if (-not $WriteRunArchive) {
        return [pscustomobject]@{
            enabled = $false
            root = $ArchiveRoot
            run_label = $RunLabel
            run_directory = $null
            launcher_directory = $null
            deliverables_directory = $null
            workers_directory = $null
            supervisor_directory = $null
        }
    }

    $timestamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
    $safeLabel = Get-SafePathSegment -Value $RunLabel -Default "run"
    $runDirectory = [System.IO.Path]::GetFullPath((Join-Path $ArchiveRoot ("{0}-{1}" -f $timestamp, $safeLabel)))

    return [pscustomobject]@{
        enabled = $true
        root = $ArchiveRoot
        run_label = $RunLabel
        run_directory = $runDirectory
        launcher_directory = (Join-Path $runDirectory "launcher")
        deliverables_directory = (Join-Path $runDirectory "deliverables")
        workers_directory = (Join-Path $runDirectory "workers")
        supervisor_directory = (Join-Path $runDirectory "supervisor")
    }
}

function Export-RunArchiveContent {
    param(
        $ArchiveInfo,
        [string]$WorkspaceRoot,
        [string]$SpecPath,
        [string]$ManifestPath,
        [string]$SummaryPath,
        [string]$DebugLogPath,
        $SharedDirectiveInfo,
        $PersonaGuideInfo,
        $WorkflowInfo,
        $AfterCreateHookResult,
        [string[]]$RequestedDeliverables,
        $Results
    )

    if ($null -eq $ArchiveInfo -or -not $ArchiveInfo.enabled) {
        return
    }

    foreach ($directory in @(
            $ArchiveInfo.run_directory,
            $ArchiveInfo.launcher_directory,
            $ArchiveInfo.deliverables_directory,
            $ArchiveInfo.workers_directory,
            $ArchiveInfo.supervisor_directory
        )) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    Copy-ExistingFile -SourcePath $SpecPath -DestinationPath (Join-Path $ArchiveInfo.launcher_directory (Split-Path -Leaf $SpecPath)) | Out-Null
    Copy-ExistingFile -SourcePath $ManifestPath -DestinationPath (Join-Path $ArchiveInfo.launcher_directory (Split-Path -Leaf $ManifestPath)) | Out-Null
    if (-not [string]::IsNullOrWhiteSpace($SummaryPath)) {
        Copy-ExistingFile -SourcePath $SummaryPath -DestinationPath (Join-Path $ArchiveInfo.launcher_directory (Split-Path -Leaf $SummaryPath)) | Out-Null
    }
    if (-not [string]::IsNullOrWhiteSpace($DebugLogPath)) {
        Copy-ExistingFile -SourcePath $DebugLogPath -DestinationPath (Join-Path $ArchiveInfo.launcher_directory (Split-Path -Leaf $DebugLogPath)) | Out-Null
    }

    $workspaceAgentsPath = Join-Path $WorkspaceRoot "AGENTS.md"
    Copy-ExistingFile -SourcePath $workspaceAgentsPath -DestinationPath (Join-Path $ArchiveInfo.supervisor_directory "AGENTS.md") | Out-Null

    if ($SharedDirectiveInfo -and -not [string]::IsNullOrWhiteSpace($SharedDirectiveInfo.source) -and (Test-Path -LiteralPath $SharedDirectiveInfo.source)) {
        $sharedDirectiveLeaf = Split-Path -Leaf $SharedDirectiveInfo.source
        $sharedDirectiveDestination = Join-Path $ArchiveInfo.supervisor_directory ("shared-directive-source-{0}" -f $sharedDirectiveLeaf)
        Copy-ExistingFile -SourcePath $SharedDirectiveInfo.source -DestinationPath $sharedDirectiveDestination | Out-Null
    }
    if ($PersonaGuideInfo -and -not [string]::IsNullOrWhiteSpace($PersonaGuideInfo.source) -and (Test-Path -LiteralPath $PersonaGuideInfo.source)) {
        $personaGuideLeaf = Split-Path -Leaf $PersonaGuideInfo.source
        $personaGuideDestination = Join-Path $ArchiveInfo.supervisor_directory ("persona-guide-source-{0}" -f $personaGuideLeaf)
        Copy-ExistingFile -SourcePath $PersonaGuideInfo.source -DestinationPath $personaGuideDestination | Out-Null
    }
    if ($WorkflowInfo -and $WorkflowInfo.enabled -and -not [string]::IsNullOrWhiteSpace($WorkflowInfo.source) -and (Test-Path -LiteralPath $WorkflowInfo.source)) {
        Copy-ExistingFile -SourcePath $WorkflowInfo.source -DestinationPath (Join-Path $ArchiveInfo.supervisor_directory (Split-Path -Leaf $WorkflowInfo.source)) | Out-Null
    }
    if ($AfterCreateHookResult -and $AfterCreateHookResult.ran) {
        Copy-ExistingFile -SourcePath $AfterCreateHookResult.stdout -DestinationPath (Join-Path $ArchiveInfo.supervisor_directory "workspace-bootstrap.stdout.log") | Out-Null
        Copy-ExistingFile -SourcePath $AfterCreateHookResult.stderr -DestinationPath (Join-Path $ArchiveInfo.supervisor_directory "workspace-bootstrap.stderr.log") | Out-Null
    }

    foreach ($deliverable in @($RequestedDeliverables)) {
        if ([string]::IsNullOrWhiteSpace($deliverable)) {
            continue
        }

        $deliverablePath = Resolve-AbsolutePath -Path $deliverable -BaseDirectory $WorkspaceRoot -AllowMissing
        if (-not (Test-Path -LiteralPath $deliverablePath)) {
            continue
        }

        $deliverableLeaf = Split-Path -Leaf $deliverablePath
        Copy-ExistingFile -SourcePath $deliverablePath -DestinationPath (Join-Path $ArchiveInfo.deliverables_directory $deliverableLeaf) | Out-Null
    }

    foreach ($result in @($Results)) {
        $workerDirectoryName = "{0}__{1}" -f `
            (Get-SafePathSegment -Value ([string]$result.worker_kind) -Default "worker"), `
            (Get-SafePathSegment -Value ([string]$result.name) -Default "worker")
        $workerDirectory = Join-Path $ArchiveInfo.workers_directory $workerDirectoryName
        New-Item -ItemType Directory -Path $workerDirectory -Force | Out-Null

        $workerMetadata = [ordered]@{
            name = $result.name
            stage = $result.stage
            worker_kind = $result.worker_kind
            session_id = $result.session_id
            succeeded = $result.succeeded
            exit_code = $result.exit_code
            is_read_only = $result.is_read_only
            cwd = $result.cwd
            required_paths = $result.required_paths
            required_non_empty_paths = $result.required_non_empty_paths
            missing_required_paths = $result.missing_required_paths
            empty_required_paths = $result.empty_required_paths
            validation_failures = $result.validation_failures
            requested_model = $result.requested_model
            requested_full_auto = $result.requested_full_auto
            actual_model = $result.actual_model
            requested_sandbox = $result.requested_sandbox
            actual_sandbox = $result.actual_sandbox
            requested_reasoning_effort = $result.requested_reasoning_effort
            actual_reasoning_effort = $result.actual_reasoning_effort
            prompt_profile = $result.prompt_profile
            response_style = $result.response_style
            max_response_lines = $result.max_response_lines
            actual_approval = $result.actual_approval
            actual_workdir = $result.actual_workdir
            footer_tokens_used = $result.footer_tokens_used
            workflow_prompt_mode = $result.workflow_prompt_mode
            workflow_prompt_chars = $result.workflow_prompt_chars
            command = $result.command
            source_paths = [ordered]@{
                prompt = $result.prompt
                stdout = $result.stdout
                stderr = $result.stderr
                last = $result.last
            }
            created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        }

        $workerMetadata | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $workerDirectory "worker-metadata.json") -Encoding utf8

        Copy-ExistingFile -SourcePath $result.prompt -DestinationPath (Join-Path $workerDirectory "prompt.txt") | Out-Null
        Copy-ExistingFile -SourcePath $result.stdout -DestinationPath (Join-Path $workerDirectory "stdout.log") | Out-Null
        Copy-ExistingFile -SourcePath $result.stderr -DestinationPath (Join-Path $workerDirectory "stderr.log") | Out-Null
        Copy-ExistingFile -SourcePath $result.last -DestinationPath (Join-Path $workerDirectory "last.txt") | Out-Null

        $sessionLogPath = Find-SessionLogPath -SessionId ([string]$result.session_id)
        if ($sessionLogPath) {
            Copy-ExistingFile -SourcePath $sessionLogPath -DestinationPath (Join-Path $workerDirectory "session.jsonl") | Out-Null
        }
    }
}

function Get-CompactDirectiveText {
    param(
        [string]$SourceText,
        [string]$Source
    )

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add($CompactPrincipalEngineerDirective.Trim())

    if (-not [string]::IsNullOrWhiteSpace($SourceText)) {
        $lines.Add("")
        if ((Split-Path -Leaf $Source) -eq "AGENTS.md") {
            $lines.Add("If workspace-specific rules are unclear, inspect AGENTS.md before editing.")
        } else {
            $lines.Add("Inspect the workspace directive file only if local rules are unclear or the task boundary is ambiguous.")
        }
    }

    return ($lines -join [Environment]::NewLine)
}

function Get-DirectiveReferenceText {
    param([string]$Source)

    if ([string]::IsNullOrWhiteSpace($Source)) {
        return "Read and follow AGENTS.md in the working directory as the governing contract. Do not restate it."
    }

    $leaf = Split-Path -Leaf $Source
    if ($leaf -eq "AGENTS.md") {
        return "Read and follow AGENTS.md in the working directory as the governing contract. Do not restate it."
    }

    return ("Read and follow the shared directive file before editing: {0}" -f $Source)
}

function Get-DefaultPersonaGuidePath {
    $candidate = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\references\subagent-persona-guide.md"))
    if (-not (Test-Path -LiteralPath $candidate)) {
        throw "Built-in persona guide is missing: $candidate"
    }

    return $candidate
}

function Get-PersonaGuideReferenceText {
    param([string]$Source)

    if ([string]::IsNullOrWhiteSpace($Source) -or $Source -eq "spec.persona_guide_text") {
        return "Derive the smallest task-appropriate working persona from the persona guide already supplied. Keep it implicit, practical, and non-theatrical."
    }

    return ("Read the persona guide before acting if it will sharpen judgment: {0}. Derive only the smallest task-appropriate working persona, keep it implicit, and do not roleplay it." -f $Source)
}

function Join-NaturalLanguageList {
    param([string[]]$Items)

    $values = @()
    foreach ($item in @($Items)) {
        if (-not [string]::IsNullOrWhiteSpace($item)) {
            $values += ([string]$item).Trim()
        }
    }

    $values = @($values | Select-Object -Unique)
    if ($values.Count -eq 0) {
        return ""
    }

    if ($values.Count -eq 1) {
        return $values[0]
    }

    if ($values.Count -eq 2) {
        return ("{0} and {1}" -f $values[0], $values[1])
    }

    return ((@($values[0..($values.Count - 2)]) -join ", ") + ", and " + $values[$values.Count - 1])
}

function Get-AgentPersonaContextText {
    param($Agent)

    $parts = New-Object System.Collections.Generic.List[string]

    foreach ($fieldName in @("role", "mission", "task", "prompt")) {
        $value = Get-OptionalProperty $Agent $fieldName
        if (-not [string]::IsNullOrWhiteSpace([string]$value)) {
            $parts.Add(([string]$value).Trim())
        }
    }

    foreach ($fieldName in @("success_criteria", "coordination_notes", "return_contract", "stop_when")) {
        foreach ($item in Get-StringList (Get-OptionalProperty $Agent $fieldName)) {
            if (-not [string]::IsNullOrWhiteSpace($item)) {
                $parts.Add($item.Trim())
            }
        }
    }

    foreach ($fieldName in @("read_first", "required_paths", "required_non_empty_paths", "writable_scope")) {
        foreach ($item in Get-StringList (Get-OptionalProperty $Agent $fieldName)) {
            if (-not [string]::IsNullOrWhiteSpace($item)) {
                $parts.Add((Split-Path -Leaf $item).Trim())
            }
        }
    }

    return ($parts -join [Environment]::NewLine)
}

function Get-KeywordMatchCount {
    param(
        [string]$Text,
        [string[]]$Patterns
    )

    if ([string]::IsNullOrWhiteSpace($Text) -or -not $Patterns) {
        return 0
    }

    $score = 0
    foreach ($pattern in $Patterns) {
        if ([string]::IsNullOrWhiteSpace($pattern)) {
            continue
        }

        if ([regex]::IsMatch($Text, $pattern)) {
            $score += 1
        }
    }

    return $score
}

function Get-PersonaDomainCatalog {
    return @(
        [pscustomobject]@{
            id = "frontend"
            label = "frontend product engineer"
            guidance = "Favor accessible interaction, responsive layout, browser correctness, clear component state, and implementation-ready polish."
            patterns = @('\bfront[\s-]?end\b', '\bhtml\b', '\bcss\b', '\bdom\b', '\bbrowser\b', '\breact\b', '\bvue\b', '\bsvelte\b', '\bnext(?:\.js)?\b', '\bcomponent\b', '\btsx\b', '\bjsx\b', '\bresponsive\b', '\bui\b')
        }
        [pscustomobject]@{
            id = "design"
            label = "visual interaction designer"
            guidance = "Protect hierarchy, typography, spacing, contrast, motion restraint, and a visual system that feels intentional rather than generic."
            patterns = @('\bdesign\b', '\bvisual\b', '\btypography\b', '\bcolor\b', '\bpalette\b', '\bspacing\b', '\blayout\b', '\bhero\b', '\bbrand\b', '\bfigma\b', '\bwireframe\b', '\bmockup\b', '\banimation\b', '\bmotion\b', '\bux\b')
        }
        [pscustomobject]@{
            id = "game"
            label = "gameplay interaction designer"
            guidance = "Preserve feedback loops, rule clarity, pacing, difficulty signaling, and game feel that stays readable under repeated play."
            patterns = @('\bgame\b', '\bgameplay\b', '\bscore\b', '\blevel\b', '\bplayer\b', '\bmine(?:sweeper)?\b', '\bdifficulty\b', '\bgame over\b', '\bleaderboard\b', '\bwin\b', '\blose\b')
        }
        [pscustomobject]@{
            id = "backend"
            label = "backend systems engineer"
            guidance = "Think in contracts, idempotency, concurrency, state transitions, explicit failure handling, and rollback-safe behavior."
            patterns = @('\bback[\s-]?end\b', '\bapi\b', '\bserver\b', '\bservice\b', '\bworker\b', '\bqueue\b', '\bretry\b', '\blease\b', '\bidempot', '\bmessage\b', '\bjob\b', '\bpostgres\b', '\bmysql\b', '\bredis\b', '\bdb\b', '\bdatabase\b')
        }
        [pscustomobject]@{
            id = "security"
            label = "security-minded application engineer"
            guidance = "Guard trust boundaries, secret handling, abuse paths, permission edges, and input validation before convenience."
            patterns = @('\bsecurity\b', '\bauth\b', '\boauth\b', '\brbac\b', '\bpermission\b', '\bsecret\b', '\btoken\b', '\bencrypt', '\bxss\b', '\bcsrf\b', '\binjection\b', '\bsandbox\b')
        }
        [pscustomobject]@{
            id = "data"
            label = "data systems analyst"
            guidance = "Favor traceable transformations, schema clarity, measurable outputs, and checks that make the data story auditable."
            patterns = @('\bdata\b', '\bdataset\b', '\banalytics\b', '\betl\b', '\bcsv\b', '\btable\b', '\bsql\b', '\bquery\b', '\bmetric\b', '\bstat', '\bwarehouse\b')
        }
        [pscustomobject]@{
            id = "narrative"
            label = "novelist and scene architect"
            guidance = "Protect voice consistency, scene logic, emotional progression, concrete detail, and character intent without losing clarity."
            patterns = @('\bnovel\b', '\bstory\b', '\bfiction\b', '\bchapter\b', '\bscene\b', '\bdialogue\b', '\bcharacter\b', '\bplot\b', '\bworldbuild', '\bprose\b', '\bpoem\b', '\bscript\b')
        }
        [pscustomobject]@{
            id = "editorial"
            label = "editor with line-level discipline"
            guidance = "Tighten structure, diction, rhythm, and redundancy so the output reads intentional, clean, and controlled."
            patterns = @('\bedit\b', '\brewrite\b', '\bpolish\b', '\bvoice\b', '\bstyle\b', '\bline edit\b', '\bcopy edit\b', '\bproofread\b')
        }
        [pscustomobject]@{
            id = "documentation"
            label = "technical writer"
            guidance = "Favor fast comprehension, reliable examples, stepwise structure, and explanations that survive first contact."
            patterns = @('\breadme\b', '\bdocumentation\b', '\bdocs\b', '\btutorial\b', '\bwalkthrough\b', '\bapi reference\b', '\boperator runbook\b')
        }
        [pscustomobject]@{
            id = "product"
            label = "product systems thinker"
            guidance = "Sharpen user intent, success criteria, tradeoffs, scope boundaries, and the sequence that turns goals into delivery."
            patterns = @('\brequirement', '\bspec\b', '\broadmap\b', '\buser flow\b', '\bacceptance\b', '\bdeliverable\b', '\bstakeholder\b', '\bproduct\b')
        }
        [pscustomobject]@{
            id = "performance"
            label = "performance engineer"
            guidance = "Protect latency, throughput, memory shape, and measurement discipline instead of speculative tuning."
            patterns = @('\bperformance\b', '\blatency\b', '\bthroughput\b', '\bbenchmark\b', '\bprofile\b', '\bmemory\b', '\bcpu\b', '\boptimi[sz]e\b')
        }
    )
}

function Get-PersonaDomainMatches {
    param([string]$ContextText)

    $matches = @()
    foreach ($domain in Get-PersonaDomainCatalog) {
        $score = Get-KeywordMatchCount -Text $ContextText -Patterns $domain.patterns
        if ($score -gt 0) {
            $matches += [pscustomobject]@{
                id = $domain.id
                label = $domain.label
                guidance = $domain.guidance
                score = $score
            }
        }
    }

    return @(
        $matches |
            Sort-Object -Property @(
                @{ Expression = "score"; Descending = $true },
                @{ Expression = "label"; Descending = $false }
            ) |
            Select-Object -First 3
    )
}

function Get-WorkerRolePersonaFrame {
    param(
        [string]$WorkerKind,
        [bool]$IsReadOnly,
        [string]$ContextText
    )

    switch ($WorkerKind) {
        "implementer" {
            return [pscustomobject]@{
                id = "implementer"
                label = "pragmatic builder"
                guidance = "Favor the smallest dependable change, visible state, rollback safety, and direct verification against the real task."
            }
        }
        "fixer" {
            return [pscustomobject]@{
                id = "fixer"
                label = "surgical recovery engineer"
                guidance = "Target the material defect directly, preserve working behavior, and leave a narrow, verifiable repair."
            }
        }
        "reviewer" {
            return [pscustomobject]@{
                id = "reviewer"
                label = "skeptical production examiner"
                guidance = "Look for hidden failure, missing evidence, weak contracts, scope creep, and edge conditions that will surface after release."
            }
        }
        "validator" {
            return [pscustomobject]@{
                id = "validator"
                label = "strict contract validator"
                guidance = "Judge only against observable requirements, evidence, and final artifact quality rather than intent alone."
            }
        }
        "planner" {
            return [pscustomobject]@{
                id = "planner"
                label = "systems planner"
                guidance = "Clarify intent, sequence, risk, dependencies, and handoff boundaries before detail."
            }
        }
    }

    if ($IsReadOnly) {
        return [pscustomobject]@{
            id = "read_only_custom"
            label = "critical analyst"
            guidance = "Interrogate ambiguity, evidence, and hidden downside while staying factual and compact."
        }
    }

    if ($ContextText -match '\b(novel|story|fiction|chapter|scene|dialogue|character|plot|prose|copy|essay|script)\b') {
        return [pscustomobject]@{
            id = "creative_custom"
            label = "craft-focused maker"
            guidance = "Use structure and taste deliberately, but keep the result useful, scoped, and revision-ready."
        }
    }

    return [pscustomobject]@{
        id = "custom"
        label = "versatile specialist"
        guidance = "Infer the shortest path to a strong result, keep state explicit, and stay grounded in the actual request."
    }
}

function New-DynamicPersonaGuideInfoRecord {
    param(
        [string]$RawText,
        [string]$Source,
        $Agent,
        [string]$WorkerKind,
        [bool]$IsReadOnly
    )

    $contextText = Get-AgentPersonaContextText -Agent $Agent
    $contextLower = if ([string]::IsNullOrWhiteSpace($contextText)) { "" } else { $contextText.ToLowerInvariant() }
    $domains = @(Get-PersonaDomainMatches -ContextText $contextLower)
    $roleFrame = Get-WorkerRolePersonaFrame -WorkerKind $WorkerKind -IsReadOnly $IsReadOnly -ContextText $contextLower

    $labels = @($roleFrame.label)
    foreach ($domain in @($domains | Select-Object -First 2)) {
        if ($domain.label -notin $labels) {
            $labels += $domain.label
        }
    }

    $guidanceParts = @($roleFrame.guidance)
    foreach ($domain in @($domains | Select-Object -First 2)) {
        if ($domain.guidance -notin $guidanceParts) {
            $guidanceParts += $domain.guidance
        }
    }

    $personaText = @(
        ("Summon the smallest fitting expert blend directly from the request itself and work as a {0}." -f (Join-NaturalLanguageList -Items $labels)),
        (($guidanceParts | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join " "),
        "Keep the persona implicit, MM-dense, factual, and subordinate to AGENTS.md, task acceptance criteria, sandbox limits, and required output format."
    ) -join " "

    return [pscustomobject]@{
        text = $personaText.Trim()
        source = $Source
        requested_mode = "dynamic"
        effective_mode = "dynamic"
        raw_text = $RawText
        original_char_count = if ($RawText) { $RawText.Length } else { 0 }
        effective_char_count = $personaText.Trim().Length
        domain_ids = [string[]]@($domains | Select-Object -ExpandProperty id)
        role_frame = [string]$roleFrame.id
    }
}

function New-PersonaGuideInfoRecord {
    param(
        [string]$RequestedMode,
        [string]$RawText,
        [string]$Source
    )

    if ($RequestedMode -eq "disabled") {
        return [pscustomobject]@{
            text = $null
            source = "disabled"
            requested_mode = $RequestedMode
            effective_mode = "disabled"
            raw_text = $null
            original_char_count = 0
            effective_char_count = 0
            domain_ids = [string[]]@()
            role_frame = $null
        }
    }

    if ([string]::IsNullOrWhiteSpace($RawText)) {
        throw "persona_guide_mode '$RequestedMode' requires persona guide text."
    }

    $effectiveText = switch ($RequestedMode) {
        "compact" {
            $RawText.Trim()
            break
        }
        "dynamic" {
            $RawText.Trim()
            break
        }
        "reference" {
            Get-PersonaGuideReferenceText -Source $Source
            break
        }
    }

    return [pscustomobject]@{
        text = $effectiveText
        source = $Source
        requested_mode = $RequestedMode
        effective_mode = $RequestedMode
        raw_text = $RawText
        original_char_count = $RawText.Length
        effective_char_count = if ($effectiveText) { $effectiveText.Length } else { 0 }
        domain_ids = [string[]]@()
        role_frame = $null
    }
}

function Get-WorkerPersonaGuideInfo {
    param(
        $PersonaGuideInfo,
        $Agent,
        [string]$WorkerKind,
        [bool]$IsReadOnly
    )

    if ($null -eq $PersonaGuideInfo -or $PersonaGuideInfo.requested_mode -eq "disabled") {
        return $PersonaGuideInfo
    }

    $requestedMode = Get-NormalizedChoice `
        -Primary (Get-OptionalProperty $Agent "persona_guide_mode") `
        -Fallback $PersonaGuideInfo.requested_mode `
        -Default $PersonaGuideInfo.requested_mode `
        -AllowedValues @("compact", "dynamic", "reference", "disabled") `
        -FieldName "persona_guide_mode"

    if ($requestedMode -eq "dynamic") {
        return New-DynamicPersonaGuideInfoRecord `
            -RawText ([string]$PersonaGuideInfo.raw_text) `
            -Source ([string]$PersonaGuideInfo.source) `
            -Agent $Agent `
            -WorkerKind $WorkerKind `
            -IsReadOnly $IsReadOnly
    }

    return New-PersonaGuideInfoRecord `
        -RequestedMode $requestedMode `
        -RawText ([string]$PersonaGuideInfo.raw_text) `
        -Source ([string]$PersonaGuideInfo.source)
}

function Get-PersonaGuideInfo {
    param(
        $Spec,
        [string]$SpecDirectory
    )

    $requestedMode = Get-NormalizedChoice `
        -Primary (Get-OptionalProperty $Spec "persona_guide_mode") `
        -Fallback $null `
        -Default "dynamic" `
        -AllowedValues @("compact", "dynamic", "reference", "disabled") `
        -FieldName "persona_guide_mode"

    if ($requestedMode -eq "disabled") {
        return New-PersonaGuideInfoRecord -RequestedMode "disabled" -RawText $null -Source "disabled"
    }

    $rawText = $null
    $source = $null

    $inlineGuide = Get-OptionalProperty $Spec "persona_guide_text"
    if ($inlineGuide) {
        $rawText = ([string]$inlineGuide).Trim()
        $source = "spec.persona_guide_text"
    }

    if ($null -eq $rawText) {
        $guideFileValue = Get-OptionalProperty $Spec "persona_guide_file"
        if ($guideFileValue) {
            $guidePath = Resolve-AbsolutePath -Path ([string]$guideFileValue) -BaseDirectory $SpecDirectory
            $rawText = (Get-Content -LiteralPath $guidePath -Raw).Trim()
            $source = $guidePath
        }
    }

    if ($null -eq $rawText) {
        $defaultGuidePath = Get-DefaultPersonaGuidePath
        $rawText = (Get-Content -LiteralPath $defaultGuidePath -Raw).Trim()
        $source = $defaultGuidePath
    }

    return New-PersonaGuideInfoRecord -RequestedMode $requestedMode -RawText $rawText -Source $source
}

function New-SharedDirectiveInfoRecord {
    param(
        [string]$RequestedMode,
        [string]$RawText,
        [string]$Source
    )

    if ($RequestedMode -eq "disabled") {
        return [pscustomobject]@{
            text = $null
            source = "disabled"
            requested_mode = $RequestedMode
            effective_mode = "disabled"
            raw_text = $null
            original_char_count = 0
            effective_char_count = 0
        }
    }

    $effectiveMode = $RequestedMode
    $effectiveText = switch ($RequestedMode) {
        "full" {
            $RawText
            break
        }
        "compact" {
            Get-CompactDirectiveText -SourceText $RawText -Source $Source
            break
        }
        "reference" {
            if ($Source -eq "spec.shared_directive_text") {
                $effectiveMode = "compact"
                Get-CompactDirectiveText -SourceText $RawText -Source $Source
            } else {
                Get-DirectiveReferenceText -Source $Source
            }
            break
        }
        "hybrid" {
            $RawText
            break
        }
    }

    return [pscustomobject]@{
        text = $effectiveText
        source = $Source
        requested_mode = $RequestedMode
        effective_mode = $effectiveMode
        raw_text = $RawText
        original_char_count = if ($RawText) { $RawText.Length } else { 0 }
        effective_char_count = if ($effectiveText) { $effectiveText.Length } else { 0 }
    }
}

function Get-HybridSharedDirectiveModeForWorker {
    param(
        [string]$WorkerKind,
        [bool]$IsReadOnly
    )

    if ($WorkerKind -in @("implementer", "fixer")) {
        return "full"
    }

    if ($WorkerKind -in @("reviewer", "validator", "planner")) {
        return "compact"
    }

    if ($WorkerKind -eq "custom" -and $IsReadOnly) {
        return "compact"
    }

    return "full"
}

function Get-WorkerSharedDirectiveInfo {
    param(
        $SharedDirectiveInfo,
        $Agent,
        [string]$WorkerKind,
        [bool]$IsReadOnly
    )

    if ($null -eq $SharedDirectiveInfo -or $SharedDirectiveInfo.requested_mode -eq "disabled") {
        return $SharedDirectiveInfo
    }

    $agentRequestedMode = Get-OptionalProperty $Agent "shared_directive_mode"
    $requestedMode = Get-NormalizedChoice `
        -Primary $agentRequestedMode `
        -Fallback $SharedDirectiveInfo.requested_mode `
        -Default $SharedDirectiveInfo.requested_mode `
        -AllowedValues @("full", "compact", "reference", "disabled", "hybrid") `
        -FieldName "shared_directive_mode"

    if ($requestedMode -eq "hybrid") {
        $requestedMode = Get-HybridSharedDirectiveModeForWorker -WorkerKind $WorkerKind -IsReadOnly $IsReadOnly
    }

    return New-SharedDirectiveInfoRecord `
        -RequestedMode $requestedMode `
        -RawText ([string]$SharedDirectiveInfo.raw_text) `
        -Source ([string]$SharedDirectiveInfo.source)
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
        -Default "hybrid" `
        -AllowedValues @("full", "compact", "reference", "disabled", "hybrid") `
        -FieldName "shared_directive_mode"

    if ($requestedMode -eq "disabled" -or -not (Get-BoolValue (Get-OptionalProperty $Spec "inject_shared_directive") $true)) {
        return New-SharedDirectiveInfoRecord -RequestedMode "disabled" -RawText $null -Source "disabled"
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
        $rawText = $FallbackPrincipalEngineerDirective.Trim()
        $source = "launcher fallback directive"
    }

    return New-SharedDirectiveInfoRecord -RequestedMode $requestedMode -RawText $rawText -Source $source
}

function New-WorkerPrompt {
    param(
        $Agent,
        $SharedDirectiveInfo,
        $PersonaGuideInfo,
        $WorkflowRenderInfo,
        [string]$PromptProfile,
        [string]$ResponseStyle,
        [int]$MaxResponseLines,
        $MemoryContextInfo
    )

    $compactPrompt = ($PromptProfile -eq "compact")
    $compactResponse = ($ResponseStyle -eq "compact")
    $lines = New-Object System.Collections.Generic.List[string]
    if ($compactPrompt) {
        $lines.Add("Mandatory instructions for this run.")
    } else {
        $lines.Add("Treat the following as mandatory operating instructions for this run.")
    }

    if (-not [string]::IsNullOrWhiteSpace($SharedDirectiveInfo.text)) {
        $lines.Add("")
        if ($SharedDirectiveInfo.effective_mode -eq "reference") {
            $lines.Add("Shared contract:")
        }
        $lines.Add($SharedDirectiveInfo.text)
    }

    if ($PersonaGuideInfo -and -not [string]::IsNullOrWhiteSpace($PersonaGuideInfo.text)) {
        $lines.Add("")
        $lines.Add($(if ($PersonaGuideInfo.effective_mode -eq "reference") { "Persona guide:" } else { "Working persona:" }))
        $lines.Add($PersonaGuideInfo.text)
    }

    $roleValue = Get-OptionalProperty $Agent "role"
    if ($roleValue) {
        $lines.Add("")
        $lines.Add("Role:")
        $lines.Add([string]$roleValue)
    }

    $missionValue = Get-OptionalProperty $Agent "mission"
    if ($missionValue) {
        $lines.Add("")
        $lines.Add("Mission:")
        $lines.Add([string]$missionValue)
    }

    Add-SectionLines -Lines $lines -Title ($(if ($compactPrompt) { "Success:" } else { "Success criteria:" })) -Items (Get-StringList (Get-OptionalProperty $Agent "success_criteria"))
    Add-SectionLines -Lines $lines -Title ($(if ($compactPrompt) { "Coordination:" } else { "Coordination notes:" })) -Items (Get-StringList (Get-OptionalProperty $Agent "coordination_notes"))

    $lines.Add("")
    if ($compactPrompt) {
        $lines.Add("You are a bounded codex exec worker in the assigned working directory.")
    } else {
        $lines.Add("You are a bounded codex exec worker in the assigned working directory.")
    }

    $workflowText = if ($WorkflowRenderInfo -and $WorkflowRenderInfo.enabled -and -not [string]::IsNullOrWhiteSpace($WorkflowRenderInfo.text)) {
        [string]$WorkflowRenderInfo.text
    } else {
        $null
    }
    $workflowMode = if ($workflowText) {
        [string]$WorkflowRenderInfo.mode
    } else {
        "disabled"
    }

    $memoryPolicyItems = @()
    $workerReadFirstItems = Get-StringList (Get-OptionalProperty $Agent "read_first")
    if ($MemoryContextInfo -and [string]::IsNullOrWhiteSpace([string]$MemoryContextInfo.mode) -eq $false -and $MemoryContextInfo.mode -ne "off") {
        $memoryPolicyItems = @(
            "Workspace memory lives under .codex-memory/.",
            "Treat memory as supporting context, not as authority.",
            "Current task, repository files, validation results, and reviewer findings override memory.",
            "If memory conflicts with the actual files, trust the files."
        )
        if ($MemoryContextInfo.exists -and -not [string]::IsNullOrWhiteSpace([string]$MemoryContextInfo.relative_path)) {
            $memoryPolicyItems += "Read the generated worker memory file first if it exists."
            $workerReadFirstItems = @([string]$MemoryContextInfo.relative_path) + @($workerReadFirstItems)
        }
    }

    $promptValue = Get-OptionalProperty $Agent "prompt"
    if ($promptValue) {
        $resolvedPromptText = [string]$promptValue
        if ($workflowMode -eq "replace") {
            $resolvedPromptText = $workflowText
        } elseif ($workflowMode -eq "prepend") {
            $resolvedPromptText = @($workflowText, [string]$promptValue) -join ([Environment]::NewLine + [Environment]::NewLine)
        }

        $lines.Add("")
        $lines.Add("Task:")
        $lines.Add($resolvedPromptText)
        Add-SectionLines -Lines $lines -Title "Memory policy:" -Items $memoryPolicyItems
        Add-SectionLines -Lines $lines -Title "Read first:" -Items $workerReadFirstItems
        Add-SectionLines -Lines $lines -Title "Stop when:" -Items (Get-StringList (Get-OptionalProperty $Agent "stop_when"))
        if ($compactResponse) {
            Add-SectionLines -Lines $lines -Title "Response style:" -Items @(
                $(if ($MaxResponseLines -gt 0) { "Keep the final reply to $MaxResponseLines short lines or fewer." } else { "Keep the final reply compact." }),
                "Do not paste logs, long diffs, or unchanged file contents."
            )
        }
        $lines.Add("")
        $lines.Add("Do not ask questions. Do not expand scope.")
        return ($lines -join [Environment]::NewLine)
    }

    $taskValue = Get-OptionalProperty $Agent "task"
    if (-not $taskValue) {
        throw "Each agent must define either 'prompt' or 'task'."
    }

    $lines.Add("")
    $lines.Add("Task:")
    if ($workflowMode -eq "replace") {
        $lines.Add($workflowText)
    } elseif ($workflowMode -eq "prepend") {
        $lines.Add(@($workflowText, [string]$taskValue) -join ([Environment]::NewLine + [Environment]::NewLine))
    } else {
        $lines.Add([string]$taskValue)
    }

    Add-SectionLines -Lines $lines -Title ($(if ($compactPrompt) { "Skills:" } else { "Use these skills if they trigger:" })) -Items (Get-StringList (Get-OptionalProperty $Agent "skills"))
    Add-SectionLines -Lines $lines -Title "Memory policy:" -Items $memoryPolicyItems
    Add-SectionLines -Lines $lines -Title "Read first:" -Items $workerReadFirstItems
    Add-SectionLines -Lines $lines -Title ($(if ($compactPrompt) { "Modify only:" } else { "You may modify only:" })) -Items (Get-StringList (Get-OptionalProperty $Agent "writable_scope"))
    Add-SectionLines -Lines $lines -Title "Requirements:" -Items (Get-StringList (Get-OptionalProperty $Agent "requirements"))
    Add-SectionLines -Lines $lines -Title ($(if ($compactPrompt) { "Check:" } else { "Validation:" })) -Items (Get-StringList (Get-OptionalProperty $Agent "validation"))
    Add-SectionLines -Lines $lines -Title "Return:" -Items (Get-StringList (Get-OptionalProperty $Agent "return_contract"))
    Add-SectionLines -Lines $lines -Title "Stop when:" -Items (Get-StringList (Get-OptionalProperty $Agent "stop_when"))

    if ($compactResponse) {
        Add-SectionLines -Lines $lines -Title "Response style:" -Items @(
            $(if ($MaxResponseLines -gt 0) { "Keep the final reply to $MaxResponseLines short lines or fewer." } else { "Keep the final reply compact." }),
            "Do not paste logs, long diffs, or unchanged file contents."
        )
    }

    $lines.Add("")
    $lines.Add("Do not ask questions. Do not expand scope.")

    return ($lines -join [Environment]::NewLine)
}

function Get-WorkerKind {
    param($Agent)

    $explicitKind = Get-OptionalProperty $Agent "kind"
    if ($explicitKind) {
        $normalizedKind = ([string]$explicitKind).Trim().ToLowerInvariant()
        if ($normalizedKind -notin @("implementer", "reviewer", "validator", "fixer", "planner", "custom")) {
            throw "Unsupported worker kind '$explicitKind'."
        }

        return $normalizedKind
    }

    $roleValue = [string](Get-OptionalProperty $Agent "role")
    if (-not [string]::IsNullOrWhiteSpace($roleValue)) {
        $normalizedRole = $roleValue.ToLowerInvariant()
        if ($normalizedRole -match "review") {
            return "reviewer"
        }
        if ($normalizedRole -match "validat|verif") {
            return "validator"
        }
        if ($normalizedRole -match "fix") {
            return "fixer"
        }
        if ($normalizedRole -match "plan") {
            return "planner"
        }
        if ($normalizedRole -match "implement|build|writer|generator") {
            return "implementer"
        }
    }

    return "custom"
}

function Test-IsReadOnlySandbox {
    param([string]$Sandbox)

    if ([string]::IsNullOrWhiteSpace($Sandbox)) {
        return $false
    }

    return ($Sandbox.Trim().ToLowerInvariant() -eq "read-only")
}

function Get-AgentStage {
    param(
        $Agent,
        [string]$ExecutionMode,
        [int]$DefaultStage
    )

    $stageValue = Get-OptionalProperty $Agent "stage"
    if ($null -ne $stageValue -and -not [string]::IsNullOrWhiteSpace([string]$stageValue)) {
        $parsedStage = 0
        if (-not [int]::TryParse(([string]$stageValue), [ref]$parsedStage) -or $parsedStage -lt 1) {
            $name = [string](Get-OptionalProperty $Agent "name")
            throw "Agent '$name' has invalid 'stage'. Use a positive integer."
        }

        return $parsedStage
    }

    if ($ExecutionMode -eq "parallel") {
        return 1
    }

    return $DefaultStage
}

function Assert-OrchestrationPolicy {
    param(
        $Runs,
        [string]$ExecutionMode,
        [bool]$SupervisorOnly,
        [bool]$RequireFinalReadOnlyReview,
        [string]$MaterialIssueStrategy,
        [string[]]$RequestedDeliverables
    )

    $lastWritableIndex = -1
    $lastWritableStage = -1
    $writableWorkerNames = New-Object System.Collections.Generic.List[string]
    $readOnlyReviewerNames = New-Object System.Collections.Generic.List[string]

    for ($index = 0; $index -lt @($Runs).Count; $index++) {
        $run = $Runs[$index]
        if (-not $run.is_read_only) {
            $lastWritableIndex = $index
            $lastWritableStage = $run.stage
            $writableWorkerNames.Add($run.name)
        }

        if ($run.is_read_only -and $run.worker_kind -in @("reviewer", "validator")) {
            $readOnlyReviewerNames.Add($run.name)
        }
    }

    $finalReadOnlyReviewerNames = New-Object System.Collections.Generic.List[string]
    if ($lastWritableIndex -ge 0) {
        for ($index = $lastWritableIndex + 1; $index -lt @($Runs).Count; $index++) {
            $run = $Runs[$index]
            $isFinalReviewCandidate = $run.is_read_only -and $run.worker_kind -in @("reviewer", "validator")
            if ($isFinalReviewCandidate -and ($ExecutionMode -ne "parallel" -or $run.stage -gt $lastWritableStage)) {
                $finalReadOnlyReviewerNames.Add($run.name)
            }
        }
    }

    if ($SupervisorOnly) {
        $invalidReviewers = @(
            $Runs | Where-Object { $_.worker_kind -in @("reviewer", "validator") -and -not $_.is_read_only }
        )
        if (@($invalidReviewers).Count -gt 0) {
            $names = @($invalidReviewers | ForEach-Object { $_.name }) -join ", "
            throw "Supervisor-only specs require reviewer and validator workers to be read-only. Invalid workers: $names"
        }
    }

    if ($RequireFinalReadOnlyReview -and $lastWritableIndex -ge 0 -and @($finalReadOnlyReviewerNames).Count -eq 0) {
        throw "Spec requires a final read-only reviewer or validator after the last writable worker, but none was found."
    }

    if ($MaterialIssueStrategy -eq "fixer_then_rereview") {
        $fixerRuns = @($Runs | Where-Object { $_.worker_kind -eq "fixer" })
        if (@($fixerRuns).Count -gt 0 -and @($finalReadOnlyReviewerNames).Count -eq 0) {
            throw "Specs using material_issue_strategy='fixer_then_rereview' must include a final read-only reviewer or validator after the last fixer."
        }
    }

    $normalizedDeliverables = @(
        @($RequestedDeliverables) |
            Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } |
            ForEach-Object { [string]$_ }
    )

    return [pscustomobject]@{
        execution_mode = $ExecutionMode
        supervisor_only = $SupervisorOnly
        require_final_read_only_review = $RequireFinalReadOnlyReview
        material_issue_strategy = $MaterialIssueStrategy
        requested_deliverables = [string[]]$normalizedDeliverables
        writable_worker_names = [string[]]$writableWorkerNames.ToArray()
        read_only_reviewer_names = [string[]]$readOnlyReviewerNames.ToArray()
        final_read_only_reviewer_names = [string[]]$finalReadOnlyReviewerNames.ToArray()
        final_read_only_review_present = (@($finalReadOnlyReviewerNames).Count -gt 0)
        last_writable_stage = if ($lastWritableStage -ge 0) { $lastWritableStage } else { $null }
    }
}

function Get-StructureEfficiencySignals {
    param(
        $Results,
        [string]$ExecutionMode,
        $PolicyEvaluation
    )

    $totalWorkers = @($Results).Count
    $succeededWorkers = @($Results | Where-Object { $_.succeeded }).Count
    $failedWorkers = $totalWorkers - $succeededWorkers
    $readOnlyWorkers = @($Results | Where-Object { $_.is_read_only }).Count
    $writableWorkers = $totalWorkers - $readOnlyWorkers
    $implementerWorkers = @($Results | Where-Object { $_.worker_kind -eq "implementer" }).Count
    $reviewerWorkers = @($Results | Where-Object { $_.worker_kind -eq "reviewer" }).Count
    $validatorWorkers = @($Results | Where-Object { $_.worker_kind -eq "validator" }).Count
    $fixerWorkers = @($Results | Where-Object { $_.worker_kind -eq "fixer" }).Count
    $fullAutoWritableWorkers = @($Results | Where-Object { -not $_.is_read_only -and $_.requested_full_auto }).Count
    $fullAutoReadOnlyWorkers = @($Results | Where-Object { $_.is_read_only -and $_.requested_full_auto }).Count
    $stageCount = @(@($Results | ForEach-Object { $_.stage } | Sort-Object -Unique)).Count
    $parallelStageCount = @(
        @($Results |
            Group-Object -Property stage |
            Where-Object { $_.Count -gt 1 })
    ).Count
    $maxParallelWorkersInStage = 0
    foreach ($group in @($Results | Group-Object -Property stage)) {
        if ($group.Count -gt $maxParallelWorkersInStage) {
            $maxParallelWorkersInStage = $group.Count
        }
    }
    $requestedDeliverableCount = @(
        @($PolicyEvaluation.requested_deliverables) |
            Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }
    ).Count

    $promptCharsMeasure = $Results | Measure-Object -Property prompt_chars -Sum
    $promptCharsTotal = if ($null -ne $promptCharsMeasure -and $null -ne $promptCharsMeasure.Sum) {
        [int]$promptCharsMeasure.Sum
    } else {
        0
    }

    $footerTokenResults = @($Results | Where-Object { $null -ne $_.footer_tokens_used })
    $footerTokensTotal = if (@($footerTokenResults).Count -gt 0) {
        $footerTokensMeasure = $footerTokenResults | Measure-Object -Property footer_tokens_used -Sum
        [int]$footerTokensMeasure.Sum
    } else {
        0
    }

    $workersPerDeliverable = if ($requestedDeliverableCount -gt 0) {
        [math]::Round(($totalWorkers / [double]$requestedDeliverableCount), 2)
    } else {
        $null
    }

    $writableWorkersPerDeliverable = if ($requestedDeliverableCount -gt 0) {
        [math]::Round(($writableWorkers / [double]$requestedDeliverableCount), 2)
    } else {
        $null
    }

    return [ordered]@{
        measurement_mode = "structure_first"
        note = "Use reruns, parent burden, repair-loop shape, and worker-to-deliverable ratios as primary efficiency signals. Treat absolute token totals as secondary."
        execution_mode = $ExecutionMode
        total_workers = $totalWorkers
        succeeded_workers = $succeededWorkers
        failed_workers = $failedWorkers
        requested_deliverable_count = $requestedDeliverableCount
        workers_per_deliverable = $workersPerDeliverable
        writable_workers_per_deliverable = $writableWorkersPerDeliverable
        writable_workers = $writableWorkers
        read_only_workers = $readOnlyWorkers
        implementer_workers = $implementerWorkers
        reviewer_workers = $reviewerWorkers
        validator_workers = $validatorWorkers
        fixer_workers = $fixerWorkers
        full_auto_writable_workers = $fullAutoWritableWorkers
        full_auto_read_only_workers = $fullAutoReadOnlyWorkers
        stage_count = $stageCount
        parallel_stage_count = $parallelStageCount
        max_parallel_workers_in_stage = $maxParallelWorkersInStage
        uses_parallel_execution = ($ExecutionMode -eq "parallel")
        uses_supervisor_only_policy = [bool]$PolicyEvaluation.supervisor_only
        uses_bounded_repair_policy = ($PolicyEvaluation.material_issue_strategy -eq "fixer_then_rereview")
        final_read_only_review_present = [bool]$PolicyEvaluation.final_read_only_review_present
        total_prompt_chars = $promptCharsTotal
        total_footer_tokens = $footerTokensTotal
    }
}

function Get-StagePlan {
    param($Runs)

    $plan = @()
    foreach ($group in @($Runs | Group-Object -Property stage | Sort-Object { [int]$_.Name })) {
        $groupRuns = @($group.Group | Sort-Object original_index)
        $plan += [pscustomobject]@{
            stage = [int]$group.Name
            worker_count = @($groupRuns).Count
            worker_names = [string[]]@($groupRuns | ForEach-Object { $_.name })
            worker_kinds = [string[]]@($groupRuns | ForEach-Object { $_.worker_kind })
            read_only_workers = [string[]]@($groupRuns | Where-Object { $_.is_read_only } | ForEach-Object { $_.name })
            writable_workers = [string[]]@($groupRuns | Where-Object { -not $_.is_read_only } | ForEach-Object { $_.name })
        }
    }

    return @($plan)
}

function New-RunSummaryText {
    param(
        [string]$WorkspaceRoot,
        [string]$ExecutionMode,
        $SharedDirectiveInfo,
        $PersonaGuideInfo,
        $WorkflowInfo,
        $AfterCreateHookResult,
        $Results,
        [string]$ManifestPath,
        $PolicyEvaluation,
        $ArchiveInfo,
        $EfficiencySignals,
        $MemoryMetrics
    )

    $lines = New-Object System.Collections.Generic.List[string]
    $successCount = @($Results | Where-Object { $_.succeeded }).Count
    $totalCount = @($Results).Count
    $promptCharsMeasure = $Results | Measure-Object -Property prompt_chars -Sum
    $promptCharsTotal = if ($null -ne $promptCharsMeasure -and $null -ne $promptCharsMeasure.Sum) {
        [int]$promptCharsMeasure.Sum
    } else {
        0
    }

    $footerTokenResults = @($Results | Where-Object { $null -ne $_.footer_tokens_used })
    $footerTokensTotal = if (@($footerTokenResults).Count -gt 0) {
        $footerTokensMeasure = $footerTokenResults | Measure-Object -Property footer_tokens_used -Sum
        [int]$footerTokensMeasure.Sum
    } else {
        0
    }

    $lines.Add("# Orchestration Summary")
    $lines.Add("")
    $lines.Add([string]::Format('- workspace_root: `{0}`', $WorkspaceRoot))
    $lines.Add([string]::Format('- execution_mode: {0}', $ExecutionMode))
    $lines.Add([string]::Format('- workers_succeeded: {0}/{1}', $successCount, $totalCount))
    $lines.Add([string]::Format('- shared_directive_mode: {0}', $SharedDirectiveInfo.effective_mode))
    if ($SharedDirectiveInfo.effective_mode -eq "hybrid") {
        $lines.Add([string]::Format('- shared_directive_chars: {0} -> per-worker (implementer/fixer=full; reviewer/validator/planner/read-only custom=compact)', $SharedDirectiveInfo.original_char_count))
    } else {
        $lines.Add([string]::Format('- shared_directive_chars: {0} -> {1}', $SharedDirectiveInfo.original_char_count, $SharedDirectiveInfo.effective_char_count))
    }
    $lines.Add([string]::Format('- persona_guide_mode: {0}', $PersonaGuideInfo.effective_mode))
    if ($PersonaGuideInfo.effective_mode -eq "disabled") {
        $lines.Add('- persona_guide_chars: 0')
    } else {
        $lines.Add([string]::Format('- persona_guide_chars: {0} -> {1}', $PersonaGuideInfo.original_char_count, $PersonaGuideInfo.effective_char_count))
    }
    if ($WorkflowInfo -and $WorkflowInfo.enabled) {
        $lines.Add([string]::Format('- workflow_file: `{0}`', $WorkflowInfo.source))
        $lines.Add([string]::Format('- workflow_prompt_mode: {0}', $WorkflowInfo.prompt_mode))
    }
    if ($AfterCreateHookResult -and $AfterCreateHookResult.enabled) {
        $lines.Add([string]::Format('- workspace_bootstrap_ran: {0}', $AfterCreateHookResult.ran))
        if ($AfterCreateHookResult.ran) {
            $lines.Add([string]::Format('- workspace_bootstrap_exit_code: {0}', $AfterCreateHookResult.exit_code))
            $lines.Add([string]::Format('- workspace_bootstrap_trigger: {0}', $AfterCreateHookResult.trigger))
        }
    }
    $lines.Add([string]::Format('- total_prompt_chars: {0}', $promptCharsTotal))
    $lines.Add([string]::Format('- total_footer_tokens: {0}', $footerTokensTotal))
    $lines.Add([string]::Format('- supervisor_only: {0}', $PolicyEvaluation.supervisor_only))
    $lines.Add([string]::Format('- require_final_read_only_review: {0}', $PolicyEvaluation.require_final_read_only_review))
    $lines.Add([string]::Format('- material_issue_strategy: {0}', $PolicyEvaluation.material_issue_strategy))
    $lines.Add([string]::Format('- final_read_only_review_present: {0}', $PolicyEvaluation.final_read_only_review_present))
    $lines.Add([string]::Format('- efficiency_measurement: {0}', $EfficiencySignals.measurement_mode))
    $lines.Add([string]::Format('- requested_deliverable_count: {0}', $EfficiencySignals.requested_deliverable_count))
    $lines.Add([string]::Format('- workers_per_deliverable: {0}', $(if ($null -ne $EfficiencySignals.workers_per_deliverable) { $EfficiencySignals.workers_per_deliverable } else { "n/a" })))
    $lines.Add([string]::Format('- writable_workers_per_deliverable: {0}', $(if ($null -ne $EfficiencySignals.writable_workers_per_deliverable) { $EfficiencySignals.writable_workers_per_deliverable } else { "n/a" })))
    $lines.Add([string]::Format('- worker_shape: writable={0}, read_only={1}, implementer={2}, reviewer={3}, validator={4}, fixer={5}', $EfficiencySignals.writable_workers, $EfficiencySignals.read_only_workers, $EfficiencySignals.implementer_workers, $EfficiencySignals.reviewer_workers, $EfficiencySignals.validator_workers, $EfficiencySignals.fixer_workers))
    $lines.Add([string]::Format('- full_auto_split: writable={0}, read_only={1}', $EfficiencySignals.full_auto_writable_workers, $EfficiencySignals.full_auto_read_only_workers))
    $lines.Add([string]::Format('- stage_shape: total={0}, parallel_stages={1}, max_parallel_workers_in_stage={2}', $EfficiencySignals.stage_count, $EfficiencySignals.parallel_stage_count, $EfficiencySignals.max_parallel_workers_in_stage))
    $lines.Add([string]::Format('- efficiency_note: {0}', $EfficiencySignals.note))
    if ($MemoryMetrics) {
        $lines.Add([string]::Format('- memory_configured: {0}', $MemoryMetrics.configured))
        $lines.Add([string]::Format('- memory_enabled: {0}', $MemoryMetrics.enabled))
        $lines.Add([string]::Format('- memory_active: {0}', $MemoryMetrics.active))
        $lines.Add([string]::Format('- memory_mode: {0}', $MemoryMetrics.mode))
        if ($MemoryMetrics.relative_root) {
            $lines.Add([string]::Format('- memory_root: `{0}`', $MemoryMetrics.relative_root))
        }
        $lines.Add([string]::Format('- memory_runtime_files: {0}', $MemoryMetrics.runtime_files_written))
        $lines.Add([string]::Format('- memory_inbox_entries_written: {0}', $MemoryMetrics.inbox_entries_written))
        $lines.Add([string]::Format('- memory_daily_entries_written: {0}', $MemoryMetrics.daily_entries_written))
        $lines.Add([string]::Format('- memory_optimize_ran: {0}', $MemoryMetrics.optimize_ran))
        $lines.Add([string]::Format('- memory_promoted_entries: {0}', $MemoryMetrics.promoted_entries))
        $lines.Add([string]::Format('- memory_pruned_entries: {0}', $MemoryMetrics.pruned_entries))
        $lines.Add([string]::Format('- memory_index_chunk_count: {0}', $MemoryMetrics.index_chunk_count))
    }
    $lines.Add([string]::Format('- manifest: `{0}`', $ManifestPath))
    if ($ArchiveInfo -and $ArchiveInfo.enabled) {
        $lines.Add([string]::Format('- archive_run_directory: `{0}`', $ArchiveInfo.run_directory))
        $lines.Add([string]::Format('- archive_workers_directory: `{0}`', $ArchiveInfo.workers_directory))
    }
    if (@($PolicyEvaluation.requested_deliverables).Count -gt 0) {
        $lines.Add([string]::Format('- requested_deliverables: {0}', ($PolicyEvaluation.requested_deliverables -join ", ")))
    }
    $lines.Add("")
    $lines.Add("## Workers")
    $lines.Add("")

    foreach ($result in $Results) {
        $status = if ($result.succeeded) { "ok" } else { "failed" }
        $footerValue = if ($null -ne $result.footer_tokens_used) { $result.footer_tokens_used } else { "n/a" }
        $lines.Add([string]::Format('- `{0}`: {1}; stage={2}; kind={3}; read_only={4}; full_auto={5}; model={6}; sandbox={7}; reasoning={8}; prompt_chars={9}; footer_tokens={10}; workflow_mode={11}',
                $result.name,
                $status,
                $result.stage,
                $result.worker_kind,
                $result.is_read_only,
                $result.requested_full_auto,
                $result.actual_model,
                $result.actual_sandbox,
                $result.actual_reasoning_effort,
                $result.prompt_chars,
                $footerValue,
                $result.workflow_prompt_mode))
        if ($null -ne $result.memory_mode -and $result.memory_mode -ne "off") {
            $lines.Add(("  memory: mode={0}; snippets={1}; chars={2}; file={3}" -f $result.memory_mode, $result.memory_snippet_count, $result.memory_injected_chars, $result.memory_context_file))
        }

        if (-not [string]::IsNullOrWhiteSpace($result.last_message_preview)) {
            $lines.Add(("  preview: {0}" -f $result.last_message_preview))
        }

        if (@($result.validation_failures).Count -gt 0) {
            foreach ($failure in @($result.validation_failures)) {
                $lines.Add(("  validation: {0}" -f $failure))
            }
        }
    }

    return ($lines -join [Environment]::NewLine)
}

function Get-ExecutionMetadata {
    param(
        [string]$StdoutPath,
        [string]$StderrPath
    )

    $metadata = [ordered]@{
        session_id = $null
        actual_workdir = $null
        actual_model = $null
        actual_approval = $null
        actual_sandbox = $null
        actual_reasoning_effort = $null
        footer_tokens_used = $null
        output_mode = $null
    }

    $stdoutLines = if (Test-Path -LiteralPath $StdoutPath) { @(Get-Content -LiteralPath $StdoutPath) } else { @() }
    $stderrLines = if (Test-Path -LiteralPath $StderrPath) { @(Get-Content -LiteralPath $StderrPath) } else { @() }

    if (@($stdoutLines).Count -eq 0 -and @($stderrLines).Count -eq 0) {
        return [pscustomobject]$metadata
    }

    $parsedJson = $false

    foreach ($line in $stdoutLines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        try {
            $entry = $line | ConvertFrom-Json -ErrorAction Stop
            $parsedJson = $true

            if ($entry.type -eq "session_meta") {
                $metadata.session_id = Get-OptionalProperty $entry.payload "id"
                $metadata.actual_workdir = Get-OptionalProperty $entry.payload "cwd"
            }

            if ($entry.type -eq "turn_context") {
                $metadata.actual_workdir = Get-OptionalProperty $entry.payload "cwd"
                $metadata.actual_model = Get-OptionalProperty $entry.payload "model"
                $metadata.actual_approval = Get-OptionalProperty $entry.payload "approval_policy"

                $sandboxPolicy = Get-OptionalProperty $entry.payload "sandbox_policy"
                if ($sandboxPolicy) {
                    $metadata.actual_sandbox = Get-OptionalProperty $sandboxPolicy "type"
                }

                $metadata.actual_reasoning_effort = Get-OptionalProperty $entry.payload "effort"
            }

            if ($entry.type -eq "event_msg" -and (Get-OptionalProperty $entry.payload "type") -eq "token_count") {
                $info = Get-OptionalProperty $entry.payload "info"
                $totalUsage = Get-OptionalProperty $info "total_token_usage"
                if ($totalUsage) {
                    $metadata.footer_tokens_used = Get-OptionalProperty $totalUsage "total_tokens"
                }
            }
        } catch {
        }
    }

    if ($parsedJson) {
        $metadata.output_mode = "json"
        return [pscustomobject]$metadata
    }

    $metadata.output_mode = "text"
    foreach ($textLines in @($stderrLines, $stdoutLines)) {
        for ($index = 0; $index -lt @($textLines).Count; $index += 1) {
            $line = $textLines[$index]

            if ($null -eq $metadata.session_id -and $line -match '^session id:\s*(.+)$') {
                $metadata.session_id = $Matches[1].Trim()
                continue
            }

            if ($null -eq $metadata.actual_workdir -and $line -match '^workdir:\s*(.+)$') {
                $metadata.actual_workdir = $Matches[1].Trim()
                continue
            }

            if ($null -eq $metadata.actual_model -and $line -match '^model:\s*(.+)$') {
                $metadata.actual_model = $Matches[1].Trim()
                continue
            }

            if ($null -eq $metadata.actual_approval -and $line -match '^approval:\s*(.+)$') {
                $metadata.actual_approval = $Matches[1].Trim()
                continue
            }

            if ($null -eq $metadata.actual_sandbox -and $line -match '^sandbox:\s*(.+)$') {
                $metadata.actual_sandbox = $Matches[1].Trim()
                continue
            }

            if ($null -eq $metadata.actual_reasoning_effort -and $line -match '^reasoning effort:\s*(.+)$') {
                $metadata.actual_reasoning_effort = $Matches[1].Trim()
                continue
            }

            if ($null -eq $metadata.footer_tokens_used -and $line -eq "tokens used" -and $index + 1 -lt @($textLines).Count) {
                $tokenLine = $textLines[$index + 1].Trim() -replace ",", ""
                if ($tokenLine -match '^\d+$') {
                    $metadata.footer_tokens_used = [int]$tokenLine
                }
            }
        }
    }

    return [pscustomobject]$metadata
}

function Invoke-WorkerCommand {
    param(
        [string]$Executable,
        [string]$RunCwd,
        [string]$RunArgLine,
        [string]$StdoutPath,
        [string]$StderrPath
    )

    $stdoutDirectory = Split-Path -Parent $StdoutPath
    $stderrDirectory = Split-Path -Parent $StderrPath

    if (-not [string]::IsNullOrWhiteSpace($stdoutDirectory)) {
        New-Item -ItemType Directory -Path $stdoutDirectory -Force | Out-Null
    }

    if (-not [string]::IsNullOrWhiteSpace($stderrDirectory)) {
        New-Item -ItemType Directory -Path $stderrDirectory -Force | Out-Null
    }

    try {
        $process = Start-Process `
            -FilePath $Executable `
            -ArgumentList $RunArgLine `
            -WorkingDirectory $RunCwd `
            -RedirectStandardOutput $StdoutPath `
            -RedirectStandardError $StderrPath `
            -PassThru `
            -Wait `
            -NoNewWindow
        $exitCode = [int]$process.ExitCode
    } catch {
        $message = $_ | Out-String
        Add-Content -LiteralPath $StderrPath -Value $message -Encoding utf8
        $exitCode = -1
    }

    return [pscustomobject]@{
        exit_code = $exitCode
    }
}

function Invoke-ParallelRunBatch {
    param(
        $Runs,
        [string]$ResolvedCodexExecutable,
        [int]$TimeoutSeconds,
        [string]$StageLabel
    )

    $results = @()
    $processRuns = @()

    foreach ($run in $Runs) {
        $stdoutDirectory = Split-Path -Parent $run.stdout
        $stderrDirectory = Split-Path -Parent $run.stderr
        if (-not [string]::IsNullOrWhiteSpace($stdoutDirectory)) {
            New-Item -ItemType Directory -Path $stdoutDirectory -Force | Out-Null
        }
        if (-not [string]::IsNullOrWhiteSpace($stderrDirectory)) {
            New-Item -ItemType Directory -Path $stderrDirectory -Force | Out-Null
        }

        try {
            $process = Start-Process `
                -FilePath $ResolvedCodexExecutable `
                -ArgumentList $run.arg_line `
                -WorkingDirectory $run.cwd `
                -RedirectStandardOutput $run.stdout `
                -RedirectStandardError $run.stderr `
                -PassThru `
                -NoNewWindow
            Write-LauncherDebug ("started_process stage={0} name={1} pid={2}" -f $StageLabel, $run.name, $process.Id)
        } catch {
            $message = $_ | Out-String
            Add-Content -LiteralPath $run.stderr -Value $message -Encoding utf8
            Write-LauncherDebug ("start_failed stage={0} name={1} error={2}" -f $StageLabel, $run.name, ($message.Trim()))
            $results += Complete-WorkerResult -Run $run -ExitCode -1
            continue
        }

        $processRuns += [pscustomobject]@{
            run = $run
            process = $process
        }
    }

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while (@($processRuns | Where-Object { -not $_.process.HasExited }).Count -gt 0) {
        if ($TimeoutSeconds -gt 0 -and $stopwatch.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
            Write-LauncherDebug ("timeout_reached stage={0} seconds={1}" -f $StageLabel, $TimeoutSeconds)
            foreach ($processRun in @($processRuns | Where-Object { -not $_.process.HasExited })) {
                try {
                    Stop-Process -Id $processRun.process.Id -Force -ErrorAction Stop
                    Write-LauncherDebug ("stopped_process stage={0} pid={1}" -f $StageLabel, $processRun.process.Id)
                } catch {
                }
            }
            break
        }

        Start-Sleep -Milliseconds 500
    }
    $stopwatch.Stop()

    foreach ($processRun in $processRuns) {
        $exitCode = if ($processRun.process.HasExited) { [int]$processRun.process.ExitCode } else { -1 }
        Write-LauncherDebug ("collecting_result stage={0} name={1} exit_code={2}" -f $StageLabel, $processRun.run.name, $exitCode)
        $results += Complete-WorkerResult -Run $processRun.run -ExitCode $exitCode
        $processRun.process.Dispose()
    }

    return @($results)
}

function Complete-WorkerResult {
    param(
        $Run,
        [int]$ExitCode
    )

    $stdoutText = Get-FileTextSafe -Path $Run.stdout
    $stderrText = Get-FileTextSafe -Path $Run.stderr
    $lastText = Get-FileTextSafe -Path $Run.last
    $executionMetadata = Get-ExecutionMetadata -StdoutPath $Run.stdout -StderrPath $Run.stderr
    $requiredPathCheck = Test-WorkerRequiredPaths -Run $Run

    $validationFailures = New-Object System.Collections.Generic.List[string]
    foreach ($missingPath in @($requiredPathCheck.missing_paths)) {
        $validationFailures.Add("missing required path: $missingPath")
    }
    foreach ($emptyPath in @($requiredPathCheck.empty_paths)) {
        $validationFailures.Add("required path is empty: $emptyPath")
    }

    $succeeded = ($ExitCode -eq 0 -and $requiredPathCheck.passed)

    return [pscustomobject]@{
        name = $Run.name
        mode = $Run.mode
        stage = $Run.stage
        worker_kind = $Run.worker_kind
        is_read_only = $Run.is_read_only
        cwd = $Run.cwd
        exit_code = $ExitCode
        succeeded = $succeeded
        required_paths = [string[]]$Run.required_paths
        required_non_empty_paths = [string[]]$Run.required_non_empty_paths
        missing_required_paths = [string[]]$requiredPathCheck.missing_paths
        empty_required_paths = [string[]]$requiredPathCheck.empty_paths
        validation_failures = [string[]]$validationFailures.ToArray()
        requested_model = $Run.requested_model
        requested_full_auto = $Run.requested_full_auto
        actual_model = $executionMetadata.actual_model
        requested_sandbox = $Run.requested_sandbox
        actual_sandbox = $executionMetadata.actual_sandbox
        requested_reasoning_effort = $Run.requested_reasoning_effort
        actual_reasoning_effort = $executionMetadata.actual_reasoning_effort
        prompt_profile = $Run.prompt_profile
        response_style = $Run.response_style
        max_response_lines = $Run.max_response_lines
        requested_shared_directive_mode = $Run.requested_shared_directive_mode
        effective_shared_directive_mode = $Run.effective_shared_directive_mode
        shared_directive_chars = $Run.shared_directive_chars
        requested_persona_guide_mode = $Run.requested_persona_guide_mode
        effective_persona_guide_mode = $Run.effective_persona_guide_mode
        persona_guide_chars = $Run.persona_guide_chars
        persona_role_frame = $Run.persona_role_frame
        persona_domain_ids = [string[]]$Run.persona_domain_ids
        actual_approval = $executionMetadata.actual_approval
        actual_workdir = $executionMetadata.actual_workdir
        output_mode = $executionMetadata.output_mode
        session_id = $executionMetadata.session_id
        footer_tokens_used = $executionMetadata.footer_tokens_used
        stdout = $Run.stdout
        stderr = $Run.stderr
        last = $Run.last
        prompt = $Run.prompt
        prompt_sha256 = $Run.prompt_sha256
        prompt_chars = $Run.prompt_chars
        workflow_prompt_mode = $Run.workflow_prompt_mode
        workflow_prompt_chars = $Run.workflow_prompt_chars
        memory_mode = $Run.memory_mode
        memory_query = $Run.memory_query
        memory_context_file = $Run.memory_context_file
        memory_snippet_count = $Run.memory_snippet_count
        memory_injected_chars = $Run.memory_injected_chars
        memory_hit_paths = [string[]]$Run.memory_hit_paths
        command = $Run.command
        last_exists = (Test-Path -LiteralPath $Run.last)
        last_message_preview = Get-PreviewText -Text $lastText
        stderr_preview = Get-PreviewText -Text $stderrText
        stdout_preview = Get-PreviewText -Text $stdoutText
    }
}

if (-not (Test-Path -LiteralPath $SpecPath)) {
    throw "Spec file not found: $SpecPath"
}

$specPathResolved = Resolve-AbsolutePath -Path $SpecPath -BaseDirectory (Get-Location).Path
$specDirectory = Split-Path -Parent $specPathResolved
$specText = Get-Content -LiteralPath $specPathResolved -Raw
$spec = $specText | ConvertFrom-Json

if (-not $spec.cwd) {
    throw "Spec must define 'cwd'."
}

if (-not $spec.agents -or @($spec.agents).Count -lt 1) {
    throw "Spec must define a non-empty 'agents' array."
}

$invocationCwd = (Get-Location).Path
$cwdResolutionMode = Get-NormalizedChoice `
    -Primary (Get-OptionalProperty $spec "cwd_resolution") `
    -Fallback $null `
    -Default "invocation" `
    -AllowedValues @("invocation", "spec") `
    -FieldName "cwd_resolution"
$cwdBaseDirectory = if ($cwdResolutionMode -eq "spec") {
    $specDirectory
} else {
    $invocationCwd
}
$cwd = Resolve-AbsolutePath -Path ([string]$spec.cwd) -BaseDirectory $cwdBaseDirectory
$outputDirValue = Get-OptionalProperty $spec "output_dir"
$outputDir = if ($outputDirValue) {
    Resolve-AbsolutePath -Path ([string]$outputDirValue) -BaseDirectory $cwd -AllowMissing
} else {
    Resolve-AbsolutePath -Path "subagent-runs" -BaseDirectory $cwd -AllowMissing
}
$debugLogValue = Get-OptionalProperty $spec "debug_log_file"
$debugLogFile = if ($debugLogValue) {
    Resolve-AbsolutePath -Path ([string]$debugLogValue) -BaseDirectory $cwd -AllowMissing
} else {
    $null
}
$manifestFileValue = Get-OptionalProperty $spec "manifest_file"
$manifestFile = if ($manifestFileValue) {
    Resolve-AbsolutePath -Path ([string]$manifestFileValue) -BaseDirectory $cwd -AllowMissing
} else {
    Resolve-AbsolutePath -Path (Join-Path $outputDir "orchestration-manifest.json") -BaseDirectory $cwd -AllowMissing
}
$summaryFileValue = Get-OptionalProperty $spec "summary_file"
$summaryFile = if ($summaryFileValue) {
    Resolve-AbsolutePath -Path ([string]$summaryFileValue) -BaseDirectory $cwd -AllowMissing
} else {
    Resolve-AbsolutePath -Path (Join-Path $outputDir "orchestration-summary.md") -BaseDirectory $cwd -AllowMissing
}
$archiveRootValue = Get-OptionalProperty $spec "archive_root"
$archiveRoot = if ($archiveRootValue) {
    Resolve-AbsolutePath -Path ([string]$archiveRootValue) -BaseDirectory $cwd -AllowMissing
} else {
    Resolve-AbsolutePath -Path "subagent-records" -BaseDirectory $cwd -AllowMissing
}
$writeRunArchive = Get-BoolValue (Get-OptionalProperty $spec "write_run_archive") $true
$archiveRunLabelValue = Get-OptionalProperty $spec "archive_run_label"
$archiveRunLabel = if ($archiveRunLabelValue) {
    [string]$archiveRunLabelValue
} elseif (-not [string]::IsNullOrWhiteSpace((Split-Path -Leaf $outputDir))) {
    Split-Path -Leaf $outputDir
} else {
    [System.IO.Path]::GetFileNameWithoutExtension($specPathResolved)
}
$archiveInfo = New-RunArchiveInfo -WriteRunArchive $writeRunArchive -ArchiveRoot $archiveRoot -RunLabel $archiveRunLabel
$skipGit = Get-BoolValue (Get-OptionalProperty $spec "skip_git_repo_check") $false
$defaults = Get-OptionalProperty $spec "defaults"
$executionModeValue = Get-OptionalProperty $spec "execution_mode"
$executionMode = if ($executionModeValue) { ([string]$executionModeValue).ToLowerInvariant() } else { "parallel" }
$writePromptFiles = Get-BoolValue (Get-OptionalProperty $spec "write_prompt_files") $true
$writeSummaryFile = Get-BoolValue (Get-OptionalProperty $spec "write_summary_file") $true
$timeoutSecondsValue = Get-OptionalProperty $spec "timeout_seconds"
$timeoutSeconds = if ($timeoutSecondsValue) { [int]$timeoutSecondsValue } else { 0 }
$requestedDeliverables = Get-StringList (Get-OptionalProperty $spec "requested_deliverables")
$supervisorOnly = Get-BoolValue (Get-OptionalProperty $spec "supervisor_only") $false
$requireFinalReadOnlyReview = Get-BoolValue (Get-OptionalProperty $spec "require_final_read_only_review") $supervisorOnly
$materialIssueStrategy = Get-NormalizedChoice `
    -Primary (Get-OptionalProperty $spec "material_issue_strategy") `
    -Fallback $null `
    -Default $(if ($supervisorOnly) { "fixer_then_rereview" } else { "none" }) `
    -AllowedValues @("none", "fixer_then_rereview") `
    -FieldName "material_issue_strategy"
$resolvedCodexExecutable = Resolve-CommandPath -Executable $CodexExecutable
$specHash = Get-TextHash -Text $specText

if ($executionMode -notin @("parallel", "sequential")) {
    throw "Spec execution_mode must be 'parallel' or 'sequential'."
}

New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
$afterCreateHookInfo = Get-AfterCreateHookInfo -Spec $spec -WorkspaceRoot $cwd -OutputDir $outputDir
$afterCreateHookResult = [pscustomobject]@{
    enabled = [bool]$afterCreateHookInfo.enabled
    ran = $false
    trigger = $null
    exit_code = $null
    missing_sentinel_paths = @()
    workspace_was_empty = $false
    stdout = $afterCreateHookInfo.stdout
    stderr = $afterCreateHookInfo.stderr
}

if ($debugLogFile) {
    $debugDirectory = Split-Path -Parent $debugLogFile
    if (-not [string]::IsNullOrWhiteSpace($debugDirectory)) {
        New-Item -ItemType Directory -Path $debugDirectory -Force | Out-Null
    }
    $script:LauncherDebugPath = $debugLogFile
    Set-Content -LiteralPath $debugLogFile -Value "" -Encoding utf8
    Write-LauncherDebug "launcher started"
    Write-LauncherDebug ("invocation_cwd={0}" -f $invocationCwd)
    Write-LauncherDebug ("spec_directory={0}" -f $specDirectory)
    Write-LauncherDebug ("cwd_requested={0}" -f ([string]$spec.cwd))
    Write-LauncherDebug ("cwd_resolution_mode={0}" -f $cwdResolutionMode)
    Write-LauncherDebug ("cwd_resolution_base={0}" -f $cwdBaseDirectory)
    Write-LauncherDebug ("workspace_root={0}" -f $cwd)
    Write-LauncherDebug ("execution_mode={0}" -f $executionMode)
    if ($afterCreateHookInfo.enabled) {
        Write-LauncherDebug "after_create_hook_configured=True"
    }
    Write-LauncherDebug ("write_run_archive={0}" -f $writeRunArchive)
    if ($archiveInfo.enabled) {
        Write-LauncherDebug ("archive_root={0}" -f $archiveInfo.root)
        Write-LauncherDebug ("archive_run_directory={0}" -f $archiveInfo.run_directory)
    }
}

if ($afterCreateHookInfo.enabled) {
    $missingSentinelPaths = New-Object System.Collections.Generic.List[string]
    foreach ($sentinelPath in @($afterCreateHookInfo.sentinel_paths)) {
        if (-not (Test-Path -LiteralPath $sentinelPath)) {
            $missingSentinelPaths.Add([string]$sentinelPath)
        }
    }

    $workspaceWasEmpty = $false
    if ($afterCreateHookInfo.if_workspace_empty) {
        $workspaceWasEmpty = Test-DirectoryIsEmpty -Path $cwd
    }

    $triggerReasons = New-Object System.Collections.Generic.List[string]
    if (@($missingSentinelPaths).Count -gt 0) {
        $triggerReasons.Add("missing_sentinel_paths")
    }
    if ($workspaceWasEmpty) {
        $triggerReasons.Add("workspace_empty")
    }

    $afterCreateHookResult = [pscustomobject]@{
        enabled = $true
        ran = (@($triggerReasons).Count -gt 0)
        trigger = if (@($triggerReasons).Count -gt 0) { @($triggerReasons) -join "," } else { "skipped" }
        exit_code = $null
        missing_sentinel_paths = [string[]]$missingSentinelPaths.ToArray()
        workspace_was_empty = $workspaceWasEmpty
        stdout = $afterCreateHookInfo.stdout
        stderr = $afterCreateHookInfo.stderr
    }

    Write-LauncherDebug ("after_create_hook_evaluated ran={0} trigger={1}" -f $afterCreateHookResult.ran, $afterCreateHookResult.trigger)
    if ($afterCreateHookResult.ran) {
        $hookRun = Invoke-PowerShellHook `
            -Command $afterCreateHookInfo.command `
            -RunCwd $cwd `
            -StdoutPath $afterCreateHookInfo.stdout `
            -StderrPath $afterCreateHookInfo.stderr
        $afterCreateHookResult.exit_code = [int]$hookRun.exit_code
        Write-LauncherDebug ("after_create_hook_exit_code={0}" -f $hookRun.exit_code)
        if ($hookRun.exit_code -ne 0) {
            throw "hooks.after_create failed with exit code $($hookRun.exit_code). See: $($hookRun.stderr)"
        }
    }
}

$memoryConfig = Get-MemoryConfig -Spec $spec -WorkspaceRoot $cwd
$memoryInitResult = $null
if ($memoryConfig.active) {
    $memoryInitResult = Initialize-MemoryStore -MemoryConfig $memoryConfig
}
if ($memoryConfig.configured) {
    Write-LauncherDebug ("memory_configured={0}" -f $memoryConfig.configured)
    Write-LauncherDebug ("memory_enabled={0}" -f $memoryConfig.enabled)
    Write-LauncherDebug ("memory_active={0}" -f $memoryConfig.active)
    Write-LauncherDebug ("memory_mode={0}" -f $memoryConfig.mode)
    if ($memoryConfig.root) {
        Write-LauncherDebug ("memory_root={0}" -f $memoryConfig.root)
    }
}

$sharedDirectiveInfo = Get-SharedDirectiveInfo -Spec $spec -WorkspaceRoot $cwd -SpecDirectory $specDirectory
$personaGuideInfo = Get-PersonaGuideInfo -Spec $spec -SpecDirectory $specDirectory
$workflowInfo = Get-WorkflowInfo -Spec $spec -WorkspaceRoot $cwd -SpecDirectory $specDirectory
Write-LauncherDebug ("shared_directive_source={0}" -f $sharedDirectiveInfo.source)
Write-LauncherDebug ("shared_directive_mode={0}" -f $sharedDirectiveInfo.effective_mode)
Write-LauncherDebug ("persona_guide_source={0}" -f $personaGuideInfo.source)
Write-LauncherDebug ("persona_guide_mode={0}" -f $personaGuideInfo.effective_mode)
if ($workflowInfo.enabled) {
    Write-LauncherDebug ("workflow_file={0}" -f $workflowInfo.source)
    Write-LauncherDebug ("workflow_prompt_mode={0}" -f $workflowInfo.prompt_mode)
    Write-LauncherDebug ("workflow_auto_detected={0}" -f $workflowInfo.auto_detected)
}

$runs = @()
$memoryWorkerContextInfos = @()

foreach ($agent in $spec.agents) {
    if (-not $agent.name) {
        throw "Each agent must define 'name'."
    }

    if (-not (Get-OptionalProperty $agent "prompt") -and -not (Get-OptionalProperty $agent "task")) {
        throw "Each agent must define either 'prompt' or 'task'."
    }

    $name = [string]$agent.name
    $originalIndex = $runs.Count
    $workerKind = Get-WorkerKind -Agent $agent
    $modeValue = Get-OptionalProperty $agent "mode"
    $mode = if ($modeValue) { ([string]$modeValue).ToLowerInvariant() } else { "exec" }
    if ($mode -notin @("exec", "resume")) {
        throw "Unsupported mode '$mode' for agent '$name'."
    }

    $workerCwdValue = Get-OptionalProperty $agent "cwd"
    $workerCwd = if ($workerCwdValue) {
        Resolve-AbsolutePath -Path ([string]$workerCwdValue) -BaseDirectory $cwd
    } else {
        $cwd
    }

    $stdoutPath = Resolve-AbsolutePath -Path (Join-Path $outputDir "$name.stdout.log") -BaseDirectory $outputDir -AllowMissing
    $stderrPath = Resolve-AbsolutePath -Path (Join-Path $outputDir "$name.stderr.log") -BaseDirectory $outputDir -AllowMissing
    $promptPath = Resolve-AbsolutePath -Path (Join-Path $outputDir "$name.prompt.txt") -BaseDirectory $outputDir -AllowMissing

    $lastPathValue = Get-OptionalProperty $agent "output_last_message_file"
    $lastPath = if ($lastPathValue) {
        Resolve-AbsolutePath -Path ([string]$lastPathValue) -BaseDirectory $outputDir -AllowMissing
    } else {
        Resolve-AbsolutePath -Path (Join-Path $outputDir "$name.last.txt") -BaseDirectory $outputDir -AllowMissing
    }
    $requiredPathsValue = Get-OptionalProperty $agent "required_paths"
    if (-not $requiredPathsValue) {
        $requiredPathsValue = Get-OptionalProperty $agent "required_outputs"
    }
    $requiredPaths = @(
        Get-UniqueStringList $requiredPathsValue |
            ForEach-Object { Resolve-AbsolutePath -Path $_ -BaseDirectory $workerCwd -AllowMissing }
    )
    $requiredNonEmptyPathsValue = Get-OptionalProperty $agent "required_non_empty_paths"
    if (-not $requiredNonEmptyPathsValue) {
        $requiredNonEmptyPathsValue = Get-OptionalProperty $agent "required_non_empty_outputs"
    }
    $requiredNonEmptyPaths = @(
        Get-UniqueStringList $requiredNonEmptyPathsValue |
            ForEach-Object { Resolve-AbsolutePath -Path $_ -BaseDirectory $workerCwd -AllowMissing }
    )
    $stage = Get-AgentStage -Agent $agent -ExecutionMode $executionMode -DefaultStage ($originalIndex + 1)

    $promptProfile = Get-NormalizedChoice `
        -Primary (Get-OptionalProperty $agent "prompt_profile") `
        -Fallback (Get-OptionalProperty $defaults "prompt_profile") `
        -Default "full" `
        -AllowedValues @("full", "compact") `
        -FieldName "prompt_profile"
    $responseStyleDefault = if ($promptProfile -eq "compact") { "compact" } else { "standard" }
    $responseStyle = Get-NormalizedChoice `
        -Primary (Get-OptionalProperty $agent "response_style") `
        -Fallback (Get-OptionalProperty $defaults "response_style") `
        -Default $responseStyleDefault `
        -AllowedValues @("standard", "compact") `
        -FieldName "response_style"
    $maxResponseLinesValue = Get-OptionalProperty $agent "max_response_lines"
    if ($null -eq $maxResponseLinesValue) {
        $maxResponseLinesValue = Get-OptionalProperty $defaults "max_response_lines"
    }
    $maxResponseLines = if ($null -ne $maxResponseLinesValue) {
        [int]$maxResponseLinesValue
    } elseif ($responseStyle -eq "compact") {
        4
    } else {
        0
    }

    $sandboxValue = Get-OptionalProperty $agent "sandbox"
    if (-not $sandboxValue) {
        $sandboxValue = Get-OptionalProperty $defaults "sandbox"
    }
    $sandbox = if ($sandboxValue) { [string]$sandboxValue } else { $null }
    $isReadOnly = Test-IsReadOnlySandbox -Sandbox $sandbox

    $workerSharedDirectiveInfo = Get-WorkerSharedDirectiveInfo `
        -SharedDirectiveInfo $sharedDirectiveInfo `
        -Agent $agent `
        -WorkerKind $workerKind `
        -IsReadOnly $isReadOnly
    $workerPersonaGuideInfo = Get-WorkerPersonaGuideInfo `
        -PersonaGuideInfo $personaGuideInfo `
        -Agent $agent `
        -WorkerKind $workerKind `
        -IsReadOnly $isReadOnly

    $workflowRenderInfo = Get-AgentWorkflowRenderInfo `
        -WorkflowInfo $workflowInfo `
        -Agent $agent `
        -WorkerName $name `
        -WorkerKind $workerKind `
        -Stage $stage `
        -WorkerCwd $workerCwd `
        -WorkspaceRoot $cwd
    $workerMemoryMode = Get-WorkerMemoryMode `
        -Agent $agent `
        -WorkerKind $workerKind `
        -IsReadOnly $isReadOnly `
        -MemoryConfig $memoryConfig
    $memoryQuery = $null
    $memoryHits = @()
    $memoryContextInfo = [pscustomobject]@{
        enabled = $false
        exists = $false
        mode = $workerMemoryMode
        path = $null
        relative_path = $null
        snippet_count = 0
        injected_chars = 0
        hit_paths = @()
    }
    if ($memoryConfig.active -and $workerMemoryMode -ne "off") {
        $memoryQuery = Get-MemoryQueryText `
            -Agent $agent `
            -WorkerKind $workerKind `
            -RequestedDeliverables $requestedDeliverables `
            -WorkflowContext $workflowRenderInfo.context
        $memorySearchPaths = @(
            Get-StringList (Get-OptionalProperty $agent "read_first")
            Get-StringList (Get-OptionalProperty $agent "writable_scope")
            $requestedDeliverables
        ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        $memoryHits = Search-MemoryIndex `
            -MemoryConfig $memoryConfig `
            -QueryText $memoryQuery `
            -WorkerPaths $memorySearchPaths
        $selectedMemoryContext = Select-MemorySnippets `
            -MemoryConfig $memoryConfig `
            -Mode $workerMemoryMode `
            -Hits $memoryHits
        $memoryContextInfo = Write-WorkerMemoryContextFile `
            -MemoryConfig $memoryConfig `
            -WorkerName $name `
            -Mode $workerMemoryMode `
            -MemoryContext $selectedMemoryContext
    }
    $memoryWorkerContextInfos += [pscustomobject]@{
        worker = $name
        mode = $workerMemoryMode
        exists = [bool]$memoryContextInfo.exists
        relative_path = $memoryContextInfo.relative_path
        snippet_count = [int]$memoryContextInfo.snippet_count
        injected_chars = [int]$memoryContextInfo.injected_chars
        hit_paths = [string[]]$memoryContextInfo.hit_paths
    }
    $promptText = New-WorkerPrompt `
        -Agent $agent `
        -SharedDirectiveInfo $workerSharedDirectiveInfo `
        -PersonaGuideInfo $workerPersonaGuideInfo `
        -WorkflowRenderInfo $workflowRenderInfo `
        -PromptProfile $promptProfile `
        -ResponseStyle $responseStyle `
        -MaxResponseLines $maxResponseLines `
        -MemoryContextInfo $memoryContextInfo
    if ($writePromptFiles) {
        Set-Content -LiteralPath $promptPath -Value $promptText -Encoding utf8
    }

    $cmdArgs = New-Object System.Collections.Generic.List[string]
    $agentFullAutoValue = Get-OptionalProperty $agent "full_auto"
    $defaultFullAutoValue = Get-OptionalProperty $defaults "full_auto"
    if ($null -ne $agentFullAutoValue) {
        $useFullAuto = [bool]$agentFullAutoValue
    } elseif ($isReadOnly) {
        $useFullAuto = $false
    } elseif ($null -ne $defaultFullAutoValue) {
        $useFullAuto = [bool]$defaultFullAutoValue
    } else {
        $useFullAuto = ($mode -eq "exec")
    }

    if ($mode -eq "resume") {
        $cmdArgs.Add("resume")
        if (Get-BoolValue (Get-OptionalProperty $agent "resume_last") $false) {
            $cmdArgs.Add("--last")
        } else {
            $sessionIdValue = Get-OptionalProperty $agent "session_id"
            if ($sessionIdValue) {
                $cmdArgs.Add([string]$sessionIdValue)
            } else {
                throw "Resume agent '$name' must set either 'resume_last' or 'session_id'."
            }
        }
    } else {
        if ($useFullAuto) {
            $cmdArgs.Add("--full-auto")
        }
        $cmdArgs.Add("exec")
    }

    if ($skipGit) {
        $cmdArgs.Add("--skip-git-repo-check")
    }

    $cmdArgs.Add("-C")
    $cmdArgs.Add($workerCwd)

    if ($sandbox) {
        $cmdArgs.Add("-s")
        $cmdArgs.Add($sandbox)
    }

    $modelValue = Get-OptionalProperty $agent "model"
    if (-not $modelValue) {
        $modelValue = Get-OptionalProperty $defaults "model"
    }
    $model = if ($modelValue) { [string]$modelValue } else { $null }
    if ($model) {
        $cmdArgs.Add("-m")
        $cmdArgs.Add($model)
    }

    $reasoningValue = Get-OptionalProperty $agent "reasoning_effort"
    if (-not $reasoningValue) {
        $reasoningValue = Get-OptionalProperty $defaults "reasoning_effort"
    }
    $reasoning = if ($reasoningValue) { [string]$reasoningValue } else { $null }
    if ($reasoning) {
        $cmdArgs.Add("-c")
        $cmdArgs.Add("model_reasoning_effort=""$reasoning""")
    }

    if (Get-BoolValue (Get-OptionalProperty $agent "json") (Get-OptionalProperty $defaults "json")) {
        $cmdArgs.Add("--json")
    }

    $outputSchemaValue = Get-OptionalProperty $agent "output_schema"
    if (-not $outputSchemaValue) {
        $outputSchemaValue = Get-OptionalProperty $defaults "output_schema"
    }
    if ($outputSchemaValue) {
        $resolvedOutputSchema = Resolve-AbsolutePath -Path ([string]$outputSchemaValue) -BaseDirectory $workerCwd
        $cmdArgs.Add("--output-schema")
        $cmdArgs.Add($resolvedOutputSchema)
    }

    if (Get-BoolValue (Get-OptionalProperty $agent "ephemeral") (Get-OptionalProperty $defaults "ephemeral")) {
        $cmdArgs.Add("--ephemeral")
    }

    $cmdArgs.Add("-o")
    $cmdArgs.Add($lastPath)

    $extraArgsValue = Get-OptionalProperty $agent "extra_args"
    if ($extraArgsValue) {
        foreach ($extraArg in $extraArgsValue) {
            $cmdArgs.Add([string]$extraArg)
        }
    }

    $cmdArgs.Add($promptText)

    $runs += [pscustomobject]@{
        name = $name
        original_index = $originalIndex
        stage = $stage
        mode = $mode
        cwd = $workerCwd
        stdout = $stdoutPath
        stderr = $stderrPath
        last = $lastPath
        required_paths = [string[]]$requiredPaths
        required_non_empty_paths = [string[]]$requiredNonEmptyPaths
        prompt = $promptPath
        prompt_sha256 = Get-TextHash -Text $promptText
        prompt_chars = $promptText.Length
        worker_kind = $workerKind
        is_read_only = $isReadOnly
        requested_model = $model
        requested_full_auto = $useFullAuto
        requested_sandbox = $sandbox
        requested_reasoning_effort = $reasoning
        prompt_profile = $promptProfile
        response_style = $responseStyle
        max_response_lines = $maxResponseLines
        requested_shared_directive_mode = $sharedDirectiveInfo.requested_mode
        effective_shared_directive_mode = $workerSharedDirectiveInfo.effective_mode
        shared_directive_chars = $workerSharedDirectiveInfo.effective_char_count
        requested_persona_guide_mode = $personaGuideInfo.requested_mode
        effective_persona_guide_mode = $workerPersonaGuideInfo.effective_mode
        persona_guide_chars = $workerPersonaGuideInfo.effective_char_count
        persona_role_frame = $workerPersonaGuideInfo.role_frame
        persona_domain_ids = [string[]]$workerPersonaGuideInfo.domain_ids
        workflow_prompt_mode = $workflowRenderInfo.mode
        workflow_prompt_chars = if ($workflowRenderInfo.text) { $workflowRenderInfo.text.Length } else { 0 }
        memory_mode = $workerMemoryMode
        memory_query = $memoryQuery
        memory_context_file = $memoryContextInfo.relative_path
        memory_snippet_count = [int]$memoryContextInfo.snippet_count
        memory_injected_chars = [int]$memoryContextInfo.injected_chars
        memory_hit_paths = [string[]]$memoryContextInfo.hit_paths
        command = Join-ArgLine -Items (@($resolvedCodexExecutable) + $cmdArgs.ToArray())
        args = [string[]]$cmdArgs.ToArray()
        arg_line = Join-ArgLine -Items $cmdArgs.ToArray()
    }
}

$orderedRuns = @($runs | Sort-Object stage, original_index)
$stagePlan = Get-StagePlan -Runs $orderedRuns
$policyEvaluation = Assert-OrchestrationPolicy `
    -Runs $orderedRuns `
    -ExecutionMode $executionMode `
    -SupervisorOnly $supervisorOnly `
    -RequireFinalReadOnlyReview $requireFinalReadOnlyReview `
    -MaterialIssueStrategy $materialIssueStrategy `
    -RequestedDeliverables $requestedDeliverables

Write-LauncherDebug ("prepared_runs={0}" -f $orderedRuns.Count)
Write-LauncherDebug ("prepared_stages={0}" -f @($stagePlan).Count)

$results = @()

if ($executionMode -eq "parallel") {
    $runStages = @($orderedRuns | Group-Object -Property stage | Sort-Object { [int]$_.Name })
    foreach ($stageGroup in $runStages) {
        $stageRuns = @($stageGroup.Group | Sort-Object original_index)
        $stageLabel = [string]$stageGroup.Name
        Write-LauncherDebug ("running_parallel_stage stage={0} workers={1}" -f $stageLabel, (@($stageRuns | ForEach-Object { $_.name }) -join ", "))
        $results += Invoke-ParallelRunBatch `
            -Runs $stageRuns `
            -ResolvedCodexExecutable $resolvedCodexExecutable `
            -TimeoutSeconds $timeoutSeconds `
            -StageLabel $stageLabel
    }
} else {
    foreach ($run in $orderedRuns) {
        Write-LauncherDebug ("running_sequential stage={0} name={1}" -f $run.stage, $run.name)
        $runOutput = Invoke-WorkerCommand -Executable $resolvedCodexExecutable -RunCwd $run.cwd -RunArgLine $run.arg_line -StdoutPath $run.stdout -StderrPath $run.stderr
        $results += Complete-WorkerResult -Run $run -ExitCode ([int]$runOutput.exit_code)
    }
}

Write-LauncherDebug ("results_collected={0}" -f $results.Count)
$efficiencySignals = Get-StructureEfficiencySignals `
    -Results $results `
    -ExecutionMode $executionMode `
    -PolicyEvaluation $policyEvaluation
$runMemoryArtifacts = if ($memoryConfig.active) {
    Write-RunMemoryArtifacts -MemoryConfig $memoryConfig -Results $results -RequestedDeliverables $requestedDeliverables
} else {
    $null
}
$memoryMetrics = Get-MemoryMetrics -MemoryConfig $memoryConfig -WorkerContextInfos $memoryWorkerContextInfos -RunMemoryArtifacts $runMemoryArtifacts

$manifestDirectory = Split-Path -Parent $manifestFile
if (-not [string]::IsNullOrWhiteSpace($manifestDirectory)) {
    New-Item -ItemType Directory -Path $manifestDirectory -Force | Out-Null
}

$manifest = [ordered]@{
    created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    launcher_version = "2026-03-12-v6"
    launcher_script = $MyInvocation.MyCommand.Path
    spec_path = $specPathResolved
    spec_directory = $specDirectory
    spec_sha256 = $specHash
    codex_executable = $resolvedCodexExecutable
    invocation_cwd = $invocationCwd
    cwd_requested = [string]$spec.cwd
    cwd_resolution_mode = $cwdResolutionMode
    cwd_resolution_base = $cwdBaseDirectory
    workspace_root = $cwd
    output_dir = $outputDir
    debug_log = $debugLogFile
    summary_file = if ($writeSummaryFile) { $summaryFile } else { $null }
    archive = $archiveInfo
    execution_mode = $executionMode
    skip_git_repo_check = $skipGit
    shared_directive = [ordered]@{
        source = $sharedDirectiveInfo.source
        requested_mode = $sharedDirectiveInfo.requested_mode
        effective_mode = $sharedDirectiveInfo.effective_mode
        sha256 = if ($sharedDirectiveInfo.text) { Get-TextHash -Text $sharedDirectiveInfo.text } else { $null }
        char_count = if ($sharedDirectiveInfo.text) { $sharedDirectiveInfo.text.Length } else { 0 }
        original_char_count = $sharedDirectiveInfo.original_char_count
        effective_char_count = $sharedDirectiveInfo.effective_char_count
        hybrid_policy = if ($sharedDirectiveInfo.effective_mode -eq "hybrid") { "implementer/fixer=full; reviewer/validator/planner/read-only custom=compact" } else { $null }
    }
    persona_guide = [ordered]@{
        source = $personaGuideInfo.source
        requested_mode = $personaGuideInfo.requested_mode
        effective_mode = $personaGuideInfo.effective_mode
        sha256 = if ($personaGuideInfo.text) { Get-TextHash -Text $personaGuideInfo.text } else { $null }
        char_count = if ($personaGuideInfo.text) { $personaGuideInfo.text.Length } else { 0 }
        original_char_count = $personaGuideInfo.original_char_count
        effective_char_count = $personaGuideInfo.effective_char_count
    }
    workflow = [ordered]@{
        enabled = [bool]$workflowInfo.enabled
        source = $workflowInfo.source
        prompt_mode = $workflowInfo.prompt_mode
        strict_render = $workflowInfo.strict_render
        auto_detected = $workflowInfo.auto_detected
        front_matter_text = $workflowInfo.front_matter_text
        prompt_template_sha256 = if ($workflowInfo.prompt_template) { Get-TextHash -Text $workflowInfo.prompt_template } else { $null }
        prompt_template_chars = if ($workflowInfo.prompt_template) { $workflowInfo.prompt_template.Length } else { 0 }
        context = $workflowInfo.context
    }
    hooks = [ordered]@{
        after_create = $afterCreateHookResult
    }
    policy = $policyEvaluation
    efficiency_signals = $efficiencySignals
    stage_plan = $stagePlan
    defaults = $defaults
    results = $results
}

if ($memoryMetrics) {
    $manifest.memory = $memoryMetrics
}

Write-LauncherDebug "writing_manifest"
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestFile -Encoding utf8
Write-LauncherDebug "manifest_written"

if ($writeSummaryFile) {
    $summaryDirectory = Split-Path -Parent $summaryFile
    if (-not [string]::IsNullOrWhiteSpace($summaryDirectory)) {
        New-Item -ItemType Directory -Path $summaryDirectory -Force | Out-Null
    }

    $summaryText = New-RunSummaryText `
        -WorkspaceRoot $cwd `
        -ExecutionMode $executionMode `
        -SharedDirectiveInfo $sharedDirectiveInfo `
        -PersonaGuideInfo $personaGuideInfo `
        -WorkflowInfo $workflowInfo `
        -AfterCreateHookResult $afterCreateHookResult `
        -Results $results `
        -ManifestPath $manifestFile `
        -PolicyEvaluation $policyEvaluation `
        -ArchiveInfo $archiveInfo `
        -EfficiencySignals $efficiencySignals `
        -MemoryMetrics $memoryMetrics
    Set-Content -LiteralPath $summaryFile -Value $summaryText -Encoding utf8
    Write-LauncherDebug "summary_written"
}

if ($archiveInfo.enabled) {
    Write-LauncherDebug "archive_copy_started"
    Export-RunArchiveContent `
        -ArchiveInfo $archiveInfo `
        -WorkspaceRoot $cwd `
        -SpecPath $specPathResolved `
        -ManifestPath $manifestFile `
        -SummaryPath $summaryFile `
        -DebugLogPath $debugLogFile `
        -SharedDirectiveInfo $sharedDirectiveInfo `
        -PersonaGuideInfo $personaGuideInfo `
        -WorkflowInfo $workflowInfo `
        -AfterCreateHookResult $afterCreateHookResult `
        -RequestedDeliverables $requestedDeliverables `
        -Results $results
    Write-LauncherDebug "archive_copy_completed"
}

$finalOutput = [pscustomobject]@{
    manifest = $manifestFile
    summary = if ($writeSummaryFile) { $summaryFile } else { $null }
    archive = $archiveInfo
    execution_mode = $executionMode
    workspace_root = $cwd
    output_dir = $outputDir
    workflow = $manifest.workflow
    hooks = $manifest.hooks
    policy = $policyEvaluation
    stage_plan = $stagePlan
    results = $results
}

if ($memoryMetrics) {
    $finalOutput | Add-Member -NotePropertyName memory -NotePropertyValue $memoryMetrics
}

if ($AsJson) {
    Write-LauncherDebug "writing_json_output"
    $finalOutput | ConvertTo-Json -Depth 8
} else {
    $results |
        Select-Object name, mode, worker_kind, requested_shared_directive_mode, effective_shared_directive_mode, requested_persona_guide_mode, effective_persona_guide_mode, persona_role_frame, persona_domain_ids, exit_code, succeeded, session_id, requested_model, actual_model, requested_sandbox, actual_sandbox, requested_reasoning_effort, actual_reasoning_effort, footer_tokens_used, last |
        Format-Table -AutoSize
    Write-Output ""
    Write-Output ("Manifest: {0}" -f $manifestFile)
}
