# Drongo Bot Leveling System Setup Guide

## Overview

The Drongo Bot Leveling System is a comprehensive XP-based progression system that rewards users for active participation in Discord servers. This guide provides step-by-step instructions for enabling and configuring the leveling system.

## Features

### Core Functionality
- **XP Formula**: `XP = min(BaseXP + (0.5 × words) + (0.1 × characters), XPmax)`
- **Level Formula**: `XPneeded(level) = 50 × (level²) + (100 × level)`
- **Anti-Abuse System**: Randomized cooldowns, message quality requirements, daily caps
- **Dashboard Integration**: Real-time web interface for monitoring and configuration
- **Discord Commands**: Full slash command integration

### Advanced Features
- **Guild-Specific Configuration**: Customize settings per server
- **Channel Controls**: Blacklist/whitelist specific channels
- **Rank Titles**: Custom rank names with Discord role integration
- **Leaderboards**: Server-wide XP rankings
- **Real-time Analytics**: Live feed of XP transactions and user activity

## Prerequisites

Before setting up the leveling system, ensure you have:

1. **Python Environment**: Python 3.8+ with discord.py
2. **Database**: SQLite database with connection pooling configured
3. **Bot Permissions**: Appropriate Discord bot permissions in your server
4. **Environment Variables**: Discord bot token and guild IDs configured

## Installation Steps

### 1. Database Migration

Run the database migration to create all necessary tables:

```bash
python3 migrate_leveling_database.py
```

**Expected Output:**
```
Drongo Bot Leveling System Migration
=====================================

✓ Leveling system migration completed successfully!
The following components were created:
  • user_levels - User XP and level progression
  • xp_transactions - XP award audit log
  • leveling_config - Guild-specific settings
  • rank_titles - Custom rank names and roles
  • xp_cooldowns - Anti-abuse cooldown tracking
  • Performance indexes and triggers
  • Database views for common queries
```

### 2. Discord Command Registration

Register the leveling commands with Discord:

```bash
python3 utilities/register_commands.py
```

This will register the following commands:
- `/level stats` - View user level statistics
- `/level leaderboard` - Server XP leaderboard
- `/level config` - Admin configuration commands
- `/level view-config` - View current settings

### 3. Bot Integration

#### Enable Leveling System in Bot

Add the leveling cog to your bot's startup sequence in [`drongo.py`](drongo.py):

```python
# Add to bot initialization
from modules.cogs.leveling_cog import LevelingCog

async def setup_hook(self):
    await self.add_cog(LevelingCog(self))
```

#### Enable Message Processing

Ensure message processing includes XP awards:

```python
from modules.leveling_system import get_leveling_system

@bot.event
async def on_message(message):
    # Your existing message processing
    
    # Add XP processing
    leveling = get_leveling_system(bot)
    result = await leveling.process_message(message)
    
    if result and result.get('level_up'):
        # Handle level up notifications
        if config.get('level_up_announcements'):
            # Send level up message
            pass
```

### 4. Dashboard Integration

The leveling system includes full dashboard integration:

1. **Start Dashboard Server**:
   ```bash
   python3 web/dashboard_server.py
   ```

2. **Access Leveling Dashboard**:
   - URL: `http://localhost:5001/dashboard/leveling`
   - Features: Real-time XP feed, leaderboards, configuration management

3. **API Endpoints**:
   - `/api/leveling/leaderboard` - Get leaderboard data
   - `/api/leveling/user-stats` - Get user statistics
   - `/api/leveling/config` - Get/update configuration
   - `/api/leveling/live-feed` - Real-time XP transactions

## Configuration

### Default Settings

The system ships with these default configuration values:

```yaml
enabled: true
base_xp: 5                    # Base XP per message
max_xp: 25                    # Maximum XP per message
word_multiplier: 0.5          # XP per word
char_multiplier: 0.1          # XP per character
min_cooldown_seconds: 30      # Minimum cooldown between XP awards
max_cooldown_seconds: 60      # Maximum cooldown between XP awards
min_message_chars: 5          # Minimum message length
min_message_words: 2          # Minimum word count
daily_xp_cap: 1000           # Daily XP limit per user
blacklisted_channels: []      # Blocked channels
whitelisted_channels: []      # Allowed channels (empty = all allowed)
level_up_announcements: true  # Enable level-up messages
dm_level_notifications: false # DM users on level up
```

### Discord Command Configuration

Use `/level config` to modify settings:

```
/level config setting:enabled value:true
/level config setting:base_xp value:10
/level config setting:daily_xp_cap value:2000
/level config setting:announcement_channel value:#general
```

### Dashboard Configuration

Access the web dashboard for advanced configuration:

1. Navigate to `http://localhost:5001/dashboard/leveling`
2. Use the configuration panel to modify settings
3. Changes are applied in real-time

## Usage Examples

### Basic Commands

**Check Your Level**:
```
/level stats
```

**Check Another User's Level**:
```
/level stats user:@username
```

**View Leaderboard**:
```
/level leaderboard limit:10
```

**View Configuration** (Anyone):
```
/level view-config
```

### Admin Commands

**Enable/Disable System**:
```
/level config setting:enabled value:true
```

**Set XP Range**:
```
/level config setting:base_xp value:5
/level config setting:max_xp value:30
```

**Configure Daily Cap**:
```
/level config setting:daily_xp_cap value:1500
```

**Set Announcement Channel**:
```
/level config setting:announcement_channel value:#level-ups
```

## Anti-Abuse Features

The system includes comprehensive anti-abuse mechanisms:

