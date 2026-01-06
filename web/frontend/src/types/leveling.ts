export interface LevelingConfig {
  guild_id: string
  enabled: boolean
  base_xp: number
  max_xp: number
  word_multiplier: number
  char_multiplier: number
  min_cooldown_seconds: number
  max_cooldown_seconds: number
  min_message_chars: number
  min_message_words: number
  daily_xp_cap: number
  blacklisted_channels: string
  whitelisted_channels: string
  level_up_announcements: boolean
  announcement_channel_id: string | null
  dm_level_notifications: boolean
}

export interface LeaderboardEntry {
  position: number
  user_id: string
  user_name: string
  current_level: number
  total_xp: number
  current_xp: number
  messages_sent: number
  range_name?: string
  rank_title?: string
  range_info?: LevelRange
}

export interface XPFeedEntry {
  user_id: string
  user_name: string
  guild_id: string
  guild_name: string
  channel_id: string
  xp_awarded: number
  message_length: number
  word_count: number
  char_count: number
  timestamp: string
  daily_cap_applied: boolean
}

export interface Rank {
  id: number
  guild_id: string
  name: string
  level_min: number
  level_max: number | null
  color: string
  emoji: string
  discord_role_id: string | null
  description: string
  user_count?: number
}

export interface MessageTemplate {
  id: number
  guild_id: string
  name: string
  type: 'default_levelup' | 'rank_promotion' | 'milestone_level' | 'first_level' | 'major_milestone'
  content: string
  conditions: string
  priority: number
  enabled: boolean
}

export interface LevelRange {
  id: number
  guild_id: string
  range_name: string
  min_level: number
  max_level: number
  description: string
}

export interface Guild {
  id: string
  name: string
  user_count: number
}
