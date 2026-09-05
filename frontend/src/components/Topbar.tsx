import { useEffect, useMemo, useState } from 'react'
import { Bell, CheckCheck, ChevronRight, Command, LogOut, Search, Settings2, X } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useComparison } from '../hooks/useComparison'
import { useTransactions } from '../hooks/useTransactions'
import { formatCompactCurrency } from '../utils/format'
import { TransactionDrawer } from './TransactionDrawer'

const pageNames: Record<string, string> = { '/': 'OVERVIEW', '/transactions': 'TRANSACTIONS', '/intelligence': 'INTELLIGENCE', '/simulation': 'SIMULATION LAB', '/settings': 'SETTINGS' }
const pages = [{ label: 'Overview', path: '/' }, { label: 'Transactions', path: '/transactions' }, { label: 'Intelligence', path: '/intelligence' }, { label: 'Simulation', path: '/simulation' }, { label: 'Settings', path: '/settings' }]
const readKey = 'secondchance-read-notifications'

export function Topbar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const transactions = useTransactions()
  const comparison = useComparison()
  const [searchOpen, setSearchOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selectedTransaction, setSelectedTransaction] = useState<string | null>(null)
  const [signedOut, setSignedOut] = useState(false)
  const [read, setRead] = useState<string[]>(() => { try { return JSON.parse(localStorage.getItem(readKey) ?? '[]') } catch { return [] } })
  const items = transactions.data?.items ?? []
  const notifications = useMemo(() => {
    const highValue = items.filter((item) => item.amount >= 12_000).length
    const escalations = items.filter((item) => item.recommended_action === 'ESCALATE_TO_HUMAN').length
    const opportunities = items.filter((item) => item.recovery_probability >= .5 && item.recommended_action !== 'STOP_RECOVERY').length
    return [
      { id: 'high-value', text: `${highValue} high-value transactions require attention` },
      { id: 'revenue', text: `Simulation shows ${formatCompactCurrency(comparison.data?.improvement.additional_recovered_revenue ?? 0)} additional recovered revenue` },
      { id: 'escalations', text: `${escalations} transactions recommended for human escalation` },
      { id: 'opportunities', text: `Recovery queue contains ${opportunities} opportunities` },
    ]
  }, [comparison.data?.improvement.additional_recovered_revenue, items])
  const unread = notifications.filter((item) => !read.includes(item.id))
  const normalized = query.trim().toLowerCase()
  const matchingTransactions = normalized ? items.filter((item) => [item.transaction_id, item.customer_id, item.failure_reason].some((value) => value.toLowerCase().includes(normalized))).slice(0, 6) : items.slice(0, 5)
  const matchingPages = pages.filter((page) => !normalized || page.label.toLowerCase().includes(normalized))

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setSearchOpen(true) }
      if (event.key === 'Escape') { setSearchOpen(false); setNotificationsOpen(false); setProfileOpen(false); setShortcutsOpen(false) }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
  const markAllRead = () => { const next = notifications.map((item) => item.id); setRead(next); localStorage.setItem(readKey, JSON.stringify(next)) }
  const navigateTo = (path: string) => { navigate(path); setSearchOpen(false); setQuery('') }

  return <>
    <header className="topbar">
      <div className="breadcrumb">WORKSPACE<span className="breadcrumb-divider">/</span><span className="breadcrumb-active">{pageNames[pathname] ?? 'OVERVIEW'}</span></div>
      <div className="topbar-actions">
        <button className="icon-button" aria-label="Open global search" onClick={() => setSearchOpen(true)}><Search size={17} /></button>
        <div className="topbar-menu"><button className="icon-button notification-button" aria-label="Notifications" onClick={() => { setNotificationsOpen((value) => !value); setProfileOpen(false) }}><Bell size={17} />{unread.length > 0 && <span className="notification-dot" />}</button>{notificationsOpen && <section className="topbar-popover notifications-popover"><header><div><span>NOTIFICATIONS</span><strong>{unread.length} unread</strong></div><button onClick={markAllRead}><CheckCheck size={14} />MARK ALL READ</button></header>{unread.length ? notifications.map((item) => <button className={`notification-item ${read.includes(item.id) ? 'read' : ''}`} key={item.id} onClick={() => { const next = [...new Set([...read, item.id])]; setRead(next); localStorage.setItem(readKey, JSON.stringify(next)) }}><i />{item.text}</button>) : <p className="popover-empty">You’re all caught up.</p>}</section>}</div>
        <div className="topbar-menu"><button className="user-avatar" aria-label="Open account menu" onClick={() => { setProfileOpen((value) => !value); setNotificationsOpen(false) }}>CP</button>{profileOpen && <section className="topbar-popover account-popover"><div className="account-heading"><strong>SecondChance Operator</strong><span>Revenue Operations</span></div><button onClick={() => { navigate('/settings'); setProfileOpen(false) }}><Settings2 size={14} />Preferences</button><button onClick={() => { setShortcutsOpen(true); setProfileOpen(false) }}><Command size={14} />Keyboard shortcuts</button><button onClick={() => { setSignedOut(true); setProfileOpen(false) }}><LogOut size={14} />Sign out</button></section>}</div>
      </div>
    </header>
    {signedOut && <div className="topbar-toast">SIGNED OUT OF THIS LOCAL SESSION <button onClick={() => setSignedOut(false)}><X size={13} /></button></div>}
    {searchOpen && <div className="command-layer" role="dialog" aria-modal="true" aria-label="Global search"><button className="command-backdrop" onClick={() => setSearchOpen(false)} aria-label="Close search" /><section className="command-palette"><div className="command-input"><Search size={17} /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search transactions, customers, pages, or signals" /><kbd>ESC</kbd></div><div className="command-results"><span>TRANSACTIONS</span>{matchingTransactions.map((item) => <button key={item.transaction_id} onClick={() => { setSelectedTransaction(item.transaction_id); setSearchOpen(false) }}><strong>{item.transaction_id}</strong><small>{item.customer_id} · {item.failure_reason}</small><ChevronRight size={14} /></button>)}<span>PAGES</span>{matchingPages.map((page) => <button key={page.path} onClick={() => navigateTo(page.path)}><strong>{page.label}</strong><small>{page.path}</small><ChevronRight size={14} /></button>)}<span>SIGNALS</span>{['BANK_TIMEOUT', 'PAYMENT_DECLINED', 'CARD_EXPIRED'].filter((signal) => !normalized || signal.toLowerCase().includes(normalized)).map((signal) => <button key={signal} onClick={() => { setQuery(signal); navigateTo('/intelligence') }}><strong>{signal}</strong><small>Failure intelligence</small><ChevronRight size={14} /></button>)}</div></section></div>}
    {shortcutsOpen && <div className="command-layer" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts"><button className="command-backdrop" onClick={() => setShortcutsOpen(false)} aria-label="Close shortcuts" /><section className="shortcut-modal"><header><strong>Keyboard shortcuts</strong><button onClick={() => setShortcutsOpen(false)}><X size={16} /></button></header><div><span>Open global search</span><kbd>⌘ / Ctrl K</kbd></div><div><span>Close overlays</span><kbd>Esc</kbd></div></section></div>}
    {selectedTransaction && <TransactionDrawer transactionId={selectedTransaction} isOpen onClose={() => setSelectedTransaction(null)} />}
  </>
}
