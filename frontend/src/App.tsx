import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom'
import { useState, useCallback, useRef, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import FloorPlan from './pages/FloorPlan'
import Evacuation from './pages/Evacuation'
import RescuerView from './pages/RescuerView'
import NavigationPage from './pages/NavigationPage'
import PeerMap from './pages/PeerMap'
import Login from './pages/Login'
import HealthMonitor from './pages/HealthMonitor'
import { getStoredAuth } from './hooks/useApi'

function Layout({ children, onLogout }: { children: React.ReactNode; onLogout: () => void }) {
  const { role } = getStoredAuth();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setMoreOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-bold text-red-600">ITDA</h1>
          <div className="flex items-center gap-4">
            {/* 코어 4탭 */}
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

            {/* 더보기 드롭다운 */}
            <div className="relative" ref={moreRef}>
              <button
                onClick={() => setMoreOpen((v) => !v)}
                className="px-3 py-1 rounded text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition"
              >
                더보기 ▾
              </button>
              {moreOpen && (
                <div className="absolute right-0 top-full mt-1 w-36 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50">
                  <NavLink
                    to="/navigate"
                    onClick={() => setMoreOpen(false)}
                    className={({ isActive }) =>
                      `block px-4 py-2 text-sm ${isActive ? 'bg-red-50 text-red-700' : 'text-gray-700 hover:bg-gray-50'}`
                    }
                  >
                    대피 안내
                  </NavLink>
                  <NavLink
                    to="/health-monitor"
                    onClick={() => setMoreOpen(false)}
                    className={({ isActive }) =>
                      `block px-4 py-2 text-sm ${isActive ? 'bg-red-50 text-red-700' : 'text-gray-700 hover:bg-gray-50'}`
                    }
                  >
                    건강 모니터
                  </NavLink>
                  <NavLink
                    to="/peers"
                    onClick={() => setMoreOpen(false)}
                    className={({ isActive }) =>
                      `block px-4 py-2 text-sm ${isActive ? 'bg-red-50 text-red-700' : 'text-gray-700 hover:bg-gray-50'}`
                    }
                  >
                    동료 위치
                  </NavLink>
                </div>
              )}
            </div>

            {/* 유저 정보 + 로그아웃 */}
            <div className="flex items-center gap-2 ml-2 pl-4 border-l">
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
        <Route path="/navigate" element={<NavigationPage />} />
        <Route path="/rescuer" element={<RescuerView />} />
        <Route path="/health-monitor" element={<HealthMonitor />} />
        <Route path="/peers" element={<PeerMap />} />
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
