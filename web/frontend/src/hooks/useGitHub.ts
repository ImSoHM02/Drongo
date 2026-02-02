import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@chakra-ui/react'
import api from '@/services/api'
import { GitHubStatus, UpdateCheckResult } from '@/types'

export const useGitHubStatus = () => {
  return useQuery({
    queryKey: ['github-status'],
    queryFn: async () => {
      const { data } = await api.get<GitHubStatus>('/github/status')
      return data
    },
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 1,
  })
}

export const useCheckUpdates = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data } = await api.get<UpdateCheckResult>('/github/check-updates')
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['github-status'] })

      if (data.updates_available) {
        toast({
          title: 'Updates available',
          description: `${data.commits_behind} commit${data.commits_behind !== 1 ? 's' : ''} behind origin/main`,
          status: 'info',
          duration: 5000,
          position: 'top-right',
        })
      } else {
        toast({
          title: 'Already up to date',
          description: 'No updates available',
          status: 'success',
          duration: 3000,
          position: 'top-right',
        })
      }
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to check for updates',
        description: error?.response?.data?.error || 'An error occurred',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}

export const useGitHubUpdate = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/github/update')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['github-status'] })
      toast({
        title: 'Update initiated',
        description: 'Bot will restart shortly',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update',
        description: error?.response?.data?.error || 'An error occurred',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}
