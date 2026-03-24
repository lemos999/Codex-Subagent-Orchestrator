import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import * as os from 'node:os';
import * as path from 'node:path';
import { afterEach, beforeEach, describe, test } from 'node:test';

import { writeNormalizedEvidence } from '../dist/evidence/normalized-writer.js';

function buildResolvedPaths(workspaceRoot, outputDir) {
  return {
    workspaceRoot,
    outputDir,
    manifestFile: path.join(outputDir, 'orchestration-manifest.json'),
    summaryFile: path.join(outputDir, 'orchestration-summary.md'),
    debugLogFile: null,
    archiveRoot: null,
    specPath: path.join(workspaceRoot, 'fixtures', 'spec.json'),
    specDirectory: path.join(workspaceRoot, 'fixtures'),
    invocationCwd: workspaceRoot,
  };
}

async function buildWorkerResult(options) {
  const stdoutPath = path.join(options.outputDir, `${options.name}.stdout.log`);
  const stderrPath = path.join(options.outputDir, `${options.name}.stderr.log`);
  const lastPath = path.join(options.outputDir, `${options.name}.last.txt`);

  await fs.mkdir(options.outputDir, { recursive: true });
  await fs.writeFile(stdoutPath, options.stdoutText, 'utf8');
  await fs.writeFile(stderrPath, options.stderrText ?? '', 'utf8');
  await fs.writeFile(lastPath, options.lastText ?? '', 'utf8');

  const isReadOnly =
    options.workerKind === 'reviewer' || options.workerKind === 'validator';

  return {
    name: options.name,
    engine: options.engine,
    mode: 'exec',
    stage: options.stage,
    worker_kind: options.workerKind,
    is_read_only: isReadOnly,
    cwd: options.workspaceRoot,
    exit_code: options.succeeded ? 0 : 1,
    succeeded: options.succeeded,
    required_paths: options.requiredPaths ?? [],
    required_non_empty_paths: [],
    missing_required_paths: [],
    empty_required_paths: [],
    validation_failures: options.succeeded ? [] : ['Reviewer reported material issues'],
    requested_model: options.model,
    requested_full_auto: !isReadOnly,
    requested_json_output: false,
    actual_model: options.model,
    requested_sandbox: isReadOnly ? 'read-only' : 'workspace-write',
    actual_sandbox: isReadOnly ? 'read-only' : 'workspace-write',
    requested_reasoning_effort: null,
    actual_reasoning_effort: null,
    prompt_profile: 'full',
    response_style: 'standard',
    max_response_lines: 0,
    actual_approval: null,
    actual_workdir: null,
    output_mode: 'text',
    session_id: null,
    footer_tokens_used: null,
    turn_failed: !options.succeeded,
    failure_message: options.succeeded ? null : 'Process exited with code 1',
    stdout: stdoutPath,
    stderr: stderrPath,
    last: lastPath,
    prompt: null,
    prompt_sha256: 'hash',
    prompt_chars: 0,
    workflow_prompt_mode: 'disabled',
    workflow_prompt_chars: 0,
    command: `${options.engine} exec`,
    last_exists: true,
    last_message_preview: (options.lastText ?? '').slice(0, 80),
    stderr_preview: (options.stderrText ?? '').slice(0, 80),
    stdout_preview: options.stdoutText.slice(0, 80),
  };
}

