import Card from '../ui/Card'
import Badge, { directionTone } from '../ui/Badge'

/** Collects and deduplicates top findings across all 4 components. */
export default function FindingsList({ result }) {
  if (!result?.profile) return null

  const profile = result.profile
  const allReasons = [
    ...(profile.repayment?.reasons ?? []),
    ...(profile.cashflow?.reasons ?? []),
    ...(profile.capacity?.reasons ?? []),
    ...(profile.evidence?.reasons ?? []),
  ]

  const seen = new Set()
  const sorted = allReasons
    .filter(r => r.message)
    .sort((a, b) => {
      const rank = { NEGATIVE: 0, POSITIVE: 1, NEUTRAL: 2 }
      return (rank[a.direction] ?? 2) - (rank[b.direction] ?? 2)
    })
    .filter(r => {
      if (seen.has(r.message)) return false
      seen.add(r.message)
      return true
    })
    .slice(0, 5)

  if (sorted.length === 0) return null

  return (
    <Card level={1} radius="md" className="mt-6">
      <h3 className="text-title-md font-jakarta text-sage-on-surface mb-4">
        Main Findings
      </h3>
      <ul className="divide-y divide-sage-outline-var">
        {sorted.map((r, i) => (
          <li key={i} className="flex gap-3 items-start py-3 first:pt-0 last:pb-0">
            <Badge label={r.code} tone={directionTone(r.direction)} size="sm" />
            <p className="text-body-md text-sage-on-surface font-jakarta flex-1">{r.message}</p>
          </li>
        ))}
      </ul>
    </Card>
  )
}
