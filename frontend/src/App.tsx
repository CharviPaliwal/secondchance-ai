import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AppLayout } from './components/AppLayout'
import Intelligence from './pages/Intelligence'
import Overview from './pages/Overview'
import RecoveryQueue from './pages/RecoveryQueue'
import Settings from './pages/Settings'
import Simulation from './pages/Simulation'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Overview />} />
          <Route path="transactions" element={<RecoveryQueue />} />
          <Route path="recovery-queue" element={<Navigate to="/transactions" replace />} />
          <Route path="intelligence" element={<Intelligence />} />
          <Route path="simulation" element={<Simulation />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
