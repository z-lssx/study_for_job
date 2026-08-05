import { requestJson } from '../api'

/** @typedef {'daily' | 'weekly' | 'pre_interview'} PlanningMode */

/**
 * @typedef {Object} PlanningAssessmentRequest
 * @property {PlanningMode} mode
 * @property {string} as_of_date
 * @property {string=} target_profile_id
 * @property {{application_id: string, interview_date: string}=} interview_context
 */

/**
 * @typedef {Object} PlanningAssessmentItem
 * @property {string} id
 * @property {'knowledge' | 'algorithm' | 'project' | 'internship'} track
 * @property {string} recommendation
 * @property {{tier: 'critical' | 'high' | 'medium' | 'low', tier_rank: number, order: number}} priority
 * @property {Array<{code: string, message: string}>} reasons
 * @property {string[]} source_types
 * @property {Record<string, string | string[] | null>} business_ids
 * @property {string} evidence_status
 * @property {Object[]} evidence_refs
 * @property {string[]} limitations
 */

/**
 * @typedef {Object} PlanningAssessment
 * @property {string} rule_version
 * @property {PlanningMode} mode
 * @property {string} as_of_date
 * @property {'explicit_request'} trigger
 * @property {PlanningAssessmentItem[]} items
 * @property {Array<{code: string, message: string}>} warnings
 */

/**
 * @param {PlanningAssessmentRequest} payload
 * @returns {Promise<PlanningAssessment>}
 */
export function createPlanningAssessmentRequest(payload) {
  return requestJson(
    '/api/planning/assessments',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    '生成本次策略建议失败',
  )
}