function buildManifest(resolvedPaths, results, requestedDeliverables, executionMode = 'sequential') {
  const reviewerNames = results
    .filter((result) => result.worker_kind === 'reviewer' || result.worker_kind === 'validator')
    .map((result) => result.name);
  const writableNames = results
    .filter((result) => !result.is_read_only)
    .map((result) => result.name);
  const lastWritableStage = writableNames.length === 0
    ? 0
    : Math.max(
        ...results
          .filter((result) => !result.is_read_only)
          .map((result) => result.stage),
      );

  return {
    created_at_utc: '2026-03-19T01:02:03.000Z',
    launcher_version: 'test',
    launcher_script: 'test-launcher',
    spec_path: resolvedPaths.specPath,
    spec_directory: resolvedPaths.specDirectory,
    spec_sha256: 'spec-hash',
    codex_executable: 'codex',
    claude_executable: 'claude',
    gemini_executable: 'npx',
    invocation_cwd: resolvedPaths.invocationCwd,
    cwd_requested: '.',
    cwd_resolution_mode: 'invocation',
    cwd_resolution_base: resolvedPaths.invocationCwd,
    workspace_root: resolvedPaths.workspaceRoot,
    output_dir: resolvedPaths.outputDir,
    debug_log: null,
    summary_file: resolvedPaths.summaryFile,
    live_usage: {
      enabled: false,
      display_mode: 'none',
      poll_interval_ms: 500,
      status_file: null,
      json_output_forced: false,
    },
    archive: {
      enabled: false,
      root: null,
      run_label: null,
      run_directory: null,
      launcher_directory: null,
      deliverables_directory: null,
      workers_directory: null,
      supervisor_directory: null,
    },
    execution_mode: executionMode,
    skip_git_repo_check: true,
    shared_directive: {
      source: 'AGENTS.md',
      requested_mode: 'reference',
      effective_mode: 'reference',
      sha256: 'directive-hash',
      char_count: 10,
      original_char_count: 10,
      effective_char_count: 10,
    },
    workflow: {
      enabled: false,
      source: null,
      prompt_mode: 'disabled',
      strict_render: true,
      auto_detected: false,
      front_matter_text: null,
      prompt_template_sha256: null,
      prompt_template_chars: 0,
      context: {},
    },
    hooks: {
      after_create: {
        enabled: false,
        ran: false,
        trigger: null,
        exit_code: null,
        missing_sentinel_paths: [],
        workspace_was_empty: false,
        stdout: null,
        stderr: null,
      },
    },
    policy: {
      execution_mode: executionMode,
      supervisor_only: false,
      require_final_read_only_review: reviewerNames.length > 0,
      material_issue_strategy: 'none',
      requested_deliverables: requestedDeliverables,
      writable_worker_names: writableNames,
      read_only_reviewer_names: reviewerNames,
      final_read_only_reviewer_names: reviewerNames.filter((name) => {
        const result = results.find((item) => item.name === name);
        return result !== undefined && result.stage > lastWritableStage;
      }),
      final_read_only_review_present: reviewerNames.some((name) => {
        const result = results.find((item) => item.name === name);
        return result !== undefined && result.stage > lastWritableStage;
      }),
      last_writable_stage: lastWritableStage,
    },
    efficiency_signals: {
      measurement_mode: 'structure_first',
      note: 'test',
      execution_mode: executionMode,
      total_workers: results.length,
      succeeded_workers: results.filter((result) => result.succeeded).length,
      failed_workers: results.filter((result) => !result.succeeded).length,
      requested_deliverable_count: requestedDeliverables.length,
      workers_per_deliverable:
        requestedDeliverables.length === 0
          ? null
          : results.length / requestedDeliverables.length,
      writable_workers_per_deliverable:
        requestedDeliverables.length === 0
          ? null
          : writableNames.length / requestedDeliverables.length,
      writable_workers: writableNames.length,
      read_only_workers: results.filter((result) => result.is_read_only).length,
      implementer_workers: results.filter((result) => result.worker_kind === 'implementer').length,
      reviewer_workers: results.filter((result) => result.worker_kind === 'reviewer').length,
      validator_workers: results.filter((result) => result.worker_kind === 'validator').length,
      fixer_workers: results.filter((result) => result.worker_kind === 'fixer').length,
      full_auto_writable_workers: writableNames.length,
      full_auto_read_only_workers: 0,
      stage_count: new Set(results.map((result) => result.stage)).size,
      parallel_stage_count: 0,
      max_parallel_workers_in_stage: 1,
      uses_parallel_execution: executionMode === 'parallel',
      uses_supervisor_only_policy: false,
      uses_bounded_repair_policy: false,
      final_read_only_review_present: reviewerNames.length > 0,
      total_prompt_chars: 0,
      total_footer_tokens: 0,
    },
    stage_plan: [...new Set(results.map((result) => result.stage))]
      .sort((left, right) => left - right)
      .map((stage) => {
        const stageResults = results.filter((result) => result.stage === stage);
        return {
          stage,
          worker_count: stageResults.length,
          worker_names: stageResults.map((result) => result.name),
          worker_kinds: stageResults.map((result) => result.worker_kind),
          read_only_workers: stageResults
            .filter((result) => result.is_read_only)
            .map((result) => result.name),
          writable_workers: stageResults
            .filter((result) => !result.is_read_only)
            .map((result) => result.name),
        };
      }),
    defaults: {},
    results,
  };
}

