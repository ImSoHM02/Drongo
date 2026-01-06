import { create } from 'zustand'
import { ChatGuild, ChatChannel, ChatMessage } from '@/types/chat'

interface ChatState {
  selectedGuild: string | null
  selectedChannel: string | null
  messages: ChatMessage[]
  channels: ChatChannel[]
  messageOffset: number

  setSelectedGuild: (guildId: string | null) => void
  setSelectedChannel: (channelId: string | null) => void
  setMessages: (messages: ChatMessage[]) => void
  setChannels: (channels: ChatChannel[]) => void
  setMessageOffset: (offset: number) => void
}

export const useChatStore = create<ChatState>((set) => ({
  selectedGuild: null,
  selectedChannel: null,
  messages: [],
  channels: [],
  messageOffset: 0,

  setSelectedGuild: (guildId) => set({ selectedGuild: guildId, selectedChannel: null }),
  setSelectedChannel: (channelId) => set({ selectedChannel: channelId, messageOffset: 0 }),
  setMessages: (messages) => set({ messages }),
  setChannels: (channels) => set({ channels }),
  setMessageOffset: (offset) => set({ messageOffset: offset }),
}))
