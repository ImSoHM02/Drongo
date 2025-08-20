# Discord Bot Leveling System Database Schema

## Overview

This document describes the comprehensive database schema for the Discord bot leveling system, implementing XP-based progression with anti-abuse mechanisms and extensive customization options.

## System Requirements Implementation

### XP Formula
```
XP = min(BaseXP + (0.5 × words) + (0.1 × characters), XPmax)
```
- **BaseXP**: 5 (configurable per guild)
- **XPmax**: 25 (configurable per guild)
- **Word multiplier**: 0.5 (configurable)
- **Character multiplier**: 0.1 (configurable)

### Level Formula
```
XPneeded(level) = 50 × (level²) + (100 × level)
```
This creates exponential growth requiring increasingly more XP for higher levels.

### Anti-Abuse Features
- **Cooldowns**: 30-60 second randomized cooldowns between XP awards
- **Message Requirements**: Minimum 5 characters and 2 words
- **Daily Caps**: Configurable daily XP limits (default: 1000 XP)
- **Channel Controls**: Blacklist/whitelist channel management

## Database Tables

### 1. `user_levels` - Primary User Progression Data

Stores the core progression data for each user in each guild.

**Columns:**
- `user_id` (TEXT, NOT NULL) - Discord user ID
- `guild_id` (TEXT, NOT NULL) - Discord guild ID
- `current_xp` (INTEGER, DEFAULT 0) - XP progress toward next level
- `current_level` (INTEGER, DEFAULT 0) - Current level
- `total_xp` (INTEGER, DEFAULT 0) - Lifetime XP earned
- `messages_sent` (INTEGER, DEFAULT 0) - Total message count
- `last_xp_timestamp` (TIMESTAMP) - When user last earned XP
- `daily_xp_earned` (INTEGER, DEFAULT 0) - XP earned today
- `daily_reset_date` (TEXT) - Date for daily reset tracking
- `level_up_timestamp` (TIMESTAMP) - When user last leveled up
- `created_at` (TIMESTAMP) - Record creation time
- `updated_at` (TIMESTAMP) - Last update time

**Primary Key:** `(user_id, guild_id)`

**Purpose:** Central hub for user progression tracking and leaderboards.

### 2. `xp_transactions` - XP Award Audit Log

Logs every XP award for transparency, analytics, and activity feeds.

**Columns:**
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT) - Unique transaction ID
- `user_id` (TEXT, NOT NULL) - Discord user ID
- `guild_id` (TEXT, NOT NULL) - Discord guild ID
- `channel_id` (TEXT, NOT NULL) - Channel where XP was earned
- `message_id` (TEXT) - Discord message ID that triggered XP
- `xp_awarded` (INTEGER, NOT NULL) - Amount of XP awarded
- `reason` (TEXT, DEFAULT 'message') - Reason for XP award
- `message_length` (INTEGER) - Length of message that earned XP
- `word_count` (INTEGER) - Word count of triggering message
- `char_count` (INTEGER) - Character count of triggering message
- `timestamp` (TIMESTAMP) - When XP was awarded
- `daily_cap_applied` (BOOLEAN, DEFAULT FALSE) - Whether daily cap affected this award

**Foreign Key:** `(user_id, guild_id)` → `user_levels(user_id, guild_id)`

**Purpose:** Provides complete audit trail and enables detailed analytics.

### 3. `leveling_config` - Guild Configuration

Stores per-guild settings and customization options.

**Columns:**
- `guild_id` (TEXT PRIMARY KEY) - Discord guild ID
- `enabled` (BOOLEAN, DEFAULT TRUE) - Whether leveling is active
- `base_xp` (INTEGER, DEFAULT 5) - Base XP per message
- `max_xp` (INTEGER, DEFAULT 25) - Maximum XP per message
- `word_multiplier` (REAL, DEFAULT 0.5) - XP multiplier per word
- `char_multiplier` (REAL, DEFAULT 0.1) - XP multiplier per character
- `min_cooldown_seconds` (INTEGER, DEFAULT 30) - Minimum cooldown
- `max_cooldown_seconds` (INTEGER, DEFAULT 60) - Maximum cooldown
- `min_message_chars` (INTEGER, DEFAULT 5) - Minimum message length
- `min_message_words` (INTEGER, DEFAULT 2) - Minimum word count
- `daily_xp_cap` (INTEGER, DEFAULT 1000) - Daily XP limit
- `blacklisted_channels` (TEXT, DEFAULT '[]') - JSON array of blocked channels
- `whitelisted_channels` (TEXT, DEFAULT '[]') - JSON array of allowed channels
- `level_up_announcements` (BOOLEAN, DEFAULT TRUE) - Enable level-up messages
- `announcement_channel_id` (TEXT) - Channel for level-up announcements
- `dm_level_notifications` (BOOLEAN, DEFAULT FALSE) - DM users on level-up
- `created_at` (TIMESTAMP) - Configuration creation time
- `updated_at` (TIMESTAMP) - Last configuration update

**Purpose:** Enables complete customization of leveling behavior per guild.

### 4. `rank_titles` - Custom Rank System

Defines custom rank names and associated Discord roles for level ranges.

