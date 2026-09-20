import { useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, FileSpreadsheet, RotateCcw, ShieldCheck, Sparkles } from 'lucide-react'
import PageWrapper from '../components/layout/PageWrapper'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import GoalForm from '../components/what-if/GoalForm'
import PlanResult from '../components/what-if/PlanResult'
import { planAssessment, planCsv, planDemo } from '../api'

const INITIAL_VALUES = {
  title: 'Car',
  targetAmount: '100000',
  deadlineMonths: '8',
  interestRatePercent: '14',
  tenureMonths: '24',
  desiredBuffer: '',
  currentGoalSavings: '0',
}

export default function WhatIf() {
  const location = useLocation()
  const navigate = useNavigate()
  const source = location.state?.source
  const file = location.state?.file
  const formContext = location.state?.formContext
  const assessmentId = location.state?.result?.assessment_id
  const [goalType, setGoalType] = useState('LOAN_READINESS')
  const [values, setValues] = useState(INITIAL_VALUES)
  const [plan, setPlan] = useState(null)
  const [plannedGoal, setPlannedGoal] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const sourceLabel = useMemo(() => {
    if (source?.startsWith('demo-')) return `${source.slice(5)} demo assessment`
    if (source === 'csv-upload') return location.state?.filename || 'uploaded statement'
    return null
  }, [source, location.state])

  const updateValue = (name, value) => setValues((current) => ({ ...current, [name]: value }))

  const buildGoal = () => {
    const common = {
      type: goalType,
      title: values.title.trim(),
      target_amount: Number(values.targetAmount),
      deadline_months: Number(values.deadlineMonths),
    }
    if (goalType === 'LOAN_READINESS') {
      return {
        ...common,
        annual_interest_rate: Number(values.interestRatePercent) / 100,
        tenure_months: Number(values.tenureMonths),
        desired_buffer: values.desiredBuffer === '' ? null : Number(values.desiredBuffer),
      }
    }
    return { ...common, current_goal_savings: Number(values.currentGoalSavings) }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    try {
      setError(null)
      setPlan(null)
      setLoading(true)
      const goal = buildGoal()
      let result
      if (assessmentId) {
        result = await planAssessment(assessmentId, goal)
      } else if (source?.startsWith('demo-')) {
        result = await planDemo(source.slice(5), goal)
      } else if (source === 'csv-upload' && file && formContext) {
        result = await planCsv(file, formContext, goal)
      } else {
        throw new Error('Your assessment source is no longer available. Run the assessment again to create a plan.')
      }
      setPlan(result)
      setPlannedGoal(goal)
    } catch (err) {
      setError(err.message || 'Unable to calculate this plan.')
    } finally {
      setLoading(false)
    }
  }

  if (!sourceLabel) {
    return (
      <PageWrapper className="max-w-2xl py-16">
        <Card level={2} radius="lg" className="text-center space-y-5">
          <div className="w-14 h-14 rounded-full bg-sage-primary-container text-sage-primary flex items-center justify-center mx-auto"><Sparkles size={26} /></div>
          <h1 className="text-headline-sm font-jakarta text-sage-on-surface">Start with a financial assessment</h1>
          <p className="text-body-md text-sage-on-surface-var font-jakarta">What If uses your actual FinMitra capacity, obligations, and safety checks. Run a demo or assess a statement first.</p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link to="/demo"><Button variant="filled"><Sparkles size={16} />Try a demo</Button></Link>
            <Link to="/assess"><Button variant="outlined"><FileSpreadsheet size={16} />Assess a statement</Button></Link>
          </div>
        </Card>
      </PageWrapper>
    )
  }

  return (
    <PageWrapper className="max-w-5xl space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <p className="text-label-md text-sage-primary font-jakarta">Planning from: {sourceLabel}</p>
          <h1 className="text-headline-md font-jakarta text-sage-on-surface mt-1">What do you want to make possible?</h1>
          <p className="text-body-lg text-sage-on-surface-var font-jakarta mt-2 max-w-3xl">Set a goal and FinMitra will work backward from your current financial position to show the gap and potential paths.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <GoalForm goalType={goalType} setGoalType={(type) => { setGoalType(type); setPlan(null) }} values={values} onChange={updateValue} />
        {error && <div role="alert" className="p-4 rounded-md bg-sage-error-container text-sage-on-error-container text-body-md font-jakarta">{error}</div>}
        <div className="flex justify-end">
          <Button type="submit" size="lg" variant="filled" loading={loading}>
            <span>{loading ? 'Analyzing your goal...' : 'Build my plan'}</span>
            {!loading && <ArrowRight size={18} />}
          </Button>
        </div>
      </form>

      {plan && (
        <section className="space-y-5 pt-4">
          <PlanResult plan={plan} />
          <div className="flex flex-wrap justify-end gap-3">
            <Button variant="tonal" onClick={() => navigate('/passport', { state: { ...location.state, goal: plannedGoal } })}><ShieldCheck size={16} />Add to Passport</Button>
            <Button variant="outlined" onClick={() => { setPlan(null); window.scrollTo({ top: 0, behavior: 'smooth' }) }}><RotateCcw size={16} />Edit this goal</Button>
          </div>
        </section>
      )}
    </PageWrapper>
  )
}
