import { Routes, Route } from 'react-router-dom'
import TopBar from './components/layout/TopBar'
import Home from './pages/Home'
import Demo from './pages/Demo'
import Assess from './pages/Assess'
import Result from './pages/Result'
import SecureShare from './pages/SecureShare'
import SecureImport from './pages/SecureImport'

export default function App() {
  return (
    <div className="min-h-screen bg-sage-bg font-jakarta text-sage-on-surface">
      <TopBar />
      <Routes>
        <Route path="/"       element={<Home />} />
        <Route path="/demo"   element={<Demo />} />
        <Route path="/assess" element={<Assess />} />
        <Route path="/result" element={<Result />} />
        <Route path="/share"  element={<SecureShare />} />
        <Route path="/import" element={<SecureImport />} />
      </Routes>
    </div>
  )
}
