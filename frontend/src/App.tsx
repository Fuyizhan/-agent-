import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Review from './pages/Review'
import ReviewDetail from './pages/ReviewDetail'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/review" replace />} />
          <Route path="/review" element={<Review />} />
          <Route path="/review/:id" element={<ReviewDetail />} />
          <Route path="*" element={<Navigate to="/review" replace />} />
        </Route>
      </Route>
    </Routes>
  )
}
