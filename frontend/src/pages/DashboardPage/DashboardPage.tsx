import { useEffect, useRef, useState, type ChangeEvent, type CSSProperties } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { apiRequest, getErrorMessage } from '../../lib/api'
import {
  formatPercent,
  getDefectLabel,
  getDefectSummary,
  getRoadScore,
  getRoadStatus,
} from '../../lib/road'
import type { AnalyzeResponse, Defect, ProfileStats } from '../../types/api'
// @ts-ignore
import 'src/pages/DashboardPage/DashboardPage.css'

function getPotholeSummary(count: number): string {
  if (count === 1) {
    return 'Найдена 1 яма'
  }

  if (count >= 2 && count <= 4) {
    return `Найдено ${count} ямы`
  }

  return `Найдено ${count} ям`
}

export function DashboardPage() {
  const { tokens } = useAuth()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null)
  const [analysisMessage, setAnalysisMessage] = useState('')
  const [stats, setStats] = useState<ProfileStats | null>(null)
  const [analysisError, setAnalysisError] = useState('')
  const [statsError, setStatsError] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isStatsLoading, setIsStatsLoading] = useState(true)

  // Track the rendered image size so markers align correctly
  const imageRef = useRef<HTMLImageElement>(null)
  const [renderedSize, setRenderedSize] = useState<{ w: number; h: number } | null>(null)

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

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl('')
      return
    }

    const nextPreviewUrl = URL.createObjectURL(selectedFile)
    setPreviewUrl(nextPreviewUrl)

    return () => {
      URL.revokeObjectURL(nextPreviewUrl)
    }
  }, [selectedFile])

  // Recalculate rendered size when analysis result arrives or window resizes
  useEffect(() => {
    if (!analysis) {
      setRenderedSize(null)
      return
    }

    function updateSize() {
      if (imageRef.current) {
        setRenderedSize({
          w: imageRef.current.clientWidth,
          h: imageRef.current.clientHeight,
        })
      }
    }

    // Wait a tick for the image to paint
    const timer = setTimeout(updateSize, 50)
    window.addEventListener('resize', updateSize)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', updateSize)
    }
  }, [analysis, previewUrl])

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setAnalysis(null)
    setAnalysisError('')
    setAnalysisMessage('')
    setRenderedSize(null)
  }

  async function handleAnalyze() {
    if (!selectedFile || !tokens?.accessToken) {
      return
    }

    setAnalysis(null)
    setAnalysisMessage('')
    setAnalysisError('')
    setRenderedSize(null)
    setIsAnalyzing(true)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const result = await apiRequest<AnalyzeResponse>('/analyze', {
        method: 'POST',
        token: tokens.accessToken,
        body: formData,
      })

      const potholeCount = result.defects.filter((defect) => defect.type === 'pothole').length

      if (potholeCount > 0) {
        setAnalysisMessage(`${getPotholeSummary(potholeCount)}. Ямы отмечены и пронумерованы на снимке.`)
      } else if (result.count > 0) {
        setAnalysisMessage('Дефекты обнаружены и отмечены на снимке.')
      } else {
        setAnalysisMessage('На фото заметных дефектов не найдено.')
      }

      setAnalysis(result)
      await loadStats()
    } catch (error) {
      setAnalysisError(getErrorMessage(error, 'Не удалось выполнить анализ изображения.'))
    } finally {
      setIsAnalyzing(false)
    }
  }

  /**
   * Convert a bbox from original-image pixel space to percentage of the
   * *rendered* <img> element so the overlay rectangles land exactly on
   * the right spots regardless of how the browser scales the photo.
   */
  function getMarkerStyle(defect: Defect): CSSProperties {
    const [x1, y1, x2, y2] = defect.bbox
    const origW = analysis?.image_width ?? 0
    const origH = analysis?.image_height ?? 0

    if (!origW || !origH) return {}

    // Use actual rendered dimensions when available, fall back to percentages
    if (renderedSize && renderedSize.w > 0 && renderedSize.h > 0) {
      // Scale factor: how many rendered px per original px
      const scaleX = renderedSize.w / origW
      const scaleY = renderedSize.h / origH

      return {
        left: `${x1 * scaleX}px`,
        top: `${y1 * scaleY}px`,
        width: `${(x2 - x1) * scaleX}px`,
        height: `${(y2 - y1) * scaleY}px`,
      }
    }

    // Fallback: simple percentages (good enough when image fills container)
    return {
      left: `${(x1 / origW) * 100}%`,
      top: `${(y1 / origH) * 100}%`,
      width: `${((x2 - x1) / origW) * 100}%`,
      height: `${((y2 - y1) / origH) * 100}%`,
    }
  }

  const roadScore = analysis ? getRoadScore(analysis.defects) : null
  const roadStatus = roadScore !== null ? getRoadStatus(roadScore) : null
  const defectDistribution = Object.entries(stats?.by_type ?? {}).sort((left, right) => right[1] - left[1])
  const maxDistributionValue = defectDistribution[0]?.[1] ?? 1
  const canRenderOverlay = Boolean(previewUrl && analysis?.image_width && analysis?.image_height)

  return (
    <div className="dashboard-page">
      <div className="container">
        <div className="dashboard-grid">
          <div className="dashboard__upload">
            <div className="upload-card">
              <h2 className="section-title">Загрузите фото дорожного покрытия</h2>
              <p className="section-subtitle">
                Система проверит покрытие, оценит его состояние в процентах и покажет найденные
                дефекты.
              </p>

              {analysisError ? <div className="status-message status-message--error">{analysisError}</div> : null}
              {analysisMessage ? <div className="status-message status-message--success">{analysisMessage}</div> : null}

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

              {previewUrl && !analysis ? (
                <div className="upload-preview">
                  <div className="analysis-preview__stage analysis-preview__stage--compact">
                    <img className="analysis-preview__image" src={previewUrl} alt="Предпросмотр дороги" />
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

                {previewUrl ? (
                  <div className="analysis-preview">
                    {/*
                      IMPORTANT: position:relative on the stage + the img fills it 100% wide.
                      Markers are positioned absolutely inside the stage using px values
                      derived from the img's clientWidth/clientHeight, so they always land
                      on the correct spots even when the browser scales the photo.
                    */}
                    <div className="analysis-preview__stage">
                      <img
                        ref={imageRef}
                        className="analysis-preview__image"
                        src={previewUrl}
                        alt="Результат анализа дороги"
                        onLoad={() => {
                          if (imageRef.current) {
                            setRenderedSize({
                              w: imageRef.current.clientWidth,
                              h: imageRef.current.clientHeight,
                            })
                          }
                        }}
                      />
                      {canRenderOverlay
                        ? analysis.defects.map((defect, index) => (
                            <div
                              key={`${defect.type}-${index}`}
                              className={`analysis-marker ${
                                defect.type === 'pothole'
                                  ? 'analysis-marker--pothole'
                                  : defect.type === 'crack'
                                    ? 'analysis-marker--crack'
                                    : 'analysis-marker--secondary'
                              }`}
                              style={getMarkerStyle(defect)}
                              title={`${getDefectLabel(defect.type)} №${index + 1} (${Math.round(defect.confidence * 100)}%)`}
                            >
                              <span className="analysis-marker__badge">№{index + 1}</span>
                              <span className="analysis-marker__label">{getDefectLabel(defect.type)}</span>
                            </div>
                          ))
                        : null}
                    </div>
                    <p className="analysis-preview__caption">
                      {analysis.count
                        ? 'Контуры поверх фото показывают найденные дефекты, а номера помогают быстро сопоставить их со списком ниже.'
                        : 'Фото без выделенных дефектов: система не нашла заметных ям и трещин на этом снимке.'}
                    </p>
                  </div>
                ) : null}

                {analysis.defects.length ? (
                  <div className="defect-list">
                    {analysis.defects.map((defect, index) => (
                      <div key={`${defect.type}-${index}`} className="defect-card">
                        <div className="defect-card__meta">
                          <span className="defect-card__title">
                            №{index + 1}. {getDefectLabel(defect.type)}
                          </span>
                          <span className={`defect-card__severity defect-card__severity--${defect.severity}`}>
                            {defect.severity === 'high'
                              ? 'Критично'
                              : defect.severity === 'medium'
                                ? 'Средне'
                                : 'Низкий риск'}
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
                  После анализа вы увидите процент качества дороги, типы дефектов, уверенность
                  модели и разметку найденных зон прямо поверх загруженного изображения.
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
                  Пока нет накопленной истории. Сделайте первый анализ, и статистика появится
                  здесь.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}