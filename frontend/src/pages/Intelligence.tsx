import { useMemo, useState } from 'react'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { TransactionDrawer } from '../components/TransactionDrawer'
import { useTransactions } from '../hooks/useTransactions'
import { formatCompactCurrency, formatCurrency, formatPercentage } from '../utils/format'
import './OperationalPages.css'

const colors = ['#d9ff57', '#8cc7ff', '#eac65e', '#ff9a67', '#ff695f', '#a794ff']
const humanize = (value: string) => value.replaceAll('_', ' ')

export default function Intelligence() {
  const transactions = useTransactions()
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const items = transactions.data?.items ?? []
  const failureData = useMemo(() => Object.values(items.reduce<Record<string, { name: string; count: number; revenue: number }>>((all, item) => { const entry = all[item.failure_reason] ?? { name: humanize(item.failure_reason), count: 0, revenue: 0 }; entry.count += 1; entry.revenue += item.amount; all[item.failure_reason] = entry; return all }, {})), [items])
  const paymentData = useMemo(() => Object.values(items.reduce<Record<string, { name: string; count: number; revenue: number }>>((all, item) => { const entry = all[item.payment_method] ?? { name: item.payment_method, count: 0, revenue: 0 }; entry.count += 1; entry.revenue += item.amount; all[item.payment_method] = entry; return all }, {})), [items])
  const actionData = useMemo(() => Object.values(items.reduce<Record<string, { name: string; count: number }>>((all, item) => { const entry = all[item.recommended_action] ?? { name: humanize(item.recommended_action), count: 0 }; entry.count += 1; all[item.recommended_action] = entry; return all }, {})), [items])
  const matches = items.filter((item) => item.transaction_id.toLowerCase().includes(search.toLowerCase()) || item.customer_id.toLowerCase().includes(search.toLowerCase())).slice(0, 8)
  const total = items.length || 1
  if (transactions.isLoading) return <section className="operational-page"><div className="operational-state">LOADING RECOVERY INTELLIGENCE</div></section>
  if (transactions.isError) return <section className="operational-page"><div className="operational-state error">INTELLIGENCE UNAVAILABLE<button onClick={() => void transactions.refetch()}>RETRY</button></div></section>
  if (!items.length) return <section className="operational-page"><div className="operational-state">NO TRANSACTIONS AVAILABLE FOR ANALYSIS</div></section>
  return <section className="operational-page intelligence-page">
    <div className="operational-header"><div className="eyebrow"><span className="live-dot" />RECOVERY INTELLIGENCE</div><h1>Why payments fail. Why recovery succeeds.</h1><p>Understand why revenue is at risk and how SecondChance prioritizes intervention.</p></div>
    <div className="intelligence-grid">
      <section className="intel-panel intel-wide"><header><span>FAILURE INTELLIGENCE</span><h2>Failure reason distribution</h2></header><div className="intel-chart"><ResponsiveContainer width="100%" height={240}><BarChart data={failureData}><XAxis dataKey="name" hide /><YAxis hide /><Tooltip contentStyle={{ background: '#141519', border: '1px solid #272930' }} /><Bar dataKey="count">{failureData.map((_, index) => <Cell key={index} fill={colors[index % colors.length]} />)}</Bar></BarChart></ResponsiveContainer></div><div className="intel-breakdown">{failureData.map((row) => <div key={row.name}><span>{row.name}</span><strong>{row.count} · {formatCompactCurrency(row.revenue)}</strong><small>{formatPercentage(row.count / total * 100)}</small></div>)}</div></section>
      <section className="intel-panel"><header><span>RECOVERY SIGNALS</span><h2>Decision inputs</h2></header><div className="signal-list">{[['Payment success rate','Reliability of past payments'],['Attempt count','Avoids repeated retries'],['Failure reason','Separates temporary from structural'],['Previous recovery','Learns recovery history'],['Contact fatigue','Limits unnecessary outreach'],['Transaction value','Prioritizes recoverable value']].map(([title, copy]) => <div key={title}><strong>{title}</strong><span>{copy}</span></div>)}</div></section>
      <section className="intel-panel"><header><span>PAYMENT METHOD INTELLIGENCE</span><h2>Payment behavior</h2></header><div className="intel-breakdown">{paymentData.map((row) => <div key={row.name}><span>{row.name}</span><strong>{row.count} cases</strong><small>Avg. {formatCurrency(row.revenue / row.count)}</small></div>)}</div></section>
      <section className="intel-panel"><header><span>RECOMMENDED ACTIONS</span><h2>Intervention distribution</h2></header><div className="action-bars">{actionData.map((row) => <div key={row.name}><span>{row.name}</span><i><b style={{ width: `${row.count / total * 100}%` }} /></i><strong>{row.count}</strong></div>)}</div></section>
    </div>
    <section className="intel-panel inspector"><header><span>DECISION INSPECTOR</span><h2>Inspect a transaction decision</h2></header><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search transaction or customer ID" aria-label="Search transactions" /><div className="inspector-results">{matches.map((item) => <button onClick={() => setSelectedId(item.transaction_id)} key={item.transaction_id}><span>{item.transaction_id}</span><span>{item.customer_id}</span><strong>{formatCurrency(item.amount)}</strong><i>{humanize(item.recommended_action)}</i></button>)}</div></section>
    {selectedId && <TransactionDrawer transactionId={selectedId} isOpen onClose={() => setSelectedId(null)} />}
  </section>
}
