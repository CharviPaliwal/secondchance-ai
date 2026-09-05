import { Outlet } from 'react-router-dom'

import '../App.css'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function AppLayout() {
  return <div className="app-shell"><Sidebar /><main className="main-content"><Topbar /><div className="page-transition"><Outlet /></div></main></div>
}
