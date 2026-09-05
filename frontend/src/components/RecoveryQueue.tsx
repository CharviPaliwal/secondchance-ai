import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { getTransactions } from '../services/api'
import type { TransactionListItem } from '../types/api'
import { formatCompactCurrency, formatCurrency } from '../utils/format'
import { QueueFilters } from './QueueFilters'
import { TransactionDrawer } from './TransactionDrawer'
import './RecoveryQueue.css'

const PAGE_SIZE = 10

function actionClass(action: string): string {
  return action.toLowerCase().replaceAll('_', '-')
}

function priorityFor(transaction: TransactionListItem): 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' {
  if (transaction.priority) return transaction.priority
  const value = transaction.amount * transaction.recovery_probability
  if (value >= 20_000 || (transaction.amount >= 15_000 && transaction.attempt_count >= 3)) return 'CRITICAL'
  if (value >= 9_000 || transaction.amount >= 12_000) return 'HIGH'
  if (transaction.attempt_count >= 2 || transaction.recovery_probability >= .55) return 'MEDIUM'
  return 'LOW'
}

export function RecoveryQueue() {
  const [search, setSearch] = useState('')
  const [failureReason, setFailureReason] = useState('')
  const [priority, setPriority] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('')
  const [sort, setSort] = useState('priority')
  const [page, setPage] = useState(1)
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | null>(null)
  const [queuedTransactionIds, setQueuedTransactionIds] = useState<Set<string>>(new Set())
  const transactionsQuery = useQuery({
    queryKey: ['recovery-queue'],
    queryFn: () => getTransactions({ limit: 500 }),
    staleTime: 30_000,
  })
  const items = transactionsQuery.data?.items
  const filteredItems = useMemo(() => {
    const queueItems = items ?? []
    const visible = queueItems.filter((transaction) => (
      (transaction.transaction_id.toLowerCase().includes(search.toLowerCase()) || transaction.customer_id.toLowerCase().includes(search.toLowerCase())) &&
      (!failureReason || transaction.failure_reason === failureReason) &&
      (!priority || priorityFor(transaction) === priority) &&
      (!paymentMethod || transaction.payment_method === paymentMethod)
    ))
    return visible.sort((first, second) => {
      if (sort === 'amount') return second.amount - first.amount
      if (sort === 'attempts') return second.attempt_count - first.attempt_count
      if (sort === 'timestamp') return new Date(second.transaction_timestamp).getTime() - new Date(first.transaction_timestamp).getTime()
      return ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].indexOf(priorityFor(second)) - ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].indexOf(priorityFor(first))
    })
  }, [failureReason, items, paymentMethod, priority, search, sort])
  const totalPages = Math.max(1, Math.ceil(filteredItems.length / PAGE_SIZE))
  const safePage = Math.min(page, totalPages)
  const pageItems = filteredItems.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE)
  const queueItems = items ?? []
  const atRiskValue = queueItems.reduce((total, item) => total + item.amount, 0)
  const highValue = queueItems.filter((item) => priorityFor(item) === 'CRITICAL' || priorityFor(item) === 'HIGH').length
  const opportunities = queueItems.filter((item) => item.recovery_probability >= .5 && item.recommended_action !== 'STOP_RECOVERY').length

  const updateFilter = (setter: (value: string) => void) => (value: string) => {
    setter(value)
    setPage(1)
  }
  const queueAction = (transactionId: string) => {
    setQueuedTransactionIds((current) => new Set(current).add(transactionId))
  }

  return (
    <section className="queue-page">
      <div className="queue-page-header">
        <div>
          <div className="eyebrow"><span className="live-dot" />TRANSACTIONS</div>
          <h1>Recovery Queue</h1>
          <p>Review failed payments and prioritize the next recovery action.</p>
        </div>
        <div className="queue-live-status"><span className="status-dot" />{transactionsQuery.data?.total ?? '--'} TRANSACTIONS ANALYZED</div>
      </div>

      <QueueFilters
        search={search}
        failureReason={failureReason}
        priority={priority}
        paymentMethod={paymentMethod}
        sort={sort}
        onSearchChange={updateFilter(setSearch)}
        onFailureReasonChange={updateFilter(setFailureReason)}
        onPriorityChange={updateFilter(setPriority)}
        onPaymentMethodChange={updateFilter(setPaymentMethod)}
        onSortChange={updateFilter(setSort)}
        onRefresh={() => void transactionsQuery.refetch()}
      />

      <div className="queue-summary-strip">
        <div><span>TRANSACTIONS AT RISK</span><strong>{transactionsQuery.data?.total ?? '--'}</strong></div>
        <div><span>TOTAL REVENUE AT RISK</span><strong>{queueItems.length ? formatCompactCurrency(atRiskValue) : '--'}</strong></div>
        <div><span>HIGH-VALUE TRANSACTIONS</span><strong>{queueItems.length ? highValue : '--'}</strong><small>Critical + high priority</small></div>
        <div><span>RECOVERY OPPORTUNITIES</span><strong>{queueItems.length ? opportunities : '--'}</strong><small>Probability ≥ 50%</small></div>
      </div>

      <div className="queue-table-panel">
        <div className="queue-page-table">
          <div className="queue-page-row queue-page-table-header">
            <span>TRANSACTION</span><span>CUSTOMER</span><span>AMOUNT</span><span>FAILURE REASON</span><span>ATTEMPTS</span><span>PAYMENT METHOD</span><span>TIMESTAMP</span><span>PRIORITY</span><span>ACTION</span>
          </div>
          {transactionsQuery.isLoading && Array.from({ length: PAGE_SIZE }, (_, index) => <div className="queue-page-row queue-skeleton-row" key={index}><span /><span /><span /><span /><span /><span /><span /></div>)}
          {transactionsQuery.isError && <div className="queue-operational-state"><strong>UNABLE TO LOAD RECOVERY QUEUE</strong><button onClick={() => void transactionsQuery.refetch()}>RETRY</button></div>}
          {!transactionsQuery.isLoading && !transactionsQuery.isError && pageItems.map((transaction) => (
            <div
              className="queue-page-row queue-data-row"
              key={transaction.transaction_id}
              role="button"
              tabIndex={0}
              onClick={() => setSelectedTransactionId(transaction.transaction_id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  setSelectedTransactionId(transaction.transaction_id)
                }
              }}
            >
              <span className="queue-transaction"><strong>{transaction.transaction_id}</strong><small>{transaction.merchant_category}</small></span>
              <span className="queue-customer">{transaction.customer_id}</span>
              <span className="queue-amount">{formatCurrency(transaction.amount)}</span>
              <span className="queue-failure">{transaction.failure_reason}</span>
              <span className="queue-confidence">{transaction.attempt_count}</span>
              <span className="queue-failure">{transaction.payment_method}</span>
              <span className="queue-failure">{new Date(transaction.transaction_timestamp).toLocaleDateString('en-IN')}</span>
              <span className={`queue-priority ${priorityFor(transaction).toLowerCase()}`}>{priorityFor(transaction)}</span>
              <span><i className={`queue-action ${actionClass(transaction.recommended_action)}`}>{queuedTransactionIds.has(transaction.transaction_id) ? 'QUEUED' : transaction.recommended_action.replaceAll('_', ' ')}</i></span>
            </div>
          ))}
          {!transactionsQuery.isLoading && !transactionsQuery.isError && !pageItems.length && <div className="queue-operational-state">NO TRANSACTIONS MATCH THE CURRENT FILTERS</div>}
        </div>
        {!transactionsQuery.isLoading && !transactionsQuery.isError && (
          <div className="queue-pagination">
            <span>Showing {filteredItems.length ? (safePage - 1) * PAGE_SIZE + 1 : 0}–{Math.min(safePage * PAGE_SIZE, filteredItems.length)} of {filteredItems.length}</span>
            <div>
              <button disabled={safePage === 1} onClick={() => setPage(safePage - 1)}>Previous</button>
              {[1, 2, 3].filter((item) => item <= totalPages).map((item) => <button className={safePage === item ? 'active' : ''} key={item} onClick={() => setPage(item)}>{item}</button>)}
              {totalPages > 4 && <span>...</span>}
              {totalPages > 3 && <button className={safePage === totalPages ? 'active' : ''} onClick={() => setPage(totalPages)}>{totalPages}</button>}
              <button disabled={safePage === totalPages} onClick={() => setPage(safePage + 1)}>Next</button>
            </div>
          </div>
        )}
      </div>

      {selectedTransactionId && <TransactionDrawer key={selectedTransactionId} transactionId={selectedTransactionId} isOpen onClose={() => setSelectedTransactionId(null)} onActionQueued={queueAction} queueMode />}
    </section>
  )
}
