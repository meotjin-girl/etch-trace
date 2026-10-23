// Shapes from docs/v1-contract.md. Backend fields stay optional where older
// tasks, unfinished tasks, or legacy local records may omit them.
export type Role = 'user' | 'worker' | 'engineer' | 'admin'

export interface Identity {
  name: string
  role: Role
}

export type TaskStatus =
  | 'QUEUED' | 'RUNNING' | 'WAITING_INPUT' | 'WAITING_APPROVAL'
  | 'DONE' | 'INCOMPLETE' | 'FAILED'

export type EventType =
  | 'QUEUED' | 'RUNNING' | 'SEARCH_STARTED' | 'ANALYSIS_STARTED' | 'REPORT_STARTED'
  | 'MESSAGE' | 'QUESTION' | 'APPROVAL_REQUIRED' | 'DONE' | 'INCOMPLETE' | 'FAILED' | 'REVIEWED'

export interface TaskEvent {
  seq: number
  type: EventType | string
  payload: Record<string, any>
  created_at?: string
}

export interface Metric {
  key: string
  value: unknown
  severity?: string
  mean?: number
  deltaPct?: number
  z?: number
}

export interface PhysicalValue {
  key: string
  value: number
  unit: string
  source: string
}

export interface PhysicsResult {
  model: 'etch_depth_constant_rate' | 'average_etch_rate' | 'selectivity'
  version: '1.0'
  status: 'calculated' | 'needs_more_data' | 'invalid_input'
  formula: string
  inputs: PhysicalValue[]
  result?: PhysicalValue | null
  assumptions: string[]
  missing_fields: string[]
  warnings: string[]
  problem?: string
  interpretation?: string
  recommended_checks?: string[]
}

export interface ControlLimit {
  lower?: number | null
  upper?: number | null
  unit: string
  approved?: boolean
  document_id?: string | null
  revision?: string | null
}

export interface QuantitativeValue {
  key: string
  value: number
  unit: string
  origin: 'MEASURED' | 'CALCULATED' | 'SIMULATED'
  source: string
}

export interface QuantitativeResult {
  analysis: 'reference_run_comparison' | 'time_resolved_etch_depth' | 'metrology_comparison'
  version: '2.0'
  problem: string
  status: 'CALCULATED' | 'INSUFFICIENT_DATA' | 'INVALID_INPUT'
  value_origin?: 'MEASURED' | 'CALCULATED' | 'SIMULATED' | null
  validation_status: 'VALIDATED' | 'NOT_VALIDATED'
  formula: string
  inputs: QuantitativeValue[]
  results: QuantitativeValue[]
  reference_ids: string[]
  missing_fields: string[]
  warnings: string[]
  interpretation?: string
  recommended_checks?: string[]
  within_control_limit?: boolean | null
  control_limit?: ControlLimit | null
}

export interface SensorSignalAnalysis {
  sensor: string
  unit: string
  minimum: number
  maximum: number
  mean: number
  first_anomaly_sec?: number | null
  anomaly_duration_sec: number
  maximum_setpoint_deviation?: number | null
  reference_comparison?: QuantitativeResult | null
  cooccurring_sensors: string[]
  related_alarms: string[]
  ocap_ids: string[]
  threshold_source: 'synthetic_baseline' | 'equipment_alarm' | 'none'
}

export interface SensorProcessPoint {
  offset_sec: number
  source_rf_w: number
  source_rf_reference_w: number
  bias_rf_w: number
  bias_rf_reference_w: number
  pressure_mtorr: number
  pressure_reference_mtorr: number
  sf6_sccm: number
  sf6_reference_sccm: number
  o2_sccm: number
  o2_reference_sccm: number
  esc_temp_c: number
  esc_temp_reference_c: number
  source: string
}

export interface SensorAnalysis {
  version: '2.0'
  problem: string
  status: 'CALCULATED' | 'INSUFFICIENT_DATA' | 'INVALID_INPUT'
  target_run_id?: string | null
  signals: SensorSignalAnalysis[]
  process_series?: SensorProcessPoint[]
  missing_fields: string[]
  warnings: string[]
  causal_conclusion: false
}

export interface SensitivityCoefficient {
  variable: 'source_rf' | 'bias_rf' | 'pressure' | 'sf6' | 'o2' | 'esc_temp'
  value: number
  unit: 'per_relative_change'
  source: string
  calibrated: false
}

