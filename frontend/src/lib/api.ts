const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

type ResponseType = 'json' | 'blob' | 'text' | 'void'

interface ApiRequestOptions extends RequestInit {
  token?: string
  responseType?: ResponseType
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function normalizeDetail(detail: unknown): string {
  if (Array.isArray(detail)) {
    return detail.join(', ')
  }

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (detail && typeof detail === 'object') {
    return JSON.stringify(detail)
  }

  return 'Server returned an unexpected error.'
}

export function getErrorMessage(
  error: unknown,
  fallback = 'Something went wrong. Please try again.'
): string {
  if (error instanceof ApiError) {
    return error.message
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return fallback
}

export async function apiRequest<T>(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const {
    token,
    responseType = 'json',
    headers,
    body,
    ...rest
  } = options

  const requestHeaders = new Headers(headers)

  if (token) {
    requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  if (body !== undefined && !(body instanceof FormData) && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...rest,
    body,
    headers: requestHeaders,
  })

  if (!response.ok) {
    let detail = response.statusText || 'Request failed'

    try {
      const errorData = await response.json()
      detail = normalizeDetail(errorData?.detail)
    } catch {
      // Some backend responses can be empty, so we keep the HTTP status text.
    }

    throw new ApiError(detail, response.status)
  }

  if (response.status === 204 || responseType === 'void') {
    return undefined as T
  }

  if (responseType === 'blob') {
    return (await response.blob()) as T
  }

  if (responseType === 'text') {
    return (await response.text()) as T
  }

  return response.json() as Promise<T>
}

export { API_BASE }
