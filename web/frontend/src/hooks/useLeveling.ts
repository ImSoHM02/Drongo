import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@chakra-ui/react'
import api from '@/services/api'
import { useLevelingStore } from '@/stores/levelingStore'
import {
  Guild,
  LevelingConfig,
  LeaderboardEntry,
  XPFeedEntry,
  Rank,
  MessageTemplate,
  LevelRange,
} from '@/types/leveling'

// Guilds
export const useGuilds = () => {
  return useQuery({
    queryKey: ['leveling-guilds'],
    queryFn: async () => {
      const { data } = await api.get<Guild[]>('/leveling/guilds')
      // Ensure data is always an array
      return Array.isArray(data) ? data : []
    },
    retry: 1,
  })
}

// Config
export const useConfig = (guildId: string | null) => {
  const { setConfig } = useLevelingStore()

  const query = useQuery({
    queryKey: ['leveling-config', guildId],
    queryFn: async () => {
      if (!guildId) return null
      const { data } = await api.get<LevelingConfig>(`/leveling/config?guild_id=${guildId}`)
      setConfig(data)
      return data
    },
    enabled: !!guildId,
  })

  return query
}

export const useUpdateConfig = () => {
  const toast = useToast()
  const queryClient = useQueryClient()
  const { setConfig } = useLevelingStore()

  return useMutation({
    mutationFn: async (config: LevelingConfig) => {
      const { data } = await api.post('/leveling/config', config)
      return data
    },
    onSuccess: (data) => {
      setConfig(data)
      queryClient.invalidateQueries({ queryKey: ['leveling-config'] })
      toast({
        title: 'Configuration updated',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to update configuration',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

// Leaderboard
export const useLeaderboard = (guildId: string | null, limit: number = 10) => {
  const { setLeaderboard } = useLevelingStore()

  return useQuery({
    queryKey: ['leaderboard', guildId, limit],
    queryFn: async () => {
      if (!guildId) return []
      const { data } = await api.get<LeaderboardEntry[]>(
        `/leveling/leaderboard?guild_id=${guildId}&limit=${limit}`
      )
      // Ensure data is always an array
      const leaderboard = Array.isArray(data) ? data : []
      setLeaderboard(leaderboard)
      return leaderboard
    },
    enabled: !!guildId,
    refetchInterval: 10000, // Refresh every 10 seconds
    retry: 1,
  })
}

// XP Feed
export const useXPFeed = (guildId: string | null) => {
  const { setXpFeed, feedPaused } = useLevelingStore()

  return useQuery({
    queryKey: ['xp-feed', guildId],
    queryFn: async () => {
      if (!guildId) return []
      const { data } = await api.get<XPFeedEntry[]>(`/leveling/live-feed?guild_id=${guildId}&limit=20`)
      // Ensure data is always an array
      const xpFeed = Array.isArray(data) ? data : []
      if (!feedPaused) {
        setXpFeed(xpFeed)
      }
      return xpFeed
    },
    enabled: !!guildId && !feedPaused,
    refetchInterval: 5000, // Refresh every 5 seconds
    retry: 1,
  })
}

// Ranks
export const useRanks = (guildId: string | null) => {
  const { setRanks } = useLevelingStore()

  return useQuery({
    queryKey: ['ranks', guildId],
    queryFn: async () => {
      if (!guildId) return []
      const { data } = await api.get<Rank[]>(`/leveling/ranks?guild_id=${guildId}`)
      // Ensure data is always an array
      const ranks = Array.isArray(data) ? data : []
      setRanks(ranks)
      return ranks
    },
    enabled: !!guildId,
    retry: 1,
  })
}

export const useCreateRank = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (rank: Omit<Rank, 'id'>) => {
      const { data } = await api.post('/leveling/ranks', rank)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ranks'] })
      toast({
        title: 'Rank created',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to create rank',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

export const useUpdateRank = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (rank: Rank) => {
      const { data } = await api.put(`/leveling/ranks/${rank.id}`, rank)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ranks'] })
      toast({
        title: 'Rank updated',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to update rank',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

export const useDeleteRank = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (rankId: number) => {
      await api.delete(`/leveling/ranks/${rankId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ranks'] })
      toast({
        title: 'Rank deleted',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to delete rank',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

// Templates
export const useTemplates = (guildId: string | null) => {
  const { setTemplates } = useLevelingStore()

  return useQuery({
    queryKey: ['templates', guildId],
    queryFn: async () => {
      if (!guildId) return []
      const { data } = await api.get<MessageTemplate[]>(`/leveling/templates?guild_id=${guildId}`)
      // Ensure data is always an array
      const templates = Array.isArray(data) ? data : []
      setTemplates(templates)
      return templates
    },
    enabled: !!guildId,
    retry: 1,
  })
}

export const useCreateTemplate = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (template: Omit<MessageTemplate, 'id'>) => {
      const { data } = await api.post('/leveling/templates', template)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      toast({
        title: 'Template created',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to create template',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

export const useUpdateTemplate = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (template: MessageTemplate) => {
      const { data } = await api.put(`/leveling/templates/${template.id}`, template)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      toast({
        title: 'Template updated',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to update template',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

export const useDeleteTemplate = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (templateId: number) => {
      await api.delete(`/leveling/templates/${templateId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      toast({
        title: 'Template deleted',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to delete template',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

// Level Ranges
export const useRanges = (guildId: string | null) => {
  const { setRanges } = useLevelingStore()

  return useQuery({
    queryKey: ['ranges', guildId],
    queryFn: async () => {
      if (!guildId) return []
      const { data } = await api.get<LevelRange[]>(`/leveling/ranges/guild/${guildId}`)
      // Ensure data is always an array
      const ranges = Array.isArray(data) ? data : []
      setRanges(ranges)
      return ranges
    },
    enabled: !!guildId,
    retry: 1,
  })
}

export const useCreateRange = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (range: Omit<LevelRange, 'id'>) => {
      const { data } = await api.post('/leveling/ranges', range)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ranges'] })
      toast({
        title: 'Level range created',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to create level range',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

export const useUpdateRange = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (range: LevelRange) => {
      const { data } = await api.put(`/leveling/ranges/${range.id}`, range)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ranges'] })
      toast({
        title: 'Level range updated',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to update level range',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

export const useDeleteRange = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (rangeId: number) => {
      await api.delete(`/leveling/ranges/${rangeId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ranges'] })
      toast({
        title: 'Level range deleted',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to delete level range',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

// User Lookup
export const useUserLookup = () => {
  const toast = useToast()

  return useMutation({
    mutationFn: async ({ guildId, userId }: { guildId: string; userId: string }) => {
      const { data } = await api.get(`/leveling/user/${guildId}/${userId}`)
      return data
    },
    onError: () => {
      toast({
        title: 'User not found',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

// Manual Adjustment
export const useManualAdjustment = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      guildId,
      userId,
      xpChange,
      levelChange,
    }: {
      guildId: string
      userId: string
      xpChange?: number
      levelChange?: number
    }) => {
      const { data } = await api.post('/leveling/manual-adjust', {
        guild_id: guildId,
        user_id: userId,
        xp_change: xpChange,
        level_change: levelChange,
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leaderboard'] })
      toast({
        title: 'User stats adjusted',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to adjust user stats',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}
