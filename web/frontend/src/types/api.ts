export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
}

export interface Command {
  name: string
  description: string
  usage?: string
  category?: string
}

export interface BotStatus {
  status: 'online' | 'offline' | 'restarting'
  uptime: string
  guilds: number
}

export interface BotConfig {
  guild_id: string
  guild_name: string
  bot_name: string
  current_nickname: string | null
}
