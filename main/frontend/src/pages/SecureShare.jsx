import { useEffect, useMemo, useState } from "react"
import { Link, useLocation } from "react-router-dom"
import { Shield, QrCode, Unlock, AlertTriangle, Trash2 } from "lucide-react"
import PageWrapper from "../components/layout/PageWrapper"
import Card from "../components/ui/Card"
import Button from "../components/ui/Button"
import {
  EXPIRY_OPTIONS,
  SHARE_EXCLUDED_LABELS,
  SHARE_FIELD_LABELS,
  SHARE_GROUPS,
  createShareableSnapshot,
  defaultSelectedGroups,
  encryptSnapshot,
  passphraseStrength,
  snapshotPreviewRows,
} from "../security"
import { envelopeToQrPayload, renderEnvelopeQrDataUrl } from "../security/qr.js"

const INR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
})

function formatValue(key, value) {
  if (value === null || value === undefined) {
    return key === "borrower_alias" ? "Not shared — no user-approved alias" : "Not included"
  }
  if (typeof value === "boolean") return value ? "Yes" : "No"
  if (key === "monthly_surplus" || key === "safe_emi_min" || key === "safe_emi_max") {
    return INR.format(value)
  }
  if (key === "overall_confidence") return `${Math.round(value * 100)}%`
  return String(value)
}

function groupLabel(group) {
  return group.fields.map((field) => SHARE_FIELD_LABELS[field]).join(", ")
}

