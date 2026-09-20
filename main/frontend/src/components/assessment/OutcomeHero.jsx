import Badge, { gradeTone } from '../ui/Badge'

/** Large hero card at the top of the result page */
export default function OutcomeHero({ result }) {
  const profile = result?.profile ?? {}
  const evidence = profile.evidence ?? {}
  const cashflow = profile.cashflow ?? {}
  const repayment = profile.repayment ?? {}
  const readiness = profile.readiness_index

  const blocked = Boolean(repayment.new_credit_blocked)
  const stress  = cashflow.stress_probability

  // Determine outcome
  let outcome, outcomeSub, heroBg, heroBorder, heroText
  if (blocked) {
    outcome    = 'Credit Blocked'
    outcomeSub = 'Unresolved repayment obligation — new credit is not advisable'
    heroBg     = 'bg-sage-error-container'
    heroBorder = 'border-sage-on-error-container/20'
    heroText   = 'text-sage-on-error-container'
  } else if (stress == null) {
    outcome    = 'Insufficient Data'
    outcomeSub = 'More verified transaction history is needed for a full assessment'
    heroBg     = 'bg-sage-warning-container'
    heroBorder = 'border-sage-warning/30'
    heroText   = 'text-sage-warning'
  } else {
    outcome    = 'Ready for Lender Review'
    outcomeSub = 'Evidence quality and cash-flow history meet minimum assessment thresholds'
    heroBg     = 'bg-sage-primary-container'
    heroBorder = 'border-sage-primary/20'
    heroText   = 'text-sage-on-primary-container'
  }

  const grade = evidence.evidence_grade ?? '—'
  const readinessText = readiness != null ? readiness.toFixed(1) : '—'

  return (
    <div className={`rounded-lg border ${heroBg} ${heroBorder} p-6 sm:p-8`}>
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-6">
        {/* Left: identity + outcome */}
        <div className="flex-1 min-w-0">
          <p className="text-label-md text-sage-on-surface-var mb-1 font-jakarta">
            Assessment for
          </p>
          <h1 className="text-headline-sm font-jakarta font-semibold text-sage-on-surface truncate mb-3">
            {result?.borrower_id ?? 'Unknown'}
          </h1>

          <div className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 border ${heroBorder} ${heroBg}`}>
            <span className={`w-2 h-2 rounded-full ${blocked ? 'bg-sage-error' : stress == null ? 'bg-sage-warning' : 'bg-sage-success'}`} />
            <span className={`text-label-lg font-jakarta font-semibold ${heroText}`}>{outcome}</span>
          </div>

          <p className="mt-3 text-body-md text-sage-on-surface-var font-jakarta max-w-lg">
            {outcomeSub}
          </p>
        </div>

        {/* Right: key metrics */}
        <div className="flex flex-row sm:flex-col gap-4 sm:gap-3 sm:items-end">
          {/* Readiness index */}
          <div className="text-center sm:text-right">
            <p className="text-label-sm text-sage-on-surface-var font-jakarta uppercase tracking-wider mb-0.5">
              Readiness
            </p>
            <p className="text-display font-jakarta font-semibold text-sage-on-surface leading-none" style={{ fontSize: '48px', lineHeight: '1' }}>
              {readinessText}
            </p>
            {readiness != null && (
              <p className="text-label-sm text-sage-on-surface-var font-jakarta">/ 100</p>
            )}
          </div>

          {/* Evidence grade */}
          <div className="text-center sm:text-right">
            <p className="text-label-sm text-sage-on-surface-var font-jakarta uppercase tracking-wider mb-1">
              Evidence Grade
            </p>
            <Badge label={`Grade ${grade}`} tone={gradeTone(grade)} size="lg" />
          </div>
        </div>
      </div>

      {/* Meta row */}
      <div className="mt-6 pt-4 border-t border-sage-outline-var/50 flex flex-wrap gap-4 text-body-sm text-sage-on-surface-var font-jakarta">
        <span>Pipeline v{result?.pipeline_version}</span>
        <span>·</span>
        <span>Evaluated {result?.evaluation_date}</span>
        <span>·</span>
        <span>{result?.lineage?.normalized_transaction_count ?? 0} normalized transactions</span>
      </div>
    </div>
  )
}
