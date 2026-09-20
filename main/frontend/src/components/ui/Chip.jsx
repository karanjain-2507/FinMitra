/** Material 3 chip — filter/assist style per DESIGN.md */
export default function Chip({ label, selected = false, onClick, icon: Icon }) {
  return (
    <button
      onClick={onClick}
      className={`
        inline-flex items-center gap-1.5 rounded-full h-8 px-4 text-label-md font-jakarta
        border transition-all duration-150 select-none
        ${selected
          ? 'bg-sage-primary-container text-sage-on-primary-container border-transparent'
          : 'bg-sage-surface-low text-sage-on-surface-var border-sage-outline-var hover:bg-sage-surface-med'}
      `}
    >
      {Icon && <Icon size={14} />}
      {label}
    </button>
  )
}