export interface RelativeRatePoint {
  offset_sec: number
  relative_rate: number
  simulated_process_rate_nm_min: number
  source: string
}

export interface ProfileFrame {
  offset_sec: number
  depth_nm: number
  opening_width_nm: number
  aspect_ratio: number
  simulated_arde_rate_nm_min: number
  removed_region: { x_nm: number; y_nm: number }[]
}

export interface EducationalSimulationResult {
  version: '3.0'
  mode: 'EDUCATIONAL_ASSUMPTION'
  status: 'SIMULATED' | 'INSUFFICIENT_DATA' | 'INVALID_INPUT'
  validation_status: 'NOT_VALIDATED'
  completed_levels: (1 | 2 | 3)[]
  source_run_id?: string | null
  arde_coefficient?: number | null
  arde_coefficient_source?: string
  arde_coefficient_calibrated?: false
  formulas: string[]
  coefficients: SensitivityCoefficient[]
  relative_rate_series: RelativeRatePoint[]
  profile_frames: ProfileFrame[]
  missing_fields: string[]
  assumptions: string[]
  warnings: string[]
  causal_conclusion: false
}

export interface CauseCase {
  id: string
  cause: string
  action?: string
  docs?: string[]
}

export interface EvidenceDocument {
  id: string
  title: string
  text: string
  // SOP RAG clauses (id like `SOP-ETCH-12#4.2`) carry source metadata.
  is_demo?: boolean | null
  source?: string | null
  revision?: string | null
  notice?: string | null
  distance?: number | null
}

export type StageKey = 'scope' | 'run_comparison' | 'physics' | 'sensor' | 'maintenance' | 'recommendation'

// One specialist agent's result (docs/v1-contract.md `stages`).
export interface InvestigationStage {
  key: StageKey
  title: string
  status: 'sample_based' | 'partial' | 'unavailable' | 'provisional' | string
  agent_mode?: 'llm' | 'rule_based'
  findings?: string[]
  unknowns?: string[]
  caseIds?: string[]
  docIds?: string[]
  historyIds?: string[]
}

// Ordered SOP clause returned by RAG MCP.
export interface InvestigationCheck {
  title: string
  rationale: string
  source?: 'rag_mcp' | 'provisional_sop'
  docId?: string | null
}

// Similar approved record visible to the requester (reference, not proof).
export interface HistoryEvidence {
  id: string
  question: string
  summary: string
  causes?: string[]
  docIds?: string[]
  approvedBy: string
  approvedAt: string
  eventTime?: string | null
  lotId?: string | null
}

export interface Report {
  context?: { equipment?: string; chamber?: string; recipe?: string; [key: string]: unknown }
  metrics?: Metric[]
  physicsResults?: PhysicsResult[]
  quantitativeResults?: QuantitativeResult[]
  sensorAnalysis?: SensorAnalysis | null
  educationalSimulation?: EducationalSimulationResult | null
  causeCases?: CauseCase[]
  docIds?: string[]
  documents?: EvidenceDocument[]
  stages?: InvestigationStage[]
  checks?: InvestigationCheck[]
  history?: HistoryEvidence[]
  unknowns?: string[]
  summary?: unknown
  demo?: boolean
  [key: string]: unknown
}

export interface Message {
  role?: string
  text?: unknown
  content?: unknown
  created_at?: string
}

export interface Review {
  action?: string
  created_at?: string
  reviewed_at?: string
  [key: string]: unknown
}

export interface Task {
  id: string
  // Local legacy records and the LOADING placeholder use display-only statuses.
  status: TaskStatus | string
  question?: string
  user_name?: string
  user_role?: string
  user_id?: string | null
  created_at?: string
  updated_at?: string
  report?: Report | null
  messages?: Message[]
  reviews?: Review[]
  events?: TaskEvent[]
  legacy?: boolean
  legacyId?: string
}

export interface ApprovalBody {
  action: 'approve' | 'revise'
  comment?: string
  event_time?: string
  lot_id?: string
}

export interface SopSummary {
  id: string
  title: string
  category: string
  version: string
  updatedAt: string
  owner: string
  description: string
  tags: string[]
  demo: boolean
}

export interface Sop extends SopSummary {
  markdown: string
}
