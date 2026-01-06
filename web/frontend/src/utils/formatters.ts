import { format, formatDistance } from 'date-fns'

export const formatNumber = (num: number): string => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export const formatDate = (dateString: string): string => {
  try {
    const date = new Date(dateString)
    if (isNaN(date.getTime())) {
      return 'Invalid date'
    }
    return format(date, 'MMM d, yyyy HH:mm')
  } catch (error) {
    return 'Invalid date'
  }
}

export const formatRelativeTime = (dateString: string): string => {
  try {
    const date = new Date(dateString)
    if (isNaN(date.getTime())) {
      return 'Invalid date'
    }
    return formatDistance(date, new Date(), { addSuffix: true })
  } catch (error) {
    return 'Invalid date'
  }
}

export const formatPercentage = (value: number, total: number): string => {
  if (total === 0) return '0%'
  return ((value / total) * 100).toFixed(1) + '%'
}
