import { Routes, Route, useLocation } from 'react-router-dom'
import Navbar from './components/common/Navbar'
import FeedPage from './pages/FeedPage'
import ArticleDetailPage from './pages/ArticleDetailPage'
import ChatPage from './pages/ChatPage'
import DigestPage from './pages/DigestPage'
import DashboardPage from './pages/DashboardPage'

function App() {
  const location = useLocation()
  const isChatPage = location.pathname === '/chat'

  return (
    <>
      {!isChatPage && <Navbar />}
      <main className={isChatPage ? '' : 'flex-1'}>
        <Routes>
          <Route path="/" element={<FeedPage />} />
          <Route path="/article/:id" element={<ArticleDetailPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/digest" element={<DigestPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </>
  )
}

export default App
