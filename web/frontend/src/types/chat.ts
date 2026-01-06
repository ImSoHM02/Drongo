export interface ChatGuild {
  id: string
  name: string
  logging_enabled: boolean
  message_count: number
}

export interface ChatChannel {
  id: string
  name: string
  message_count: number
}

export interface ChatMessage {
  id: string
  author_id: string
  author_name: string
  content: string
  timestamp: string
  channel_id: string
  guild_id: string
  attachments: string[]
  embeds: number
}

export interface FetchProgress {
  guild_id: string
  guild_name: string
  total_messages: number
  fetched_at: string
  status: 'in_progress' | 'completed' | 'failed'
  current_channel: string | null
}
