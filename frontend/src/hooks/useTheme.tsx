import { createContext, useContext, useEffect, useMemo, useState } from 'react'

export type ThemePreference = 'dark' | 'light' | 'system'

interface ThemeContextValue {
  preference: ThemePreference
  setPreference: (preference: ThemePreference) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)
const storageKey = 'secondchance-theme'

function readPreference(): ThemePreference {
  const stored = localStorage.getItem(storageKey)
  return stored === 'light' || stored === 'system' || stored === 'dark' ? stored : 'dark'
}

function resolvedTheme(preference: ThemePreference): 'light' | 'dark' {
  return preference === 'system'
    ? window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
    : preference
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(readPreference)
  useEffect(() => {
    const apply = () => document.documentElement.dataset.theme = resolvedTheme(preference)
    apply()
    localStorage.setItem(storageKey, preference)
    const media = window.matchMedia('(prefers-color-scheme: light)')
    if (preference === 'system') media.addEventListener('change', apply)
    return () => media.removeEventListener('change', apply)
  }, [preference])
  const value = useMemo(() => ({ preference, setPreference: setPreferenceState }), [preference])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const value = useContext(ThemeContext)
  if (!value) throw new Error('useTheme must be used inside ThemeProvider')
  return value
}
