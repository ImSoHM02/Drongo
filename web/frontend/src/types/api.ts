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
