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

export interface AIMode {
  name: string
  chance: number
  insult_weight: number
  compliment_weight: number
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

export interface GitHubStatus {
  current_commit: string
  current_commit_short: string
  current_branch: string
  has_uncommitted_changes: boolean
  remote_url: string
}

export interface CommitInfo {
  hash: string
  author: string
  date: string
  message: string
}

export interface UpdateCheckResult {
  updates_available: boolean
  current_commit: string
  current_commit_short: string
  latest_commit: string
  latest_commit_short: string
  commits_behind: number
  commit_log: CommitInfo[]
}
