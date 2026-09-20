import { useState } from 'react'
import { Landmark, AlertTriangle, ChevronDown, ChevronUp, ShieldAlert, CheckCircle2 } from 'lucide-react'
import Card from '../ui/Card'
import Badge, { directionTone, repaymentTone } from '../ui/Badge'

/* ── Pure SVG Radial Score Meter ─────────────────────────────────────── */
function ScoreRadial({ score }) {
  const s = score != null ? Math.min(100, Math.max(0, score)) : null
  const radius = 46
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = s != null ? circumference - (s / 100) * circumference : circumference

  const color =
    s == null ? '#C2C8BF' :
    s >= 75   ? '#2E7D32' :
    s >= 50   ? '#4F6354' :
    s >= 35   ? '#B7791F' :
    '#BA1A1A'

  return (
    <div className="flex flex-col items-center py-2">
      <div className="relative w-32 h-32 flex items-center justify-center">
        <svg viewBox="0 0 120 120" className="w-full h-full transform -rotate-90">
          {/* Background Track */}
          <circle
            cx="60" cy="60" r={radius}
            fill="none"
            stroke="#E2E7E0"
            strokeWidth="10"
          />
          {/* Active Progress Circle */}
          {s != null && (
            <circle
              cx="60" cy="60" r={radius}
              fill="none"
              stroke={color}
              strokeWidth="10"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              className="transition-all duration-700 ease-out"
            />
          )}
        </svg>

        {/* Centered Score Readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-headline-sm font-jakarta font-semibold leading-tight" style={{ color }}>
            {s != null ? s.toFixed(0) : '—'}
          </span>
          <span className="text-label-sm text-sage-on-surface-var font-jakarta">/ 100</span>
        </div>
      </div>

      <p className="text-label-sm text-sage-on-surface-var font-jakarta mt-1 uppercase tracking-wider">
        Repayment Score
      </p>
    </div>
  )
}

function ProgressRow({ label, value, tone = 'default' }) {
  const pct = value != null ? Math.min(100, Math.max(0, value * 100)) : 0
  const color =
    tone === 'danger' && pct < 50 ? 'bg-sage-error' :
    pct >= 70 ? 'bg-sage-success' :
    pct >= 40 ? 'bg-sage-primary' :
    'bg-sage-warning'

  return (
    <div className="p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var space-y-1.5">
      <div className="flex justify-between items-center text-body-sm font-jakarta">
        <span className="text-sage-on-surface">{label}</span>
        <span className="font-semibold text-sage-on-surface">
          {value != null ? `${(value * 100).toFixed(0)}%` : '—'}
        </span>
      </div>
      <div className="w-full bg-sage-surface-highest rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-1.5 rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function RepaymentCard({ repayment }) {
  const [expanded, setExpanded] = useState(false)
  if (!repayment) return null

  const {
    status, score, confidence, new_credit_blocked, hard_cap,
    features = {}, reasons = [],
  } = repayment

  return (
    <Card level={1} radius="md">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-sage-surface-high flex items-center justify-center">
            <Landmark size={18} className="text-sage-secondary" />
          </div>
          <div>
            <h3 className="text-title-md font-jakarta text-sage-on-surface">Repayment</h3>
            <p className="text-body-sm text-sage-on-surface-var font-jakarta">Informal Loan Engine</p>
          </div>
        </div>
        <Badge label={status ?? '—'} tone={repaymentTone(status)} size="sm" />
      </div>

      {/* Hard Block Alert Banner */}
      {new_credit_blocked && (
        <div className="flex items-start gap-2.5 bg-sage-error-container rounded-md p-3 my-3 border border-sage-on-error-container/20">
          <ShieldAlert size={18} className="text-sage-error mt-0.5 flex-shrink-0" />
          <div className="space-y-0.5">
            <p className="text-label-md text-sage-on-error-container font-jakarta font-semibold">
              Hard Credit Block Active
            </p>
            <p className="text-body-sm text-sage-on-error-container/90 font-jakarta">
              Unresolved delinquent informal debt on record. Hard cap score applied ({hard_cap ?? 35}/100). Safe EMI set to ₹0.
            </p>
          </div>
        </div>
      )}

      {/* Radial Score */}
      <ScoreRadial score={score} />

      {/* Confidence & Cycle Stats */}
      <div className="grid grid-cols-2 gap-3 py-3 border-t border-sage-outline-var">
        <div className="p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var text-center">
          <span className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Confidence</span>
          <p className="text-title-md font-jakarta font-semibold text-sage-on-surface mt-0.5">
            {confidence != null ? `${(confidence * 100).toFixed(0)}%` : '—'}
          </p>
        </div>
        <div className="p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var text-center">
          <span className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Completed Cycles</span>
          <p className="text-title-md font-jakarta font-semibold text-sage-on-surface mt-0.5">
            {features.completed_credit_cycles ?? 0}
          </p>
        </div>
      </div>

      {/* Key Repayment Metrics */}
      <div className="space-y-2.5 mt-1">
        {features.on_time_payment_ratio != null && (
          <ProgressRow label="On-Time Payment Ratio" value={features.on_time_payment_ratio} />
        )}
        {features.digitally_matched_repayment_ratio != null && (
          <ProgressRow label="Digitally Matched Ratio" value={features.digitally_matched_repayment_ratio} />
        )}
      </div>

      {/* Reasons toggle */}
      {reasons.length > 0 && (
        <button
          className="mt-4 flex items-center gap-1 text-label-md text-sage-primary font-jakarta hover:opacity-80 transition-opacity"
          onClick={() => setExpanded(v => !v)}
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {expanded ? 'Hide' : 'Show'} {reasons.length} repayment finding{reasons.length !== 1 ? 's' : ''}
        </button>
      )}

      {expanded && (
        <ul className="mt-3 space-y-2">
          {reasons.map((r, i) => (
            <li key={i} className="flex gap-2.5 items-start">
              <Badge label={r.code} tone={directionTone(r.direction)} size="sm" />
              <p className="text-body-sm text-sage-on-surface-var font-jakarta flex-1">{r.message}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
