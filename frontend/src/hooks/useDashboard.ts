import { useQuery } from "@tanstack/react-query"
import {
  getComparison,
  getDashboard,
  getTransactions,
} from "../services/api"

export function useDashboard() {
  const dashboardQuery = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
  })
  const comparisonQuery = useQuery({
    queryKey: ["comparison"],
    queryFn: () => getComparison(),
  })

  const transactionsQuery = useQuery({
    queryKey: ["transactions"],
    queryFn: () => getTransactions(),
  })

  return {
    comparison: comparisonQuery.data,
    dashboard: dashboardQuery.data,
    transactions: transactionsQuery.data,

    isLoading:
      comparisonQuery.isLoading ||
      dashboardQuery.isLoading ||
      transactionsQuery.isLoading,

    isError:
      comparisonQuery.isError ||
      dashboardQuery.isError ||
      transactionsQuery.isError,

    dashboardQuery,
    comparisonQuery,
    transactionsQuery,

    refetch: async () => {
      await Promise.all([dashboardQuery.refetch(), comparisonQuery.refetch(), transactionsQuery.refetch()])
    },
  }
}