### Message Quality Requirements
- **Minimum Length**: 5 characters (configurable)
- **Minimum Words**: 2 words (configurable)
- **Whitespace Filtering**: Empty/whitespace-only messages ignored

### Cooldown System
- **Randomized Cooldowns**: 30-60 second random intervals
- **Per-User Tracking**: Individual cooldown states
- **Consecutive Message Tracking**: Additional abuse detection

### Daily Limits
- **Daily XP Cap**: Configurable limit (default: 1000 XP)
- **Automatic Reset**: Resets at midnight UTC
- **Real-time Tracking**: Live monitoring of daily progress

### Channel Controls
- **Blacklist Channels**: Block specific channels from earning XP
- **Whitelist Channels**: Restrict XP earning to specific channels
- **Dynamic Configuration**: Update restrictions without restart

## Monitoring and Analytics

### Real-Time Dashboard
- **Live XP Feed**: See XP awards as they happen
- **User Statistics**: Detailed progression tracking
- **Server Leaderboards**: Real-time rankings
- **Configuration Panel**: Admin controls

### Database Views
The system includes optimized database views:
- **`view_xp_leaderboard`**: Pre-calculated rankings
- **`view_user_ranks`**: User data with rank titles
- **`view_recent_xp_activity`**: Recent activity feed

### Performance Monitoring
- **Cached Configurations**: 5-minute configuration caching
- **Cached User Data**: 1-minute user data caching
- **Optimized Queries**: Indexed database operations
- **Connection Pooling**: Efficient database connections

## Troubleshooting

### Common Issues

**Commands Not Appearing**:
1. Verify bot has `applications.commands` scope
2. Run command registration: `python3 utilities/register_commands.py`
3. Wait 1-5 minutes for Discord to update commands

**XP Not Being Awarded**:
1. Check if leveling is enabled: `/level view-config`
2. Verify user isn't on cooldown
3. Check message meets quality requirements (5 chars, 2 words)
4. Verify channel isn't blacklisted

**Dashboard Not Loading**:
1. Ensure dashboard server is running: `python3 web/dashboard_server.py`
2. Check port 5001 is available
3. Verify all dependencies are installed

### Database Issues

**Migration Failed**:
```bash
# Check database permissions
ls -la chat_database.db

# Re-run migration with verbose output
python3 migrate_leveling_database.py
```

**Performance Issues**:
```bash
# Check database indexes
python3 -c "
import sqlite3
conn = sqlite3.connect('chat_database.db')
cursor = conn.execute(\"SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%leveling%'\")
print('Indexes:', [row[0] for row in cursor.fetchall()])
"
```

### Testing the System

Run the comprehensive test suite:
```bash
python3 test_leveling_system.py
```

**Expected Results**:
- XP Calculation Tests: ✅ PASSED
- Level Progression Tests: ✅ PASSED  
- Anti-Abuse System Tests: ✅ PASSED
- Database Integration Tests: ✅ PASSED
- Configuration Tests: ✅ PASSED
- Performance Tests: ✅ PASSED
- Error Handling Tests: ✅ PASSED

## Advanced Configuration

### Custom Rank Titles

Create custom rank titles with role assignment:

```sql
INSERT INTO rank_titles (guild_id, min_level, max_level, title, description, role_id)
VALUES 
    ('YOUR_GUILD_ID', 1, 5, 'Newbie', 'Just getting started', 'ROLE_ID'),
    ('YOUR_GUILD_ID', 6, 15, 'Active Member', 'Regular participant', 'ROLE_ID'),
    ('YOUR_GUILD_ID', 16, 30, 'Veteran', 'Experienced member', 'ROLE_ID'),
    ('YOUR_GUILD_ID', 31, NULL, 'Legend', 'Community pillar', 'ROLE_ID');
```

### API Integration

The system provides REST API endpoints for external integration:

```javascript
// Get leaderboard
fetch('/api/leveling/leaderboard?guild_id=123&limit=10')
  .then(response => response.json())
  .then(data => console.log(data));

// Get user stats
fetch('/api/leveling/user-stats?user_id=456&guild_id=123')
  .then(response => response.json())
  .then(data => console.log(data));

// Update configuration
fetch('/api/leveling/config', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    guild_id: '123',
    daily_xp_cap: 2000,
    enabled: true
  })
});
```

## Security Considerations

### Input Validation
- All user inputs are sanitized and validated
- SQL injection prevention through parameterized queries
- Rate limiting on API endpoints

### Permission Checks
- Admin commands require `administrator` permission
- API endpoints include proper authorization
- Configuration changes are logged

### Data Privacy
- User data is stored securely with appropriate indexing
- Personal information is minimized
- Audit trails maintain accountability

## Maintenance

### Regular Tasks

**Daily**:
- Monitor dashboard for system health
- Check error logs for issues
- Verify daily XP resets are working

**Weekly**:
- Review leaderboards for anomalies
- Check database performance metrics
- Update configuration as needed

**Monthly**:
- Analyze XP transaction patterns
- Review and update rank titles
- Optimize database if needed

### Backup Recommendations

```bash
# Backup leveling data
sqlite3 chat_database.db "
.output leveling_backup_$(date +%Y%m%d).sql
.dump user_levels
.dump xp_transactions
.dump leveling_config
.dump rank_titles
.dump xp_cooldowns
"
```

## Support

For additional support or feature requests:

1. Check the comprehensive test results
2. Review error logs in the dashboard
3. Consult the database schema documentation
4. Run system diagnostics with the test suite

The leveling system is designed to be robust, scalable, and easy to manage. With proper setup and configuration, it will provide years of reliable service for your Discord community.