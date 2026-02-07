import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@chakra-ui/react'
import api from '@/services/api'
import { EventSettings } from '@/types'

export const useEventSettings = (guildId: string | null) => {
  return useQuery({
    queryKey: ['event-settings', guildId],
    queryFn: async () => {
      if (!guildId) return null
      const { data } = await api.get<EventSettings>(`/events/settings/${guildId}`)
      return data
    },
    enabled: !!guildId,
  })
}

export const useUpdateEventSettings = (guildId: string | null) => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: { channel_id: string | null }) => {
      if (!guildId) throw new Error('No guild selected')
      const { data } = await api.post(`/events/settings/${guildId}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['event-settings', guildId] })
      toast({
        title: 'Event settings saved',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to save event settings',
        description: error?.response?.data?.error || undefined,
        status: 'error',
        duration: 4000,
        position: 'top-right',
      })
    },
  })
}
