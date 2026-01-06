import { useEffect } from 'react'
import { wsService } from '@/services/websocket'
import { useStatsStore } from '@/stores/statsStore'
import { DashboardStats } from '@/types/stats'

export const useStats = () => {
  const { stats, setStats } = useStatsStore()

  useEffect(() => {
    const handleStatsUpdate = (data: DashboardStats) => {
      setStats(data)
    }

    wsService.on('stats_update', handleStatsUpdate)

    return () => {
      wsService.off('stats_update', handleStatsUpdate)
    }
  }, [setStats])

  return { stats }
}
