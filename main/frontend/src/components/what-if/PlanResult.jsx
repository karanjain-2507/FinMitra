import { AlertTriangle, CheckCircle2, CircleDollarSign, Route, ShieldAlert } from 'lucide-react'
import Card from '../ui/Card'
import Badge from '../ui/Badge'

const INR = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })
const formatMoney = (value, fallback = 'Not available') => value == null ? fallback : INR.format(value)

const OUTCOMES = {
  ACHIEVABLE_NOW: { title: 'Achievable with your current capacity', tone: 'positive', icon: CheckCircle2, className: 'bg-sage-success-container text-sage-success' },
  ACHIEVABLE_WITH_CHANGES: { title: 'Possible if your monthly position changes', tone: 'warning', icon: Route, className: 'bg-sage-warning-container text-sage-warning' },
  BLOCKED: { title: 'Resolve the repayment block first', tone: 'negative', icon: ShieldAlert, className: 'bg-sage-error-container text-sage-error' },
  INSUFFICIENT_DATA: { title: 'More financial history is needed', tone: 'warning', icon: AlertTriangle, className: 'bg-sage-warning-container text-sage-warning' },
}

const PATH_LABELS = {
  REDUCE_EXPENSES: 'Reduce monthly expenses',
  INCREASE_INCOME: 'Increase monthly income',
  MIXED_CHANGE: 'Combine income and expense changes',
  LOWER_PRINCIPAL: 'Choose a smaller loan',
  EXTEND_LOAN_TENURE: 'Use a longer loan tenure',
  EXTEND_SAVINGS_DEADLINE: 'Allow more time to save',
  REDUCE_TARGET: 'Use a lower savings target',
  BUILD_BUFFER: 'Build the desired cash buffer',
  RESOLVE_REPAYMENT_BLOCK: 'Resolve the overdue repayment issue',
}

function Metric({ label, value, suffix = '' }) {
  return (
    <div className="p-3 rounded-md bg-sage-surface-low border border-sage-outline-var">
      <p className="text-label-sm uppercase tracking-wider text-sage-on-surface-var font-jakarta">{label}</p>
      <p className="text-title-md font-semibold text-sage-on-surface font-jakarta mt-1">{value}{suffix}</p>
    </div>
  )
}

function pathDetail(path) {
  if (!path.available) return 'Not available within the modeled limits.'
  if (path.type === 'MIXED_CHANGE') return `${INR.format(path.expense_reduction)}/month less spending + ${INR.format(path.income_increase)}/month more income.`
  if (path.new_principal != null) return `Affordable principal at these terms: about ${INR.format(path.new_principal)}.`
  if (path.new_tenure_months != null) return `Shortest modeled tenure that fits: ${path.new_tenure_months} months.`
  if (path.new_deadline_months != null) return `Estimated deadline at the current contribution: ${path.new_deadline_months} months.`
  if (path.new_target_amount != null) return `Projected reachable target: about ${INR.format(path.new_target_amount)}.`
  if (path.monthly_amount != null) return `${INR.format(path.monthly_amount)} per month.`
  return 'This condition must be addressed before new borrowing is considered.'
}

