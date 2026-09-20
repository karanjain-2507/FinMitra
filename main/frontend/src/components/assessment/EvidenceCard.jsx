import { useState } from 'react'
import { ChevronDown, ChevronUp, ShieldCheck } from 'lucide-react'
import Card from '../ui/Card'
import Badge, { gradeTone, directionTone } from '../ui/Badge'

function ScoreBar({ score, max = 100, color = 'bg-sage-primary' }) {
  const pct = score != null ? Math.min(100, Math.max(0, (score / max) * 100)) : 0
  return (
    <div className="w-full bg-sage-surface-highest rounded-full h-2 overflow-hidden">
      <div
        className={`h-2 rounded-full transition-all duration-700 ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export default function EvidenceCard({ evidence }) {
  const [expanded, setExpanded] = useState(false)
  if (!evidence) return null

  const { evidence_grade, score, confidence, status, reasons = [], warnings = [], features = {} } = evidence
  const grade = evidence_grade ?? '—'
  const scoreColor =
    score >= 75 ? 'bg-sage-success' :
    score >= 50 ? 'bg-sage-primary' :
    score >= 25 ? 'bg-sage-warning' :
    'bg-sage-error'

  return (
    <Card level={1} radius="md">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-sage-surface-high flex items-center justify-center">
            <ShieldCheck size={18} className="text-sage-primary" />
          </div>
          <div>
            <h3 className="text-title-md font-jakarta text-sage-on-surface">Evidence</h3>
            <p className="text-body-sm text-sage-on-surface-var font-jakarta">Ingestion &amp; Grading</p>
          </div>
        </div>
        <Badge label={`Grade ${grade}`} tone={gradeTone(grade)} size="md" />
      </div>

      {/* Score row */}
      <div className="mb-4">
        <div className="flex justify-between items-end mb-1.5">
          <span className="text-label-md text-sage-on-surface-var font-jakarta">Evidence Score</span>
          <span className="text-title-md font-jakarta text-sage-on-surface">
            {score != null ? score.toFixed(0) : '—'}
            <span className="text-body-sm text-sage-on-surface-var"> /100</span>
          </span>
        </div>
        <ScoreBar score={score} color={scoreColor} />
      </div>

      {/* Confidence */}
      <div className="flex justify-between py-2.5 border-b border-sage-outline-var">
        <span className="text-body-md text-sage-on-surface-var font-jakarta">Confidence</span>
        <span className="text-body-md font-semibold font-jakarta text-sage-on-surface">
          {confidence != null ? `${(confidence * 100).toFixed(0)}%` : '—'}
        </span>
      </div>

      {/* Status */}
      <div className="flex justify-between py-2.5 border-b border-sage-outline-var">
        <span className="text-body-md text-sage-on-surface-var font-jakarta">Status</span>
        <Badge
          label={status ?? '—'}
          tone={status === 'SUFFICIENT' ? 'positive' : status === 'DEGRADED' ? 'warning' : 'neutral'}
          size="sm"
        />
      </div>

      {/* Key features */}
      {features.active_months != null && (
        <div className="flex justify-between py-2.5 border-b border-sage-outline-var">
          <span className="text-body-md text-sage-on-surface-var font-jakarta">Active Months</span>
          <span className="text-body-md font-semibold font-jakarta text-sage-on-surface">{features.active_months}</span>
        </div>
      )}
      {features.source_count != null && (
        <div className="flex justify-between py-2.5 border-b border-sage-outline-var">
          <span className="text-body-md text-sage-on-surface-var font-jakarta">Data Sources</span>
          <span className="text-body-md font-semibold font-jakarta text-sage-on-surface">{features.source_count}</span>
        </div>
      )}

      {/* Reasons toggle */}
      {reasons.length > 0 && (
        <button
          className="mt-4 flex items-center gap-1 text-label-md text-sage-primary font-jakarta hover:opacity-80 transition-opacity"
          onClick={() => setExpanded(v => !v)}
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {expanded ? 'Hide' : 'Show'} {reasons.length} finding{reasons.length !== 1 ? 's' : ''}
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
