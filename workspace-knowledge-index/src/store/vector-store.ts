import fs from 'node:fs';
import path from 'node:path';
import * as lancedb from '@lancedb/lancedb';
import { Field, FixedSizeList, Float32, Schema, Utf8 } from 'apache-arrow';
import type { VectorBackend } from '../interfaces/vector-backend.js';
import type { ChunkWithEmbedding, SearchFilter, VectorSearchResult } from '../types/index.js';
import { EXTENSION_TYPE_MAP } from '../utils/file-types.js';

const TABLE_NAME = 'chunks';
const DELETE_BATCH_SIZE = 999;

interface LanceChunkRow {
  id: string;
  embedding: number[];
  file_path: string;
  project_id: string;
  chunk_type: string;
  file_type: string;
  _distance?: number;
}

export class LanceVectorStore implements VectorBackend {
  private db: lancedb.Connection | null = null;
  private table: lancedb.Table | null = null;
  private dimensions: number;

  constructor(private dbPath: string, dimensions: number = 768) {
    this.dimensions = dimensions;
  }

  async init(): Promise<void> {
    if (this.db && this.table && this.db.isOpen() && this.table.isOpen()) {
      return;
    }

    ensureDatabaseParentDirectory(this.dbPath);

    this.db = await lancedb.connect(this.dbPath);
    const tableNames = await this.db.tableNames();

    this.table = tableNames.includes(TABLE_NAME)
      ? await this.db.openTable(TABLE_NAME)
      : await this.db.createEmptyTable(TABLE_NAME, createChunkSchema(this.dimensions));
  }

  async insert(chunks: ChunkWithEmbedding[]): Promise<void> {
    const table = this.requireTable('insert');

    if (chunks.length === 0) {
      return;
    }

    const rows = chunks.map((chunk) => ({
      id: buildStoredChunkId(chunk),
      embedding: toVectorValues(chunk.embedding, this.dimensions),
      file_path: chunk.filePath,
      project_id: chunk.projectId,
      chunk_type: chunk.chunkType,
      file_type: detectFileType(chunk.filePath),
    }));

    await table.add(rows);
  }

  async search(
    query: number[],
    topK: number,
    filter?: SearchFilter,
  ): Promise<VectorSearchResult[]> {
    const table = this.requireTable('search');
    const safeTopK = Number.isFinite(topK) ? Math.max(0, Math.trunc(topK)) : 0;

    if (safeTopK === 0) {
      return [];
    }

    const searchQuery = table
      .vectorSearch(toVectorValues(query, this.dimensions))
      .column('embedding')
      .distanceType('cosine');

    const predicate = buildFilterPredicate(filter);
    if (predicate) {
      searchQuery.where(predicate);
    }

    const rows = (await searchQuery.limit(safeTopK).toArray()) as LanceChunkRow[];

    return rows
      .filter((row) => typeof row.id === 'string')
      .map((row) => ({
        chunkId: row.id,
        score: distanceToSimilarity(row._distance),
      }));
  }

  async delete(chunkIds: string[]): Promise<void> {
    const table = this.requireTable('delete');
    const normalizedIds = Array.from(
      new Set(chunkIds.map((chunkId) => chunkId.trim()).filter((chunkId) => chunkId.length > 0)),
    );

    for (let offset = 0; offset < normalizedIds.length; offset += DELETE_BATCH_SIZE) {
      const batch = normalizedIds.slice(offset, offset + DELETE_BATCH_SIZE);
      const predicate = `id IN (${batch.map((chunkId) => toSqlString(chunkId)).join(', ')})`;
      await table.delete(predicate);
    }
  }

  async rebuild(): Promise<void> {
    const db = this.requireDb('rebuild');

    if (this.table?.isOpen()) {
      this.table.close();
    }

    this.table = null;

    const tableNames = await db.tableNames();
    if (tableNames.includes(TABLE_NAME)) {
      await db.dropTable(TABLE_NAME);
    }

    this.table = await db.createEmptyTable(TABLE_NAME, createChunkSchema(this.dimensions));
  }

