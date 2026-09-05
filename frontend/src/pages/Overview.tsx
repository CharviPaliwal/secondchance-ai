import { useState } from 'react'
import { Activity, ArrowUpRight, ShieldAlert, TrendingUp, WalletCards, Zap } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { TransactionDrawer } from '../components/TransactionDrawer'
import { useDashboard } from '../hooks/useDashboard'
import { formatCompactCurrency, formatCurrency, formatPercentage } from '../utils/format'

export default function Overview() {
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | null>(null)
  const { comparison, transactions, dashboardQuery, comparisonQuery, transactionsQuery } = useDashboard()
  const navigate = useNavigate()

  const secondchance = comparison?.secondchance
  const improvement = comparison?.improvement
  const queueTransactions = transactions?.items.slice(0, 6) ?? []
  const priorityTransaction = queueTransactions[0]
  const metrics = [
    ['RECOVERY RATE', secondchance ? formatPercentage(secondchance.recovery_rate) : '--', improvement ? `+${formatPercentage(improvement.recovery_rate_improvement)}` : '--', TrendingUp, `Baseline ${comparison ? formatPercentage(comparison.baseline.recovery_rate) : '--'}`],
    ['RECOVERED REVENUE', secondchance ? formatCompactCurrency(secondchance.recovered_revenue) : '--', improvement ? `+${formatCompactCurrency(improvement.additional_recovered_revenue)}` : '--', WalletCards, `Baseline ${comparison ? formatCompactCurrency(comparison.baseline.recovered_revenue) : '--'} · Delta ${improvement ? formatCompactCurrency(improvement.additional_recovered_revenue) : '--'}`],
    ['ACTIVE RECOVERIES', '--', '--', Activity, 'Review live opportunities in Transactions'],
    ['AVG. FRICTION', secondchance ? secondchance.average_friction_per_transaction.toFixed(2) : '--', improvement ? improvement.friction_difference.toFixed(2) : '--', ShieldAlert, `Strategy total ${secondchance?.total_friction_cost.toFixed(0) ?? '--'}`],
  ] as const

  return <>
    <section className="dashboard-content">
      {(dashboardQuery.isError && comparisonQuery.isError && transactionsQuery.isError) && <div className="overview-inline-error">RECOVERY INTELLIGENCE UNAVAILABLE <button onClick={() => void Promise.all([dashboardQuery.refetch(), comparisonQuery.refetch(), transactionsQuery.refetch()])}>RETRY</button></div>}
      <div className="page-header"><div><div className="eyebrow"><span className="live-dot" />LIVE RECOVERY INTELLIGENCE</div><h1>Revenue recovery,<br />without the guesswork.</h1><p>SecondChance analyzes failed transactions and recommends the highest-probability recovery action while minimizing unnecessary customer friction.</p></div><button className="primary-action" onClick={() => navigate('/simulation?autostart=true')}><Zap size={16} />RUN SIMULATION</button></div>
      <div className="metrics-grid">{metrics.map(([label, value, change, Icon, detail]) => <div className="metric-card" key={label}><div className="metric-top"><Icon className="metric-icon" size={17} /><span className="metric-change positive">{change}</span></div><div className="metric-value">{value}</div><div className="metric-label">{label}</div><div className="metric-detail">{detail}</div></div>)}</div>
      <div className="content-grid">
        <div className="panel"><div className="panel-header"><div><div className="panel-label">RECOVERY PERFORMANCE</div><h2>Recovery trajectory</h2></div><div className="legend"><span><i className="legend-dot accent" />SecondChance</span><span><i className="legend-dot muted" />Baseline</span></div></div><div className="chart-placeholder"><div className="chart-grid"><span /><span /><span /><span /><span /></div><svg className="trajectory-chart" viewBox="0 0 700 260" preserveAspectRatio="none"><polyline points="0,210 80,190 160,175 240,160 320,135 400,120 480,90 560,70 640,45 700,30" fill="none" stroke="currentColor" strokeWidth="3" /><polyline points="0,215 80,210 160,200 240,195 320,180 400,170 480,160 560,150 640,140 700,130" fill="none" stroke="#8c9099" strokeWidth="2" strokeDasharray="5 6" /></svg><div className="chart-axis"><span>MON</span><span>TUE</span><span>WED</span><span>THU</span><span>FRI</span><span>SAT</span><span>SUN</span></div></div></div>
        <div className="panel"><div className="panel-header"><div><div className="panel-label">PRIORITY SIGNAL</div><h2>Needs attention</h2></div><div className="signal-indicator"><span />HIGH VALUE</div></div><div className="priority-content"><div className="priority-id">{priorityTransaction?.transaction_id ?? '--'}</div><div className="priority-amount">{priorityTransaction ? formatCurrency(priorityTransaction.amount) : '--'}</div><div className="priority-reason">{priorityTransaction?.failure_reason ?? '--'}</div><div className="recommendation"><div className="recommendation-label">RECOMMENDED ACTION</div><div className="recommendation-value">{priorityTransaction?.recommended_action.replaceAll('_', ' ') ?? '--'}</div></div><div className="confidence-row"><span>RECOVERY CONFIDENCE</span><strong>{priorityTransaction ? formatPercentage(priorityTransaction.confidence * 100) : '--'}</strong></div><div className="confidence-bar"><div style={{ width: priorityTransaction ? formatPercentage(priorityTransaction.confidence * 100) : '0%' }} /></div></div></div>
      </div>
      <div className="panel queue-panel"><div className="panel-header"><div><div className="panel-label">LIVE RECOVERY QUEUE</div><h2>Transactions requiring action</h2></div><button className="text-button" onClick={() => navigate('/transactions')}>VIEW ALL <ArrowUpRight size={13} /></button></div><div className="queue-table"><div className="queue-row queue-header"><span>TRANSACTION</span><span>FAILURE SIGNAL</span><span>AMOUNT</span><span>RECOMMENDATION</span><span>CONFIDENCE</span></div>{queueTransactions.map((transaction) => <div className="queue-row" key={transaction.transaction_id} role="button" tabIndex={0} onClick={() => setSelectedTransactionId(transaction.transaction_id)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedTransactionId(transaction.transaction_id) } }}><span className="transaction-id">{transaction.transaction_id}</span><span className="failure-reason">{transaction.failure_reason}</span><span className="transaction-amount">{formatCurrency(transaction.amount)}</span><span><span className={`action-tag ${transaction.recommended_action === 'STOP_RECOVERY' ? 'danger' : ''}`}>{transaction.recommended_action.replaceAll('_', ' ')}</span></span><span className="confidence-value">{formatPercentage(transaction.confidence * 100)}</span></div>)}</div></div>
    </section>
    {selectedTransactionId && <TransactionDrawer key={selectedTransactionId} transactionId={selectedTransactionId} isOpen onClose={() => setSelectedTransactionId(null)} />}
  </>
}
