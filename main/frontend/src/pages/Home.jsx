import { Link, useNavigate } from 'react-router-dom'
import { Sparkles, FileSpreadsheet, ShieldCheck, ArrowRight, Activity, Landmark, Wallet } from 'lucide-react'
import PageWrapper from '../components/layout/PageWrapper'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'

export default function Home() {
  const navigate = useNavigate()

  const featureCards = [
    {
      icon: ShieldCheck,
      title: 'Evidence Verification',
      desc: 'Multi-source ingestion, deduplication, anomaly detection, and automated grading (A to D).',
      tone: 'text-sage-primary',
      bg: 'bg-sage-primary-container/40',
    },
    {
      icon: Activity,
      title: 'Cash-Flow ML Model',
      desc: '12 temporal feature extractions and ML-driven 90-day cash-flow stress probability scoring.',
      tone: 'text-sage-tertiary',
      bg: 'bg-sage-tertiary-container/30',
    },
    {
      icon: Landmark,
      title: 'Repayment & Hard Blocks',
      desc: 'Deterministic loan cycle tracking, digital corroboration, and automatic hard caps for delinquency.',
      tone: 'text-sage-secondary',
      bg: 'bg-sage-secondary-container/40',
    },
    {
      icon: Wallet,
      title: 'Capacity & Safe EMI',
      desc: 'Deterministic monthly surplus derivation, stress test matrix, and tenured loan capacity tables.',
      tone: 'text-sage-warning',
      bg: 'bg-sage-warning-container/40',
    },
  ]

  return (
    <PageWrapper className="space-y-12">
      {/* Hero Section */}
      <section className="text-center max-w-3xl mx-auto space-y-6 pt-6">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-primary-container text-sage-on-primary-container text-label-md font-jakarta border border-sage-primary/10">
          <Sparkles size={14} />
          <span>Holistic Alternative Credit Intelligence</span>
        </div>

        <h1 className="text-headline-lg sm:text-display font-jakarta font-semibold text-sage-on-surface tracking-tight">
          Clarity &amp; Dignity for Informal Borrowers
        </h1>

        <p className="text-body-lg text-sage-on-surface-var font-jakarta max-w-2xl mx-auto leading-relaxed">
          FinMitra fuses raw transaction evidence, machine learning cash-flow forecasting, informal repayment histories, and conservative capacity modeling into one auditable credit passport.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
          <Button
            size="lg"
            variant="filled"
            onClick={() => navigate('/demo')}
            className="group"
          >
            <span>Explore Live Demos</span>
            <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
          </Button>

          <Button
            size="lg"
            variant="outlined"
            onClick={() => navigate('/assess')}
          >
            <FileSpreadsheet size={18} />
            <span>Assess Statement CSV</span>
          </Button>
        </div>
      </section>

      {/* Quick Action Tiles */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
        <Card level={2} radius="lg" className="p-8 flex flex-col justify-between group hover:border-sage-primary/40 transition-colors">
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-full bg-sage-primary-container flex items-center justify-center">
              <Sparkles size={22} className="text-sage-on-primary-container" />
            </div>
            <h2 className="text-title-lg font-jakarta text-sage-on-surface">
              Interactive Demos
            </h2>
            <p className="text-body-md text-sage-on-surface-var font-jakarta">
              Explore pre-packaged scenarios including a strong shopkeeper, an unpaid informal debt block, and a thin-file applicant.
            </p>
          </div>
          <div className="pt-6">
            <Link to="/demo">
              <Button variant="tonal" size="md">
                <span>View 3 Scenarios</span>
                <ArrowRight size={16} />
              </Button>
            </Link>
          </div>
        </Card>

        <Card level={2} radius="lg" className="p-8 flex flex-col justify-between group hover:border-sage-primary/40 transition-colors">
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-full bg-sage-secondary-container flex items-center justify-center">
              <FileSpreadsheet size={22} className="text-sage-secondary" />
            </div>
            <h2 className="text-title-lg font-jakarta text-sage-on-surface">
              Statement Evaluation
            </h2>
            <p className="text-body-md text-sage-on-surface-var font-jakarta">
              Upload bank transaction CSVs or ledger exports to trigger end-to-end normalization, ML feature extraction, and capacity analysis.
            </p>
          </div>
          <div className="pt-6">
            <Link to="/assess">
              <Button variant="outlined" size="md">
                <span>Upload Statement</span>
                <ArrowRight size={16} />
              </Button>
            </Link>
          </div>
        </Card>
      </section>

      {/* Four Engines Breakdown */}
      <section className="space-y-6 pt-4">
        <div className="text-center max-w-xl mx-auto space-y-2">
          <h2 className="text-headline-sm font-jakarta text-sage-on-surface">
            The Four-Engine Architecture
          </h2>
          <p className="text-body-md text-sage-on-surface-var font-jakarta">
            Engineered with strict process boundaries and zero hidden mock data.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {featureCards.map((feat, idx) => {
            const Icon = feat.icon
            return (
              <Card key={idx} level={1} radius="md" className="p-5 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className={`w-10 h-10 rounded-full ${feat.bg} flex items-center justify-center`}>
                    <Icon size={20} className={feat.tone} />
                  </div>
                  <h3 className="text-title-md font-jakarta text-sage-on-surface">
                    {feat.title}
                  </h3>
                  <p className="text-body-sm text-sage-on-surface-var font-jakarta">
                    {feat.desc}
                  </p>
                </div>
              </Card>
            )
          })}
        </div>
      </section>
    </PageWrapper>
  )
}
