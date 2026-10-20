// Shapes from docs/v1-contract.md. Backend fields stay optional where older
// tasks, unfinished tasks, or legacy local records may omit them.
export type Role = 'worker' | 'engineer' | 'admin'

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
}

export interface Report {
  context?: { equipment?: string; chamber?: string; recipe?: string; [key: string]: unknown }
  metrics?: Metric[]
  causeCases?: CauseCase[]
  docIds?: string[]
  documents?: EvidenceDocument[]
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
