import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@chakra-ui/react'
import api from '@/services/api'
import { Command } from '@/types'

export const useCommands = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  const { data: commands = [], isLoading } = useQuery({
    queryKey: ['commands'],
    queryFn: async () => {
      const { data } = await api.get<Command[]>('/commands/list')
      return data
    },
  })

  const registerMutation = useMutation({
    mutationFn: () => api.post('/commands/register'),
    onSuccess: () => {
      toast({
        title: 'Commands registered successfully',
        status: 'success',
        position: 'top-right',
        duration: 3000,
      })
      queryClient.invalidateQueries({ queryKey: ['commands'] })
    },
    onError: () => {
      toast({
        title: 'Failed to register commands',
        status: 'error',
        position: 'top-right',
        duration: 3000,
      })
    },
  })

  const restartBotMutation = useMutation({
    mutationFn: () => api.post('/bot/restart'),
    onSuccess: () => {
      toast({
        title: 'Bot is restarting...',
        status: 'success',
        position: 'top-right',
        duration: 3000,
      })
    },
    onError: () => {
      toast({
        title: 'Failed to restart bot',
        status: 'error',
        position: 'top-right',
        duration: 3000,
      })
    },
  })

  const shutdownBotMutation = useMutation({
    mutationFn: () => api.post('/bot/shutdown'),
    onSuccess: () => {
      toast({
        title: 'Bot is shutting down...',
        status: 'info',
        position: 'top-right',
        duration: 3000,
      })
    },
    onError: () => {
      toast({
        title: 'Failed to shutdown bot',
        status: 'error',
        position: 'top-right',
        duration: 3000,
      })
    },
  })

  return {
    commands,
    isLoading,
    registerCommands: registerMutation.mutate,
    restartBot: restartBotMutation.mutate,
    shutdownBot: shutdownBotMutation.mutate,
    isRegistering: registerMutation.isPending,
  }
}
