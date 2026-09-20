/** Material 3 button variants per DESIGN.md */
export default function Button({
  children,
  variant = 'filled',   // 'filled' | 'tonal' | 'outlined' | 'text'
  size = 'md',          // 'sm' | 'md' | 'lg'
  onClick,
  type = 'button',
  disabled = false,
  className = '',
  loading = false,
  ...rest
}) {
  const base = `
    inline-flex items-center justify-center gap-2 font-jakarta font-semibold
    rounded-full transition-all duration-150 select-none
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-primary/50
    disabled:opacity-40 disabled:pointer-events-none
  `

  const sizes = {
    sm: 'px-4 py-1.5 text-label-md h-8',
    md: 'px-6 py-2.5 text-label-lg h-11',
    lg: 'px-8 py-3 text-body-lg h-14',
  }

  const variants = {
    filled:   'bg-sage-primary text-white hover:brightness-110 active:brightness-90 shadow-level1',
    tonal:    'bg-sage-primary-container text-sage-on-primary-container hover:brightness-95 active:brightness-90',
    outlined: 'bg-transparent border border-sage-outline text-sage-primary hover:bg-sage-surface-low',
    text:     'bg-transparent text-sage-primary hover:bg-sage-surface-low',
  }

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}
      {...rest}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  )
}
