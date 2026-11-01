/**
 * 全局统一数据与日期格式化工具 (零外部依赖，极简高效)
 */

/**
 * 格式化日期/时间字符串或时间戳为标准格式
 * @param val 输入时间 (ISO 字符串、Date 对象或时间戳)
 * @param pattern 格式化模式，默认为 'YYYY-MM-DD'，可选 'YYYY-MM-DD HH:mm:ss' 或 'YYYY-MM-DD HH:mm'
 * @returns 格式化后的字符串，空值返回 '-'
 */
export function formatDate(val: any, pattern: string = 'YYYY-MM-DD'): string {
  if (val === null || val === undefined || val === '') {
    return '-'
  }

  const d = val instanceof Date ? val : new Date(val)
  if (isNaN(d.getTime())) {
    return String(val)
  }

  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')

  if (pattern === 'YYYY-MM-DD') {
    return `${year}-${month}-${day}`
  }

  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')

  if (pattern === 'YYYY-MM-DD HH:mm') {
    return `${year}-${month}-${day} ${hours}:${minutes}`
  }

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

/**
 * 格式化为标准日期+时间 (精确到分)
 */
export function formatDateTime(val: any): string {
  return formatDate(val, 'YYYY-MM-DD HH:mm')
}

/**
 * 统一空值占位
 */
export function formatEmpty(val: any, placeholder: string = '-'): string {
  if (val === null || val === undefined || val === '') {
    return placeholder
  }
  return String(val)
}
