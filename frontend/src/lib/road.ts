import type { AnalysisItem, Defect } from '../types/api'

const defectLabels: Record<string, string> = {
  pothole: 'Яма',
  crack: 'Трещина',
  patch: 'Заплатка',
  patched: 'Заплатка',
  rut: 'Колея',
  bump: 'Неровность',
  d00: 'Продольная трещина',
  d10: 'Поперечная трещина',
  d20: 'Сетчатая трещина',
  d40: 'Яма',
  longitudinal_crack: 'Продольная трещина',
  transverse_crack: 'Поперечная трещина',
  alligator_crack: 'Сетчатая трещина',
}

const severityPenalty: Record<string, number> = {
  low: 8,
  medium: 15,
  high: 24,
}

export function getDefectLabel(type: string): string {
  const normalized = type.trim().toLowerCase()
  return defectLabels[normalized] || normalized.replace(/_/g, ' ')
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

export function getRoadScore(defects: Defect[]): number {
  if (!defects.length) {
    return 100
  }

  const penalty = defects.reduce((sum, defect) => {
    const base = severityPenalty[defect.severity] ?? 12
    const confidence = Number.isFinite(defect.confidence) ? defect.confidence : 0.5
    return sum + base * Math.max(0.2, Math.min(confidence, 1))
  }, 0)

  return Math.max(0, Math.min(100, Math.round(100 - penalty)))
}

export function getRoadStatus(score: number): {
  label: string
  description: string
  tone: 'ok' | 'warning' | 'critical'
} {
  if (score >= 80) {
    return {
      label: 'Дорога в хорошем состоянии',
      description: 'Серьёзных повреждений почти нет, покрытие выглядит стабильным.',
      tone: 'ok',
    }
  }

  if (score >= 55) {
    return {
      label: 'Нужен контроль участка',
      description: 'Обнаружены дефекты средней тяжести. Лучше запланировать осмотр.',
      tone: 'warning',
    }
  }

  return {
    label: 'Состояние плохое',
    description: 'Есть выраженные дефекты покрытия. Участок требует внимания.',
    tone: 'critical',
  }
}

export function getAnalysisTone(defectCount: number): 'ok' | 'warning' | 'critical' {
  if (defectCount === 0) {
    return 'ok'
  }

  if (defectCount <= 2) {
    return 'warning'
  }

  return 'critical'
}

export function getDisplayName(email: string): string {
  const localPart = email.split('@')[0] || 'user'
  return localPart
    .split(/[._-]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function getInitials(email: string): string {
  const name = getDisplayName(email)
  const parts = name.split(' ').filter(Boolean)

  if (!parts.length) {
    return 'RC'
  }

  return parts
    .slice(0, 2)
    .map((part) => part.charAt(0))
    .join('')
    .toUpperCase()
}

export function getRecentDefectTypes(items: AnalysisItem[]): Array<[string, number]> {
  const counts: Record<string, number> = {}

  for (const item of items) {
    for (const defect of item.result.defects) {
      counts[defect.type] = (counts[defect.type] || 0) + 1
    }
  }

  return Object.entries(counts).sort((left, right) => right[1] - left[1])
}

export function getDefectSummary(count: number): string {
  if (count === 1) {
    return '1 дефект'
  }

  if (count >= 2 && count <= 4) {
    return `${count} дефекта`
  }

  return `${count} дефектов`
}
