import { requestJson } from '../api'

/** @typedef {'json' | 'markdown'} ExportFormat */

/**
 * @typedef {Object} ExportSnapshotRequest
 * @property {ExportFormat} format
 * @property {string} as_of_date
 */

/**
 * @typedef {Object} ExportManifest
 * @property {string} schema_version
 * @property {string} export_version
 * @property {'explicit_request'} trigger
 * @property {string} as_of_date
 * @property {string} snapshot_fingerprint
 * @property {{collections: Record<string, number>, relationships: Record<string, number>, total_records: number, total_relationships: number, classifications: Object}} counts
 * @property {Array<{code: string, message: string}>} warnings
 * @property {string[]} limitations
 */

/**
 * @typedef {Object} ExportSnapshotResponse
 * @property {ExportFormat} format
 * @property {string} file_name
 * @property {string} media_type
 * @property {ExportManifest} manifest
 * @property {Object | string} content
 */

/**
 * @param {ExportSnapshotRequest} payload
 * @returns {Promise<ExportSnapshotResponse>}
 */
export function createExportSnapshotRequest(payload) {
  return requestJson(
    '/api/exports/snapshots',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    '生成事实关系导出失败',
  )
}
