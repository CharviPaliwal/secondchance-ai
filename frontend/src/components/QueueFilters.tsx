interface QueueFiltersProps {
  search: string
  failureReason: string
  priority: string
  paymentMethod: string
  sort: string
  onSearchChange: (value: string) => void
  onFailureReasonChange: (value: string) => void
  onPriorityChange: (value: string) => void
  onPaymentMethodChange: (value: string) => void
  onSortChange: (value: string) => void
  onRefresh: () => void
}

const failureReasons = [
  'BANK_TIMEOUT',
  'NETWORK_ERROR',
  'INSUFFICIENT_FUNDS',
  'USER_ABANDONED',
  'PAYMENT_DECLINED',
  'CARD_EXPIRED',
  'MANDATE_FAILED',
]

export function QueueFilters({
  search,
  failureReason,
  priority,
  paymentMethod,
  sort,
  onSearchChange,
  onFailureReasonChange,
  onPriorityChange,
  onPaymentMethodChange,
  onSortChange,
  onRefresh,
}: QueueFiltersProps) {
  return (
    <div className="queue-toolbar">
      <div className="queue-toolbar-left">
        <input
          className="queue-search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search transaction or customer ID..."
          aria-label="Search transaction or customer ID"
        />
        <select value={failureReason} onChange={(event) => onFailureReasonChange(event.target.value)} aria-label="Filter by failure reason">
          <option value="">Failure Reason</option>
          {failureReasons.map((reason) => <option key={reason} value={reason}>{reason}</option>)}
        </select>
        <select value={priority} onChange={(event) => onPriorityChange(event.target.value)} aria-label="Filter by priority">
          <option value="">All priorities</option>
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        <select value={paymentMethod} onChange={(event) => onPaymentMethodChange(event.target.value)} aria-label="Filter by payment method">
          <option value="">Payment method</option>
          <option value="CARD">CARD</option><option value="UPI">UPI</option><option value="NETBANKING">NETBANKING</option><option value="WALLET">WALLET</option>
        </select>
      </div>
      <div className="queue-toolbar-right">
        <select value={sort} onChange={(event) => onSortChange(event.target.value)} aria-label="Sort transactions">
          <option value="priority">Priority</option>
          <option value="amount">Amount</option>
          <option value="attempts">Attempts</option>
          <option value="timestamp">Timestamp</option>
        </select>
        <button className="queue-refresh" onClick={onRefresh} aria-label="Refresh recovery queue">REFRESH</button>
      </div>
    </div>
  )
}
