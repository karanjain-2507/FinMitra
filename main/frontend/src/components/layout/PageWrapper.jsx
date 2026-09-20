export default function PageWrapper({ children, className = '' }) {
  return (
    <main className={`max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 ${className}`}>
      {children}
    </main>
  )
}
