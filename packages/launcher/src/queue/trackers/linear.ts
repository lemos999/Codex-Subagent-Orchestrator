/**
 * Linear GraphQL tracker.
 *
 * Polls Linear API for issues in a specific project.
 * API key is read from environment variable (default: LINEAR_API_KEY).
 *
 * PS-compatible: same GraphQL query, same field mapping, same blocker extraction.
 */

import type { RawIssue } from '../queue-types.js';
import type { Tracker } from './tracker.js';

// ============================================================
// GraphQL query (PS-compatible)
// ============================================================

const LINEAR_ISSUES_QUERY = `
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
`;

// ============================================================
// Types for Linear API response
// ============================================================

interface LinearNode {
  id: string;
  identifier: string;
  title: string;
  description: string;
  priority: number | null;
  state: { name: string };
  branchName: string | null;
  url: string;
  labels: { nodes: Array<{ name: string }> };
  inverseRelations: {
    nodes: Array<{
      type: string;
      issue: {
        id: string;
        identifier: string;
        state: { name: string };
      } | null;
    }>;
  };
  createdAt: string;
  updatedAt: string;
}

interface LinearResponse {
  data?: {
    issues: {
      nodes: LinearNode[];
    };
  };
  errors?: Array<{ message: string }>;
}

// ============================================================
// GraphQL client
// ============================================================

async function invokeLinearGraphQL(
  endpoint: string,
  apiToken: string,
  query: string,
  variables: Record<string, unknown>,
): Promise<LinearResponse> {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      Authorization: apiToken,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query, variables }),
    signal: AbortSignal.timeout(30000),
  });

  if (!response.ok) {
    throw new Error(`Linear API HTTP ${response.status}: ${response.statusText}`);
  }

  const json = (await response.json()) as LinearResponse;

  if (json.errors && json.errors.length > 0) {
    throw new Error(`Linear GraphQL errors: ${JSON.stringify(json.errors)}`);
  }

  return json;
}

// ============================================================
// Tracker implementation
// ============================================================

export class LinearTracker implements Tracker {
  constructor(
    private projectSlug: string,
    private apiKeyEnv: string,
    private endpoint: string,
    private activeStates: string[],
  ) {}

  async fetchRawIssues(): Promise<RawIssue[]> {
    const apiKey = process.env[this.apiKeyEnv];
    if (!apiKey) {
      throw new Error(`Linear API key env var is not set: ${this.apiKeyEnv}`);
    }

    if (!this.projectSlug) {
      throw new Error('tracker.project_slug is required for tracker.kind=linear');
    }

    const response = await invokeLinearGraphQL(
      this.endpoint,
      apiKey,
      LINEAR_ISSUES_QUERY,
      {
        projectSlug: this.projectSlug,
        stateNames: this.activeStates,
        first: 50,
      },
    );

    if (!response.data?.issues?.nodes) {
      return [];
    }

    return response.data.issues.nodes.map((node) => this.mapNodeToRawIssue(node));
  }

  /**
   * Map Linear API node to RawIssue format.
   * PS-compatible: same field mapping, same blocker extraction from inverseRelations.
   */
  private mapNodeToRawIssue(node: LinearNode): RawIssue {
    // Extract blockers from inverse relations (PS: "blocks" type)
    const blockers: Array<{ id: string; identifier: string; state: string }> = [];
    for (const relation of node.inverseRelations?.nodes ?? []) {
      if (relation.type === 'blocks' && relation.issue) {
        blockers.push({
          id: relation.issue.id,
          identifier: relation.issue.identifier,
          state: relation.issue.state.name,
        });
      }
    }

    return {
      id: node.id,
      identifier: node.identifier,
      title: node.title,
      description: node.description,
      priority: node.priority,
      state: node.state.name,
      branch_name: node.branchName ?? '',
      url: node.url,
      labels: (node.labels?.nodes ?? []).map((l) => l.name.toLowerCase()),
      blocked_by: blockers,
      created_at: node.createdAt,
      updated_at: node.updatedAt,
      source_kind: 'linear',
    };
  }
}
