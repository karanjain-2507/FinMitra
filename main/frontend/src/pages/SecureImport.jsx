import { useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { Camera, Image as ImageIcon, FileJson, AlertTriangle, Check, Trash2 } from "lucide-react"
import PageWrapper from "../components/layout/PageWrapper"
import Card from "../components/ui/Card"
import Button from "../components/ui/Button"
import {
  SHARE_FIELD_LABELS,
  openImportedShare,
  snapshotPreviewRows,
  userMessageForShareError,
} from "../security"
import {
  decodeQrFromImageFile,
  requestScanCamera,
  scanVideoFrame,
  stopMediaStream,
} from "../security/scanQr.js"
import { parseImportedPayload } from "../security/importFlow.js"

const INR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
})

function formatValue(key, value) {
  if (value === null || value === undefined) return "Not included"
  if (typeof value === "boolean") return value ? "Yes" : "No"
  if (key === "monthly_surplus" || key === "safe_emi_min" || key === "safe_emi_max") {
    return INR.format(value)
  }
  if (key === "overall_confidence") return `${Math.round(value * 100)}%`
  return String(value)
}

export default function SecureImport() {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const scanTimerRef = useRef(null)
  const fileRef = useRef(null)

  const [envelopeText, setEnvelopeText] = useState("")
  const [passphrase, setPassphrase] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [preview, setPreview] = useState(null)
  const [accepted, setAccepted] = useState(null)

  const stopScan = () => {
    if (scanTimerRef.current) {
      window.clearInterval(scanTimerRef.current)
      scanTimerRef.current = null
    }
    stopMediaStream(streamRef.current)
    streamRef.current = null
    setScanning(false)
  }

  useEffect(() => () => stopScan(), [])

  const discard = () => {
    stopScan()
    setPreview(null)
    setAccepted(null)
    setPassphrase("")
    setEnvelopeText("")
    setError("")
  }

  const onEnvelopeDecoded = (text) => {
    try {
      parseImportedPayload(text)
      setEnvelopeText(text)
      setError("")
      stopScan()
    } catch (err) {
      setError(userMessageForShareError(err))
    }
  }

  const handleScan = async () => {
    setError("")
    setPreview(null)
    setAccepted(null)
    try {
      const stream = await requestScanCamera()
      streamRef.current = stream
      setScanning(true)
      const video = videoRef.current
      if (video) {
        video.srcObject = stream
        await video.play()
      }
      scanTimerRef.current = window.setInterval(() => {
        const payload = scanVideoFrame(videoRef.current)
        if (payload) onEnvelopeDecoded(payload)
      }, 250)
    } catch (err) {
      stopScan()
      setError(userMessageForShareError(err))
    }
  }

  const handleImage = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (!file) return
    setError("")
    try {
      const payload = await decodeQrFromImageFile(file)
      onEnvelopeDecoded(payload)
    } catch (err) {
      setError(userMessageForShareError(err))
    }
  }

  const handleOpen = async () => {
    setError("")
    setPreview(null)
    setAccepted(null)
    setBusy(true)
    try {
      const snapshot = await openImportedShare(envelopeText, passphrase)
      setPreview(snapshot)
      setPassphrase("")
    } catch (err) {
      setPreview(null)
      setError(userMessageForShareError(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <PageWrapper className="max-w-3xl space-y-6 px-4">
      <div className="space-y-2">
        <p className="text-label-md text-sage-on-surface-var font-jakarta uppercase tracking-wider">
          Person 2 · Encrypted QR
        </p>
        <h1 className="text-headline-sm font-jakarta">Secure Import</h1>
        <p className="text-body-md text-sage-on-surface-var font-jakarta">
          Scan or import an encrypted envelope, then enter the passphrase separately. Camera access is requested only after you choose Scan secure QR.
          QR encoding is not encryption. This is a demo transfer, not production-grade key management.
        </p>
        <p className="text-body-sm font-jakarta">
          <Link to="/share" className="text-sage-primary underline">Create a share</Link>
        </p>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-md border border-sage-outline-var bg-sage-surface-low p-3 text-body-sm font-jakarta">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      <Card level={2} radius="md" className="p-4 sm:p-5 space-y-4">
        <h2 className="text-title-sm font-jakarta">1. Scan or import the envelope</h2>
        <div className="flex flex-col sm:flex-row flex-wrap gap-2">
          <Button variant="filled" size="sm" onClick={handleScan} aria-label="Scan secure QR with camera">
            <Camera size={14} aria-hidden="true" />
            <span>Scan secure QR</span>
          </Button>
          <Button variant="outlined" size="sm" onClick={() => fileRef.current?.click()} aria-label="Import QR image">
            <ImageIcon size={14} aria-hidden="true" />
            <span>Import QR image</span>
          </Button>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImage} />
        </div>

        {scanning && (
          <div className="space-y-2">
            <video ref={videoRef} className="w-full max-w-sm rounded-md bg-black" playsInline muted autoPlay />
            <Button variant="outlined" size="sm" onClick={stopScan}>Stop camera</Button>
          </div>
        )}
        {!scanning && <video ref={videoRef} className="hidden" playsInline muted />}

        <label htmlFor="envelope-import" className="block text-label-md font-jakarta text-sage-on-surface-var">
          Encrypted-text fallback (envelope JSON)
          <textarea
            id="envelope-import"
            className="mt-1 w-full min-h-[120px] rounded-md border border-sage-outline-var bg-sage-surface-low px-3 py-2 font-mono text-label-sm"
            value={envelopeText}
            onChange={(event) => setEnvelopeText(event.target.value)}
            autoComplete="off"
          />
        </label>
        <p className="text-label-sm text-sage-on-surface-var font-jakarta">
          <FileJson size={12} className="inline" aria-hidden="true" /> Paste ciphertext envelope only. Do not paste a passphrase.
        </p>
      </Card>

      <Card level={2} radius="md" className="p-4 sm:p-5 space-y-4">
        <h2 className="text-title-sm font-jakarta">2. Enter passphrase</h2>
        <label htmlFor="import-pass" className="block text-label-md font-jakarta text-sage-on-surface-var">
          Passphrase
          <input
            id="import-pass"
            type="password"
            autoComplete="off"
            className="mt-1 w-full rounded-md border border-sage-outline-var bg-sage-surface-low px-3 py-2 text-body-md"
            value={passphrase}
            onChange={(event) => setPassphrase(event.target.value)}
          />
        </label>
        <Button
          variant="filled"
          size="md"
          onClick={handleOpen}
          disabled={busy || !envelopeText}
          loading={busy}
          aria-label="Decrypt and validate share"
        >
          Decrypt and validate
        </Button>
      </Card>

      {preview && !accepted && (
        <Card level={2} radius="md" className="p-4 sm:p-5 space-y-4">
          <h2 className="text-title-sm font-jakarta">3. Preview (untrusted until you accept)</h2>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {snapshotPreviewRows(preview).map((row) => (
              <div key={row.key} className="rounded-md bg-sage-surface-low border border-sage-outline-var p-2.5">
                <dt className="text-label-sm text-sage-on-surface-var font-jakarta">{row.label}</dt>
                <dd className="text-title-sm font-jakarta mt-0.5">{formatValue(row.key, row.value)}</dd>
              </div>
            ))}
            <div className="rounded-md bg-sage-surface-low border border-sage-outline-var p-2.5">
              <dt className="text-label-sm text-sage-on-surface-var font-jakarta">What If summary</dt>
              <dd className="text-title-sm font-jakarta mt-0.5">{preview.what_if == null ? "Not included" : "Included"}</dd>
            </div>
            <div className="rounded-md bg-sage-surface-low border border-sage-outline-var p-2.5 sm:col-span-2">
              <dt className="text-label-sm text-sage-on-surface-var font-jakarta">Expiry</dt>
              <dd className="text-title-sm font-jakarta mt-0.5">{preview.expires_at}</dd>
            </div>
          </dl>
          <div className="flex flex-col sm:flex-row gap-2">
            <Button variant="filled" size="md" onClick={() => setAccepted(preview)} aria-label="Use this summary">
              <Check size={14} aria-hidden="true" />
              <span>Use this summary</span>
            </Button>
            <Button variant="outlined" size="md" onClick={discard} aria-label="Discard imported summary">
              <Trash2 size={14} aria-hidden="true" />
              <span>Discard</span>
            </Button>
          </div>
        </Card>
      )}

      {accepted && (
        <Card level={2} radius="md" className="p-4 sm:p-5 space-y-3">
          <h2 className="text-title-sm font-jakarta">Summary in use for this session only</h2>
          <p className="text-body-sm text-sage-on-surface-var font-jakarta">
            Nothing was written to storage or attached to scoring, repayment, capacity, or What If. Refresh or discard to clear it.
          </p>
          <p className="text-body-sm font-jakarta">
            {SHARE_FIELD_LABELS.borrower_alias}: {accepted.assessment.borrower_alias}
          </p>
          <Button variant="outlined" size="sm" onClick={discard}>Discard</Button>
        </Card>
      )}
    </PageWrapper>
  )
}