export default function PlanResult({ plan }) {
  const config = OUTCOMES[plan.outcome] ?? OUTCOMES.INSUFFICIENT_DATA
  const Icon = config.icon
  const isLoan = plan.goal.type === 'LOAN_READINESS'
  const required = isLoan ? plan.required_state.required_emi : plan.required_state.required_monthly_saving
  const monthlyGap = isLoan ? plan.gap.monthly_cashflow_gap : plan.gap.monthly_savings_gap
  const gapDisplay = plan.outcome === 'BLOCKED' ? 'Not applicable' : formatMoney(monthlyGap)

  return (
    <div className="space-y-6" aria-live="polite">
      <Card level={2} radius="lg" className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${config.className}`}><Icon size={24} /></div>
        <div className="flex-1">
          <Badge label={plan.outcome.replaceAll('_', ' ')} tone={config.tone} size="sm" />
          <h2 className="text-title-lg text-sage-on-surface font-jakarta mt-2">{config.title}</h2>
          <p className="text-body-md text-sage-on-surface-var font-jakarta mt-1">
            {plan.goal.title}: {INR.format(plan.goal.target_amount)} target in {plan.goal.deadline_months} months.
          </p>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card level={1} radius="md">
          <h3 className="text-title-md font-jakarta text-sage-on-surface mb-4">Where you are now</h3>
          <div className="grid grid-cols-2 gap-3">
            <Metric label="Monthly inflow" value={formatMoney(plan.current_state.monthly_inflow)} />
            <Metric label="Monthly surplus" value={formatMoney(plan.current_state.monthly_surplus)} />
            <Metric label="Safe EMI maximum" value={formatMoney(plan.current_state.safe_emi_max)} suffix={plan.current_state.safe_emi_max == null ? '' : '/month'} />
            <Metric label="Available buffer" value={formatMoney(plan.current_state.available_balance_buffer)} />
          </div>
        </Card>
        <Card level={1} radius="md">
          <h3 className="text-title-md font-jakarta text-sage-on-surface mb-4">What the goal requires</h3>
          <div className="grid grid-cols-2 gap-3">
            <Metric label={isLoan ? 'Required EMI' : 'Monthly saving'} value={formatMoney(required)} suffix={required == null ? '' : '/month'} />
            <Metric label="Monthly change needed" value={gapDisplay} suffix={monthlyGap == null || plan.outcome === 'BLOCKED' ? '' : '/month'} />
            {isLoan && <Metric label="Loan tenure" value={plan.goal.tenure_months} suffix=" months" />}
            {isLoan && <Metric label="EMI above safe limit" value={plan.outcome === 'BLOCKED' ? 'Not applicable' : formatMoney(plan.gap.emi_gap)} suffix={plan.gap.emi_gap == null || plan.outcome === 'BLOCKED' ? '' : '/month'} />}
            {!isLoan && <Metric label="Projected amount" value={formatMoney(plan.required_state.projected_goal_amount)} />}
          </div>
        </Card>
      </div>

      {plan.paths.length > 0 && (
        <Card level={1} radius="md">
          <div className="flex items-center gap-2 mb-4"><CircleDollarSign size={19} className="text-sage-primary" /><h3 className="text-title-md font-jakarta text-sage-on-surface">Potential paths</h3></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {plan.paths.map((path, index) => (
              <div key={`${path.type}-${index}`} className={`p-4 rounded-md border ${path.available ? 'bg-sage-surface-low border-sage-outline-var' : 'bg-sage-surface-highest border-sage-outline-var opacity-70'}`}>
                <p className="text-label-lg font-jakarta text-sage-on-surface">{PATH_LABELS[path.type] ?? path.type}</p>
                <p className="text-body-sm text-sage-on-surface-var font-jakarta mt-1">{pathDetail(path)}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {(plan.safety.warning_keys.length > 0 || plan.safety.failed_stress_tests.length > 0) && (
        <Card level={1} radius="md" className="border-sage-warning/40">
          <div className="flex items-center gap-2"><AlertTriangle size={18} className="text-sage-warning" /><h3 className="text-title-md font-jakarta">Important safety checks</h3></div>
          <ul className="mt-3 space-y-2 text-body-sm text-sage-on-surface-var font-jakarta list-disc pl-5">
            {plan.safety.new_credit_blocked && <li>New borrowing is blocked because the assessment found an unresolved repayment issue.</li>}
            {plan.safety.warning_keys.includes('whatIf.safety.highStressFailure') && <li>The current assessment failed one or more high-severity affordability stress tests.</li>}
            {plan.safety.warning_keys.includes('whatIf.safety.lowConfidence') && <li>This result uses limited-confidence financial information.</li>}
            {plan.safety.warning_keys.includes('whatIf.safety.noRemainingMargin') && <li>This savings path uses all modeled monthly surplus and leaves no extra monthly margin.</li>}
            {plan.safety.warning_keys.includes('whatIf.safety.insufficientHistory') && <li>Monthly inflow, surplus, and safe EMI are unavailable until more transaction history is provided.</li>}
          </ul>
        </Card>
      )}

      <details className="p-5 rounded-md bg-sage-surface-low border border-sage-outline-var">
        <summary className="cursor-pointer text-label-lg text-sage-primary font-jakarta">Assumptions and limitations</summary>
        <ul className="mt-3 space-y-2 text-body-sm text-sage-on-surface-var font-jakarta list-disc pl-5">
          <li>The plan uses the current FinMitra assessment and does not change the underlying financial data.</li>
          <li>Amounts are estimates under the entered rate, tenure, deadline, and existing capacity policy.</li>
          <li>This is planning guidance, not loan approval or a guarantee.</li>
        </ul>
      </details>
    </div>
  )
}
