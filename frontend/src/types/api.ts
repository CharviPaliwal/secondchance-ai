export interface StrategyMetrics {
  total_transactions: number
  recovered_transactions: number
  recovery_rate: number
  total_revenue_at_risk: number
  recovered_revenue: number
  revenue_recovery_rate: number
  total_friction_cost: number
  average_friction_per_transaction: number
  action_distribution: Record<string, number>
}

export interface ComparisonResponse {
  status: 'completed'
  transaction_count: number
  completed_at: string
  scenario?: string
  run_seed?: number
  run_id?: string
  duration_ms?: number
  baseline: StrategyMetrics
  secondchance: StrategyMetrics
  improvement: {
    additional_recovered_revenue: number
    revenue_recovery_rate_improvement: number
    recovery_rate_improvement: number
    friction_difference: number
  }
  decision_trace: Array<{
    transaction_id: string
    amount: number
    failure_reason: string
    diagnosis: string
    recommended_action: string
    recovery_probability: number
    guardrail: string
    outcome: 'RECOVERED' | 'NOT_RECOVERED'
  }>
  action_distribution: Record<string, number>
  trajectory: Array<{
    step: number
    baseline_recovered_revenue: number
    secondchance_recovered_revenue: number
  }>
  activity_log?: string[]
}

export interface DashboardResponse {
  summary: {
    total_cases: number
    revenue_at_risk: number
    recovered_revenue: number
    revenue_recovery_rate: number
    recovery_rate: number
    total_friction_cost: number
  }
  action_distribution: Record<string, number>
  recent_cases: Array<Pick<TransactionListItem, 'transaction_id' | 'amount' | 'failure_reason' | 'recommended_action' | 'recovery_probability' | 'confidence' | 'transaction_timestamp'>>
}

export interface TransactionListItem {
  transaction_id: string
  customer_id: string
  amount: number
  currency: string
  payment_method: string
  failure_reason: string
  attempt_count: number
  transaction_timestamp: string
  merchant_category: string
  recommended_action: string
  recovery_probability: number
  confidence: number
  priority?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface ObservableTransaction extends TransactionListItem {
  customer_id: string
}

export interface CustomerProfile {
  customer_id: string
  tenure_days: number
  total_transactions: number
  successful_transactions: number
  payment_success_rate: number
  average_transaction_amount: number
  previous_recovery_success_rate: number
  contacts_last_7_days: number
}

export interface TransactionsResponse {
  total: number
  limit: number
  offset: number
  items: TransactionListItem[]
}

export interface TransactionDetailResponse {
  transaction: ObservableTransaction
  customer_profile: CustomerProfile
  analysis: AnalyzeResponse['analysis']
  guardrails: AnalyzeResponse['guardrails']
}

export interface AnalyzeRequest {
  transaction: ObservableTransaction
  customer_profile: CustomerProfile
}

export interface AnalyzeResponse {
  analysis: {
    diagnosis: string
    recommended_action: string
    recommended_delay_minutes: number | null
    recovery_probability: number
    confidence: number
    reasoning: string[]
    reason_codes: string[]
    action_scores: Record<string, number>
    estimated_action_probabilities: Record<string, number>
    expected_action_values: Record<string, number>
    model: {
      model_status: string
      model_version: string
      feature_version: string
      training_dataset_size?: number
    }
    priority_score: number
    priority_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  }
  guardrails: {
    original_action: string
    final_action: string
    was_modified: boolean
    guardrail_reasons: string[]
  }
}
