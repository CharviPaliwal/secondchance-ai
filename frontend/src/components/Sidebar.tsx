import {
  Activity,
  BrainCircuit,
  ChevronRight,
  LayoutDashboard,
  List,
  Settings,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

const navigation = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/transactions', label: 'Transactions', icon: Activity },
  { to: '/intelligence', label: 'Intelligence', icon: BrainCircuit },
  { to: '/simulation', label: 'Simulation', icon: List },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div>
        <div className="brand"><div className="brand-mark"><div className="brand-mark-inner" /></div><div><div className="brand-name">SECONDCHANCE</div><div className="brand-subtitle">RECOVERY INTELLIGENCE</div></div></div>
        <div className="sidebar-section-label">WORKSPACE</div>
        <nav className="navigation">
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink end={end} to={to} key={to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Icon size={17} /><span>{label}</span><ChevronRight size={14} />
            </NavLink>
          ))}
        </nav>
      </div>
      <div className="sidebar-bottom"><div className="system-status"><div className="status-dot" /><div><div className="status-title">SYSTEM OPERATIONAL</div><div className="status-meta">ENGINE v0.1.0</div></div></div></div>
    </aside>
  )
}
