export interface DashboardStats {
  messages_processed: number
  commands_executed: number
  active_users: number
  uptime: string
  status: string
  memory_usage: number
  cpu_usage: number
  bot_guilds: number
  database_size: number
  recent_activity: number
  message_rate: number
  command_rate: number
  recent_messages: RecentMessage[]
  recent_events: RecentEvent[]
  database_health: DatabaseHealth
  last_updated: string
}

export interface RecentMessage {
  timestamp: string
  author: string
  guild: string
  channel: string
  type: string
}

export interface RecentEvent {
  timestamp: string
  event: string
  type: 'info' | 'system' | 'command' | 'status' | 'error'
}

export interface DatabaseHealth {
  database_size_mb: number
  table_count: number
  index_count: number
}

export interface MessageActivity {
  timestamps: string[]
  message_counts: number[]
}
