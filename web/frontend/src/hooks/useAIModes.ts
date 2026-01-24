import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@chakra-ui/react'
import api from '@/services/api'
import { AIMode } from '@/types'

export const useAIModeOptions = () => {
  return useQuery({
    queryKey: ['ai-modes'],
    queryFn: async () => {
      const { data } = await api.get<{ modes: AIMode[] }>('/ai/modes')
      return data?.modes ?? []
    },
  })
}

export const useGuildAIMode = (guildId: string | null) => {
  return useQuery({
    queryKey: ['ai-mode', guildId],
    queryFn: async () => {
      if (!guildId) return null
      const { data } = await api.get<{ guild_id: string; mode: string }>(`/ai/mode/${guildId}`)
      return data
    },
    enabled: !!guildId,
  })
}

export const useUpdateGuildAIMode = (guildId: string | null) => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (mode: string) => {
      if (!guildId) throw new Error('No guild selected')
      const { data } = await api.post(`/ai/mode/${guildId}`, { mode })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-mode', guildId] })
      toast({
        title: 'AI mode updated',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update AI mode',
        description: error?.response?.data?.error || undefined,
        status: 'error',
        duration: 4000,
        position: 'top-right',
      })
    },
  })
}