export default function SecureShare() {
  const location = useLocation()
  const result = location.state?.result ?? null

  const [ttlId, setTtlId] = useState("24h")
  const [selectedGroups, setSelectedGroups] = useState(defaultSelectedGroups)
  const [passphrase, setPassphrase] = useState("")
  const [confirm, setConfirm] = useState("")
  const [consent, setConsent] = useState(false)
  const [approvedAlias, setApprovedAlias] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [qrUrl, setQrUrl] = useState("")
  const [payload, setPayload] = useState("")

  const ttlMs = useMemo(
    () => EXPIRY_OPTIONS.find((option) => option.id === ttlId)?.ms,
    [ttlId]
  )
  const strength = useMemo(() => passphraseStrength(passphrase), [passphrase])

  const previewSnapshot = useMemo(() => {
    if (!result) return null
    try {
      const base = createShareableSnapshot(result, { ttlMs, selectedGroups, borrowerAlias: approvedAlias })
      return base
    } catch {
      return null
    }
  }, [result, ttlMs, selectedGroups, approvedAlias])

  const previewRows = previewSnapshot ? snapshotPreviewRows(previewSnapshot) : []

  useEffect(() => {
    return () => {
      setPassphrase("")
      setConfirm("")
      setQrUrl("")
      setPayload("")
    }
  }, [])

  const destroySession = () => {
    setQrUrl("")
    setPayload("")
    setPassphrase("")
    setConfirm("")
    setConsent(false)
    setError("")
  }

  const toggleGroup = (groupId, locked) => {
    if (locked) return
    setSelectedGroups((current) => (
      current.includes(groupId)
        ? current.filter((id) => id !== groupId)
        : [...current, groupId]
    ))
  }

  const handleCreate = async () => {
    setError("")
    if (!result || !previewSnapshot) {
      setError("Run an assessment first, then share from the result page.")
      return
    }
    if (passphrase.length < 8) {
      setError("Choose a passphrase of at least 8 characters. It is never stored.")
      return
    }
    if (passphrase !== confirm) {
      setError("Passphrase confirmation does not match.")
      return
    }
    if (!consent) {
      setError("Confirm that you will send the passphrase separately before encrypting.")
      return
    }
    setBusy(true)
    try {
      const envelope = await encryptSnapshot(previewSnapshot, passphrase)
      const encoded = envelopeToQrPayload(envelope)
      const dataUrl = await renderEnvelopeQrDataUrl(envelope)
      setPayload(encoded)
      setQrUrl(dataUrl)
      setPassphrase("")
      setConfirm("")
    } catch {
      setError("Unable to create a secure share. Try again with a new passphrase.")
      setQrUrl("")
      setPayload("")
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
        <h1 className="text-headline-sm font-jakarta text-sage-on-surface">Secure Share</h1>
        <p className="text-body-md text-sage-on-surface-var font-jakarta">
          Only an allowlisted summary is encrypted on this device. The passphrase is never written into the QR, URL, or storage.
          This is a demo transfer, not production-grade key management.
        </p>
      </div>

      <div className="flex flex-wrap gap-2" aria-label="Secure share actions">
        <Button variant="filled" size="sm" aria-pressed="true">
          <QrCode size={14} aria-hidden="true" />
          <span>Create QR</span>
        </Button>
        <Link to="/import">
          <Button variant="outlined" size="sm" aria-label="Open a secure share">
            <Unlock size={14} aria-hidden="true" />
            <span>Open a share</span>
          </Button>
        </Link>
      </div>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-md border border-sage-outline-var bg-sage-surface-low p-3 text-body-sm text-sage-on-surface font-jakarta"
        >
          <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      <Card level={2} radius="md" className="p-4 sm:p-5 space-y-5">
          <div className="flex items-center gap-2">
            <Shield size={18} className="text-sage-primary" aria-hidden="true" />
            <h2 className="text-title-sm font-jakarta">Create an encrypted QR</h2>
          </div>

          {!result && (
            <p className="text-body-sm font-jakarta">
              No result in this session.{" "}
              <Link to="/result" className="text-sage-primary underline">
                Go to Results
              </Link>{" "}
              after an assessment.
            </p>
          )}

          <fieldset className="space-y-2">
            <legend className="text-label-md font-jakarta text-sage-on-surface-var uppercase">What to share</legend>
            {SHARE_GROUPS.map((group) => (
              <label key={group.id} className="flex items-start gap-2 text-body-sm font-jakarta">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={selectedGroups.includes(group.id)}
                  disabled={group.locked || !result}
                  onChange={() => toggleGroup(group.id, group.locked)}
                />
                <span>
                  {groupLabel(group)}
                  {group.locked ? " (always included)" : ""}
                </span>
              </label>
            ))}
          </fieldset>

          <label htmlFor="share-alias" className="block text-label-md font-jakarta text-sage-on-surface-var">
            User-approved alias (optional)
            <input
              id="share-alias"
              type="text"
              autoComplete="off"
              className="mt-1 w-full rounded-md border border-sage-outline-var bg-sage-surface-low px-3 py-2 text-body-md"
              value={approvedAlias}
              onChange={(event) => setApprovedAlias(event.target.value)}
              placeholder="Leave blank to share no name"
            />
          </label>
          <p className="text-body-sm text-sage-on-surface-var font-jakarta">
            Alias in this share: {previewSnapshot?.assessment.borrower_alias
              ? previewSnapshot.assessment.borrower_alias
              : "not shared"}
          </p>

          <section aria-labelledby="preview-heading" className="space-y-2">
            <h3 id="preview-heading" className="text-label-md font-jakarta text-sage-on-surface-var uppercase">
              Pre-encryption preview
            </h3>
            <p className="text-body-sm text-sage-on-surface-var font-jakarta">
              These values come from the allowlisted snapshot that will be encrypted. Nothing else is added.
            </p>
            {previewRows.length > 0 ? (
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {previewRows.map((row) => (
                  <div key={row.key} className="rounded-md bg-sage-surface-low border border-sage-outline-var p-2.5">
                    <dt className="text-label-sm text-sage-on-surface-var font-jakarta">{row.label}</dt>
                    <dd className="text-title-sm text-sage-on-surface mt-0.5 font-jakarta">
                      {formatValue(row.key, row.value)}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-body-sm font-jakarta">Preview appears after an assessment result is available.</p>
            )}
          </section>

          <section aria-labelledby="excluded-heading">
            <h3 id="excluded-heading" className="text-label-md text-sage-on-surface-var font-jakarta uppercase mb-1">
              Never included
            </h3>
            <ul className="text-body-sm text-sage-on-surface-var font-jakarta space-y-0.5">
              {SHARE_EXCLUDED_LABELS.map((label) => (
                <li key={label}>• {label}</li>
              ))}
            </ul>
          </section>

          <label htmlFor="share-expiry" className="block text-label-md font-jakarta text-sage-on-surface-var">
            Expiry
            <select
              id="share-expiry"
              className="mt-1 w-full rounded-md border border-sage-outline-var bg-sage-surface-low px-3 py-2 text-body-md"
              value={ttlId}
              onChange={(event) => setTtlId(event.target.value)}
            >
              {EXPIRY_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {previewSnapshot && (
            <p className="text-label-sm text-sage-on-surface-var font-jakarta">
              Issued {previewSnapshot.issued_at}. Expires {previewSnapshot.expires_at}.
            </p>
          )}

          <label htmlFor="share-passphrase" className="block text-label-md font-jakarta text-sage-on-surface-var">
            Passphrase (min 8 characters)
            <input
              id="share-passphrase"
              type="password"
              autoComplete="new-password"
              className="mt-1 w-full rounded-md border border-sage-outline-var bg-sage-surface-low px-3 py-2 text-body-md"
              value={passphrase}
              onChange={(event) => setPassphrase(event.target.value)}
            />
          </label>
          <p id="passphrase-strength" aria-live="polite" className="text-body-sm font-jakarta">
            Strength: {passphrase ? strength.label : "Enter a passphrase"}
            {passphrase && (
              <span className="block text-sage-on-surface-var mt-1">
                Use 8+ characters with mixed case, a number, and a symbol.
              </span>
            )}
          </p>
          <label htmlFor="share-confirm" className="block text-label-md font-jakarta text-sage-on-surface-var">
            Confirm passphrase
            <input
              id="share-confirm"
              type="password"
              autoComplete="new-password"
              className="mt-1 w-full rounded-md border border-sage-outline-var bg-sage-surface-low px-3 py-2 text-body-md"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
            />
          </label>

          <label className="flex items-start gap-2 text-body-sm font-jakarta">
            <input
              type="checkbox"
              className="mt-1"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            <span>
              I understand this summary is encrypted on this device. Send the passphrase separately from the QR.
            </span>
          </label>

          <div className="flex flex-col sm:flex-row gap-2">
            <Button
              variant="filled"
              size="md"
              onClick={handleCreate}
              disabled={busy || !result || !consent}
              loading={busy}
              aria-label="Encrypt snapshot and show QR code"
            >
              <span>Encrypt and show QR</span>
            </Button>
            <Button
              variant="outlined"
              size="md"
              onClick={destroySession}
              aria-label="Destroy sharing session and clear QR"
            >
              <Trash2 size={14} aria-hidden="true" />
              <span>Destroy session</span>
            </Button>
          </div>

          {qrUrl && (
            <div className="space-y-3 pt-2">
              <img
                src={qrUrl}
                alt="QR code containing only the encrypted share envelope, not the passphrase or financial plaintext"
                className="mx-auto w-full max-w-[320px] aspect-square bg-white p-3 rounded-md"
              />
              <p className="text-body-sm text-sage-on-surface-var font-jakarta">
                This QR is ciphertext only. Send the passphrase separately from the QR.
              </p>
              <details className="text-body-sm font-jakarta">
                <summary className="cursor-pointer text-sage-primary">Show envelope JSON</summary>
                <pre className="mt-2 p-3 rounded-md bg-sage-surface-highest overflow-x-auto text-label-sm">{payload}</pre>
              </details>
            </div>
          )}
        </Card>
    </PageWrapper>
  )
}
