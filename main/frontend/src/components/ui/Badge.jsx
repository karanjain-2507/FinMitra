/** Status / grade badge */
export default function Badge({ label, tone = 'neutral', size = 'md' }) {
  const tones = {
    positive: 'bg-sage-success-container text-sage-success border-sage-success/30',
    negative: 'bg-sage-error-container text-sage-on-error-container border-sage-on-error-container/30',
    warning:  'bg-sage-warning-container text-sage-warning border-sage-warning/30',
    neutral:  'bg-sage-surface-highest text-sage-on-surface-var border-sage-outline-var',
    primary:  'bg-sage-primary-container text-sage-on-primary-container border-sage-primary/20',
    tertiary: 'bg-sage-tertiary-container text-sage-on-tertiary-container border-sage-tertiary/20',
  }

  const sizes = {
    sm: 'text-label-sm px-2 py-0.5 rounded-sm',
    md: 'text-label-md px-3 py-1 rounded-sm',
    lg: 'text-label-lg px-4 py-1.5 rounded',
  }

  return (
    <span className={`inline-flex items-center font-jakarta font-semibold border ${tones[tone]} ${sizes[size]}`}>
      {label}
    </span>
  )
}

/** Map a direction string to a badge tone */
export function directionTone(direction) {
  if (!direction) return 'neutral'
  const d = direction.toUpperCase()
  if (d === 'POSITIVE') return 'positive'
  if (d === 'NEGATIVE') return 'negative'
  return 'neutral'
}

/** Map repayment status string to tone */
export function repaymentTone(status) {
  if (!status) return 'neutral'
  const s = status.toUpperCase()
  if (s === 'COMPLETED' || s === 'CURRENT') return 'positive'
  if (s === 'BEHIND_SCHEDULE') return 'warning'
  if (s.includes('UNPAID') || s === 'DELINQUENT') return 'negative'
  return 'neutral'
}

/** Map evidence grade to tone */
export function gradeTone(grade) {
  const g = (grade ?? '').toUpperCase()
  if (g === 'A') return 'positive'
  if (g === 'B') return 'primary'
  if (g === 'C') return 'warning'
  return 'negative'
}
