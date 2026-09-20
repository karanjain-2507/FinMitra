import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { BadgeCheck, QrCode, ScanLine, ShieldAlert, ShieldCheck } from 'lucide-react'
import PageWrapper from '../components/layout/PageWrapper'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { verifyPassport } from '../api'

export default function Verifier() {
  const location = useLocation()
  const [credentialId, setCredentialId] = useState(location.state?.credentialId ?? '')
  const [verification, setVerification] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const verify = async (event) => {
    event.preventDefault()
    try {
      setError(null)
      setVerification(null)
      setLoading(true)
      setVerification(await verifyPassport(credentialId.trim()))
    } catch (err) {
      setError(err.message || 'Verification failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <PageWrapper className="max-w-2xl space-y-6">
      <h1 className="text-headline-md font-jakarta">Credential verifier</h1>
      <Card level={1} radius="lg" className="bg-sage-primary-container/70">
        <div className="flex items-center gap-3 text-sage-success"><BadgeCheck size={24} /><span className="text-title-md font-jakarta">Signature engine ready</span></div>
        <div className="w-full h-2 bg-sage-outline-var/50 rounded-full overflow-hidden mt-4"><div className="w-full h-full bg-sage-success rounded-full" /></div>
      </Card>

      <Card level={2} radius="lg" className="space-y-4">
        <p className="text-label-lg font-jakarta">Optical scan</p>
        <div className="relative aspect-video sm:aspect-square sm:max-h-64 rounded-md bg-white border border-sage-outline-var flex items-center justify-center overflow-hidden">
          <QrCode size={76} className="text-sage-primary/20" />
          <div className="absolute left-10 right-10 top-1/2 h-0.5 bg-sage-success/70 shadow-level2" />
          <ScanLine className="absolute inset-5 w-[calc(100%-2.5rem)] h-[calc(100%-2.5rem)] text-sage-primary" strokeWidth={1} />
        </div>
        <p className="text-center text-body-sm text-sage-on-surface-var font-jakarta">Camera QR decoding is not enabled in this web build. Enter the credential ID below.</p>
      </Card>

      <form onSubmit={verify} className="space-y-3">
        <label htmlFor="credential-id" className="text-title-md font-jakarta block">Enter ID manually</label>
        <input id="credential-id" required minLength={8} maxLength={64} value={credentialId} onChange={(event) => setCredentialId(event.target.value.toUpperCase())} placeholder="TP-IN-XXXXXXXX" className="w-full h-14 px-4 rounded-md bg-sage-surface-med border border-sage-outline-var font-mono font-semibold focus:outline-none focus:ring-2 focus:ring-sage-primary" />
        <Button type="submit" size="lg" className="w-full" loading={loading}><ShieldCheck size={19} />Verify</Button>
      </form>

      {error && <div role="alert" className="p-4 rounded-md bg-sage-error-container text-sage-on-error-container font-jakarta">{error}</div>}
      {verification && <Card level={1} radius="lg" className={verification.valid ? 'border-sage-success bg-sage-success-container/50' : 'border-sage-error bg-sage-error-container/50'}><div className="flex items-start gap-3">{verification.valid ? <BadgeCheck className="text-sage-success" /> : <ShieldAlert className="text-sage-error" />}<div><h2 className="text-title-lg font-jakarta">{verification.valid ? 'Credential confirmed' : `Credential ${verification.status.toLowerCase().replaceAll('_', ' ')}`}</h2><p className="text-body-sm text-sage-on-surface-var font-jakarta mt-1">{verification.valid ? 'The signature and expiry are valid. The disclosed claims came from FinMitra.' : 'No verified claims should be relied upon.'}</p></div></div>{verification.valid && <div className="grid grid-cols-2 gap-3 mt-5"><div><p className="text-label-sm uppercase text-sage-on-surface-var">Credit status</p><p className="text-label-lg mt-1">{verification.claims.credit_status.replaceAll('_', ' ')}</p></div><div><p className="text-label-sm uppercase text-sage-on-surface-var">Readiness</p><p className="text-label-lg mt-1">{verification.claims.readiness_band}</p></div><div><p className="text-label-sm uppercase text-sage-on-surface-var">Evidence</p><p className="text-label-lg mt-1">Grade {verification.claims.evidence_grade}</p></div><div><p className="text-label-sm uppercase text-sage-on-surface-var">Expires</p><p className="text-label-lg mt-1">{new Date(verification.expires_at).toLocaleDateString('en-IN')}</p></div></div>}</Card>}
    </PageWrapper>
  )
}
