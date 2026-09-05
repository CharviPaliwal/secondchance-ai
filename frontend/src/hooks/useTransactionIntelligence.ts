import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { analyzeTransaction, getTransaction } from '../services/api'
import type { AnalyzeResponse } from '../types/api'

export function useTransactionIntelligence(
  transactionId: string | null,
  isOpen: boolean,
) {
  const queryClient = useQueryClient()
  const transactionQuery = useQuery({
    queryKey: ['transaction', transactionId],
    queryFn: () => getTransaction(transactionId!),
    enabled: isOpen && Boolean(transactionId),
    staleTime: 5 * 60 * 1000,
  })
  const analysisKey = ['transaction-analysis', transactionId] as const
  const cachedAnalysis = queryClient.getQueryData<AnalyzeResponse>(analysisKey)
  const analysisMutation = useMutation({
    mutationFn: analyzeTransaction,
    onSuccess: (result) => {
      queryClient.setQueryData(analysisKey, result)
    },
  })

  useEffect(() => {
    if (
      isOpen &&
      transactionQuery.data &&
      !cachedAnalysis &&
      analysisMutation.isIdle
    ) {
      analysisMutation.mutate({
        transaction: transactionQuery.data.transaction,
        customer_profile: transactionQuery.data.customer_profile,
      })
    }
  }, [
    analysisMutation,
    cachedAnalysis,
    isOpen,
    transactionQuery.data,
  ])

  const analyze = () => {
    if (!transactionQuery.data) {
      void transactionQuery.refetch()
      return
    }
    analysisMutation.mutate({
      transaction: transactionQuery.data.transaction,
      customer_profile: transactionQuery.data.customer_profile,
    })
  }

  return {
    transaction: transactionQuery.data?.transaction,
    analysis: cachedAnalysis?.analysis,
    isLoadingTransaction: transactionQuery.isLoading,
    isAnalyzing: analysisMutation.isPending,
    isError: transactionQuery.isError || analysisMutation.isError,
    error: transactionQuery.error ?? analysisMutation.error,
    analyze,
    reset: analysisMutation.reset,
  }
}
