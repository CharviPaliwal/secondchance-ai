import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ComparisonResponse,
  DashboardResponse,
  TransactionDetailResponse,
  TransactionsResponse,
} from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const REQUEST_TIMEOUT_MS = 15_000

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, signal: controller.signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Recovery intelligence request timed out. Please retry.')
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }

  if (!response.ok) {
    throw new Error(`Recovery intelligence request failed (${response.status})`)
  }

  return response.json() as Promise<T>
}

export function getComparison(options?: { rerun?: boolean }): Promise<ComparisonResponse> {
  return request<ComparisonResponse>(options?.rerun ? '/api/comparison?rerun=true' : '/api/comparison')
}

export function runSimulation(input: { scenario: string; seed: number }): Promise<ComparisonResponse> {
  return request<ComparisonResponse>('/api/simulation/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) })
}

export function getDashboard(): Promise<DashboardResponse> {
  return request<DashboardResponse>('/api/dashboard')
}

export function getTransactions(options?: {
  limit?: number
  offset?: number
}): Promise<TransactionsResponse> {
  const params = new URLSearchParams()
  if (options?.limit) params.set('limit', String(options.limit))
  if (options?.offset) params.set('offset', String(options.offset))
  const query = params.size ? `?${params.toString()}` : ''
  return request<TransactionsResponse>(`/api/transactions${query}`)
}

export function getTransaction(transactionId: string): Promise<TransactionDetailResponse> {
  return request<TransactionDetailResponse>(
    `/api/transactions/${encodeURIComponent(transactionId)}`,
  )
}

export function analyzeTransaction(data: AnalyzeRequest): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}
