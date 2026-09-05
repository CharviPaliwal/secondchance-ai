import { useEffect, useRef, useState } from 'react'

export function useAnimatedNumber(target: number, duration = 550): number {
  const [value, setValue] = useState(target)
  const previousValue = useRef(target)

  useEffect(() => {
    const startValue = previousValue.current
    const startTime = performance.now()
    let frameId = 0
    const update = (time: number) => {
      const progress = Math.min((time - startTime) / duration, 1)
      setValue(startValue + (target - startValue) * progress)
      if (progress < 1) {
        frameId = requestAnimationFrame(update)
      } else {
        previousValue.current = target
      }
    }
    frameId = requestAnimationFrame(update)
    return () => cancelAnimationFrame(frameId)
  }, [duration, target])

  return value
}
