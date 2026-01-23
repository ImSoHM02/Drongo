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

export interface GuildCommand {
  name: string
  description: string
  type: string
  subcommands?: string[]
  enabled: boolean
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
