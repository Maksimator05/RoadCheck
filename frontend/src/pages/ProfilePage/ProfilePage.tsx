import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { apiRequest, getErrorMessage } from '../../lib/api'
import {
  formatDate,
  formatPercent,
  getAnalysisTone,
  getDefectLabel,
  getDefectSummary,
  getDisplayName,
  getInitials,
  getRecentDefectTypes,
} from '../../lib/road'
import type { AnalysisItem, HistoryResponse, ProfileStats } from '../../types/api'
import './ProfilePage.css'

export function ProfilePage() {
  const navigate = useNavigate()
  const { logout, refreshUser, tokens, user } = useAuth()
  const [stats, setStats] = useState<ProfileStats | null>(null)
  const [recentItems, setRecentItems] = useState<AnalysisItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [passwordData, setPasswordData] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  })

  useEffect(() => {
    async function loadProfileData() {
      if (!tokens?.accessToken) {
        return
      }

      setLoading(true)
      setError('')

      try {
        await refreshUser()

        const [statsData, historyData] = await Promise.all([
          apiRequest<ProfileStats>('/profile/stats', { token: tokens.accessToken }),
          apiRequest<HistoryResponse>('/history?limit=4&offset=0', { token: tokens.accessToken }),
        ])

        setStats(statsData)
        setRecentItems(historyData.items)
      } catch (loadError) {
        setError(getErrorMessage(loadError, 'Не удалось загрузить данные профиля.'))
      } finally {
        setLoading(false)
      }
    }

    void loadProfileData()
  }, [tokens?.accessToken])

  function handlePasswordChange(event: ChangeEvent<HTMLInputElement>) {
    setPasswordData((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }))
  }

  async function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setMessage('')

    if (passwordData.newPassword.length < 8) {
      setError('Новый пароль должен содержать минимум 8 символов.')
      return
    }

    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setError('Новые пароли не совпадают.')
      return
    }

    if (!tokens?.accessToken) {
      return
    }

    setIsSaving(true)

    try {
      await apiRequest('/profile/password', {
        method: 'PATCH',
        token: tokens.accessToken,
        body: JSON.stringify({
          old_password: passwordData.oldPassword,
          new_password: passwordData.newPassword,
        }),
      })

      setMessage('Пароль успешно обновлён.')
      setPasswordData({
        oldPassword: '',
        newPassword: '',
        confirmPassword: '',
      })
    } catch (saveError) {
      setError(getErrorMessage(saveError, 'Не удалось изменить пароль.'))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleLogout() {
    setIsLoggingOut(true)
    await logout()
    navigate('/login')
  }

  const recentDefectTypes = getRecentDefectTypes(recentItems)
  const displayName = user ? getDisplayName(user.email) : 'Пользователь'
  const initials = user ? getInitials(user.email) : 'RC'

  return (
    <div className="profile-page">
      <div className="container">
        {error ? <div className="status-message status-message--error">{error}</div> : null}
        {message ? <div className="status-message status-message--success">{message}</div> : null}

        <div className="profile-grid">
          <div className="profile-sidebar">
            <div className="profile-card">
              <div className="profile-avatar">
                <span className="avatar-initials">{initials}</span>
              </div>
              <h2 className="profile-name">{displayName}</h2>
              <p className="profile-email">{user?.email ?? 'Почта загружается...'}</p>

              <div className="profile-join">
                <span>
                  Роль: {user?.role ?? 'user'}{user?.created_at ? ` • с ${formatDate(user.created_at)}` : ''}
                </span>
              </div>

              <div className="profile-stats">
                <div className="profile-stat">
                  <div className="stat-number stat-green">{stats?.total_checks ?? 0}</div>
                  <div className="stat-label">проверок</div>
                </div>
                <div className="profile-stat">
                  <div className="stat-number stat-red">{stats?.total_defects ?? 0}</div>
                  <div className="stat-label">дефектов</div>
                </div>
                <div className="profile-stat">
                  <div className="stat-number stat-yellow">{formatPercent(stats?.avg_confidence ?? 0)}</div>
                  <div className="stat-label">средняя точность</div>
                </div>
                <div className="profile-stat">
                  <div className="stat-number stat-blue">{stats?.no_defect_photos ?? 0}</div>
                  <div className="stat-label">чистых фото</div>
                </div>
              </div>

              <button className="btn btn-logout" onClick={handleLogout} disabled={isLoggingOut}>
                {isLoggingOut ? 'Выходим...' : 'Выйти из аккаунта'}
              </button>
            </div>
          </div>

          <div className="profile-main">
            <div className="profile-section">
              <h3 className="section-title">Распределение дефектов</h3>

              {loading ? (
                <div className="empty-state">Загружаем статистику...</div>
              ) : recentDefectTypes.length ? (
                <div className="defects-distribution">
                  {recentDefectTypes.map(([type, count]) => {
                    const maxValue = recentDefectTypes[0]?.[1] ?? 1

                    return (
                      <div key={type} className="distribution-row">
                        <span className="distribution-label">{getDefectLabel(type)}</span>
                        <div className="distribution-bar">
                          <div
                            className="distribution-progress info"
                            style={{ width: `${(count / maxValue) * 100}%` }}
                          />
                        </div>
                        <span className="distribution-value">{count}</span>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="empty-state">После первых анализов здесь появится разбивка по типам дефектов.</div>
              )}
            </div>

            <div className="profile-section">
              <h3 className="section-title">Последние проверки</h3>

              {recentItems.length ? (
                <div className="recent-checks">
                  {recentItems.map((item) => (
                    <div key={item.id} className="check-item">
                      <span className="check-name">{item.filename}</span>
                      <span className="check-date">{formatDate(item.created_at)}</span>
                      <span className={`check-defects ${getAnalysisTone(item.result.count)}`}>
                        {getDefectSummary(item.result.count)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">Пока нет ни одного анализа, который можно показать в профиле.</div>
              )}
            </div>

            <div className="profile-section">
              <h3 className="section-title">Смена пароля</h3>

              <form className="password-form" onSubmit={handlePasswordSubmit}>
                <div className="form-group">
                  <label className="form-label" htmlFor="oldPassword">Текущий пароль</label>
                  <input
                    id="oldPassword"
                    type="password"
                    name="oldPassword"
                    className="input"
                    value={passwordData.oldPassword}
                    onChange={handlePasswordChange}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="newPassword">Новый пароль</label>
                  <input
                    id="newPassword"
                    type="password"
                    name="newPassword"
                    className="input"
                    value={passwordData.newPassword}
                    onChange={handlePasswordChange}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="confirmPassword">Повторите новый пароль</label>
                  <input
                    id="confirmPassword"
                    type="password"
                    name="confirmPassword"
                    className="input"
                    value={passwordData.confirmPassword}
                    onChange={handlePasswordChange}
                    required
                  />
                </div>

                <button className="btn btn-primary" type="submit" disabled={isSaving}>
                  {isSaving ? 'Сохраняем...' : 'Сохранить новый пароль'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
