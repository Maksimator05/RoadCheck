import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { Layout } from '../components/Layout/Layout'
import { DashboardPage } from '../pages/DashboardPage/DashboardPage'
import { HistoryPage } from '../pages/HistoryPage/HistoryPage'
import { LoginPage } from '../pages/LoginPage/LoginPage'
import { ProfilePage } from '../pages/ProfilePage/ProfilePage'
import { RegisterPage } from '../pages/RegisterPage/ReagisterPage'
import { AboutPage } from '../pages/AboutPage/AboutPage'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/dashboard"
          element={(
            <ProtectedRoute>
              <Layout>
                <DashboardPage />
              </Layout>
            </ProtectedRoute>
          )}
        />
        <Route
          path="/history"
          element={(
            <ProtectedRoute>
              <Layout>
                <HistoryPage />
              </Layout>
            </ProtectedRoute>
          )}
        />
        <Route
          path="/about"
          element={(
            <Layout>
              <AboutPage />
            </Layout>
          )}
        />
        <Route
          path="/profile"
          element={(
            <ProtectedRoute>
              <Layout>
                <ProfilePage />
              </Layout>
            </ProtectedRoute>
          )}
        />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
