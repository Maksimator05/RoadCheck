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
  const [message, setMessage] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<AnalysisItem | null>(null)

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
    setMessage('')

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
    setMessage('')

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

  function handleDelete(item: AnalysisItem) {
    setError('')
    setMessage('')
    setPendingDelete(item)
  }

  async function confirmDelete() {
    if (!tokens?.accessToken || !pendingDelete) {
      return
    }

    const currentItem = pendingDelete
    setBusyId(currentItem.id)

    try {
      await apiRequest<void>(`/history/${currentItem.id}`, {
        method: 'DELETE',
        token: tokens.accessToken,
        responseType: 'void',
      })

      setPendingDelete(null)
      setMessage(`Анализ "${currentItem.filename}" удалён из истории.`)

      if (history.items.length === 1 && page > 0) {
        setPage((currentPage) => Math.max(0, currentPage - 1))
      } else {
        await loadHistory()
      }
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
        {message ? <div className="status-message status-message--success">{message}</div> : null}

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
                    <span className={`defect-badge defect-${tone}`}>{getDefectSummary(item.result.count)}</span>
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

      {pendingDelete ? (
        <div className="modal-backdrop" role="presentation" onClick={() => setPendingDelete(null)}>
          <div
            className="confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-analysis-title"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="delete-analysis-title" className="confirm-dialog__title">
              Удалить анализ?
            </h2>
            <p className="confirm-dialog__text">
              Запись <strong>{pendingDelete.filename}</strong> исчезнет из истории. Файл отчёта потом
              нужно будет сформировать заново.
            </p>
            <div className="confirm-dialog__actions">
              <button className="btn" onClick={() => setPendingDelete(null)} disabled={busyId === pendingDelete.id}>
                Отмена
              </button>
              <button
                className="btn btn-danger"
                onClick={() => void confirmDelete()}
                disabled={busyId === pendingDelete.id}
              >
                {busyId === pendingDelete.id ? 'Удаляем...' : 'Удалить'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
