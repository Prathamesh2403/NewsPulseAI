import { Routes, Route, useLocation } from 'react-router-dom'
import Navbar from './components/common/Navbar'
import FeedPage from './pages/FeedPage'
import ArticleDetailPage from './pages/ArticleDetailPage'
import ChatPage from './pages/ChatPage'
import DigestPage from './pages/DigestPage'
import DashboardPage from './pages/DashboardPage'
import LoginPage from './pages/LoginPage'
import ProtectedRoute from './components/common/ProtectedRoute'

function App() {
  const location = useLocation()
  const isChatPage = location.pathname === '/chat'

  const isAuthPage = location.pathname === '/login'

  return (
    <>
      {!isChatPage && !isAuthPage && <Navbar />}
      <main className={isChatPage ? '' : 'flex-1'}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<ProtectedRoute><FeedPage /></ProtectedRoute>} />
          <Route path="/article/:id" element={<ProtectedRoute><ArticleDetailPage /></ProtectedRoute>} />
          <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
          <Route path="/digest" element={<ProtectedRoute><DigestPage /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        </Routes>
      </main>
    </>
  )
}

export default App
