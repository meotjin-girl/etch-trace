// Shapes from docs/development/v1-contract.md. Backend fields stay optional where older
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

export type StageKey = 'scope' | 'run_comparison' | 'sensor' | 'maintenance' | 'recommendation'

// One specialist agent's result (docs/development/v1-contract.md `stages`).
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
