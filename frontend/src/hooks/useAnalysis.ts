import { useMutation } from '@tanstack/react-query'

import { analyzeTransaction } from '../services/api'

export function useAnalysis() {
  return useMutation({ mutationFn: analyzeTransaction })
}
