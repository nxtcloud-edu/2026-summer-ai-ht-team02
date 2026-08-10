import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import FloorPlan from './pages/FloorPlan'
import Evacuation from './pages/Evacuation'
import RescuerView from './pages/RescuerView'

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-100">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-bold text-red-600">🔥 FireEscape AI</h1>
          <nav className="flex gap-4">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `px-3 py-1 rounded text-sm ${isActive ? 'bg-red-100 text-red-700' : 'text-gray-600 hover:text-gray-900'}`
              }
            >
              대시보드
            </NavLink>
            <NavLink
              to="/floor-plan"
              className={({ isActive }) =>
                `px-3 py-1 rounded text-sm ${isActive ? 'bg-red-100 text-red-700' : 'text-gray-600 hover:text-gray-900'}`
              }
            >
              도면 관리
            </NavLink>
            <NavLink
              to="/evacuation"
              className={({ isActive }) =>
                `px-3 py-1 rounded text-sm ${isActive ? 'bg-red-100 text-red-700' : 'text-gray-600 hover:text-gray-900'}`
              }
            >
              탈출 경로
            </NavLink>
            <NavLink
              to="/rescuer"
              className={({ isActive }) =>
                `px-3 py-1 rounded text-sm ${isActive ? 'bg-red-100 text-red-700' : 'text-gray-600 hover:text-gray-900'}`
              }
            >
              구조대
            </NavLink>
          </nav>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="max-w-7xl mx-auto">
        {children}
      </main>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/floor-plan" element={<FloorPlan />} />
          <Route path="/evacuation" element={<Evacuation />} />
          <Route path="/rescuer" element={<RescuerView />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
