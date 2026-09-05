import { useQuery } from '@tanstack/react-query'

import { getComparison } from '../services/api'

export function useComparison() {
  return useQuery({ queryKey: ['comparison'], queryFn: () => getComparison(), staleTime: 30_000 })
}
