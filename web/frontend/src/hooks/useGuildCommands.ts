import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@chakra-ui/react'
import api from '@/services/api'
import { GuildCommand } from '@/types'

export const useGuildCommands = (guildId: string | null) => {
  return useQuery({
    queryKey: ['guild-commands', guildId],
    queryFn: async () => {
      if (!guildId) return []
      const { data } = await api.get<GuildCommand[]>(`/commands/guild/${guildId}`)
      return Array.isArray(data) ? data : []
    },
    enabled: !!guildId,
  })
}

export const useUpdateGuildCommands = (guildId: string | null) => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (overrides: Record<string, boolean>) => {
      if (!guildId) throw new Error('No guild selected')
      const { data } = await api.post(`/commands/guild/${guildId}`, { overrides })
      return data
    },
    onSuccess: (_data, _vars, context) => {
      queryClient.invalidateQueries({ queryKey: ['guild-commands', guildId] })
      toast({
        title: 'Commands updated',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
      return context
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update commands',
        description: error?.response?.data?.error || undefined,
        status: 'error',
        duration: 4000,
        position: 'top-right',
      })
    },
  })
}
