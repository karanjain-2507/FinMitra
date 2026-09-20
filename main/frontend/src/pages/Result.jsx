import { useState } from 'react'
import { useLocation, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Code, Copy, Check, RotateCcw, AlertTriangle, Layers, SlidersHorizontal, Sparkles, Shield } from 'lucide-react'
import PageWrapper from '../components/layout/PageWrapper'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import OutcomeHero from '../components/assessment/OutcomeHero'
import EvidenceCard from '../components/assessment/EvidenceCard'
import CashflowCard from '../components/assessment/CashflowCard'
import RepaymentCard from '../components/assessment/RepaymentCard'
import CapacityCard from '../components/assessment/CapacityCard'
import FindingsList from '../components/assessment/FindingsList'

export default function Result() {
  const location = useLocation()
  const navigate = useNavigate()
  const result = location.state?.result
  const [showJson, setShowJson] = useState(false)
  const [copied, setCopied] = useState(false)

  if (!result) {
    return (
      <PageWrapper className="max-w-xl text-center space-y-6 py-16">
        <div className="w-16 h-16 rounded-full bg-sage-warning-container text-sage-warning flex items-center justify-center mx-auto">
          <AlertTriangle size={32} />
        </div>
        <h1 className="text-headline-sm font-jakarta text-sage-on-surface">
          No Assessment Result Found
        </h1>
        <p className="text-body-md text-sage-on-surface-var font-jakarta">
          Select a demo scenario or upload a transaction CSV statement to run an evaluation.
        </p>
        <div className="flex justify-center gap-3">
          <Link to="/demo">
            <Button variant="filled" size="md">
              <span>View Demos</span>
            </Button>
          </Link>
          <Link to="/assess">
            <Button variant="outlined" size="md">
              <span>Assess CSV</span>
            </Button>
          </Link>
        </div>
      </PageWrapper>
    )
  }

  const profile = result.profile ?? {}
  const lineage = result.lineage ?? {}

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(result, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <PageWrapper className="space-y-8">
      {/* Top Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1.5 text-label-lg font-jakarta text-sage-on-surface-var hover:text-sage-on-surface transition-colors"
        >
          <ArrowLeft size={16} />
          <span>Back</span>
        </button>

        <div className="flex flex-wrap items-center gap-2">
          <Link to="/share" state={{ result }}>
            <Button variant="tonal" size="sm" aria-label="Share assessment summary securely">
              <Shield size={14} aria-hidden="true" />
              <span>Share securely</span>
            </Button>
          </Link>
          <Link to="/import">
            <Button variant="outlined" size="sm" aria-label="Open a secure share">
              <span>Open a share</span>
            </Button>
          </Link>

          <Link to="/assess">
            <Button variant="filled" size="sm">
              <SlidersHorizontal size={14} />
              <span>Tweak Data &amp; Re-Assess</span>
            </Button>
          </Link>

          <Button
            variant="tonal"
            size="sm"
            onClick={() => setShowJson((v) => !v)}
          >
            <Code size={14} />
            <span>{showJson ? 'Hide Raw JSON' : 'Inspect JSON'}</span>
          </Button>

          <Link to="/demo">
            <Button variant="outlined" size="sm">
              <Sparkles size={14} />
              <span>Try Other Demos</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* Outcome Hero Banner */}
      <OutcomeHero result={result} />

      {/* 2x2 Grid of the 4 Engines */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <EvidenceCard evidence={profile.evidence} />
        <CashflowCard cashflow={profile.cashflow} />
        <RepaymentCard repayment={profile.repayment} />
        <CapacityCard capacity={profile.capacity} safeEmi={profile.safe_emi} />
      </div>

      {/* Aggregated Top Findings */}
      <FindingsList result={result} />

      {/* Audit & Lineage Trail */}
      <Card level={2} radius="md" className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <Layers size={18} className="text-sage-primary" />
          <h3 className="text-title-sm font-jakarta text-sage-on-surface">
            Data Lineage &amp; Verification Audit
          </h3>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-center">
          <div className="p-2.5 rounded bg-sage-surface-low border border-sage-outline-var">
            <p className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Sources</p>
            <p className="text-title-md font-jakarta text-sage-on-surface mt-0.5">{lineage.source_count ?? 0}</p>
          </div>
          <div className="p-2.5 rounded bg-sage-surface-low border border-sage-outline-var">
            <p className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Raw Txns</p>
            <p className="text-title-md font-jakarta text-sage-on-surface mt-0.5">{lineage.raw_transaction_count ?? 0}</p>
          </div>
          <div className="p-2.5 rounded bg-sage-surface-low border border-sage-outline-var">
            <p className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Normalized</p>
            <p className="text-title-md font-jakarta text-sage-on-surface mt-0.5">{lineage.normalized_transaction_count ?? 0}</p>
          </div>
          <div className="p-2.5 rounded bg-sage-surface-low border border-sage-outline-var">
            <p className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Model Eligible</p>
            <p className="text-title-md font-jakarta text-sage-on-surface mt-0.5">{lineage.cashflow_transaction_count ?? 0}</p>
          </div>
          <div className="p-2.5 rounded bg-sage-surface-low border border-sage-outline-var">
            <p className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Declared Loans</p>
            <p className="text-title-md font-jakarta text-sage-on-surface mt-0.5">{lineage.informal_loan_count ?? 0}</p>
          </div>
          <div className="p-2.5 rounded bg-sage-surface-low border border-sage-outline-var">
            <p className="text-label-sm text-sage-on-surface-var font-jakarta uppercase">Claims Matched</p>
            <p className="text-title-md font-jakarta text-sage-on-surface mt-0.5">{lineage.repayment_claim_count ?? 0}</p>
          </div>
        </div>
      </Card>

      {/* Collapsible Raw JSON Viewer */}
      {showJson && (
        <Card level={2} radius="md" className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-title-sm font-jakarta text-sage-on-surface">
              Raw Pipeline JSON Response
            </h3>
            <Button variant="tonal" size="sm" onClick={handleCopyJson}>
              {copied ? <Check size={14} /> : <Copy size={14} />}
              <span>{copied ? 'Copied' : 'Copy JSON'}</span>
            </Button>
          </div>
          <pre className="p-4 rounded-md bg-sage-surface-highest text-sage-on-surface font-mono text-body-sm overflow-x-auto max-h-[500px] border border-sage-outline-var scrollbar-hide">
            {JSON.stringify(result, null, 2)}
          </pre>
        </Card>
      )}
    </PageWrapper>
  )
}
