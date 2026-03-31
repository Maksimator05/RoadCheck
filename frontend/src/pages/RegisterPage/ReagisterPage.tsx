import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { getErrorMessage } from '../../lib/api'
import './RegisterPage.css'

export function RegisterPage() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading, register } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isLoading && isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    if (password.length < 8) {
      setError('Пароль должен содержать минимум 8 символов.')
      return
    }

    if (password !== confirmPassword) {
      setError('Пароли не совпадают.')
      return
    }

    setIsSubmitting(true)

    try {
      await register({ email, password })
      navigate('/dashboard', { replace: true })
    } catch (submitError) {
      setError(getErrorMessage(submitError, 'Не удалось создать аккаунт.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="register-page login-page">
      <div className="auth-card">
        <h1 className="auth-card__title">Регистрация</h1>
        <p className="auth-card__subtitle">
          Создайте аккаунт, чтобы сохранять историю анализов и отчёты по дорогам.
        </p>

        {error ? <div className="status-message status-message--error">{error}</div> : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="register-email">Почта</label>
            <input
              id="register-email"
              type="email"
              className="input"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="roadcheck@example.com"
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label" htmlFor="register-password">Пароль</label>
              <input
                id="register-password"
                type="password"
                className="input"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Минимум 8 символов"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="register-confirm-password">Повторите пароль</label>
              <input
                id="register-confirm-password"
                type="password"
                className="input"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Повторите пароль"
                required
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary auth-form__submit" disabled={isSubmitting}>
            {isSubmitting ? 'Создаём аккаунт...' : 'Создать аккаунт'}
          </button>
        </form>

        <div className="auth-card__footer">
          <span>Уже зарегистрированы?</span>
          <Link to="/login" className="auth-link">Войти</Link>
        </div>
      </div>
    </div>
  )
}
