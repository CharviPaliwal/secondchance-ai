import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { runSimulation as runSimulationRequest } from '../services/api'

const stages = [
  'Loading transaction cohort',
  'Evaluating baseline recovery policy',
  'Running SecondChance decisions',
  'Applying guardrails',
  'Simulating outcomes',
  'Calculating impact',
]

export function useSimulation(input: { scenario: string; seed: number }) {
  const queryClient = useQueryClient()
  const runningRef = useRef(false)
  const [stage, setStage] = useState(0)
  const stageTimer = useRef<number | null>(null)
  const simulationMutation = useMutation({
    mutationFn: () => runSimulationRequest(input),
    onSuccess: (result) => {
      queryClient.setQueryData(['comparison'], result)
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  useEffect(() => () => { if (stageTimer.current) window.clearInterval(stageTimer.current) }, [])

  const runSimulation = useCallback(async () => {
    if (runningRef.current) return
    runningRef.current = true
    setStage(0)
    stageTimer.current = window.setInterval(() => setStage((current) => Math.min(current + 1, stages.length - 1)), 300)
    try {
      await simulationMutation.mutateAsync()
      setStage(stages.length - 1)
    } finally {
      if (stageTimer.current) window.clearInterval(stageTimer.current)
      stageTimer.current = null
      runningRef.current = false
    }
  }, [simulationMutation])

  return {
    comparison: simulationMutation.data,
    isIdle: !simulationMutation.data && !simulationMutation.isPending,
    isRunning: simulationMutation.isPending,
    isComplete: Boolean(simulationMutation.data) && !simulationMutation.isPending,
    isError: simulationMutation.isError,
    stage,
    stages,
    runSimulation,
  }
}
