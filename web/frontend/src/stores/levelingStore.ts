import { create } from 'zustand'
import {
  LevelingConfig,
  LeaderboardEntry,
  XPFeedEntry,
  Rank,
  MessageTemplate,
  LevelRange,
  Guild,
} from '@/types/leveling'

interface LevelingState {
  selectedGuild: string | null
  config: LevelingConfig | null
  leaderboard: LeaderboardEntry[]
  xpFeed: XPFeedEntry[]
  ranks: Rank[]
  templates: MessageTemplate[]
  ranges: LevelRange[]
  feedPaused: boolean

  setSelectedGuild: (guildId: string | null) => void
  setConfig: (config: LevelingConfig | null) => void
  setLeaderboard: (leaderboard: LeaderboardEntry[]) => void
  setXpFeed: (xpFeed: XPFeedEntry[]) => void
  setRanks: (ranks: Rank[]) => void
  setTemplates: (templates: MessageTemplate[]) => void
  setRanges: (ranges: LevelRange[]) => void
  setFeedPaused: (paused: boolean) => void
}

export const useLevelingStore = create<LevelingState>((set) => ({
  selectedGuild: null,
  config: null,
  leaderboard: [],
  xpFeed: [],
  ranks: [],
  templates: [],
  ranges: [],
  feedPaused: false,

  setSelectedGuild: (guildId) => set({ selectedGuild: guildId }),
  setConfig: (config) => set({ config }),
  setLeaderboard: (leaderboard) => set({ leaderboard }),
  setXpFeed: (xpFeed) => set({ xpFeed }),
  setRanks: (ranks) => set({ ranks }),
  setTemplates: (templates) => set({ templates }),
  setRanges: (ranges) => set({ ranges }),
  setFeedPaused: (paused) => set({ feedPaused: paused }),
}))
