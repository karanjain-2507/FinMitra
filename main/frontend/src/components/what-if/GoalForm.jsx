import Card from '../ui/Card'

const fieldClass = 'w-full h-11 px-3.5 rounded-sm bg-sage-surface-low border border-sage-outline text-body-md font-jakarta text-sage-on-surface focus:outline-none focus:border-sage-primary focus:ring-1 focus:ring-sage-primary'

function Field({ id, label, hint, children }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-label-md font-jakarta text-sage-on-surface">{label}</label>
      {children}
      {hint && <p id={`${id}-hint`} className="text-body-sm text-sage-on-surface-var font-jakarta">{hint}</p>}
    </div>
  )
}

export default function GoalForm({ goalType, setGoalType, values, onChange }) {
  const set = (name) => (event) => onChange(name, event.target.value)

  return (
    <Card level={1} radius="lg" className="space-y-6">
      <div>
        <p className="text-label-sm uppercase tracking-wider text-sage-on-surface-var font-jakarta">Goal type</p>
        <div className="grid grid-cols-2 gap-2 mt-2" role="radiogroup" aria-label="Financial goal type">
          <button
            type="button"
            role="radio"
            aria-checked={goalType === 'LOAN_READINESS'}
            onClick={() => setGoalType('LOAN_READINESS')}
            className={`p-3 rounded-md border text-label-lg font-jakarta transition-colors ${goalType === 'LOAN_READINESS' ? 'bg-sage-primary-container border-sage-primary text-sage-on-primary-container' : 'bg-sage-surface-low border-sage-outline-var text-sage-on-surface-var'}`}
          >
            Prepare for a loan
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={goalType === 'SAVINGS_TARGET'}
            onClick={() => setGoalType('SAVINGS_TARGET')}
            className={`p-3 rounded-md border text-label-lg font-jakarta transition-colors ${goalType === 'SAVINGS_TARGET' ? 'bg-sage-primary-container border-sage-primary text-sage-on-primary-container' : 'bg-sage-surface-low border-sage-outline-var text-sage-on-surface-var'}`}
          >
            Reach a savings target
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <Field id="goal-title" label="What is this goal for?">
          <input id="goal-title" required maxLength={80} className={fieldClass} value={values.title} onChange={set('title')} placeholder="e.g. Car, equipment, emergency fund" />
        </Field>
        <Field id="goal-target" label="Target amount" hint="The total amount in Indian rupees.">
          <input id="goal-target" aria-describedby="goal-target-hint" required min="0.01" max="100000000" step="0.01" type="number" className={fieldClass} value={values.targetAmount} onChange={set('targetAmount')} />
        </Field>
        <Field id="goal-deadline" label="When do you want to be ready?" hint="Readiness deadline in months.">
          <input id="goal-deadline" aria-describedby="goal-deadline-hint" required min="1" max="120" type="number" className={fieldClass} value={values.deadlineMonths} onChange={set('deadlineMonths')} />
        </Field>

        {goalType === 'LOAN_READINESS' ? (
          <>
            <Field id="goal-interest" label="Expected annual interest" hint="Enter the percentage quoted by the lender.">
              <div className="relative">
                <input id="goal-interest" aria-describedby="goal-interest-hint" required min="0" max="100" step="0.0001" type="number" className={`${fieldClass} pr-10`} value={values.interestRatePercent} onChange={set('interestRatePercent')} />
                <span className="absolute right-3 top-2.5 text-sage-on-surface-var">%</span>
              </div>
            </Field>
            <Field id="goal-tenure" label="Loan repayment tenure" hint="How many months the loan itself will run.">
              <input id="goal-tenure" aria-describedby="goal-tenure-hint" required min="1" max="360" type="number" className={fieldClass} value={values.tenureMonths} onChange={set('tenureMonths')} />
            </Field>
            <Field id="goal-buffer" label="Desired cash buffer (optional)" hint="Kept separate from the loan amount and EMI.">
              <input id="goal-buffer" aria-describedby="goal-buffer-hint" min="0" max="100000000" step="0.01" type="number" className={fieldClass} value={values.desiredBuffer} onChange={set('desiredBuffer')} placeholder="No additional target" />
            </Field>
          </>
        ) : (
          <Field id="goal-saved" label="Already saved for this goal" hint="Do not include emergency money unless you intend to use it.">
            <input id="goal-saved" aria-describedby="goal-saved-hint" required min="0" max="100000000" step="0.01" type="number" className={fieldClass} value={values.currentGoalSavings} onChange={set('currentGoalSavings')} />
          </Field>
        )}
      </div>
    </Card>
  )
}
