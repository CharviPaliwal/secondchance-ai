import { useState } from 'react'
import { useTheme } from '../hooks/useTheme'
import './OperationalPages.css'

const defaults = { retries: 3, highValue: 15000, contacts: 2, probability: 45, escalation: 75, density: 'comfortable', rowSize: 'standard', autoRefresh: true }
type SettingsValue = typeof defaults
const load = (): SettingsValue => { try { return { ...defaults, ...JSON.parse(localStorage.getItem('secondchance-settings') ?? '{}') } } catch { return defaults } }

export default function Settings() {
  const [settings, setSettings] = useState<SettingsValue>(load)
  const { preference, setPreference } = useTheme()
  const [saved, setSaved] = useState(false)
  const update = <K extends keyof SettingsValue>(key: K, value: SettingsValue[K]) => { setSaved(false); setSettings((current) => ({ ...current, [key]: value })) }
  const save = () => { localStorage.setItem('secondchance-settings', JSON.stringify(settings)); setSaved(true) }
  const numeric = (key: keyof SettingsValue, label: string) => <label className="setting-field" key={String(key)}><span>{label}</span><input type="number" value={settings[key] as number} onChange={(event) => update(key, Number(event.target.value))} /></label>
  return <section className="operational-page settings-page"><div className="operational-header"><div className="eyebrow"><span className="live-dot" />SYSTEM SETTINGS</div><h1>Configure recovery policy and operational guardrails.</h1><p>These settings are stored in this browser and do not change backend behavior.</p></div>
    <div className="settings-form"><section><header><span>RECOVERY POLICY</span><h2>Local operating thresholds</h2></header><div className="settings-fields">{numeric('retries', 'Maximum retry attempts')}{numeric('highValue', 'High-value transaction threshold (₹)')}{numeric('contacts', 'Maximum customer contacts / 7 days')}{numeric('probability', 'Minimum recovery probability (%)')}{numeric('escalation', 'Human escalation threshold (%)')}</div></section>
    <section><header><span>GUARDRAILS</span><h2>Safety rules in effect</h2></header><ul className="guardrail-list"><li>Stop retrying after excessive attempts.</li><li>Prevent repeated customer contact within seven days.</li><li>Escalate high-value risky retries for human review.</li><li>Stop low-probability retries to control friction.</li></ul></section>
    <section><header><span>INTERFACE</span><h2>Console preferences</h2></header><div className="settings-fields"><label className="setting-field"><span>Theme</span><select value={preference} onChange={(e) => setPreference(e.target.value as 'dark' | 'light' | 'system')}><option value="dark">Dark</option><option value="light">Light</option><option value="system">System</option></select></label><label className="setting-field"><span>Density</span><select value={settings.density} onChange={(e) => update('density', e.target.value)}><option value="compact">Compact</option><option value="comfortable">Comfortable</option></select></label><label className="setting-field"><span>Table row size</span><select value={settings.rowSize} onChange={(e) => update('rowSize', e.target.value)}><option value="compact">Compact</option><option value="standard">Standard</option><option value="large">Large</option></select></label><label className="toggle-field"><span>Auto-refresh</span><input type="checkbox" checked={settings.autoRefresh} onChange={(e) => update('autoRefresh', e.target.checked)} /></label></div></section></div>
    <div className="settings-actions"><button onClick={() => { setSettings(defaults); setSaved(false) }}>RESET TO DEFAULTS</button><button className="save" onClick={save}>SAVE CHANGES</button>{saved && <span>SAVED LOCALLY</span>}</div>
  </section>
}
