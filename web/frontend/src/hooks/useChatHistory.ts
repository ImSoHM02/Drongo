import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@chakra-ui/react'
import api from '@/services/api'
import { useChatStore } from '@/stores/chatStore'
import { ChatGuild, ChatChannel, ChatMessage } from '@/types/chat'

export const useChatGuilds = () => {
  return useQuery({
    queryKey: ['chat-guilds'],
    queryFn: async () => {
      const { data } = await api.get<{ guilds: any[] }>('/chat/guilds')
      // Map backend response to frontend format
      return data.guilds.map((guild: any) => ({
        id: guild.guild_id,
        name: guild.guild_name,
        logging_enabled: guild.logging_enabled,
        message_count: guild.total_messages,
      })) as ChatGuild[]
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  })
}

export const useChannels = (guildId: string | null) => {
  const { setChannels } = useChatStore()

  return useQuery({
    queryKey: ['chat-channels', guildId],
    queryFn: async () => {
      if (!guildId) return []
      const { data } = await api.get<{ channels: any[] }>(`/chat/guild/${guildId}/channels`)
      // Map backend response to frontend format
      const channels = data.channels.map((channel: any) => ({
        id: channel.channel_id,
        name: channel.channel_name,
        message_count: channel.message_count,
      })) as ChatChannel[]
      setChannels(channels)
      return channels
    },
    enabled: !!guildId,
  })
}

export const useMessages = (
  guildId: string | null,
  channelId: string | null,
  limit: number = 50,
  offset: number = 0
) => {
  const { setMessages } = useChatStore()

  return useQuery({
    queryKey: ['chat-messages', guildId, channelId, limit, offset],
    queryFn: async () => {
      if (!guildId || !channelId) return []
      const { data } = await api.get<ChatMessage[]>(
        `/chat/messages/${guildId}/${channelId}?limit=${limit}&offset=${offset}`
      )
      setMessages(data)
      return data
    },
    enabled: !!guildId && !!channelId,
  })
}

export const useRecentMessages = (
  guildId: string | null,
  channelId: string | null
) => {
  return useQuery({
    queryKey: ['chat-recent', guildId, channelId],
    queryFn: async () => {
      if (!guildId || !channelId) return []
      const { data } = await api.get<{ messages: any[] }>(
        `/chat/guild/${guildId}/recent?channel_id=${channelId}`
      )
      // Map backend response to frontend format
      return data.messages.map((msg: any) => ({
        id: msg.id,
        author_id: msg.user_id,
        author_name: msg.username,
        content: msg.message_content,
        timestamp: msg.timestamp,
        channel_id: msg.channel_id,
        guild_id: guildId,
      })) as ChatMessage[]
    },
    enabled: !!guildId && !!channelId,
    refetchInterval: 5000, // Refresh every 5 seconds
  })
}

export const useTriggerFullFetch = () => {
  const toast = useToast()

  return useMutation({
    mutationFn: async (guildId: string) => {
      const { data } = await api.post(`/chat/guild/${guildId}/fetch-all`)
      return data
    },
    onSuccess: (data) => {
      toast({
        title: 'Full Fetch Started',
        description: data.message || 'Historical message fetch has been queued',
        status: 'success',
        duration: 5000,
        isClosable: true,
        position: 'top-right',
      })
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.error || 'Failed to start full fetch',
        status: 'error',
        duration: 5000,
        isClosable: true,
        position: 'top-right',
      })
    },
  })
}

export const useToggleLogging = () => {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ guildId, enabled }: { guildId: string; enabled: boolean }) => {
      const { data } = await api.post(`/chat/guild/${guildId}/settings`, {
        logging_enabled: enabled
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-guilds'] })
      toast({
        title: 'Logging settings updated',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to update logging settings',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    },
  })
}
