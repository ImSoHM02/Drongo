import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@chakra-ui/react'
import api from '@/services/api'
import { BotConfig } from '@/types'

export const useBotConfig = (guildId: string | null) => {
  return useQuery({
    queryKey: ['bot-config', guildId],
    queryFn: async () => {
      if (!guildId) return null
      const { data } = await api.get<BotConfig>(`/bot/config/${guildId}`)
      return data
    },
    enabled: !!guildId,
    retry: 1,
  })
}

export const useUpdateBotName = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ guildId, botName }: { guildId: string; botName: string }) => {
      const { data } = await api.post(`/bot/config/${guildId}`, { bot_name: botName })
      return data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['bot-config', variables.guildId] })
      toast({
        title: 'Bot name updated',
        description: `Trigger phrase is now "oi ${variables.botName}"`,
        status: 'success',
        duration: 5000,
        position: 'top-right',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update bot name',
        description: error?.response?.data?.error || 'An error occurred',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

export const useUpdateNickname = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ guildId, nickname }: { guildId: string; nickname: string }) => {
      const { data } = await api.post(`/bot/nickname/${guildId}`, { nickname })
      return data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['bot-config', variables.guildId] })
      toast({
        title: 'Nickname updated',
        description: variables.nickname
          ? `Nickname set to "${variables.nickname}"`
          : 'Nickname reset to default',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update nickname',
        description: error?.response?.data?.error || 'An error occurred',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}
