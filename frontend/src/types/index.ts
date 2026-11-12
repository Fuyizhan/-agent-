export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface TaskResponse {
  review_id: string
  status: string
  message: string
}

export interface StepEvent {
  step: string
  status: 'running' | 'done' | 'error'
  message: string
  started_at: string
  finished_at: string | null
}

export interface ContractEntity {
  entity_type: string
  value: string
  location: string
}

export interface Clause {
  id: string
  title: string
  content: string
  category: string
  section_number: string
  entities: ContractEntity[]
}

export interface RiskFinding {
  clause_id: string
  risk_level: string
  risk_type: string
  description: string
  buyer_impact: string
  seller_impact: string
  rationale: string
}

export interface ComplianceFinding {
  clause_id: string
  status: string
  regulation: string
  issue: string
  recommendation: string
}

export interface Suggestion {
  clause_id: string
  original_text: string
  suggested_text: string
  reason: string
  priority: string
}

export interface DetailedReview {
  review_id: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  contract_type: string
  filename: string
  created_at: string
  updated_at: string
  clauses: Clause[]
  risk_findings: RiskFinding[]
  risk_summary: string
  overall_risk_level: string
  risk_score: number
  compliance_findings: ComplianceFinding[]
  missing_clauses: string[]
  overall_compliance: string
  suggestions: Suggestion[]
  errors: string[]
  current_step: string
  progress: number
  step_log: StepEvent[]
  warnings: string[]
  degraded_steps: string[]
  has_quality_issues: boolean
}