describe('writeNormalizedEvidence', () => {
  let tempRoot = '';

  beforeEach(async () => {
    tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'stage9-writer-'));
    await fs.mkdir(path.join(tempRoot, 'fixtures'), { recursive: true });
    await fs.writeFile(path.join(tempRoot, 'fixtures', 'spec.json'), '{}', 'utf8');
  });

  afterEach(async () => {
    if (tempRoot) {
      await fs.rm(tempRoot, { recursive: true, force: true });
    }
  });

  test('writes normalized manifest, summary, prompts, and results for a single-engine run', async () => {
    const outputDir = path.join(tempRoot, 'subagent-runs', 'codex', 'stage9-single');
    const resolvedPaths = buildResolvedPaths(tempRoot, outputDir);
    const deliverableRelativePath = path.join('tests', 'artifacts', 'stage9.txt');
    const deliverableAbsolutePath = path.join(tempRoot, deliverableRelativePath);

    await fs.mkdir(path.dirname(deliverableAbsolutePath), { recursive: true });
    await fs.writeFile(deliverableAbsolutePath, 'hello', 'utf8');

    const writerResult = await buildWorkerResult({
      name: 'file-writer',
      engine: 'codex',
      stage: 1,
      workerKind: 'implementer',
      model: 'gpt-5',
      succeeded: true,
      workspaceRoot: tempRoot,
      outputDir,
      stdoutText: 'raw writer output',
      lastText: 'Created tests/artifacts/stage9.txt',
      requiredPaths: [deliverableAbsolutePath],
    });
    const reviewerResult = await buildWorkerResult({
      name: 'file-checker',
      engine: 'codex',
      stage: 2,
      workerKind: 'reviewer',
      model: 'gpt-5-mini',
      succeeded: true,
      workspaceRoot: tempRoot,
      outputDir,
      stdoutText: 'raw reviewer output',
      lastText: 'ACCEPTED',
    });

    const workers = [
      {
        name: 'file-writer',
        engine: 'codex',
        model: 'gpt-5',
        taskText: 'Create tests/artifacts/stage9.txt with exact content',
        prompt: 'Create tests/artifacts/stage9.txt with exact content',
        cwd: tempRoot,
        outputDir,
        sandbox: 'workspace-write',
        kind: 'implementer',
        stage: 1,
        isReadOnly: false,
        reasoningEffort: null,
        promptProfile: 'full',
        responseStyle: 'standard',
        maxResponseLines: 0,
        json: false,
        outputSchema: null,
        writePromptFile: false,
        requiredPaths: [deliverableAbsolutePath],
        requiredNonEmptyPaths: [],
        extraArgs: [],
        timeoutMs: 0,
      },
      {
        name: 'file-checker',
        engine: 'codex',
        model: 'gpt-5-mini',
        taskText: 'Verify tests/artifacts/stage9.txt exists and matches the contract',
        prompt: 'Verify tests/artifacts/stage9.txt exists and matches the contract',
        cwd: tempRoot,
        outputDir,
        sandbox: 'read-only',
        kind: 'reviewer',
        stage: 2,
        isReadOnly: true,
        reasoningEffort: null,
        promptProfile: 'full',
        responseStyle: 'standard',
        maxResponseLines: 0,
        json: false,
        outputSchema: null,
        writePromptFile: false,
        requiredPaths: [],
        requiredNonEmptyPaths: [],
        extraArgs: [],
        timeoutMs: 0,
      },
    ];

    const manifest = buildManifest(
      resolvedPaths,
      [writerResult, reviewerResult],
      [deliverableRelativePath],
    );

    await writeNormalizedEvidence(
      resolvedPaths,
      manifest,
      [writerResult, reviewerResult],
      workers,
    );

    const runManifest = await fs.readFile(path.join(outputDir, 'run-manifest.md'), 'utf8');
    const runSummary = await fs.readFile(path.join(outputDir, 'run-summary.md'), 'utf8');
    const promptFile = await fs.readFile(
      path.join(outputDir, 'prompts', 'file-writer.prompt.md'),
      'utf8',
    );
    const resultFile = await fs.readFile(
      path.join(outputDir, 'results', 'file-checker.result.md'),
      'utf8',
    );

    assert.match(runManifest, /# Run Manifest - stage9-single/);
    assert.match(runManifest, /prompts\/file-writer\.prompt\.md/);
    assert.match(runManifest, /results\/file-checker\.result\.md/);
    assert.match(
      runManifest,
      /tests\/artifacts\/stage9\.txt \| present \| Requested deliverable/,
    );
    assert.equal(promptFile, 'Create tests/artifacts/stage9.txt with exact content');
    assert.equal(resultFile, 'ACCEPTED');
    assert.match(runSummary, /- \*\*Verdict\*\*: ACCEPTED/);
    assert.match(runSummary, /- \*\*Evidence\*\*: subagent-runs\/codex\/stage9-single\//);
  });

  test('writes mixed-engine raw evidence and records material issues for failed runs', async () => {
    const outputDir = path.join(tempRoot, 'subagent-runs', 'mixed', 'stage9-mixed');
    const resolvedPaths = buildResolvedPaths(tempRoot, outputDir);
    const missingDeliverable = path.join('tests', 'artifacts', 'missing-stage9.txt');

    const codexResult = await buildWorkerResult({
      name: 'codex-writer',
      engine: 'codex',
      stage: 1,
      workerKind: 'implementer',
      model: 'gpt-5',
      succeeded: true,
      workspaceRoot: tempRoot,
      outputDir,
      stdoutText: 'codex raw stdout',
      lastText: 'Patched the target file',
    });
    const geminiResult = await buildWorkerResult({
      name: 'gemini-reviewer',
      engine: 'gemini',
      stage: 2,
      workerKind: 'reviewer',
      model: 'gemini-2.5-pro',
      succeeded: false,
      workspaceRoot: tempRoot,
      outputDir,
      stdoutText: 'gemini raw stdout',
      stderrText: 'MATERIAL_ISSUES: missing regression test',
      lastText: '',
    });

    const workers = [
      {
        name: 'codex-writer',
        engine: 'codex',
        model: 'gpt-5',
        taskText: 'Implement the requested file change',
        prompt: 'Implement the requested file change',
        cwd: tempRoot,
        outputDir,
        sandbox: 'workspace-write',
        kind: 'implementer',
        stage: 1,
        isReadOnly: false,
        reasoningEffort: null,
        promptProfile: 'full',
        responseStyle: 'standard',
        maxResponseLines: 0,
        json: false,
        outputSchema: null,
        writePromptFile: false,
        requiredPaths: [],
        requiredNonEmptyPaths: [],
        extraArgs: [],
        timeoutMs: 0,
      },
      {
        name: 'gemini-reviewer',
        engine: 'gemini',
        model: 'gemini-2.5-pro',
        taskText: 'Review the implementer output and reject material issues',
        prompt: 'Review the implementer output and reject material issues',
        cwd: tempRoot,
        outputDir,
        sandbox: 'read-only',
        kind: 'reviewer',
        stage: 2,
        isReadOnly: true,
        reasoningEffort: null,
        promptProfile: 'full',
        responseStyle: 'standard',
        maxResponseLines: 0,
        json: false,
        outputSchema: null,
        writePromptFile: false,
        requiredPaths: [],
        requiredNonEmptyPaths: [],
        extraArgs: [],
        timeoutMs: 0,
      },
    ];

    const manifest = buildManifest(
      resolvedPaths,
      [codexResult, geminiResult],
      [missingDeliverable],
      'parallel',
    );

    await writeNormalizedEvidence(
      resolvedPaths,
      manifest,
      [codexResult, geminiResult],
      workers,
    );

    const runManifest = await fs.readFile(path.join(outputDir, 'run-manifest.md'), 'utf8');
    const runSummary = await fs.readFile(path.join(outputDir, 'run-summary.md'), 'utf8');
    const reviewerResultFile = await fs.readFile(
      path.join(outputDir, 'results', 'gemini-reviewer.result.md'),
      'utf8',
    );
    const codexRaw = await fs.readFile(
      path.join(outputDir, 'engines', 'codex', 'codex-writer.raw.txt'),
      'utf8',
    );
    const geminiRaw = await fs.readFile(
      path.join(outputDir, 'engines', 'gemini', 'gemini-reviewer.raw.txt'),
      'utf8',
    );

    assert.match(runSummary, /- \*\*Verdict\*\*: MATERIAL_ISSUES/);
    assert.match(runManifest, /requested deliverable missing at evidence time/);
    assert.match(reviewerResultFile, /MATERIAL_ISSUES: missing regression test/);
    assert.equal(codexRaw, 'codex raw stdout');
    assert.equal(geminiRaw, 'gemini raw stdout');
  });
});
