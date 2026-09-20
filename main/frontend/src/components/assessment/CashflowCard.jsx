import { useState } from 'react'
import { TrendingUp, TrendingDown, ChevronDown, ChevronUp, Activity, CheckCircle2, AlertCircle } from 'lucide-react'
import Card from '../ui/Card'
import Badge, { directionTone } from '../ui/Badge'

const INR = new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR',
  maximumFractionDigits: 0,
})

/* ── High-Precision Semicircle Gauge ─────────────────────────────────── */
function StressGauge({ probability }) {
  const p = probability != null ? Math.max(0, Math.min(1, probability)) : null
  const cx = 130, cy = 105, r = 80

  const color =
    p == null ? '#C2C8BF' :
    p < 0.35  ? '#2E7D32' :
    p < 0.65  ? '#B7791F' :
    '#BA1A1A'

  // Fill path calculation
  let fillPath = ''
  if (p != null && p > 0.005) {
    const clampedP = Math.min(Math.max(p, 0.005), 0.995)
    const theta = Math.PI * (1 - clampedP)
    const fx = cx + r * Math.cos(theta)
    const fy = cy - r * Math.sin(theta)
    fillPath = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${fx.toFixed(2)} ${fy.toFixed(2)}`
  }

  const deg = p != null ? -90 + p * 180 : -90
  const label = p == null ? '—' : `${(p * 100).toFixed(1)}%`

  return (
    <div className="flex flex-col items-center pt-2">
      <div className="relative w-full max-w-[260px] flex justify-center">
        <svg viewBox="0 0 260 135" className="w-full overflow-visible">
          {/* Background Gradient / Zone segments */}
          {/* Low Zone (Green): 0 to 35% */}
          <path
            d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r * Math.cos(Math.PI * 0.65)} ${cy - r * Math.sin(Math.PI * 0.65)}`}
            fill="none" stroke="#2E7D32" strokeWidth="12" strokeOpacity="0.2"
          />
          {/* Mid Zone (Amber): 35 to 65% */}
          <path
            d={`M ${cx + r * Math.cos(Math.PI * 0.65)} ${cy - r * Math.sin(Math.PI * 0.65)} A ${r} ${r} 0 0 1 ${cx + r * Math.cos(Math.PI * 0.35)} ${cy - r * Math.sin(Math.PI * 0.35)}`}
            fill="none" stroke="#B7791F" strokeWidth="12" strokeOpacity="0.2"
          />
          {/* High Zone (Red): 65 to 100% */}
          <path
            d={`M ${cx + r * Math.cos(Math.PI * 0.35)} ${cy - r * Math.sin(Math.PI * 0.35)} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none" stroke="#BA1A1A" strokeWidth="12" strokeOpacity="0.2"
          />

          {/* Neutral Base Track */}
          <path
            d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none" stroke="#E2E7E0" strokeWidth="10" strokeLinecap="round"
          />

          {/* Active Value Arc */}
          {fillPath && (
            <path
              d={fillPath}
              fill="none"
              stroke={color}
              strokeWidth="10"
              strokeLinecap="round"
            />
          )}

          {/* Needle */}
          {p != null && (
            <g transform={`rotate(${deg} ${cx} ${cy})`}>
              <line
                x1={cx} y1={cy}
                x2={cx} y2={cy - r + 14}
                stroke="#1A1C1A"
                strokeWidth="3"
                strokeLinecap="round"
              />
              <polygon
                points={`${cx - 3},${cy - r + 18} ${cx + 3},${cy - r + 18} ${cx},${cy - r + 10}`}
                fill="#1A1C1A"
              />
            </g>
          )}

          {/* Pivot Dot */}
          <circle cx={cx} cy={cy} r="6" fill="#1A1C1A" stroke="#FFFFFF" strokeWidth="2" />

          {/* Scale Labels */}
          <text x={cx - r} y={cy + 18} textAnchor="middle" fill="#5F635E" fontSize="11" fontWeight="600" fontFamily="Plus Jakarta Sans">Low</text>
          <text x={cx} y={cy - r - 8} textAnchor="middle" fill="#5F635E" fontSize="10" fontFamily="Plus Jakarta Sans">Moderate</text>
          <text x={cx + r} y={cy + 18} textAnchor="middle" fill="#5F635E" fontSize="11" fontWeight="600" fontFamily="Plus Jakarta Sans">High</text>
        </svg>
      </div>

      {/* Label Callout */}
      <div className="text-center mt-1">
        <p className="text-headline-sm font-jakarta font-semibold leading-tight" style={{ color }}>
          {label}
        </p>
        <p className="text-body-sm text-sage-on-surface-var font-jakarta">
          90-Day Cash-Flow Stress Probability
        </p>
      </div>
    </div>
  )
}

/* ── Structured Key Feature Indicators ──────────────────────────────── */
function FeatureMetrics({ features }) {
  const trend = features.six_month_inflow_trend
  const volatility = features.inflow_volatility
  const negMonths = features.negative_cashflow_month_ratio
  const inflow = features.conservative_monthly_inflow_paise != null
    ? features.conservative_monthly_inflow_paise / 100
    : null
  const expense = features.median_monthly_business_expense_paise != null
    ? features.median_monthly_business_expense_paise / 100
    : null

  return (
    <div className="mt-4 space-y-3 pt-3 border-t border-sage-outline-var">
      <p className="text-label-sm uppercase tracking-wider text-sage-on-surface-var font-jakarta">
        Key Driver Features
      </p>

      {/* Metric 1: Inflow Trend */}
      {trend != null && (
        <div className="flex items-center justify-between p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var">
          <div className="flex items-center gap-2">
            {trend >= 0 ? (
              <TrendingUp size={16} className="text-sage-success flex-shrink-0" />
            ) : (
              <TrendingDown size={16} className="text-sage-error flex-shrink-0" />
            )}
            <span className="text-body-sm text-sage-on-surface font-jakarta">6M Inflow Trend</span>
          </div>
          <span className={`text-label-md font-jakarta font-semibold ${trend >= 0 ? 'text-sage-success' : 'text-sage-error'}`}>
            {trend >= 0 ? `+${(trend * 100).toFixed(1)}%` : `${(trend * 100).toFixed(1)}%`}
          </span>
        </div>
      )}

      {/* Metric 2: Volatility */}
      {volatility != null && (
        <div className="p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var space-y-1.5">
          <div className="flex justify-between items-center text-body-sm font-jakarta">
            <span className="text-sage-on-surface">Inflow Volatility</span>
            <span className="font-semibold text-sage-on-surface">{(volatility * 100).toFixed(0)}%</span>
          </div>
          <div className="w-full bg-sage-surface-highest rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-1.5 rounded-full transition-all duration-500 ${volatility > 0.4 ? 'bg-sage-error' : volatility > 0.2 ? 'bg-sage-warning' : 'bg-sage-success'}`}
              style={{ width: `${Math.min(100, volatility * 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Metric 3: Inflow & Expense summary */}
      {(inflow != null || expense != null) && (
        <div className="grid grid-cols-2 gap-2">
          {inflow != null && (
            <div className="p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var">
              <p className="text-label-sm text-sage-on-surface-var font-jakarta">Est. Monthly Inflow</p>
              <p className="text-title-sm font-jakarta text-sage-on-surface font-semibold mt-0.5">
                {INR.format(inflow)}
              </p>
            </div>
          )}
          {expense != null && (
            <div className="p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var">
              <p className="text-label-sm text-sage-on-surface-var font-jakarta">Median Expense</p>
              <p className="text-title-sm font-jakarta text-sage-on-surface font-semibold mt-0.5">
                {INR.format(expense)}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Main Cashflow Card ──────────────────────────────────────────────── */
export default function CashflowCard({ cashflow }) {
  const [expanded, setExpanded] = useState(false)
  if (!cashflow) return null

  const { score, status, confidence, stress_probability, features = {}, reasons = [] } = cashflow

  return (
    <Card level={1} radius="md">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-sage-surface-high flex items-center justify-center">
            <Activity size={18} className="text-sage-tertiary" />
          </div>
          <div>
            <h3 className="text-title-md font-jakarta text-sage-on-surface">Cash Flow</h3>
            <p className="text-body-sm text-sage-on-surface-var font-jakarta">ML Stress Assessment</p>
          </div>
        </div>
        <Badge
          label={status ?? '—'}
          tone={status === 'SUFFICIENT' ? 'positive' : status === 'DEGRADED' ? 'warning' : 'neutral'}
          size="sm"
        />
      </div>

      {/* Semicircle Gauge */}
      <StressGauge probability={stress_probability} />

      {/* Health Score & Confidence */}
      <div className="grid grid-cols-2 gap-3 py-3 mt-3 border-t border-sage-outline-var">
        <div className="p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var text-center">
          <span className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Health Score</span>
          <p className="text-title-md font-jakarta font-semibold text-sage-on-surface mt-0.5">
            {score != null ? score.toFixed(1) : '—'}
            <span className="text-body-sm font-normal text-sage-on-surface-var"> /100</span>
          </p>
        </div>
        <div className="p-2.5 rounded-md bg-sage-surface-low border border-sage-outline-var text-center">
          <span className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Model Confidence</span>
          <p className="text-title-md font-jakarta font-semibold text-sage-on-surface mt-0.5">
            {confidence != null ? `${(confidence * 100).toFixed(0)}%` : '—'}
          </p>
        </div>
      </div>

      {/* Key Feature breakdown */}
      <FeatureMetrics features={features} />

      {/* Explainable Reasons */}
      {reasons.length > 0 && (
        <button
          className="mt-4 flex items-center gap-1 text-label-md text-sage-primary font-jakarta hover:opacity-80 transition-opacity"
          onClick={() => setExpanded(v => !v)}
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {expanded ? 'Hide' : 'Show'} {reasons.length} model finding{reasons.length !== 1 ? 's' : ''}
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