**Columns:**
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT) - Unique rank ID
- `guild_id` (TEXT, NOT NULL) - Discord guild ID
- `min_level` (INTEGER, NOT NULL) - Minimum level for this rank
- `max_level` (INTEGER) - Maximum level (NULL = no upper limit)
- `title` (TEXT, NOT NULL) - Display name for the rank
- `description` (TEXT) - Optional rank description
- `color_hex` (TEXT, DEFAULT '#7289DA') - Color for rank display
- `emoji` (TEXT) - Optional emoji for the rank
- `role_id` (TEXT) - Discord role to assign at this rank
- `created_at` (TIMESTAMP) - Rank creation time

**Unique Constraint:** `(guild_id, min_level)`
**Foreign Key:** `guild_id` → `leveling_config(guild_id)`

**Purpose:** Provides meaningful progression milestones and role automation.

### 5. `xp_cooldowns` - Anti-Abuse Cooldown Tracking

Tracks individual user cooldown states to prevent XP farming.

**Columns:**
- `user_id` (TEXT, NOT NULL) - Discord user ID
- `guild_id` (TEXT, NOT NULL) - Discord guild ID
- `last_xp_message_id` (TEXT) - ID of last message that earned XP
- `last_xp_timestamp` (TIMESTAMP, NOT NULL) - When user last earned XP
- `cooldown_ends_at` (TIMESTAMP, NOT NULL) - When cooldown expires
- `consecutive_messages` (INTEGER, DEFAULT 1) - Sequential message count

**Primary Key:** `(user_id, guild_id)`
**Foreign Key:** `(user_id, guild_id)` → `user_levels(user_id, guild_id)`

**Purpose:** Implements randomized cooldown system to prevent abuse.

## Database Views

### `view_xp_leaderboard`
Pre-calculated leaderboard with ranking information for efficient queries.

### `view_user_ranks`
Combines user levels with their current rank titles for display purposes.

### `view_recent_xp_activity`
Shows recent XP activity across the server for activity feeds.

## Performance Indexes

### User Levels
- `idx_user_levels_guild_level` - Guild leaderboards by level
- `idx_user_levels_guild_xp` - Guild leaderboards by XP
- `idx_user_levels_daily_reset` - Daily reset processing
- `idx_user_levels_updated` - Recent activity queries

### XP Transactions
- `idx_xp_transactions_user_guild` - User history queries
- `idx_xp_transactions_timestamp` - Chronological lookups
- `idx_xp_transactions_channel` - Channel-specific analytics
- `idx_xp_transactions_reason` - Award reason analysis

### Rank Titles
- `idx_rank_titles_guild_level` - Rank assignment queries
- `idx_rank_titles_role` - Role management queries

### XP Cooldowns
- `idx_xp_cooldowns_ends_at` - Cooldown expiration checks
- `idx_xp_cooldowns_timestamp` - Recent activity tracking

## Database Triggers

### Auto-Update Timestamps
- `trigger_user_levels_updated_at` - Updates `updated_at` on user_levels changes
- `trigger_leveling_config_updated_at` - Updates `updated_at` on config changes

### Daily Reset Management
- `trigger_daily_xp_reset` - Automatically resets daily XP when date changes

## Migration Script

The `migrate_leveling_database.py` script provides:

1. **Table Creation** - Creates all tables with proper constraints
2. **Index Creation** - Adds performance indexes
3. **Trigger Setup** - Installs auto-update triggers
4. **View Creation** - Creates convenience views
5. **Verification** - Tests that migration completed successfully

## Usage Examples

### Award XP to User
```sql
-- Check cooldown
SELECT cooldown_ends_at FROM xp_cooldowns 
WHERE user_id = ? AND guild_id = ? AND cooldown_ends_at > CURRENT_TIMESTAMP;

-- Award XP (if not on cooldown)
INSERT INTO xp_transactions 
(user_id, guild_id, channel_id, message_id, xp_awarded, word_count, char_count)
VALUES (?, ?, ?, ?, ?, ?, ?);

-- Update user level
UPDATE user_levels 
SET current_xp = current_xp + ?, 
    total_xp = total_xp + ?,
    messages_sent = messages_sent + 1,
    daily_xp_earned = daily_xp_earned + ?
WHERE user_id = ? AND guild_id = ?;
```

### Get Leaderboard
```sql
SELECT user_id, current_level, total_xp, rank, position 
FROM view_xp_leaderboard 
WHERE guild_id = ? 
ORDER BY position 
LIMIT 10;
```

### Check User Rank
```sql
SELECT current_level, current_xp, total_xp, rank_title, rank_description
FROM view_user_ranks
WHERE user_id = ? AND guild_id = ?;
```

## Security Considerations

1. **SQL Injection Prevention** - All queries use parameterized statements
2. **Rate Limiting** - Cooldown system prevents abuse
3. **Input Validation** - Message length and word count requirements
4. **Audit Trail** - Complete transaction logging for accountability

## Scalability Features

1. **Connection Pooling** - Uses existing database pool infrastructure
2. **Optimized Indexes** - Designed for common query patterns
3. **Batch Operations** - Supports bulk XP processing
4. **View Caching** - Pre-calculated views for expensive queries

This schema provides a robust, scalable foundation for a comprehensive Discord bot leveling system with extensive customization options and built-in anti-abuse protections.