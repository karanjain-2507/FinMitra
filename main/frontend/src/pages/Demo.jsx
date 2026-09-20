import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, AlertOctagon, HelpCircle, ArrowRight, Loader2 } from 'lucide-react'
import PageWrapper from '../components/layout/PageWrapper'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import { runDemo } from '../api'

export default function Demo() {
  const navigate = useNavigate()
  const [loadingScenario, setLoadingScenario] = useState(null)
  const [error, setError] = useState(null)

  const scenarios = [
    {
      id: 'strong',
      name: 'Strong Shopkeeper',
      subtitle: 'Healthy Cash Flow & Verified Repayments',
      badge: 'Ready for Review',
      badgeTone: 'positive',
      icon: CheckCircle,
      iconBg: 'bg-sage-success-container text-sage-success',
      description:
        'A micro-retailer with 6 months of steady POS settlements, active bank deposits, low volatility, and on-time closure of prior supplier advances.',
      highlights: [
        'Evidence Grade A with high confidence',
        'Low cash-flow stress probability (~15%)',
        'Positive monthly surplus (Safe EMI: ~₹4,000–₹8,000)',
        'Zero delinquency; clean repayment history',
      ],
    },
    {
      id: 'unpaid',
      name: 'Unpaid Informal Loan',
      subtitle: 'Hard Repayment Block Triggered',
      badge: 'Credit Blocked',
      badgeTone: 'negative',
      icon: AlertOctagon,
      iconBg: 'bg-sage-error-container text-sage-error',
      description:
        'A borrower with moderate operating cash flow but an active, overdue informal loan that remains materially unpaid (>20% principal overdue).',
      highlights: [
        'Person 3 Repayment Engine enforces hard cap (35/100)',
        'New credit blocked flag strictly set to true',
        'Safe EMI forced to ₹0 across all tenures',
        'Outcome displays clear non-negotiable blocking reason',
      ],
    },
    {
      id: 'thin',
      name: 'Thin History',
      subtitle: 'Insufficient Verification Window',
      badge: 'Insufficient Data',
      badgeTone: 'warning',
      icon: HelpCircle,
      iconBg: 'bg-sage-warning-container text-sage-warning',
      description:
        'An early-stage micro-entrepreneur with fewer than 3 months of bank activity and under 30 valid transactions.',
      highlights: [
        'Evidence status graded as INSUFFICIENT',
        'Cash-flow ML classifier safely returns score=None',
        'No false positive score generated for thin file',
        'Readiness Index cleanly omitted (None)',
      ],
    },
  ]

  const handleRunDemo = async (scenarioId) => {
    try {
      setError(null)
      setLoadingScenario(scenarioId)
      const data = await runDemo(scenarioId)
      navigate('/result', { state: { result: data, source: `demo-${scenarioId}` } })
    } catch (err) {
      setError(err.message || 'Failed to run scenario')
    } finally {
      setLoadingScenario(null)
    }
  }

  return (
    <PageWrapper className="space-y-8">
      <div className="space-y-2 max-w-2xl">
        <h1 className="text-headline-md font-jakarta text-sage-on-surface">
          Interactive Demo Scenarios
        </h1>
        <p className="text-body-lg text-sage-on-surface-var font-jakarta">
          Run complete, end-to-end evaluations across all four engines using pre-configured benchmark profiles.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-md bg-sage-error-container text-sage-on-error-container text-body-md font-jakarta border border-sage-error/20">
          <strong>Error running demo:</strong> {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {scenarios.map((sc) => {
          const Icon = sc.icon
          const isLoading = loadingScenario === sc.id
          return (
            <Card
              key={sc.id}
              level={1}
              radius="lg"
              className="flex flex-col justify-between p-6 hover:border-sage-primary/40 transition-all hover:shadow-level2"
            >
              <div className="space-y-5">
                <div className="flex items-start justify-between gap-3">
                  <div className={`w-12 h-12 rounded-full ${sc.iconBg} flex items-center justify-center flex-shrink-0`}>
                    <Icon size={24} />
                  </div>
                  <Badge label={sc.badge} tone={sc.badgeTone} size="md" />
                </div>

                <div>
                  <h2 className="text-title-lg font-jakarta text-sage-on-surface">
                    {sc.name}
                  </h2>
                  <p className="text-body-sm text-sage-on-surface-var font-jakarta mt-0.5">
                    {sc.subtitle}
                  </p>
                </div>

                <p className="text-body-sm text-sage-on-surface font-jakarta leading-relaxed">
                  {sc.description}
                </p>

                <div className="space-y-2 pt-2 border-t border-sage-outline-var/60">
                  <p className="text-label-sm font-jakarta text-sage-on-surface-var uppercase tracking-wider">
                    Key Pipeline Behaviors
                  </p>
                  <ul className="space-y-1.5">
                    {sc.highlights.map((h, i) => (
                      <li key={i} className="text-body-sm text-sage-on-surface-var font-jakarta flex items-start gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-sage-primary mt-1.5 flex-shrink-0" />
                        <span>{h}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="pt-6">
                <Button
                  variant="filled"
                  size="md"
                  className="w-full"
                  disabled={loadingScenario !== null}
                  onClick={() => handleRunDemo(sc.id)}
                >
                  {isLoading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>Executing Pipeline...</span>
                    </>
                  ) : (
                    <>
                      <span>Run Assessment</span>
                      <ArrowRight size={16} />
                    </>
                  )}
                </Button>
              </div>
            </Card>
          )
        })}
      </div>
    </PageWrapper>
  )
}
