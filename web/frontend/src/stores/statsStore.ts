import { create } from 'zustand'
import { DashboardStats } from '@/types/stats'

interface StatsState {
  stats: DashboardStats | null
  setStats: (stats: DashboardStats) => void
}

export const useStatsStore = create<StatsState>((set) => ({
  stats: null,
  setStats: (stats) => set({ stats }),
}))
