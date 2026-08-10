import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom'
import { useState, useCallback } from 'react'
import Dashboard from './pages/Dashboard'
import FloorPlan from './pages/FloorPlan'
import Evacuation from './pages/Evacuation'
import RescuerView from './pages/RescuerView'
import Login from './pages/Login'
import { getStoredAuth } from './hooks/useApi'

function Layout({ children, onLogout }: { children: React.ReactNode; onLogout: () => void }) {
  const { role } = getStoredAuth();

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-bold text-red-600">FireEscape AI</h1>
          <div className="flex items-center gap-4">
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
            <div className="flex items-center gap-2 ml-4 pl-4 border-l">
              <span className="text-xs text-gray-500">{role}</span>
              <button
                onClick={onLogout}
                className="text-xs text-gray-400 hover:text-red-600 transition"
              >
                로그아웃
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="max-w-7xl mx-auto">
        {children}
      </main>
    </div>
  )
}

function AppRoutes() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!getStoredAuth().token);
  const navigate = useNavigate();

  const handleLoginSuccess = useCallback(() => {
    setIsAuthenticated(true);
    navigate("/");
  }, [navigate]);

  const handleLogout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_role");
    setIsAuthenticated(false);
    navigate("/login");
  }, [navigate]);

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<Login onLoginSuccess={handleLoginSuccess} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Layout onLogout={handleLogout}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/floor-plan" element={<FloorPlan />} />
        <Route path="/evacuation" element={<Evacuation />} />
        <Route path="/rescuer" element={<RescuerView />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}

export default App
