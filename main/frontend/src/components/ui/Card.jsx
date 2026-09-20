/**
 * Card container with tonal elevation per DESIGN.md.
 * level: 0 (flat) | 1 | 2 | 3
 */
export default function Card({
  children,
  level = 1,
  className = '',
  padding = true,
  radius = 'md',      // 'sm' | 'md' | 'lg'
}) {
  const surfaces = {
    0: 'bg-sage-bg',
    1: 'bg-white shadow-level1',
    2: 'bg-sage-surface-med shadow-level2',
    3: 'bg-sage-surface-high shadow-level3',
  }

  const radii = {
    sm: 'rounded',       // 1rem
    md: 'rounded-md',    // 1.5rem
    lg: 'rounded-lg',    // 2rem
  }

  return (
    <div
      className={`
        ${surfaces[level]}
        ${radii[radius]}
        border border-sage-outline-var
        ${padding ? 'p-6' : ''}
        ${className}
      `}
    >
      {children}
    </div>
  )
}
