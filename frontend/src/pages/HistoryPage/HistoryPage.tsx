import { useEffect, useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { apiRequest, getErrorMessage } from '../../lib/api'
import {
  formatDate,
  getAnalysisTone,
  getDefectSummary,
  getRoadScore,
  getRoadStatus,
} from '../../lib/road'
import type { AnalysisItem, HistoryResponse } from '../../types/api'
import './HistoryPage.css'

type FilterMode = 'all' | 'defects' | 'clean'

const PAGE_SIZE = 10

export function HistoryPage() {
  const { tokens } = useAuth()
  const [history, setHistory] = useState<HistoryResponse>({ items: [], total: 0 })
  const [filter, setFilter] = useState<FilterMode>('all')
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)

  async function loadHistory() {
    if (!tokens?.accessToken) {
      return
    }

    setLoading(true)
    setError('')

    try {
      const data = await apiRequest<HistoryResponse>(
        `/history?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`,
        { token: tokens.accessToken }
      )

      setHistory(data)
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Не удалось загрузить историю анализов.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadHistory()
  }, [tokens?.accessToken, page])

  const filteredItems = history.items.filter((item) => {
    if (filter === 'defects') {
      return item.result.count > 0
    }

    if (filter === 'clean') {
      return item.result.count === 0
    }

    return true
  })

  const totalPages = Math.max(1, Math.ceil(history.total / PAGE_SIZE))

  function downloadBlob(blob: Blob, fileName: string) {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = fileName
    link.click()
    window.URL.revokeObjectURL(url)
  }

  async function handleDownloadPdf(item: AnalysisItem) {
    if (!tokens?.accessToken) {
      return
    }

    setBusyId(item.id)

    try {
      const blob = await apiRequest<Blob>(`/history/${item.id}/pdf`, {
        token: tokens.accessToken,
        responseType: 'blob',
      })

      downloadBlob(blob, `${item.filename.replace(/\.[^.]+$/, '') || 'analysis'}-report.pdf`)
    } catch (downloadError) {
      setError(getErrorMessage(downloadError, 'Не удалось скачать PDF-отчёт.'))
    } finally {
      setBusyId(null)
    }
  }

  function handleDownloadJson(item: AnalysisItem) {
    const blob = new Blob(
      [
        JSON.stringify(
          {
            id: item.id,
            filename: item.filename,
            created_at: item.created_at,
            result: item.result,
          },
          null,
          2
        ),
      ],
      { type: 'application/json' }
    )

    downloadBlob(blob, `${item.filename.replace(/\.[^.]+$/, '') || 'analysis'}.json`)
  }

  async function handleDelete(item: AnalysisItem) {
    if (!tokens?.accessToken || !window.confirm(`Удалить анализ "${item.filename}"?`)) {
      return
    }

    setBusyId(item.id)

    try {
      await apiRequest<void>(`/history/${item.id}`, {
        method: 'DELETE',
        token: tokens.accessToken,
        responseType: 'void',
      })

      await loadHistory()
    } catch (deleteError) {
      setError(getErrorMessage(deleteError, 'Не удалось удалить анализ.'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="history-page">
      <div className="container">
        <h1 className="page-title">История проверок дорог</h1>

        <div className="history-filters">
          <button className={`filter-btn ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>
            Все
          </button>
          <button className={`filter-btn ${filter === 'defects' ? 'active' : ''}`} onClick={() => setFilter('defects')}>
            С дефектами
          </button>
          <button className={`filter-btn ${filter === 'clean' ? 'active' : ''}`} onClick={() => setFilter('clean')}>
            Без дефектов
          </button>
        </div>

        {error ? <div className="status-message status-message--error">{error}</div> : null}

        {loading ? (
          <div className="card page-state">Загружаем историю...</div>
        ) : filteredItems.length ? (
          <div className="history-list">
            {filteredItems.map((item) => {
              const score = getRoadScore(item.result.defects)
              const status = getRoadStatus(score)
              const tone = getAnalysisTone(item.result.count)

              return (
                <div key={item.id} className="history-item">
                  <div className="history-item__preview">
                    <div className="preview-placeholder">{score}%</div>
                  </div>

                  <div className="history-item__info">
                    <div className="item-name">{item.filename}</div>
                    <div className="item-date">{formatDate(item.created_at)}</div>
                    <div className="history-item__summary">{status.label}</div>
                  </div>

                  <div className="history-item__defects">
                    <span className={`defect-badge defect-${tone}`}>
                      {getDefectSummary(item.result.count)}
                    </span>
                  </div>

                  <div className="history-item__actions">
                    <button className="btn btn-sm" onClick={() => handleDownloadPdf(item)} disabled={busyId === item.id}>
                      PDF
                    </button>
                    <button className="btn btn-sm" onClick={() => handleDownloadJson(item)} disabled={busyId === item.id}>
                      JSON
                    </button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(item)} disabled={busyId === item.id}>
                      Удалить
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="card page-state">По текущему фильтру анализов пока нет.</div>
        )}

        <div className="pagination">
          <button
            className="pagination-btn"
            onClick={() => setPage((currentPage) => Math.max(0, currentPage - 1))}
            disabled={page === 0}
          >
            Назад
          </button>
          <span className="pagination-info">
            Страница {page + 1} из {totalPages}
          </span>
          <button
            className="pagination-btn"
            onClick={() => setPage((currentPage) => Math.min(totalPages - 1, currentPage + 1))}
            disabled={page >= totalPages - 1}
          >
            Вперёд
          </button>
        </div>
      </div>
    </div>
  )
}
