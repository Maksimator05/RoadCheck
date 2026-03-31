import type { ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import './Layout.css'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { isAuthenticated, isLoading, logout, user } = useAuth()

  const isActive = (path: string) => location.pathname === path

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="layout">
      <header className="header">
        <div className="header__container">
          <Link to="/" className="header__logo">
            <span className="logo-icon">▲</span>
            ROADCHECK
          </Link>

          <nav className="header__nav">
            <Link
              to="/dashboard"
              className={`header__link ${isActive('/dashboard') ? 'active' : ''}`}
            >
              Анализ
            </Link>
            <Link
              to="/history"
              className={`header__link ${isActive('/history') ? 'active' : ''}`}
            >
              История
            </Link>
            <Link
              to="/about"
              className={`header__link ${isActive('/about') ? 'active' : ''}`}
            >
              О проекте
            </Link>
          </nav>

          <div className="header__actions">
            {isLoading ? (
              <span className="header__status">Проверяем сессию...</span>
            ) : isAuthenticated ? (
              <>
                <Link
                  to="/profile"
                  className={`header__link ${isActive('/profile') ? 'active' : ''}`}
                >
                  {user?.email ?? 'Профиль'}
                </Link>
                <button type="button" className="btn btn-sm header__button" onClick={handleLogout}>
                  Выйти
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className={`header__link ${isActive('/login') ? 'active' : ''}`}
                >
                  Войти
                </Link>
                <Link to="/register" className="btn btn-sm">
                  Регистрация
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="main">{children}</main>
    </div>
  )
}
