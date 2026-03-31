import { useEffect, useState, type ChangeEvent } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { apiRequest, getErrorMessage } from '../../lib/api'
import {
  formatPercent,
  getDefectLabel,
  getDefectSummary,
  getRoadScore,
  getRoadStatus,
} from '../../lib/road'
import type { AnalyzeResponse, ProfileStats } from '../../types/api'
import './DashboardPage.css'

export function DashboardPage() {
  const { tokens } = useAuth()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null)
  const [stats, setStats] = useState<ProfileStats | null>(null)
  const [analysisError, setAnalysisError] = useState('')
  const [statsError, setStatsError] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isStatsLoading, setIsStatsLoading] = useState(true)

  async function loadStats() {
    if (!tokens?.accessToken) {
      return
    }

    setIsStatsLoading(true)
    setStatsError('')

    try {
      const nextStats = await apiRequest<ProfileStats>('/profile/stats', {
        token: tokens.accessToken,
      })
      setStats(nextStats)
    } catch (error) {
      setStatsError(getErrorMessage(error, 'Не удалось загрузить статистику.'))
    } finally {
      setIsStatsLoading(false)
    }
  }

  useEffect(() => {
    void loadStats()
  }, [tokens?.accessToken])

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setAnalysisError('')
  }

  async function handleAnalyze() {
    if (!selectedFile || !tokens?.accessToken) {
      return
    }

    setAnalysisError('')
    setIsAnalyzing(true)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const result = await apiRequest<AnalyzeResponse>('/analyze', {
        method: 'POST',
        token: tokens.accessToken,
        body: formData,
      })

      setAnalysis(result)
      await loadStats()
    } catch (error) {
      setAnalysisError(getErrorMessage(error, 'Не удалось выполнить анализ изображения.'))
    } finally {
      setIsAnalyzing(false)
    }
  }

  const roadScore = analysis ? getRoadScore(analysis.defects) : null
  const roadStatus = roadScore !== null ? getRoadStatus(roadScore) : null
  const defectDistribution = Object.entries(stats?.by_type ?? {}).sort((left, right) => right[1] - left[1])
  const maxDistributionValue = defectDistribution[0]?.[1] ?? 1

  return (
    <div className="dashboard-page">
      <div className="container">
        <div className="dashboard-grid">
          <div className="dashboard__upload">
            <div className="upload-card">
              <h2 className="section-title">Загрузите фото дорожного покрытия</h2>
              <p className="section-subtitle">
                Система проверит покрытие, оценит его состояние в процентах и покажет найденные дефекты.
              </p>

              {analysisError ? <div className="status-message status-message--error">{analysisError}</div> : null}

              <div className="upload-area">
                <input
                  type="file"
                  id="file-input"
                  accept="image/jpeg,image/png"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                />
                <label htmlFor="file-input" className="upload-label">
                  <div className="upload-icon">📷</div>
                  <p>Нажмите, чтобы выбрать фото дороги</p>
                  <p className="upload-hint">Поддерживаются JPG и PNG до 10 МБ</p>
                </label>
              </div>

              {selectedFile ? (
                <div className="file-list">
                  <div className="file-item">
                    <span className="file-name">{selectedFile.name}</span>
                    <span className="file-size">{(selectedFile.size / 1024 / 1024).toFixed(2)} МБ</span>
                  </div>
                </div>
              ) : null}

              <button
                className="btn btn-primary analyze-btn"
                onClick={handleAnalyze}
                disabled={!selectedFile || isAnalyzing}
              >
                {isAnalyzing ? 'Анализируем изображение...' : 'Запустить анализ'}
              </button>
            </div>

            {analysis ? (
              <div className={`results-card quality-card quality-card--${roadStatus?.tone}`}>
                <div className="quality-card__header">
                  <div>
                    <h3 className="results-title">Результат последнего анализа</h3>
                    <p className="quality-card__subtitle">{roadStatus?.description}</p>
                  </div>
                  <div className="quality-score">
                    <span className="quality-score__value">{roadScore}%</span>
                    <span className="quality-score__label">качество покрытия</span>
                  </div>
                </div>

                <div className="quality-pill-row">
                  <span className="quality-pill">{roadStatus?.label}</span>
                  <span className="quality-pill">{getDefectSummary(analysis.count)}</span>
                  <span className="quality-pill">{analysis.processing_ms} мс</span>
                </div>

                {analysis.defects.length ? (
                  <div className="defect-list">
                    {analysis.defects.map((defect, index) => (
                      <div key={`${defect.type}-${index}`} className="defect-card">
                        <div className="defect-card__meta">
                          <span className="defect-card__title">{getDefectLabel(defect.type)}</span>
                          <span className={`defect-card__severity defect-card__severity--${defect.severity}`}>
                            {defect.severity === 'high' ? 'Критично' : defect.severity === 'medium' ? 'Средне' : 'Низкий риск'}
                          </span>
                        </div>
                        <div className="defect-card__details">
                          <span>Уверенность модели: {formatPercent(defect.confidence)}</span>
                          <span>Координаты: {defect.bbox.join(', ')}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    На изображении не найдено ям, трещин и других заметных дефектов.
                  </div>
                )}
              </div>
            ) : (
              <div className="results-card empty-state-card">
                <h3 className="results-title">Результат появится здесь</h3>
                <p>
                  После анализа вы увидите процент качества дороги, типы дефектов и уверенность модели.
                </p>
              </div>
            )}
          </div>

          <div className="dashboard__stats">
            <div className="stats-card">
              <h3 className="stats-title">Сводка по аккаунту</h3>

              {statsError ? <div className="status-message status-message--error">{statsError}</div> : null}

              {isStatsLoading ? (
                <div className="empty-state">Загружаем статистику...</div>
              ) : (
                <div className="stats-grid">
                  <div className="stat-item">
                    <div className="stat-value">{stats?.total_checks ?? 0}</div>
                    <div className="stat-label">Проверок выполнено</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value stat-warning">{stats?.total_defects ?? 0}</div>
                    <div className="stat-label">Дефектов найдено</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value stat-critical">{formatPercent(stats?.avg_confidence ?? 0)}</div>
                    <div className="stat-label">Средняя уверенность</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value stat-ok">{stats?.no_defect_photos ?? 0}</div>
                    <div className="stat-label">Фото без дефектов</div>
                  </div>
                </div>
              )}
            </div>

            <div className="defects-card">
              <h3 className="defects-title">Распределение дефектов</h3>

              {defectDistribution.length ? (
                <div className="defects-chart">
                  {defectDistribution.map(([type, count]) => (
                    <div key={type} className="defect-row">
                      <span className="defect-label">{getDefectLabel(type)}</span>
                      <div className="defect-bar">
                        <div
                          className="defect-progress info"
                          style={{ width: `${(count / maxDistributionValue) * 100}%` }}
                        />
                      </div>
                      <span className="defect-value">{count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  Пока нет накопленной истории. Сделайте первый анализ, и статистика появится здесь.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
