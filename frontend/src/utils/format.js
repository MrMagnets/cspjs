export const TYPE_LABELS = {
  single: '单项选择',
  reading: '阅读程序',
  completion: '完善程序',
}

export const TYPE_SHORT = {
  single: '单选',
  reading: '阅读程序',
  completion: '完善程序',
}

export const SOURCE_LABELS = {
  original: '原创',
  real: '真题',
  adapted: '改编',
}

export const STATUS_META = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
}

export const ERROR_TYPE_OPTIONS = [
  { value: 1, label: '概念不清' },
  { value: 2, label: '方法不会' },
  { value: 3, label: '粗心' },
  { value: 4, label: '审题错误' },
]

export function errorTypeLabel(value) {
  return ERROR_TYPE_OPTIONS.find((o) => o.value === value)?.label || '未标注'
}

export function formatDate(value, withTime = false) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  const base = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  return withTime ? `${base} ${pad(date.getHours())}:${pad(date.getMinutes())}` : base
}

export function percent(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${(Number(value) * 100).toFixed(digits)}%`
}

export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '—'
  const total = Math.max(0, Math.floor(seconds))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const pad = (n) => String(n).padStart(2, '0')
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`
}

export function answerText(value) {
  return value ? String(value).toUpperCase() : '未作答'
}

/** 模拟考试按真实结构还原每题分值：1-15 题各 2 分，16-18 题 13/13/14 分，19-20 题各 15 分 */
export function mockProblemPoints(index) {
  if (index < 15) return 2
  if (index < 18) return [13, 13, 14][index - 15]
  return 15
}
