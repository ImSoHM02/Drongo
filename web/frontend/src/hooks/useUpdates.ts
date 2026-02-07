import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@chakra-ui/react'
import api from '@/services/api'
import { CommitInfo, UpdateSettings } from '@/types'

export const useUpdateSettings = (guildId: string | null) => {
  return useQuery({
    queryKey: ['update-settings', guildId],
    queryFn: async () => {
      if (!guildId) return null
      const { data } = await api.get<UpdateSettings>(`/updates/settings/${guildId}`)
      return data
    },
    enabled: !!guildId,
  })
}

export const useUpdateUpdateSettings = (guildId: string | null) => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: { channel_id: string | null }) => {
      if (!guildId) throw new Error('No guild selected')
      const { data } = await api.post(`/updates/settings/${guildId}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['update-settings', guildId] })
      toast({
        title: 'Update settings saved',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to save update settings',
        description: error?.response?.data?.error || undefined,
        status: 'error',
        duration: 4000,
        position: 'top-right',
      })
    },
  })
}

export const useGitCommits = (limit: number = 50) => {
  return useQuery({
    queryKey: ['git-commits', limit],
    queryFn: async () => {
      const { data } = await api.get<{ commits: CommitInfo[] }>(`/github/commits?limit=${limit}`)
      return data.commits
    },
  })
}

export const usePushUpdates = () => {
  const toast = useToast()

  return useMutation({
    mutationFn: async (commits: string[]) => {
      const { data } = await api.post<{ success: boolean; sent: number; failed: number; message: string }>(
        '/github/push-updates',
        { commits }
      )
      return data
    },
    onSuccess: (data) => {
      toast({
        title: 'Updates pushed',
        description: data.message,
        status: 'success',
        duration: 5000,
        position: 'top-right',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to push updates',
        description: error?.response?.data?.error || undefined,
        status: 'error',
        duration: 4000,
        position: 'top-right',
      })
    },
  })
}
