import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'

import { useTransactionIntelligence } from '../hooks/useTransactionIntelligence'
import { formatCurrency, formatPercentage } from '../utils/format'
import './TransactionDrawer.css'

const overrideActions = [
  'RETRY_NOW',
  'RETRY_LATER',
  'SEND_REMINDER',
  'UPDATE_PAYMENT_METHOD',
  'ESCALATE_TO_HUMAN',
]

interface TransactionDrawerProps {
  transactionId: string | null
  isOpen: boolean
  onClose: () => void
  onActionQueued?: (transactionId: string) => void
  queueMode?: boolean
}

function humanizeAction(action: string): string {
  return action.replaceAll('_', ' ')
}

export function TransactionDrawer({
  transactionId,
  isOpen,
  onClose,
  onActionQueued,
  queueMode = false,
}: TransactionDrawerProps) {
  const {
    transaction,
    analysis,
    isLoadingTransaction,
    isAnalyzing,
    isError,
    analyze,
  } = useTransactionIntelligence(transactionId, isOpen)
  const [showOverride, setShowOverride] = useState(false)
  const [showStopConfirmation, setShowStopConfirmation] = useState(false)
  const [selectedAction, setSelectedAction] = useState<string | null>(null)
  const [isApproved, setIsApproved] = useState(false)
  const [isStopped, setIsStopped] = useState(false)
  const [isQueued, setIsQueued] = useState(false)
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const displayAction = isStopped
    ? 'STOP_RECOVERY'
    : selectedAction ?? analysis?.recommended_action
  const isLoading = isLoadingTransaction || isAnalyzing

  return (
    <div className="drawer-layer" role="presentation">
      <button
        className="drawer-backdrop"
        aria-label="Close transaction intelligence"
        onClick={onClose}
      />
      <aside className="transaction-drawer" aria-label="Transaction intelligence">
        <header className="drawer-header">
          <div>
            <div className="drawer-label">TRANSACTION INTELLIGENCE</div>
            <div className="drawer-id">{transactionId ?? '--'}</div>
          </div>
          <button className="drawer-close" aria-label="Close drawer" onClick={onClose}>
            <X size={18} />
          </button>
        </header>

        <div className="drawer-content" ref={contentRef}>
          {isLoading && (
            <div className="drawer-scanning">
              <div className="drawer-scan-line" />
              <strong>ANALYZING RECOVERY PATH</strong>
              <span>Evaluating transaction signals</span>
              <span>Calculating recovery probability</span>
              <span>Optimizing customer friction</span>
            </div>
          )}

          {isError && !isLoading && (
            <div className="drawer-error">
              <strong>INTELLIGENCE UNAVAILABLE</strong>
              <p>Unable to generate a recovery recommendation.</p>
              <button className="drawer-outline-button" onClick={analyze}>
                RETRY ANALYSIS
              </button>
            </div>
          )}

          {!isLoading && !isError && transaction && analysis && (
            <>
              <section className="drawer-section">
                <div className="drawer-section-label">TRANSACTION SIGNAL</div>
                <div className="signal-grid">
                  <div><span>AMOUNT</span><strong>{formatCurrency(transaction.amount)}</strong></div>
                  <div><span>FAILURE REASON</span><strong>{transaction.failure_reason}</strong></div>
                  <div><span>PAYMENT METHOD</span><strong>{transaction.payment_method}</strong></div>
                  <div><span>ATTEMPTS</span><strong>{transaction.attempt_count}</strong></div>
                </div>
              </section>

              <section className="drawer-section">
                <div className="drawer-section-label">AI DIAGNOSIS</div>
                <p className="drawer-diagnosis">{analysis.diagnosis}</p>
              </section>

              {queueMode && (
                <section className="drawer-section">
                  <div className="drawer-section-label">CUSTOMER CONTEXT</div>
                  <div className="signal-grid">
                    <div><span>CUSTOMER ID</span><strong>{transaction.customer_id}</strong></div>
                    <div><span>PAYMENT METHOD</span><strong>{transaction.payment_method}</strong></div>
                    <div><span>MERCHANT CATEGORY</span><strong>{transaction.merchant_category}</strong></div>
                    <div><span>ATTEMPT COUNT</span><strong>{transaction.attempt_count}</strong></div>
                  </div>
                </section>
              )}

              <section className="drawer-section">
                <div className="drawer-section-label">RECOMMENDED ACTION</div>
                <div className={`drawer-action ${displayAction === 'STOP_RECOVERY' ? 'danger' : ''}`}>
                  {displayAction ? humanizeAction(displayAction) : '--'}
                </div>
                {isApproved && <div className="drawer-feedback">ACTION APPROVED FOR REVIEW</div>}
                {isQueued && <div className="drawer-feedback">ACTION QUEUED — NOT YET EXECUTED</div>}
                {selectedAction && !isStopped && <div className="drawer-feedback">OVERRIDE SELECTED — NOT PERSISTED</div>}
              </section>

              <section className="drawer-section probability-section">
                <div className="drawer-meter-row"><span>RECOVERY PROBABILITY</span><strong>{formatPercentage(analysis.recovery_probability * 100)}</strong></div>
                <div className="drawer-meter"><div style={{ width: formatPercentage(analysis.recovery_probability * 100) }} /></div>
                <div className="drawer-meter-row"><span>CONFIDENCE</span><strong>{formatPercentage(analysis.confidence * 100)}</strong></div>
                <div className="drawer-meter muted"><div style={{ width: formatPercentage(analysis.confidence * 100) }} /></div>
                <div className="drawer-meter-row"><span>RECOMMENDED DELAY</span><strong>{analysis.recommended_delay_minutes == null ? 'IMMEDIATE' : `${analysis.recommended_delay_minutes} MIN`}</strong></div>
                <div className="drawer-meter-row"><span>EXPECTED RECOVERED VALUE</span><strong>{formatCurrency(transaction.amount * analysis.recovery_probability)}</strong></div>
                <div className="drawer-meter-row"><span>PRIORITY</span><strong>{analysis.priority_level} · {formatCurrency(analysis.priority_score)}</strong></div>
              </section>

              <section className="drawer-section">
                <div className="drawer-section-label">REASONING SIGNALS</div>
                <div className="reasoning-signals">
                  {analysis.reasoning.map((reason) => <div key={reason}>{reason}</div>)}
                </div>
              </section>

              <section className="drawer-section">
                <div className="drawer-section-label">ACTION VALUE RANKING</div>
                <div className="action-value-list">{Object.entries(analysis.expected_action_values).sort(([, first], [, second]) => second - first).map(([action, value]) => <div key={action}><span>{humanizeAction(action)}</span><strong>{formatCurrency(value)}</strong><small>{formatPercentage((analysis.estimated_action_probabilities[action] ?? 0) * 100)} probability</small></div>)}</div>
              </section>

              <section className="drawer-section">
                <div className="drawer-section-label">MODEL &amp; SAFETY</div>
                <div className="reasoning-signals"><div>{analysis.model.model_status} · {analysis.model.model_version}</div>{analysis.reason_codes.map((code) => <div key={code}>{humanizeAction(code)}</div>)}</div>
              </section>

              {showOverride && (
                <section className="drawer-section override-area">
                  <div className="drawer-section-label">OVERRIDE RECOMMENDATION</div>
                  <div className="override-actions">
                    {overrideActions.map((action) => (
                      <button key={action} onClick={() => setSelectedAction(action)}>
                        {humanizeAction(action)}
                      </button>
                    ))}
                  </div>
                </section>
              )}

              {showStopConfirmation && (
                <section className="drawer-section stop-confirmation">
                  <strong>STOP RECOVERY?</strong>
                  <p>This transaction will be removed from the active recovery path.</p>
                  <div>
                    <button className="drawer-outline-button" onClick={() => setShowStopConfirmation(false)}>CANCEL</button>
                    <button className="drawer-danger-button" onClick={() => { setIsStopped(true); setShowStopConfirmation(false) }}>CONFIRM STOP</button>
                  </div>
                </section>
              )}
            </>
          )}
        </div>

        {!isLoading && !isError && analysis && (
          <footer className="drawer-footer">
            {queueMode ? (
              <>
                <button className="drawer-primary-button" onClick={() => { setIsQueued(true); if (transactionId) onActionQueued?.(transactionId) }}>EXECUTE RECOMMENDATION</button>
                <button className="drawer-outline-button" onClick={() => contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' })}>VIEW FULL ANALYSIS</button>
              </>
            ) : (
              <>
                <button className="drawer-primary-button" onClick={() => setIsApproved(true)}>APPROVE ACTION</button>
                <button className="drawer-outline-button" onClick={() => setShowOverride((value) => !value)}>OVERRIDE</button>
                <button className="drawer-danger-button" onClick={() => setShowStopConfirmation(true)}>STOP RECOVERY</button>
              </>
            )}
          </footer>
        )}
      </aside>
    </div>
  )
}
