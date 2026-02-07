import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@chakra-ui/react'
import api from '@/services/api'
import { BirthdaySettings } from '@/types'

export const useBirthdaySettings = (guildId: string | null) => {
  return useQuery({
    queryKey: ['birthday-settings', guildId],
    queryFn: async () => {
      if (!guildId) return null
      const { data } = await api.get<BirthdaySettings>(`/birthdays/settings/${guildId}`)
      return data
    },
    enabled: !!guildId,
  })
}

export const useUpdateBirthdaySettings = (guildId: string | null) => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: { channel_id: string | null; message_template: string }) => {
      if (!guildId) throw new Error('No guild selected')
      const { data } = await api.post(`/birthdays/settings/${guildId}`, payload)
      return data
    },
    onSuccess: (_data, _vars, _ctx) => {
      queryClient.invalidateQueries({ queryKey: ['birthday-settings', guildId] })
      toast({
        title: 'Birthday settings saved',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to save birthday settings',
        description: error?.response?.data?.error || undefined,
        status: 'error',
        duration: 4000,
        position: 'top-right',
      })
    },
  })
}
