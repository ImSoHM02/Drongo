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
  guild_breakdown: GuildStats[]
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
  database_files: number
  system_databases: SystemDatabase[]
}

export interface SystemDatabase {
  name: string
  file: string
  size_mb: number
}

export interface GuildStats {
  guild_id: string
  guild_name: string
  total_messages: number
  unique_users: number
  active_channels: number
  recent_activity: number
  database_size_mb: number
  last_message: string | null
  is_scanning: boolean
}

export interface MessageActivity {
  timestamps: string[]
  message_counts: number[]
}