  async close(): Promise<void> {
    if (this.table?.isOpen()) {
      this.table.close();
    }

    if (this.db?.isOpen()) {
      this.db.close();
    }

    this.db = null;
    this.table = null;
  }

  private requireDb(operation: string): lancedb.Connection {
    if (!this.db || !this.db.isOpen()) {
      throw new Error(`LanceVectorStore.init() must be called before ${operation}()`);
    }

    return this.db;
  }

  private requireTable(operation: string): lancedb.Table {
    this.requireDb(operation);

    if (!this.table || !this.table.isOpen()) {
      throw new Error(`LanceVectorStore.init() must be called before ${operation}()`);
    }

    return this.table;
  }
}

function createChunkSchema(dimensions: number): Schema {
  return new Schema([
    new Field('id', new Utf8(), false),
    new Field(
      'embedding',
      new FixedSizeList(dimensions, new Field('item', new Float32(), true)),
      false,
    ),
    new Field('file_path', new Utf8(), false),
    new Field('project_id', new Utf8(), false),
    new Field('chunk_type', new Utf8(), false),
    new Field('file_type', new Utf8(), false),
  ]);
}

function ensureDatabaseParentDirectory(dbPath: string): void {
  if (dbPath.includes('://')) {
    return;
  }

  const directoryPath = path.dirname(path.resolve(dbPath));
  if (!fs.existsSync(directoryPath)) {
    fs.mkdirSync(directoryPath, { recursive: true });
  }
}

function buildStoredChunkId(chunk: Pick<ChunkWithEmbedding, 'contentHash' | 'filePath' | 'ordinal'>): string {
  const contentHash = chunk.contentHash.trim();
  if (contentHash.length > 0) {
    // Include filePath to avoid collisions when different files produce
    // chunks with identical content (and therefore identical hashes).
    return `${chunk.filePath}::${contentHash}`;
  }

  return `${chunk.filePath}:${chunk.ordinal}`;
}

function detectFileType(filePath: string): string {
  const extension = path.extname(filePath).toLowerCase();
  if (extension.length === 0) {
    return '';
  }

  return EXTENSION_TYPE_MAP[extension] ?? extension.slice(1);
}

function toVectorValues(values: number[], dimensions: number): number[] {
  if (values.length !== dimensions) {
    throw new Error(`Expected embedding dimension ${dimensions}, received ${values.length}`);
  }

  const vector = Float32Array.from(values);

  for (const value of vector) {
    if (!Number.isFinite(value)) {
      throw new Error('Embedding contains non-finite values');
    }
  }

  return Array.from(vector);
}

function buildFilterPredicate(filter?: SearchFilter): string | null {
  if (!filter) {
    return null;
  }

  const predicates: string[] = [];

  const projectId = filter.projectId?.trim();
  if (projectId) {
    predicates.push(`project_id = ${toSqlString(projectId)}`);
  }

  const fileType = normalizeFileTypeFilter(filter.fileType);
  if (fileType) {
    predicates.push(`file_type = ${toSqlString(fileType)}`);
  }

  const symbolKind = filter.symbolKind?.trim();
  if (symbolKind) {
    predicates.push(`chunk_type = ${toSqlString(symbolKind)}`);
  }

  return predicates.length > 0 ? predicates.join(' AND ') : null;
}

function normalizeFileTypeFilter(fileType: string | undefined): string | null {
  const normalized = fileType?.trim().toLowerCase();
  if (!normalized) {
    return null;
  }

  if (normalized.startsWith('*.')) {
    return EXTENSION_TYPE_MAP[normalized.slice(1)] ?? normalized.slice(2);
  }

  if (normalized.startsWith('.')) {
    return EXTENSION_TYPE_MAP[normalized] ?? normalized.slice(1);
  }

  return normalized;
}

function toSqlString(value: string): string {
  return `'${value.replace(/'/g, "''")}'`;
}

function distanceToSimilarity(distance: number | undefined): number {
  if (typeof distance !== 'number' || !Number.isFinite(distance)) {
    return 0;
  }

  const similarity = 1 - distance / 2;
  return Math.max(0, Math.min(1, similarity));
}
