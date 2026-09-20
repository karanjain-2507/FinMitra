import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { BadgeCheck, Copy, EyeOff, Fingerprint, QrCode, ShieldCheck, Target } from 'lucide-react'
import PageWrapper from '../components/layout/PageWrapper'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import { issuePassport } from '../api'

const CLAIM_LABELS = {
  evidence_grade: 'Evidence grade',
  cashflow_status: 'Cash-flow status',
  repayment_status: 'Repayment status',
  credit_status: 'Credit review',
  readiness_band: 'Readiness band',
  confidence_band: 'Confidence band',
}

export default function Passport() {
  const location = useLocation()
  const navigate = useNavigate()
  const assessmentId = location.state?.result?.assessment_id
  const goal = location.state?.goal ?? null
  const [credential, setCredential] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  const issue = async () => {
    try {
      setError(null)
      setLoading(true)
      setCredential(await issuePassport(assessmentId, goal))
    } catch (err) {
      setError(err.message || 'Unable to issue this passport.')
    } finally {
      setLoading(false)
    }
  }

  const copyId = async () => {
    await navigator.clipboard.writeText(credential.credential_id)
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  if (!assessmentId) {
    return (
      <PageWrapper className="max-w-2xl py-16">
        <Card level={2} radius="lg" className="text-center space-y-5">
          <ShieldCheck size={32} className="mx-auto text-sage-primary" />
          <h1 className="text-headline-sm font-jakarta">Run an assessment first</h1>
          <p className="text-body-md text-sage-on-surface-var font-jakarta">A financial passport can only be issued from an immutable FinMitra assessment.</p>
          <div className="flex justify-center gap-3"><Link to="/demo"><Button variant="filled">Try a demo</Button></Link><Link to="/assess"><Button variant="outlined">Assess a statement</Button></Link></div>
        </Card>
      </PageWrapper>
    )
  }

  return (
    <PageWrapper className="max-w-4xl space-y-7">
      <div className="space-y-2">
        <p className="text-label-md text-sage-primary font-jakarta">Selective disclosure credential</p>
        <h1 className="text-headline-md font-jakarta">Your FinMitra Passport</h1>
        <p className="text-body-lg text-sage-on-surface-var font-jakarta max-w-3xl">Share verified status bands without exposing income, balances, transaction history, borrower ID, or exact affordability figures.</p>
      </div>

      {error && <div role="alert" className="p-4 rounded-md bg-sage-error-container text-sage-on-error-container font-jakarta">{error}</div>}

      {!credential ? (
        <Card level={2} radius="lg" className="space-y-6">
          <div className="flex gap-4 items-start"><div className="w-12 h-12 rounded-full bg-sage-primary-container flex items-center justify-center text-sage-primary"><Fingerprint /></div><div><h2 className="text-title-lg font-jakarta">Create a signed credential</h2><p className="text-body-md text-sage-on-surface-var font-jakarta mt-1">The credential expires after 30 days and contains only categorical claims. {goal ? 'Your current What If outcome will be included without its amount or title.' : 'No goal information will be included.'}</p></div></div>
          <div className="grid sm:grid-cols-3 gap-3">
            <div className="p-4 rounded-md bg-sage-surface-low"><EyeOff size={18} className="text-sage-primary" /><p className="text-label-lg font-jakarta mt-2">No raw finances</p></div>
            <div className="p-4 rounded-md bg-sage-surface-low"><ShieldCheck size={18} className="text-sage-primary" /><p className="text-label-lg font-jakarta mt-2">Signed by FinMitra</p></div>
            <div className="p-4 rounded-md bg-sage-surface-low"><BadgeCheck size={18} className="text-sage-primary" /><p className="text-label-lg font-jakarta mt-2">Tamper evident</p></div>
          </div>
          <Button size="lg" variant="filled" loading={loading} onClick={issue}><ShieldCheck size={18} />Issue passport</Button>
        </Card>
      ) : (
        <>
          <Card level={2} radius="lg" className="bg-sage-success-container/60 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-white text-sage-success flex items-center justify-center"><BadgeCheck size={30} /></div>
              <div className="flex-1"><Badge label="SIGNED AND ACTIVE" tone="positive" size="sm" /><h2 className="text-title-lg font-jakarta mt-2">Financial credential issued</h2><p className="font-mono text-body-md mt-1">{credential.credential_id}</p></div>
            </div>
            <div className="flex flex-wrap gap-3"><Button variant="filled" onClick={copyId}><Copy size={16} />{copied ? 'Copied' : 'Copy ID'}</Button><Button variant="outlined" onClick={() => navigate('/verifier', { state: { credentialId: credential.credential_id } })}><QrCode size={16} />Open verifier</Button></div>
          </Card>

          <Card level={1} radius="md">
            <h3 className="text-title-md font-jakarta mb-4">Disclosed claims</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(credential.claims).filter(([key]) => CLAIM_LABELS[key]).map(([key, value]) => <div key={key} className="p-3 rounded-md bg-sage-surface-low"><p className="text-label-sm uppercase text-sage-on-surface-var font-jakarta">{CLAIM_LABELS[key]}</p><p className="text-title-sm font-jakarta mt-1 break-words">{String(value).replaceAll('_', ' ')}</p></div>)}
            </div>
            <p className="text-body-sm text-sage-on-surface-var font-jakarta mt-4">Stress checks passed: {credential.claims.stress_checks_passed} of {credential.claims.stress_checks_total}</p>
          </Card>

          {credential.goal_claim && <Card level={1} radius="md"><div className="flex items-center gap-2"><Target size={18} className="text-sage-primary" /><h3 className="text-title-md font-jakarta">What If claim</h3></div><p className="text-body-md font-jakarta mt-3">{credential.goal_claim.goal_type.replaceAll('_', ' ')} · {credential.goal_claim.outcome.replaceAll('_', ' ')} · {credential.goal_claim.deadline_months} months</p><p className="text-body-sm text-sage-on-surface-var font-jakarta mt-2">Goal title and amount are not disclosed.</p></Card>}

          <p className="text-body-sm text-sage-on-surface-var font-jakarta">Subject: <span className="font-mono">{credential.subject_id}</span> · Expires {new Date(credential.expires_at).toLocaleDateString('en-IN')}</p>
        </>
      )}
    </PageWrapper>
  )
}
