import { Routes, Route } from 'react-router-dom'
import TopBar from './components/layout/TopBar'
import Home from './pages/Home'
import Demo from './pages/Demo'
import Assess from './pages/Assess'
import Result from './pages/Result'
import WhatIf from './pages/WhatIf'
import Passport from './pages/Passport'
import Verifier from './pages/Verifier'

export default function App() {
  return (
    <div className="min-h-screen bg-sage-bg font-jakarta text-sage-on-surface">
      <TopBar />
      <Routes>
        <Route path="/"       element={<Home />} />
        <Route path="/demo"   element={<Demo />} />
        <Route path="/assess" element={<Assess />} />
        <Route path="/result" element={<Result />} />
        <Route path="/what-if" element={<WhatIf />} />
        <Route path="/passport" element={<Passport />} />
        <Route path="/verifier" element={<Verifier />} />
      </Routes>
    </div>
  )
}
