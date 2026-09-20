import { useState } from 'react'
import { Wallet, CheckCircle2, XCircle, ChevronDown, ChevronUp, ShieldCheck } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import Card from '../ui/Card'
import Badge, { directionTone } from '../ui/Badge'

const INR = new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR',
  maximumFractionDigits: 0,
})

function EmiRangeViz({ minimum, maximum, blocked }) {
  if (blocked || (minimum === 0 && maximum === 0)) {
    return (
      <div className="my-3 p-3 rounded-md bg-sage-surface-low border border-sage-outline-var text-center">
        <p className="text-label-md text-sage-error font-jakarta font-semibold">
          Safe EMI: ₹0 / month
        </p>
        <p className="text-body-sm text-sage-on-surface-var font-jakarta mt-0.5">
          New borrowing is blocked due to active informal delinquency.
        </p>
      </div>
    )
  }

  const min = minimum ?? 0
  const max = maximum ?? 0
  const mid = Math.round((min + max) / 2)

  return (
    <div className="my-3 space-y-1.5">
      <div className="flex justify-between items-center text-label-sm text-sage-on-surface-var font-jakarta uppercase tracking-wider">
        <span>Safe Monthly EMI Window</span>
        <span className="text-sage-on-surface font-semibold lowercase font-jakarta">
          {INR.format(min)} – {INR.format(max)}
        </span>
      </div>

      <div className="relative h-11 bg-sage-surface-highest rounded-full overflow-hidden flex items-center px-4 border border-sage-outline-var">
        <div
          className="absolute top-1 bottom-1 bg-sage-primary-container rounded-full border border-sage-primary/30"
          style={{ left: '8%', right: '8%' }}
        />
        <div className="relative z-10 flex w-full justify-between items-center text-body-sm font-jakarta">
          <span className="font-semibold text-sage-on-surface">{INR.format(min)}</span>
          <span className="font-semibold text-sage-on-primary-container px-2 py-0.5 rounded-full bg-sage-primary/15 text-label-md">
            Mid: {INR.format(mid)}
          </span>
          <span className="font-semibold text-sage-on-surface">{INR.format(max)}</span>
        </div>
      </div>

      <div className="flex justify-between text-body-sm text-sage-on-surface-var font-jakarta px-1">
        <span>Conservative Base</span>
        <span>Optimistic Limit</span>
      </div>
    </div>
  )
}

function MaxPrincipalChart({ maxPrincipal, blocked }) {
  if (blocked || !maxPrincipal || Object.keys(maxPrincipal).length === 0) return null

  const data = Object.entries(maxPrincipal).map(([tenure, amount]) => ({
    tenure: `${tenure} Months`,
    amount: Math.round(amount),
  }))

  const maxVal = Math.max(...data.map(d => d.amount), 1)

  return (
    <div className="mt-4 pt-3 border-t border-sage-outline-var space-y-2">
      <p className="text-label-sm uppercase tracking-wider text-sage-on-surface-var font-jakarta">
        Max Loan Principal by Tenure
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {data.map((item, i) => (
          <div key={i} className="p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var text-center">
            <span className="text-label-sm text-sage-on-surface-var font-jakarta">{item.tenure}</span>
            <p className="text-title-sm font-jakarta font-semibold text-sage-on-surface mt-0.5">
              {INR.format(item.amount)}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

function StressTestList({ stressTests }) {
  if (!stressTests || stressTests.length === 0) return null
  return (
    <div className="mt-4 pt-3 border-t border-sage-outline-var space-y-2">
      <p className="text-label-sm uppercase tracking-wider text-sage-on-surface-var font-jakarta">
        Affordability Stress Tests
      </p>
      <div className="space-y-1.5">
        {stressTests.map((st, i) => (
          <div key={i} className="flex items-center justify-between p-2 rounded-md bg-sage-surface-low border border-sage-outline-var text-body-sm font-jakarta">
            <div className="flex items-center gap-2 min-w-0">
              {st.passed
                ? <CheckCircle2 size={16} className="text-sage-success flex-shrink-0" />
                : <XCircle size={16} className="text-sage-error flex-shrink-0" />
              }
              <span className="text-sage-on-surface truncate">{st.name}</span>
            </div>
            {st.passed ? (
              <span className="text-label-sm font-semibold text-sage-success">PASS</span>
            ) : (
              <span className="text-label-sm font-semibold text-sage-error px-1.5 py-0.5 rounded bg-sage-error-container">
                {st.severity || 'FAIL'}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function CapacityCard({ capacity, safeEmi }) {
  const [expanded, setExpanded] = useState(false)
  if (!capacity) return null

  const { status, confidence, features = {}, reasons = [], stress_tests = [], max_principal = {}, safe_emi } = capacity
  const emi = safe_emi ?? safeEmi ?? {}
  const blocked = Boolean(features.new_credit_blocked)

  return (
    <Card level={1} radius="md">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-sage-surface-high flex items-center justify-center">
            <Wallet size={18} className="text-sage-warning" />
          </div>
          <div>
            <h3 className="text-title-md font-jakarta text-sage-on-surface">Capacity</h3>
            <p className="text-body-sm text-sage-on-surface-var font-jakarta">Affordability &amp; EMI Engine</p>
          </div>
        </div>
        <Badge
          label={status ?? '—'}
          tone={
            status === 'STRONG' || status === 'ADEQUATE' ? 'positive' :
            status === 'LIMITED' ? 'warning' :
            status === 'BLOCKED' || status === 'NONE' ? 'negative' : 'neutral'
          }
          size="sm"
        />
      </div>

      {/* EMI Range Visualizer */}
      <EmiRangeViz minimum={emi.minimum} maximum={emi.maximum} blocked={blocked} />

      {/* Surplus & Confidence */}
      <div className="grid grid-cols-2 gap-3 py-3 border-t border-sage-outline-var">
        <div className="p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var text-center">
          <span className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Monthly Surplus</span>
          <p className={`text-title-md font-jakarta font-semibold mt-0.5 ${(features.monthly_surplus ?? 0) >= 0 ? 'text-sage-success' : 'text-sage-error'}`}>
            {INR.format(features.monthly_surplus ?? 0)}
          </p>
        </div>
        <div className="p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var text-center">
          <span className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Confidence</span>
          <p className="text-title-md font-jakarta font-semibold text-sage-on-surface mt-0.5">
            {confidence != null ? `${(confidence * 100).toFixed(0)}%` : '—'}
          </p>
        </div>
      </div>

      {/* Max Principal Tenure Cards */}
      <MaxPrincipalChart maxPrincipal={max_principal} blocked={blocked} />

      {/* Stress Tests */}
      <StressTestList stressTests={stress_tests} />

      {/* Reasons toggle */}
      {reasons.length > 0 && (
        <button
          className="mt-4 flex items-center gap-1 text-label-md text-sage-primary font-jakarta hover:opacity-80 transition-opacity"
          onClick={() => setExpanded(v => !v)}
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {expanded ? 'Hide' : 'Show'} {reasons.length} capacity reason{reasons.length !== 1 ? 's' : ''}
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
