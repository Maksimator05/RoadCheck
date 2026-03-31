export interface AuthTokens {
  accessToken: string
  refreshToken: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface User {
  id: string
  email: string
  role: 'user' | 'pro' | 'admin'
  created_at: string
}

export interface Defect {
  type: string
  confidence: number
  bbox: number[]
  severity: 'low' | 'medium' | 'high'
}

export interface AnalysisResult {
  defects: Defect[]
  count: number
  processing_ms: number
}

export interface AnalyzeResponse extends AnalysisResult {
  analysis_id: string
}

export interface AnalysisItem {
  id: string
  filename: string
  result: AnalysisResult
  created_at: string
}

export interface HistoryResponse {
  items: AnalysisItem[]
  total: number
}

export interface ProfileStats {
  total_checks: number
  total_defects: number
  avg_confidence: number
  no_defect_photos: number
  by_type: Record<string, number>
}
