import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileSpreadsheet, ArrowRight, Loader2, HelpCircle, Sparkles, SlidersHorizontal, Download } from 'lucide-react'
import PageWrapper from '../components/layout/PageWrapper'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import CsvUpload from '../components/form/CsvUpload'
import { assessCsv } from '../api'
import { SAMPLE_DATASETS } from '../sampleData'

export default function Assess() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [activePreset, setActivePreset] = useState(null)
  const [borrowerId, setBorrowerId] = useState('BORROWER-001')
  const [businessName, setBusinessName] = useState('')
  const [evaluationDate, setEvaluationDate] = useState(() => new Date().toISOString().split('T')[0])
  const [sourceType, setSourceType] = useState('BANK_STATEMENT')
  const [householdExpense, setHouseholdExpense] = useState(12000)
  const [balanceBuffer, setBalanceBuffer] = useState(5000)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleLoadPreset = (preset) => {
    setActivePreset(preset.id)
    const blob = new Blob([preset.csvContent], { type: 'text/csv' })
    const syntheticFile = new File([blob], `${preset.id}_statement.csv`, { type: 'text/csv' })
    setFile(syntheticFile)
    setBorrowerId(preset.defaultContext.borrowerId)
    setBusinessName(preset.defaultContext.businessName)
    setEvaluationDate(preset.defaultContext.evaluationDate)
    setSourceType(preset.defaultContext.sourceType)
    setHouseholdExpense(preset.defaultContext.householdExpense)
    setBalanceBuffer(preset.defaultContext.balanceBuffer)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) {
      setError('Please upload a transaction CSV file or select one of the Quick-Load presets above.')
      return
    }

    try {
      setError(null)
      setLoading(true)
      const formData = new FormData()
      formData.append('file', file)
      formData.append('borrower_id', borrowerId.trim() || 'BORROWER-001')
      formData.append('business_name', businessName.trim())
      formData.append('evaluation_date', evaluationDate)
      formData.append('source_type', sourceType)
      formData.append('household_expense', householdExpense)
      formData.append('balance_buffer', balanceBuffer)

      const result = await assessCsv(formData)
      navigate('/result', {
        state: {
          result,
          source: 'csv-upload',
          filename: file.name,
          formContext: {
            borrowerId,
            businessName,
            evaluationDate,
            sourceType,
            householdExpense,
            balanceBuffer,
          },
        },
      })
    } catch (err) {
      setError(err.message || 'Assessment failed. Verify the CSV format and server availability.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <PageWrapper className="max-w-3xl space-y-8">
      <div className="space-y-2">
        <h1 className="text-headline-md font-jakarta text-sage-on-surface">
          Assess &amp; Experiment with Statements
        </h1>
        <p className="text-body-lg text-sage-on-surface-var font-jakarta">
          Upload your own bank CSV or pick a sample dataset below, tweak the household expenses and financial parameters, and watch how the scores, stress gauge, and Safe EMI update.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-md bg-sage-error-container text-sage-on-error-container text-body-md font-jakarta border border-sage-error/20">
          <strong>Assessment Error:</strong> {error}
        </div>
      )}

      {/* Preset Scenarios Selector */}
      <Card level={2} radius="lg" className="space-y-3 p-5">
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-sage-primary" />
          <h2 className="text-title-md font-jakarta text-sage-on-surface">
            Quick-Load Sample Datasets
          </h2>
        </div>
        <p className="text-body-sm text-sage-on-surface-var font-jakarta">
          Select a benchmark business profile to instantly load statement records and see how different transaction patterns alter the graphs:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          {SAMPLE_DATASETS.map((preset) => {
            const isSelected = activePreset === preset.id
            return (
              <button
                key={preset.id}
                type="button"
                onClick={() => handleLoadPreset(preset)}
                className={`
                  p-3 rounded-md text-left transition-all border font-jakarta flex flex-col justify-between
                  ${isSelected
                    ? 'bg-sage-primary-container/40 border-sage-primary text-sage-on-surface shadow-level1'
                    : 'bg-sage-surface-low border-sage-outline-var hover:bg-sage-surface-med text-sage-on-surface'}
                `}
              >
                <div>
                  <p className="text-label-lg font-semibold">{preset.title}</p>
                  <p className="text-body-sm text-sage-on-surface-var mt-0.5 leading-snug">
                    {preset.subtitle}
                  </p>
                </div>
                <span className="text-label-sm font-semibold text-sage-primary mt-3 flex items-center gap-1">
                  {isSelected ? '✓ Loaded' : 'Load Dataset →'}
                </span>
              </button>
            )
          })}
        </div>
      </Card>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Step 1: File Upload */}
        <Card level={1} radius="md" className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-sage-primary text-white text-label-sm flex items-center justify-center font-jakarta">
              1
            </span>
            <h2 className="text-title-md font-jakarta text-sage-on-surface">
              Upload or Edit Statement CSV
            </h2>
          </div>

          <CsvUpload onFile={(f) => { setFile(f); setActivePreset(null); }} file={file} error={null} />

          <div className="p-3 rounded-md bg-sage-surface-low border border-sage-outline-var text-body-sm text-sage-on-surface-var font-jakarta flex items-start gap-2">
            <HelpCircle size={16} className="text-sage-primary flex-shrink-0 mt-0.5" />
            <span>
              Expected CSV columns: <strong>date</strong>, <strong>amount</strong>, <strong>direction (CREDIT/DEBIT)</strong>, <strong>category</strong>, <strong>narration</strong>.
            </span>
          </div>
        </Card>

        {/* Step 2: Context Parameters & Sliders */}
        <Card level={1} radius="md" className="space-y-5">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-sage-primary text-white text-label-sm flex items-center justify-center font-jakarta">
              2
            </span>
            <h2 className="text-title-md font-jakarta text-sage-on-surface">
              Borrower &amp; Financial Context
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-label-md font-jakarta text-sage-on-surface">
                Borrower Reference ID
              </label>
              <input
                type="text"
                value={borrowerId}
                onChange={(e) => setBorrowerId(e.target.value)}
                placeholder="e.g. BORROWER-001"
                className="w-full h-11 px-3.5 rounded-sm bg-sage-surface-low border border-sage-outline text-body-md font-jakarta text-sage-on-surface focus:outline-none focus:border-sage-primary focus:ring-1 focus:ring-sage-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-label-md font-jakarta text-sage-on-surface">
                Business Name (Optional)
              </label>
              <input
                type="text"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                placeholder="e.g. Gupta General Store"
                className="w-full h-11 px-3.5 rounded-sm bg-sage-surface-low border border-sage-outline text-body-md font-jakarta text-sage-on-surface focus:outline-none focus:border-sage-primary focus:ring-1 focus:ring-sage-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-label-md font-jakarta text-sage-on-surface">
                Evaluation Cutoff Date
              </label>
              <input
                type="date"
                value={evaluationDate}
                onChange={(e) => setEvaluationDate(e.target.value)}
                className="w-full h-11 px-3.5 rounded-sm bg-sage-surface-low border border-sage-outline text-body-md font-jakarta text-sage-on-surface focus:outline-none focus:border-sage-primary focus:ring-1 focus:ring-sage-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-label-md font-jakarta text-sage-on-surface">
                Source Document Type
              </label>
              <select
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value)}
                className="w-full h-11 px-3.5 rounded-sm bg-sage-surface-low border border-sage-outline text-body-md font-jakarta text-sage-on-surface focus:outline-none focus:border-sage-primary focus:ring-1 focus:ring-sage-primary"
              >
                <option value="BANK_STATEMENT">Bank Statement</option>
                <option value="UPI">UPI Transaction Log</option>
                <option value="POS">POS Settlement Report</option>
                <option value="LEDGER">Digital Khatabook / Ledger</option>
                <option value="MARKETPLACE">E-Commerce Marketplace</option>
              </select>
            </div>

            <div className="space-y-1.5 sm:col-span-2 p-3.5 rounded-md bg-sage-surface-low border border-sage-outline-var">
              <div className="flex justify-between items-center mb-1">
                <label className="text-label-md font-jakarta text-sage-on-surface">
                  Monthly Household Expense
                </label>
                <span className="text-title-sm font-semibold font-jakarta text-sage-on-surface">
                  ₹{householdExpense.toLocaleString('en-IN')}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="60000"
                step="1000"
                value={householdExpense}
                onChange={(e) => setHouseholdExpense(parseFloat(e.target.value) || 0)}
                className="w-full accent-sage-primary cursor-pointer"
              />
              <p className="text-body-sm text-sage-on-surface-var font-jakarta mt-1">
                Directly reduces monthly surplus and adjusts the Safe EMI capacity calculation.
              </p>
            </div>

            <div className="space-y-1.5 sm:col-span-2 p-3.5 rounded-md bg-sage-surface-low border border-sage-outline-var">
              <div className="flex justify-between items-center mb-1">
                <label className="text-label-md font-jakarta text-sage-on-surface">
                  Available Balance Buffer
                </label>
                <span className="text-title-sm font-semibold font-jakarta text-sage-on-surface">
                  ₹{balanceBuffer.toLocaleString('en-IN')}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="50000"
                step="1000"
                value={balanceBuffer}
                onChange={(e) => setBalanceBuffer(parseFloat(e.target.value) || 0)}
                className="w-full accent-sage-primary cursor-pointer"
              />
              <p className="text-body-sm text-sage-on-surface-var font-jakarta mt-1">
                Cash buffer tested during liquidity stress tests.
              </p>
            </div>
          </div>
        </Card>

        {/* Submit */}
        <div className="flex justify-end gap-3 pt-2">
          <Button
            type="submit"
            size="lg"
            variant="filled"
            disabled={!file || loading}
            loading={loading}
          >
            {loading ? (
              <span>Running All 4 Engines...</span>
            ) : (
              <>
                <span>Run FinMitra Assessment</span>
                <ArrowRight size={18} />
              </>
            )}
          </Button>
        </div>
      </form>
    </PageWrapper>
  )
}
