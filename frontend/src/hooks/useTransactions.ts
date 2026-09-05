import { useQuery } from '@tanstack/react-query'

import { getTransactions } from '../services/api'

export function useTransactions(limit = 500) {
  return useQuery({
    queryKey: ['transactions', limit],
    queryFn: () => getTransactions({ limit }),
    staleTime: 30_000,
  })
}
