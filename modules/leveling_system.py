import json
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from math import sqrt

import discord
from database_modules.database_pool import get_leveling_pool

class LevelingSystem:
    """
    Core leveling system implementation with XP calculation, level progression,
    anti-abuse mechanisms, and database integration.

    Formula:
    - XP = min(BaseXP + (0.5 × words) + (0.1 × characters), XPmax)
    - Level XP requirement: XPneeded(level) = 50 × (level²) + (100 × level)
    """

    def __init__(self, bot):
        self.bot = bot
        
        # Cache for guild configurations
        self._config_cache = {}
        self._cache_expiry = {}
        self._cache_duration = 300  # 5 minutes
        
        # Cache for user data to reduce database hits
        self._user_cache = {}
        self._user_cache_expiry = {}
        self._user_cache_duration = 60  # 1 minute
        
        # Compatibility flags for optional schema features
        self._rank_view_has_server_rank = None  # None = unknown, bool once detected
        self._rank_view_warning_logged = False
        
    def clear_guild_config_cache(self, guild_id: str):
        """Invalidate cached configuration for a guild."""
        cache_key = str(guild_id)
        self._config_cache.pop(cache_key, None)
        self._cache_expiry.pop(cache_key, None)

    def _normalize_bool(self, value: Any, default: bool = False) -> bool:
        """Convert a database value into a boolean with robust handling."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            truthy = {'1', 'true', 'yes', 'on', 'enable', 'enabled', 'y', 't'}
            falsy = {'0', 'false', 'no', 'off', 'disable', 'disabled', 'n', 'f'}
            if normalized in truthy:
                return True
            if normalized in falsy:
                return False
        return default

    # =========================================================================
    # XP CALCULATION FUNCTIONS
    # =========================================================================
    
    def calculate_xp(self, message_content: str, guild_config: Optional[Dict] = None) -> int:
        """
        Calculate XP for a message using the formula:
        XP = min(BaseXP + (0.5 × words) + (0.1 × characters), XPmax)
        
        Args:
            message_content: The message content to calculate XP for
            guild_config: Guild configuration overrides
            
        Returns:
            Calculated XP amount
        """
        if not message_content or not message_content.strip():
            return 0
            
        # Default configuration
        config = {
            'base_xp': 5,
            'max_xp': 25,
            'word_multiplier': 0.5,
            'char_multiplier': 0.1
        }
        
        if guild_config:
            config.update(guild_config)
        
        # Count words and characters
        words = len(message_content.split())
        characters = len(message_content)
        
        # Apply formula
        xp = config['base_xp'] + (config['word_multiplier'] * words) + (config['char_multiplier'] * characters)
        
        # Apply maximum cap before converting to int
        xp = min(xp, config['max_xp'])
        
        return int(xp)
    
    # =========================================================================
    # LEVEL CALCULATION FUNCTIONS  
    # =========================================================================
    
    def calculate_level_from_xp(self, total_xp: int) -> int:
        """
        Calculate the current level based on total XP using:
        XPneeded(level) = 50 × (level²) + (100 × level)
        
        Args:
            total_xp: Total XP accumulated
            
        Returns:
            Current level
        """
        if total_xp <= 0:
            return 0
            
        # Use quadratic formula to solve for level
        # 50*level^2 + 100*level - total_xp = 0
        # level = (-100 + sqrt(100^2 + 4*50*total_xp)) / (2*50)
        discriminant = 10000 + (200 * total_xp)
        level = (-100 + sqrt(discriminant)) / 100
        
        return int(level)
    
    def get_xp_required_for_level(self, level: int) -> int:
        """
        Get the total XP required to reach a specific level.
        
        Args:
            level: Target level
            
        Returns:
            Total XP required
        """
        if level <= 0:
            return 0
            
        return 50 * (level * level) + (100 * level)
    
    def get_xp_for_next_level(self, current_level: int, current_xp: int) -> Tuple[int, int]:
        """
        Calculate XP needed for next level and progress.
        
        Args:
            current_level: User's current level
            current_xp: User's current XP within the level
            
        Returns:
            Tuple of (xp_needed_for_next_level, progress_percentage)
        """
        current_level_xp = self.get_xp_required_for_level(current_level)
        next_level_xp = self.get_xp_required_for_level(current_level + 1)
        
        xp_needed = next_level_xp - current_level_xp
        progress = int((current_xp / xp_needed) * 100) if xp_needed > 0 else 100
        
        return xp_needed - current_xp, progress
    
    # =========================================================================
    # ANTI-ABUSE CHECKS
    # =========================================================================
    
    async def can_earn_xp(self, user_id: str, guild_id: str, channel_id: str, 
                         message_content: str) -> Tuple[bool, str]:
        """
        Check if user can earn XP based on anti-abuse rules.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID  
            channel_id: Discord channel ID
            message_content: Message content to validate
            
        Returns:
            Tuple of (can_earn_xp, reason_if_blocked)
        """
        try:
            # Get guild configuration
            config = await self.get_guild_config(guild_id)
            if not config.get('enabled', True):
                return False, "Leveling system disabled"
            
            # Check message quality requirements
            if len(message_content) < config.get('min_message_chars', 5):
                return False, "Message too short"
                
            words = len(message_content.split())
            if words < config.get('min_message_words', 2):
                return False, "Insufficient word count"
            
            # Check channel restrictions
            blacklist = json.loads(config.get('blacklisted_channels', '[]'))
            if channel_id in blacklist:
                return False, "Channel blacklisted"
                
            whitelist = json.loads(config.get('whitelisted_channels', '[]'))
            if whitelist and channel_id not in whitelist:
                return False, "Channel not whitelisted"
            
            # Check cooldown
            pool = await get_leveling_pool()
            cooldown_result = await pool.execute_single(
                "SELECT cooldown_ends_at FROM xp_cooldowns WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            )
            
            if cooldown_result:
                cooldown_end = datetime.fromisoformat(cooldown_result[0])
                if datetime.now() < cooldown_end:
                    return False, "User on cooldown"
            
            # Check daily XP cap
            user_data = await self.get_user_level_data(user_id, guild_id)
            daily_cap = config.get('daily_xp_cap', 1000)
            
            if user_data and user_data.get('daily_xp_earned', 0) >= daily_cap:
                return False, "Daily XP cap reached"
            
            return True, ""
            
        except Exception as e:
            self.bot.logger.error(f"Error checking XP eligibility: {e}")
            return False, "System error"
    
    # =========================================================================
    # XP AWARD SYSTEM
    # =========================================================================
    
    async def award_xp(self, user_id: str, guild_id: str, channel_id: str, 
                      message_content: str, message_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete XP processing pipeline: validate, calculate, award, and check level up.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            channel_id: Discord channel ID  
            message_content: Message content
            message_id: Discord message ID (optional)
            
        Returns:
            Dictionary with award results including level up status
        """
        result = {
            'success': False,
            'xp_awarded': 0,
            'level_up': False,
            'old_level': 0,
            'new_level': 0,
            'reason': ''
        }
        
        try:
            # Check if user can earn XP
            can_earn, reason = await self.can_earn_xp(user_id, guild_id, channel_id, message_content)
            if not can_earn:
                result['reason'] = reason
                return result
            
            # Get guild configuration
            config = await self.get_guild_config(guild_id)
            
            # Calculate XP
            xp_amount = self.calculate_xp(message_content, config)
            if xp_amount <= 0:
                result['reason'] = "No XP calculated"
                return result
            
            # Get current user data
            user_data = await self.get_user_level_data(user_id, guild_id)
            current_level = user_data.get('current_level', 0) if user_data else 0
            
            # Check daily cap
            daily_earned = user_data.get('daily_xp_earned', 0) if user_data else 0
            daily_cap = config.get('daily_xp_cap', 1000)
            
            # Apply daily cap
            remaining_daily = max(0, daily_cap - daily_earned)
            xp_amount = min(xp_amount, remaining_daily)
            daily_cap_applied = xp_amount < self.calculate_xp(message_content, config)
            
            if xp_amount <= 0:
                result['reason'] = "Daily XP cap reached"
                return result
            
            # Award XP in database
            pool = await get_leveling_pool()
            
            # Begin transaction
            async with pool.get_connection() as conn:
                try:
                    # Create or update user level data
                    await conn.execute("""
                        INSERT INTO user_levels (user_id, guild_id, current_xp, total_xp, messages_sent, daily_xp_earned)
                        VALUES (?, ?, ?, ?, 1, ?)
                        ON CONFLICT(user_id, guild_id) DO UPDATE SET
                            current_xp = current_xp + ?,
                            total_xp = total_xp + ?,
                            messages_sent = messages_sent + 1,
                            daily_xp_earned = daily_xp_earned + ?,
                            last_xp_timestamp = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                    """, (user_id, guild_id, xp_amount, xp_amount, xp_amount,
                          xp_amount, xp_amount, xp_amount))
                    
                    # Log transaction
                    await conn.execute("""
                        INSERT INTO xp_transactions 
                        (user_id, guild_id, channel_id, message_id, xp_awarded, 
                         message_length, word_count, char_count, daily_cap_applied)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (user_id, guild_id, channel_id, message_id, xp_amount,
                          len(message_content), len(message_content.split()),
                          len(message_content), daily_cap_applied))
                    
                    # Set cooldown
                    await self._set_user_cooldown(conn, user_id, guild_id, config)
                    
                    await conn.commit()
                    
                    # Check for level up
                    level_up_result = await self.check_level_up(user_id, guild_id)
                    
                    result.update({
                        'success': True,
                        'xp_awarded': xp_amount,
                        'level_up': level_up_result['level_up'],
                        'old_level': current_level,
                        'new_level': level_up_result['new_level'],
                        'reason': 'XP awarded successfully'
                    })
                    
                    # Add range info if level changed
                    if level_up_result['level_up']:
                        range_info = await self.get_user_range(user_id, guild_id)
                        if range_info:
                            result['range_name'] = range_info['name']
                            result['range_description'] = range_info['description']
                    
                except Exception as e:
                    await conn.rollback()
                    raise e
                    
        except Exception as e:
            self.bot.logger.error(f"Error awarding XP: {e}")
            result['reason'] = f"System error: {str(e)}"
            
        return result
    
    async def _set_user_cooldown(self, conn, user_id: str, guild_id: str, config: Dict):
        """Set randomized cooldown for user."""
        min_cooldown = config.get('min_cooldown_seconds', 30)
        max_cooldown = config.get('max_cooldown_seconds', 60)
        
        cooldown_duration = random.randint(min_cooldown, max_cooldown)
        cooldown_end = datetime.now() + timedelta(seconds=cooldown_duration)
        
        await conn.execute("""
            INSERT INTO xp_cooldowns (user_id, guild_id, last_xp_timestamp, cooldown_ends_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET
                last_xp_timestamp = CURRENT_TIMESTAMP,
                cooldown_ends_at = ?,
                consecutive_messages = consecutive_messages + 1
        """, (user_id, guild_id, cooldown_end.isoformat(), cooldown_end.isoformat()))
    
    # =========================================================================
    # LEVEL UP DETECTION
    # =========================================================================
    
    async def check_level_up(self, user_id: str, guild_id: str) -> Dict[str, Any]:
        """
        Check if user has leveled up and update their level.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            
        Returns:
            Dictionary with level up information including rewards
        """
        result = {
            'level_up': False,
            'old_level': 0,
            'new_level': 0,
            'xp_for_next_level': 0,
            'rewards': []
        }
        
        try:
            user_data = await self.get_user_level_data(user_id, guild_id)
            if not user_data:
                return result
            
            current_level = user_data['current_level']
            total_xp = user_data['total_xp']
            
            # Calculate what level they should be
            calculated_level = self.calculate_level_from_xp(total_xp)
            
            if calculated_level > current_level:
                # Level up detected!
                pool = await get_leveling_pool()
                
                # Update current level and current_xp (progress within level)
                level_start_xp = self.get_xp_required_for_level(calculated_level)
                current_xp_in_level = total_xp - level_start_xp
                
                await pool.execute_write("""
                    UPDATE user_levels
                    SET current_level = ?,
                        current_xp = ?,
                        level_up_timestamp = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND guild_id = ?
                """, (calculated_level, current_xp_in_level, user_id, guild_id))
                
                # Distribute level rewards
                rewards = await self.distribute_level_rewards(user_id, guild_id, current_level, calculated_level)
                
                result.update({
                    'level_up': True,
                    'old_level': current_level,
                    'new_level': calculated_level,
                    'xp_for_next_level': self.get_xp_required_for_level(calculated_level + 1) - total_xp,
                    'rewards': rewards
                })
                
                # Clear cache for this user
                cache_key = f"{user_id}:{guild_id}"
                if cache_key in self._user_cache:
                    del self._user_cache[cache_key]
                    del self._user_cache_expiry[cache_key]
                
        except Exception as e:
            self.bot.logger.error(f"Error checking level up: {e}")
            
        return result
    
    # =========================================================================
    # DATABASE INTEGRATION FUNCTIONS
    # =========================================================================
    
    async def get_guild_config(self, guild_id: str) -> Dict[str, Any]:
        """Get guild configuration with caching."""
        cache_key = guild_id
        now = datetime.now()
        
        # Check cache
        if (cache_key in self._config_cache and 
            cache_key in self._cache_expiry and 
            now < self._cache_expiry[cache_key]):
            return self._config_cache[cache_key]
        
        try:
            pool = await get_leveling_pool()
            result = await pool.execute_single(
                "SELECT * FROM leveling_config WHERE guild_id = ?",
                (guild_id,)
            )
            
            if result:
                config = {
                    'guild_id': result[0],
                    'enabled': self._normalize_bool(result[1], True),
                    'base_xp': result[2],
                    'max_xp': result[3],
                    'word_multiplier': result[4],
                    'char_multiplier': result[5],
                    'min_cooldown_seconds': result[6],
                    'max_cooldown_seconds': result[7],
                    'min_message_chars': result[8],
                    'min_message_words': result[9],
                    'daily_xp_cap': result[10],
                    'blacklisted_channels': result[11],
                    'whitelisted_channels': result[12],
                    'level_up_announcements': self._normalize_bool(result[13], True),
                    'announcement_channel_id': result[14],
                    'dm_level_notifications': self._normalize_bool(result[15], False)
                }
            else:
                # Create default config
                config = await self._create_default_guild_config(guild_id)
            
            # Cache the result
            self._config_cache[cache_key] = config
            self._cache_expiry[cache_key] = now + timedelta(seconds=self._cache_duration)
            
            return config
            
        except Exception as e:
            self.bot.logger.error(f"Error getting guild config: {e}")
            return self._get_default_config()
    
    async def _create_default_guild_config(self, guild_id: str) -> Dict[str, Any]:
        """Create default configuration for a guild."""
        config = self._get_default_config()
        config['guild_id'] = guild_id
        
        try:
            pool = await get_leveling_pool()
            await pool.execute_write("""
                INSERT INTO leveling_config (guild_id) VALUES (?)
            """, (guild_id,))
        except Exception as e:
            self.bot.logger.error(f"Error creating default guild config: {e}")
            
        return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            'enabled': True,
            'base_xp': 5,
            'max_xp': 25,
            'word_multiplier': 0.5,
            'char_multiplier': 0.1,
            'min_cooldown_seconds': 30,
            'max_cooldown_seconds': 60,
            'min_message_chars': 5,
            'min_message_words': 2,
            'daily_xp_cap': 1000,
            'blacklisted_channels': '[]',
            'whitelisted_channels': '[]',
            'level_up_announcements': True,
            'announcement_channel_id': None,
            'dm_level_notifications': False
        }
    
    async def get_user_level_data(self, user_id: str, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get user level data with caching."""
        cache_key = f"{user_id}:{guild_id}"
        now = datetime.now()
        
        # Check cache
        if (cache_key in self._user_cache and 
            cache_key in self._user_cache_expiry and 
            now < self._user_cache_expiry[cache_key]):
            return self._user_cache[cache_key]
        
        try:
            pool = await get_leveling_pool()
            result = await pool.execute_single("""
                SELECT user_id, guild_id, current_xp, current_level, total_xp, 
                       messages_sent, daily_xp_earned, daily_reset_date,
                       last_xp_timestamp, level_up_timestamp
                FROM user_levels 
                WHERE user_id = ? AND guild_id = ?
            """, (user_id, guild_id))
            
            if result:
                user_data = {
                    'user_id': result[0],
                    'guild_id': result[1],
                    'current_xp': result[2],
                    'current_level': result[3],
                    'total_xp': result[4],
                    'messages_sent': result[5],
                    'daily_xp_earned': result[6],
                    'daily_reset_date': result[7],
                    'last_xp_timestamp': result[8],
                    'level_up_timestamp': result[9]
                }
                
                # Cache the result
                self._user_cache[cache_key] = user_data
                self._user_cache_expiry[cache_key] = now + timedelta(seconds=self._user_cache_duration)
                
                return user_data
            
        except Exception as e:
            self.bot.logger.error(f"Error getting user level data: {e}")
            
        return None
    
    async def get_leaderboard(self, guild_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get guild leaderboard."""
        try:
            pool = await get_leveling_pool()
            results = await pool.execute_query("""
                SELECT user_id, current_level, total_xp, messages_sent, rank, position
                FROM view_xp_leaderboard 
                WHERE guild_id = ?
                ORDER BY position
                LIMIT ?
            """, (guild_id, limit))
            
            leaderboard = []
            for result in results:
                leaderboard.append({
                    'user_id': result[0],
                    'current_level': result[1],
                    'total_xp': result[2],
                    'messages_sent': result[3],
                    'rank': result[4],
                    'position': result[5]
                })
                
            # Add range info and configured rank title for each user (no Discord role assignment)
            for item in leaderboard:
                # Level range info
                range_info = await self.get_user_range(item['user_id'], guild_id)
                if range_info:
                    item['range_info'] = range_info
                    item['range_name'] = range_info['name']
                else:
                    item['range_info'] = None
                    item['range_name'] = None

                # Configured rank title (display only)
                rank_info = await self.get_user_rank(item['user_id'], guild_id)
                item['rank_title'] = rank_info['rank_title'] if rank_info and rank_info.get('rank_title') else None
            
            return leaderboard
            
        except Exception as e:
            self.bot.logger.error(f"Error getting leaderboard: {e}")
            return []
    
    async def get_user_rank(self, user_id: str, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get user's rank information."""
        try:
            pool = await get_leveling_pool()
            base_query = """
                SELECT current_level, current_xp, total_xp, rank_title,
                       rank_description, color_hex, emoji, rank_role_id, rank
                FROM view_user_ranks
                WHERE user_id = ? AND guild_id = ?
            """
            fallback_query = """
                SELECT current_level, current_xp, total_xp, rank_title,
                       rank_description, color_hex, emoji, rank_role_id
                FROM view_user_ranks
                WHERE user_id = ? AND guild_id = ?
            """
            
            result = None
            if self._rank_view_has_server_rank is False:
                result = await pool.execute_single(fallback_query, (user_id, guild_id))
            else:
                try:
                    result = await pool.execute_single(base_query, (user_id, guild_id))
                    self._rank_view_has_server_rank = True
                except Exception as e:
                    if "no such column: rank" in str(e).lower():
                        self._rank_view_has_server_rank = False
                        if not self._rank_view_warning_logged:
                            self.bot.logger.warning(
                                "view_user_ranks is missing 'rank' column; falling back to legacy schema without server rank column."
                            )
                            self._rank_view_warning_logged = True
                        result = await pool.execute_single(fallback_query, (user_id, guild_id))
                    else:
                        raise
            
            if result:
                return {
                    'current_level': result[0],
                    'current_xp': result[1],
                    'total_xp': result[2],
                    'rank_title': result[3],
                    'rank_description': result[4],
                    'color_hex': result[5],
                    'emoji': result[6],
                    'rank_role_id': result[7],
                    'server_rank': result[8] if len(result) > 8 else None
                }
            
        except Exception as e:
            self.bot.logger.error(f"Error getting user rank: {e}")
            
        return None

    async def get_rank_for_level(self, guild_id: str, level: int) -> Optional[Dict[str, Any]]:
        """Get rank metadata that corresponds to a specific level."""
        if level is None or level < 0:
            return None
        try:
            pool = await get_leveling_pool()
            result = await pool.execute_single("""
                SELECT id, title, description, color_hex, emoji, role_id, min_level, max_level
                FROM rank_titles
                WHERE guild_id = ?
                  AND ? >= min_level
                  AND (max_level IS NULL OR ? <= max_level)
                ORDER BY min_level DESC
                LIMIT 1
            """, (guild_id, level, level))
            
            if result:
                return {
                    'id': result[0],
                    'title': result[1],
                    'description': result[2],
                    'color_hex': result[3],
                    'emoji': result[4],
                    'role_id': result[5],
                    'min_level': result[6],
                    'max_level': result[7]
                }
        except Exception as e:
            self.bot.logger.error(f"Error getting rank for level {level} in guild {guild_id}: {e}")
        return None
    
    # =========================================================================
    # RANK MANAGEMENT FUNCTIONS
    # =========================================================================
    
    async def create_rank_title(self, guild_id: str, min_level: int, max_level: Optional[int],
                               title: str, description: Optional[str] = None,
                               color_hex: str = '#7289DA', emoji: Optional[str] = None,
                               role_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new rank title for a guild.
        
        Args:
            guild_id: Discord guild ID
            min_level: Minimum level for this rank
            max_level: Maximum level for this rank (None for open-ended)
            title: Rank title name
            description: Optional rank description
            color_hex: Color for the rank (hex format)
            emoji: Optional emoji for the rank
            role_id: Optional Discord role ID to assign
            
        Returns:
            Dictionary with creation result
        """
        try:
            pool = await get_leveling_pool()
            
            # Check for overlapping ranks
            existing_rank = await pool.execute_single("""
                SELECT id FROM rank_titles
                WHERE guild_id = ? AND min_level = ?
            """, (guild_id, min_level))
            
            if existing_rank:
                return {
                    'success': False,
                    'reason': f'A rank already exists for level {min_level}'
                }
            
            # Insert new rank
            await pool.execute_write("""
                INSERT INTO rank_titles
                (guild_id, min_level, max_level, title, description, color_hex, emoji, role_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, min_level, max_level, title, description, color_hex, emoji, role_id))
            
            return {
                'success': True,
                'rank_title': title,
                'min_level': min_level,
                'max_level': max_level
            }
            
        except Exception as e:
            self.bot.logger.error(f"Error creating rank title: {e}")
            return {
                'success': False,
                'reason': f"Database error: {str(e)}"
            }
    
    async def update_rank_title(self, guild_id: str, rank_id: int, **updates) -> Dict[str, Any]:
        """
        Update an existing rank title.
        
        Args:
            guild_id: Discord guild ID
            rank_id: Rank ID to update
            **updates: Fields to update
            
        Returns:
            Dictionary with update result
        """
        try:
            pool = await get_leveling_pool()
            
            # Verify rank exists and belongs to guild
            existing_rank = await pool.execute_single("""
                SELECT * FROM rank_titles WHERE id = ? AND guild_id = ?
            """, (rank_id, guild_id))
            
            if not existing_rank:
                return {
                    'success': False,
                    'reason': 'Rank not found or access denied'
                }
            
            # Build update query
            valid_fields = ['min_level', 'max_level', 'title', 'description', 'color_hex', 'emoji', 'role_id']
            update_fields = []
            update_values = []
            
            for field, value in updates.items():
                if field in valid_fields:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if not update_fields:
                return {
                    'success': False,
                    'reason': 'No valid fields to update'
                }
            
            update_values.extend([rank_id, guild_id])
            
            await pool.execute_write(f"""
                UPDATE rank_titles
                SET {', '.join(update_fields)}
                WHERE id = ? AND guild_id = ?
            """, update_values)
            
            return {
                'success': True,
                'updated_fields': list(updates.keys())
            }
            
        except Exception as e:
            self.bot.logger.error(f"Error updating rank title: {e}")
            return {
                'success': False,
                'reason': f"Database error: {str(e)}"
            }
    
    async def delete_rank_title(self, guild_id: str, rank_id: int) -> Dict[str, Any]:
        """
        Delete a rank title.
        
        Args:
            guild_id: Discord guild ID
            rank_id: Rank ID to delete
            
        Returns:
            Dictionary with deletion result
        """
        try:
            pool = await get_leveling_pool()
            
            # Verify rank exists and belongs to guild
            existing_rank = await pool.execute_single("""
                SELECT title FROM rank_titles WHERE id = ? AND guild_id = ?
            """, (rank_id, guild_id))
            
            if not existing_rank:
                return {
                    'success': False,
                    'reason': 'Rank not found or access denied'
                }
            
            await pool.execute_write("""
                DELETE FROM rank_titles WHERE id = ? AND guild_id = ?
            """, (rank_id, guild_id))
            
            return {
                'success': True,
                'deleted_rank': existing_rank[0]
            }
            
        except Exception as e:
            self.bot.logger.error(f"Error deleting rank title: {e}")
            return {
                'success': False,
                'reason': f"Database error: {str(e)}"
            }
    
    async def get_guild_ranks(self, guild_id: str) -> List[Dict[str, Any]]:
        """
        Get all rank titles for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            List of rank dictionaries
        """
        try:
            pool = await get_leveling_pool()
            results = await pool.execute_query("""
                SELECT id, min_level, max_level, title, description, color_hex, emoji, role_id, created_at
                FROM rank_titles
                WHERE guild_id = ?
                ORDER BY min_level ASC
            """, (guild_id,))
            
            ranks = []
            for result in results:
                ranks.append({
                    'id': result[0],
                    'min_level': result[1],
                    'max_level': result[2],
                    'title': result[3],
                    'description': result[4],
                    'color_hex': result[5],
                    'emoji': result[6],
                    'role_id': result[7],
                    'created_at': result[8]
                })
            
            return ranks
            
        except Exception as e:
            self.bot.logger.error(f"Error getting guild ranks: {e}")
            return []
    
    # =========================================================================
    # REWARD MANAGEMENT FUNCTIONS
    # =========================================================================
    
    async def create_level_reward(self, guild_id: str, level: int, reward_type: str,
                                 reward_data: Dict[str, Any], is_milestone: bool = False,
                                 milestone_interval: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a new level reward.
        
        Args:
            guild_id: Discord guild ID
            level: Level to award reward at
            reward_type: Type of reward ('role', 'custom_message', 'xp_bonus', 'milestone')
            reward_data: Reward configuration data
            is_milestone: Whether this is a milestone reward
            milestone_interval: Interval for milestone rewards
            
        Returns:
            Dictionary with creation result
        """
        try:
            pool = await get_leveling_pool()
            
            # Validate reward type
            valid_types = ['role', 'custom_message', 'xp_bonus', 'milestone']
            if reward_type not in valid_types:
                return {
                    'success': False,
                    'reason': f'Invalid reward type. Must be one of: {", ".join(valid_types)}'
                }
            
            # Check for existing reward
            existing_reward = await pool.execute_single("""
                SELECT id FROM level_rewards
                WHERE guild_id = ? AND level = ? AND reward_type = ?
            """, (guild_id, level, reward_type))
            
            if existing_reward:
                return {
                    'success': False,
                    'reason': f'A {reward_type} reward already exists for level {level}'
                }
            
            # Insert new reward
            await pool.execute_write("""
                INSERT INTO level_rewards
                (guild_id, level, reward_type, reward_data, is_milestone, milestone_interval)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (guild_id, level, reward_type, json.dumps(reward_data), is_milestone, milestone_interval))
            
            return {
                'success': True,
                'reward_type': reward_type,
                'level': level,
                'is_milestone': is_milestone
            }
            
        except Exception as e:
            self.bot.logger.error(f"Error creating level reward: {e}")
            return {
                'success': False,
                'reason': f"Database error: {str(e)}"
            }
    
    async def update_level_reward(self, guild_id: str, reward_id: int, **updates) -> Dict[str, Any]:
        """
        Update an existing level reward.
        
        Args:
            guild_id: Discord guild ID
            reward_id: Reward ID to update
            **updates: Fields to update
            
        Returns:
            Dictionary with update result
        """
        try:
            pool = await get_leveling_pool()
            
            # Verify reward exists and belongs to guild
            existing_reward = await pool.execute_single("""
                SELECT * FROM level_rewards WHERE id = ? AND guild_id = ?
            """, (reward_id, guild_id))
            
            if not existing_reward:
                return {
                    'success': False,
                    'reason': 'Reward not found or access denied'
                }
            
            # Build update query
            valid_fields = ['level', 'reward_type', 'reward_data', 'is_milestone', 'milestone_interval', 'active']
            update_fields = []
            update_values = []
            
            for field, value in updates.items():
                if field in valid_fields:
                    if field == 'reward_data' and isinstance(value, dict):
                        value = json.dumps(value)
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if not update_fields:
                return {
                    'success': False,
                    'reason': 'No valid fields to update'
                }
            
            update_values.extend([reward_id, guild_id])
            
            await pool.execute_write(f"""
                UPDATE level_rewards
                SET {', '.join(update_fields)}
                WHERE id = ? AND guild_id = ?
            """, update_values)
            
            return {
                'success': True,
                'updated_fields': list(updates.keys())
            }
            
        except Exception as e:
            self.bot.logger.error(f"Error updating level reward: {e}")
            return {
                'success': False,
                'reason': f"Database error: {str(e)}"
            }
    
    async def delete_level_reward(self, guild_id: str, reward_id: int) -> Dict[str, Any]:
        """
        Delete a level reward.
        
        Args:
            guild_id: Discord guild ID
            reward_id: Reward ID to delete
            
        Returns:
            Dictionary with deletion result
        """
        try:
            pool = await get_leveling_pool()
            
            # Verify reward exists and belongs to guild
            existing_reward = await pool.execute_single("""
                SELECT level, reward_type FROM level_rewards WHERE id = ? AND guild_id = ?
            """, (reward_id, guild_id))
            
            if not existing_reward:
                return {
                    'success': False,
                    'reason': 'Reward not found or access denied'
                }
            
            await pool.execute_write("""
                DELETE FROM level_rewards WHERE id = ? AND guild_id = ?
            """, (reward_id, guild_id))
            
            return {
                'success': True,
                'deleted_reward': f"Level {existing_reward[0]} {existing_reward[1]} reward"
            }
            
        except Exception as e:
            self.bot.logger.error(f"Error deleting level reward: {e}")
            return {
                'success': False,
                'reason': f"Database error: {str(e)}"
            }
    
    async def get_guild_rewards(self, guild_id: str) -> List[Dict[str, Any]]:
        """
        Get all level rewards for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            List of reward dictionaries
        """
        try:
            pool = await get_leveling_pool()
            results = await pool.execute_query("""
                SELECT id, level, reward_type, reward_data, is_milestone, milestone_interval, active, created_at
                FROM level_rewards
                WHERE guild_id = ? AND active = TRUE
                ORDER BY level ASC, reward_type ASC
            """, (guild_id,))
            
            rewards = []
            for result in results:
                try:
                    reward_data = json.loads(result[3])
                except:
                    reward_data = {}
                
                rewards.append({
                    'id': result[0],
                    'level': result[1],
                    'reward_type': result[2],
                    'reward_data': reward_data,
                    'is_milestone': bool(result[4]),
                    'milestone_interval': result[5],
                    'active': bool(result[6]),
                    'created_at': result[7]
                })
            
            return rewards
            
        except Exception as e:
            self.bot.logger.error(f"Error getting guild rewards: {e}")
            return []
    
    async def get_level_rewards(self, guild_id: str, level: int) -> List[Dict[str, Any]]:
        """
        Get rewards for a specific level.
        
        Args:
            guild_id: Discord guild ID
            level: Level to get rewards for
            
        Returns:
            List of reward dictionaries for the level
        """
        try:
            pool = await get_leveling_pool()
            
            # Get direct level rewards
            direct_rewards = await pool.execute_query("""
                SELECT id, reward_type, reward_data, created_at
                FROM level_rewards
                WHERE guild_id = ? AND level = ? AND active = TRUE AND is_milestone = FALSE
            """, (guild_id, level))
            
            # Get milestone rewards
            milestone_rewards = await pool.execute_query("""
                SELECT id, reward_type, reward_data, milestone_interval, created_at
                FROM level_rewards
                WHERE guild_id = ? AND active = TRUE AND is_milestone = TRUE
                AND ? % milestone_interval = 0
            """, (guild_id, level))
            
            rewards = []
            
            # Process direct rewards
            for result in direct_rewards:
                try:
                    reward_data = json.loads(result[2])
                except:
                    reward_data = {}
                
                rewards.append({
                    'id': result[0],
                    'level': level,
                    'reward_type': result[1],
                    'reward_data': reward_data,
                    'is_milestone': False,
                    'created_at': result[3]
                })
            
            # Process milestone rewards
            for result in milestone_rewards:
                try:
                    reward_data = json.loads(result[2])
                except:
                    reward_data = {}
                
                rewards.append({
                    'id': result[0],
                    'level': level,
                    'reward_type': result[1],
                    'reward_data': reward_data,
                    'is_milestone': True,
                    'milestone_interval': result[3],
                    'created_at': result[4]
                })
            
            return rewards
            
        except Exception as e:
            self.bot.logger.error(f"Error getting level rewards: {e}")
            return []
    
    async def distribute_level_rewards(self, user_id: str, guild_id: str, old_level: int, new_level: int) -> List[Dict[str, Any]]:
        """
        Distribute rewards for leveling up.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            old_level: Previous level
            new_level: New level achieved
            
        Returns:
            List of distributed rewards
        """
        distributed_rewards = []
        
        try:
            # Get rewards for all levels between old and new
            for level in range(old_level + 1, new_level + 1):
                level_rewards = await self.get_level_rewards(guild_id, level)
                
                for reward in level_rewards:
                    # Process the reward based on type
                    reward_result = await self._process_reward(user_id, guild_id, level, reward)
                    if reward_result['success']:
                        distributed_rewards.append({
                            'level': level,
                            'reward_type': reward['reward_type'],
                            'reward_data': reward['reward_data'],
                            'is_milestone': reward['is_milestone'],
                            'result': reward_result
                        })
            
        except Exception as e:
            self.bot.logger.error(f"Error distributing level rewards: {e}")
        
        return distributed_rewards
    
    async def _process_reward(self, user_id: str, guild_id: str, level: int, reward: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single reward.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            level: Level achieved
            reward: Reward configuration
            
        Returns:
            Dictionary with processing result
        """
        try:
            reward_type = reward['reward_type']
            reward_data = reward['reward_data']
            
            if reward_type == 'xp_bonus':
                # Award bonus XP
                bonus_xp = reward_data.get('amount', 0)
                pool = await get_leveling_pool()
                
                await pool.execute_write("""
                    UPDATE user_levels
                    SET total_xp = total_xp + ?, current_xp = current_xp + ?
                    WHERE user_id = ? AND guild_id = ?
                """, (bonus_xp, bonus_xp, user_id, guild_id))
                
                return {
                    'success': True,
                    'type': 'xp_bonus',
                    'amount': bonus_xp
                }
            
            elif reward_type == 'role':
                # Role assignment will be handled by the bot command layer
                return {
                    'success': True,
                    'type': 'role',
                    'role_id': reward_data.get('role_id'),
                    'action': reward_data.get('action', 'add')  # 'add' or 'remove'
                }
            
            elif reward_type == 'custom_message':
                # Custom message reward
                return {
                    'success': True,
                    'type': 'custom_message',
                    'message': reward_data.get('message', f'Congratulations on reaching level {level}!'),
                    'channel_id': reward_data.get('channel_id')
                }
            
            else:
                return {
                    'success': False,
                    'reason': f'Unknown reward type: {reward_type}'
                }
                
        except Exception as e:
            self.bot.logger.error(f"Error processing reward: {e}")
            return {
                'success': False,
                'reason': f'Processing error: {str(e)}'
            }
    
    # =========================================================================
    # LEVEL RANGE MANAGEMENT FUNCTIONS
    # =========================================================================
    
    async def get_user_range(self, user_id: str, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get the level range name for a user's current level"""
        try:
            pool = await get_leveling_pool()
            
            # Get user's current level
            user_data = await self.get_user_level_data(user_id, guild_id)
            if not user_data:
                return None
            
            level = user_data['current_level']
            
            # Get the range for this level
            range_result = await pool.execute_single('''
                SELECT id, range_name, description, min_level, max_level
                FROM level_range_names
                WHERE guild_id = ? AND ? >= min_level AND ? <= max_level
                ORDER BY min_level
                LIMIT 1
            ''', (guild_id, level, level))
            
            if range_result:
                return {
                    'id': range_result[0],
                    'name': range_result[1],
                    'description': range_result[2],
                    'min_level': range_result[3],
                    'max_level': range_result[4]
                }
            
            return None
            
        except Exception as e:
            self.bot.logger.error(f"Error getting user range: {e}")
            return None
    
    async def get_guild_ranges(self, guild_id: str) -> List[Dict[str, Any]]:
        """Get all level ranges for a guild"""
        try:
            pool = await get_leveling_pool()
            results = await pool.execute_query('''
                SELECT id, min_level, max_level, range_name, description, created_at
                FROM level_range_names
                WHERE guild_id = ?
                ORDER BY min_level
            ''', (guild_id,))
            
            ranges = []
            for row in results:
                ranges.append({
                    'id': row[0],
                    'min_level': row[1],
                    'max_level': row[2],
                    'range_name': row[3],
                    'description': row[4],
                    'created_at': row[5]
                })
            
            return ranges
            
        except Exception as e:
            self.bot.logger.error(f"Error getting guild ranges: {e}")
            return []
    
    async def add_level_range(self, guild_id: str, min_level: int, max_level: int,
                            range_name: str, description: str = None) -> Tuple[bool, str]:
        """Add a new level range for a guild"""
        try:
            pool = await get_leveling_pool()
            
            # Check for overlapping ranges
            overlap_check = await pool.execute_single('''
                SELECT COUNT(*) FROM level_range_names
                WHERE guild_id = ? AND (
                    (? >= min_level AND ? <= max_level) OR
                    (? >= min_level AND ? <= max_level) OR
                    (min_level >= ? AND min_level <= ?) OR
                    (max_level >= ? AND max_level <= ?)
                )
            ''', (guild_id, min_level, min_level, max_level, max_level,
                  min_level, max_level, min_level, max_level))
            
            if overlap_check[0] > 0:
                return False, "Range overlaps with existing ranges"
            
            # Insert new range
            await pool.execute_write('''
                INSERT INTO level_range_names
                (guild_id, min_level, max_level, range_name, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (guild_id, min_level, max_level, range_name, description))
            
            return True, "Range added successfully"
            
        except Exception as e:
            self.bot.logger.error(f"Error adding level range: {e}")
            return False, str(e)
    
    async def update_level_range(self, range_id: int, min_level: int, max_level: int,
                               range_name: str, description: str = None) -> Tuple[bool, str]:
        """Update an existing level range"""
        try:
            pool = await get_leveling_pool()
            
            # Get guild_id for this range
            range_info = await pool.execute_single(
                'SELECT guild_id FROM level_range_names WHERE id = ?',
                (range_id,)
            )
            if not range_info:
                return False, "Range not found"
            
            guild_id = range_info[0]
            
            # Check for overlapping ranges (excluding current range)
            overlap_check = await pool.execute_single('''
                SELECT COUNT(*) FROM level_range_names
                WHERE guild_id = ? AND id != ? AND (
                    (? >= min_level AND ? <= max_level) OR
                    (? >= min_level AND ? <= max_level) OR
                    (min_level >= ? AND min_level <= ?) OR
                    (max_level >= ? AND max_level <= ?)
                )
            ''', (guild_id, range_id, min_level, min_level, max_level, max_level,
                  min_level, max_level, min_level, max_level))
            
            if overlap_check[0] > 0:
                return False, "Range overlaps with existing ranges"
            
            # Update range
            await pool.execute_write('''
                UPDATE level_range_names
                SET min_level = ?, max_level = ?, range_name = ?, description = ?
                WHERE id = ?
            ''', (min_level, max_level, range_name, description, range_id))
            
            return True, "Range updated successfully"
            
        except Exception as e:
            self.bot.logger.error(f"Error updating level range: {e}")
            return False, str(e)
    
    async def delete_level_range(self, range_id: int) -> Tuple[bool, str]:
        """Delete a level range"""
        try:
            pool = await get_leveling_pool()
            
            result = await pool.execute_write(
                'DELETE FROM level_range_names WHERE id = ?',
                (range_id,)
            )
            
            # Check if any rows were deleted
            if result:
                return True, "Range deleted successfully"
            else:
                return False, "Range not found"
            
        except Exception as e:
            self.bot.logger.error(f"Error deleting level range: {e}")
            return False, str(e)
    
    # =========================================================================
    # MESSAGE PROCESSING INTEGRATION
    # =========================================================================
    
    async def process_message(self, message: discord.Message) -> Optional[Dict[str, Any]]:
        """
        Process a Discord message for XP award.
        Integrates with existing message processing system.
        
        Args:
            message: Discord message object
            
        Returns:
            XP award result or None if not processed
        """
        # Skip bot messages
        if message.author.bot:
            return None
            
        # Skip if no guild
        if not message.guild:
            return None
            
        # Process message content
        content = message.clean_content.strip()
        if not content:
            return None
            
        # Award XP
        result = await self.award_xp(
            str(message.author.id),
            str(message.guild.id),
            str(message.channel.id),
            content,
            str(message.id)
        )
        
        return result if result['success'] else None


    async def get_level_up_message(self, user_id: str, guild_id: str, old_level: int, new_level: int) -> str:
        """
        Retrieve and render the level-up message using configured templates.
        Falls back to the default message if no template matches.
        """
        try:
            pool = await get_leveling_pool()
            rank_info = await self.get_user_rank(user_id, guild_id)
            new_rank_data = await self.get_rank_for_level(guild_id, new_level)
            old_rank_data = await self.get_rank_for_level(guild_id, old_level)
            rank_changed = (
                new_rank_data is not None and
                (old_rank_data is None or old_rank_data.get('id') != new_rank_data.get('id'))
            )

            # Try rank promotion template if rank changed
            template_row = None
            if rank_changed:
                promotion_query = """
                    SELECT message_content FROM level_up_message_templates
                    WHERE guild_id = ?
                      AND template_type = 'rank_promotion'
                      AND enabled = 1
                      AND (? >= COALESCE(min_level, -1))
                      AND (? <= COALESCE(max_level, 9223372036854775807))
                    ORDER BY priority DESC
                    LIMIT 1
                """
                template_row = await pool.execute_single(promotion_query, (guild_id, new_level, new_level))

            # Fall back to standard level-up template
            if not template_row:
                default_query = """
                    SELECT message_content FROM level_up_message_templates
                    WHERE guild_id = ?
                      AND template_type = 'default_levelup'
                      AND enabled = 1
                      AND (? >= COALESCE(min_level, -1))
                      AND (? <= COALESCE(max_level, 9223372036854775807))
                    ORDER BY priority DESC
                    LIMIT 1
                """
                template_row = await pool.execute_single(default_query, (guild_id, new_level, new_level))

            if template_row and template_row[0]:
                message = template_row[0]
                message = message.replace('{user}', f'<@{user_id}>')
                message = message.replace('{username}', f'<@{user_id}>')
                message = message.replace('{user_id}', user_id)
                message = message.replace('{old_level}', str(old_level))
                message = message.replace('{level}', str(new_level))

                # Rank placeholders
                new_rank_title = ''
                if rank_info and rank_info.get('rank_title'):
                    new_rank_title = rank_info['rank_title']
                elif new_rank_data and new_rank_data.get('title'):
                    new_rank_title = new_rank_data['title']
                previous_rank_title = old_rank_data['title'] if old_rank_data else ''

                message = message.replace('{rank}', new_rank_title)
                message = message.replace('{rankname}', new_rank_title)
                message = message.replace('{old_rank}', previous_rank_title)
                message = message.replace('{previous_rank}', previous_rank_title)

                rank_emoji = ''
                if new_rank_data and new_rank_data.get('emoji'):
                    rank_emoji = new_rank_data['emoji']
                message = message.replace('{rank_emoji}', rank_emoji)

                rank_color = ''
                if new_rank_data and new_rank_data.get('color_hex'):
                    rank_color = new_rank_data['color_hex']
                message = message.replace('{rank_color}', rank_color)

                rank_role_id = ''
                if new_rank_data and new_rank_data.get('role_id'):
                    rank_role_id = str(new_rank_data['role_id'])
                message = message.replace('{rank_role_id}', rank_role_id)

                # Leaderboard/server rank placeholders
                if rank_info and rank_info.get('server_rank'):
                    server_rank_str = str(rank_info['server_rank'])
                    message = message.replace('{leaderboard_position}', server_rank_str)
                    message = message.replace('{server_rank}', server_rank_str)
                else:
                    message = message.replace('{leaderboard_position}', '')
                    message = message.replace('{server_rank}', '')

                # Range placeholders
                range_info = await self.get_user_range(user_id, guild_id)
                range_name = range_info.get('name') if range_info and range_info.get('name') else ''
                message = message.replace('{range}', range_name)
                message = message.replace('{tier}', range_name)

                return message
        except Exception:
            # On error, ignore and fall back to default
            pass
        # Fallback default
        return f"🎉 <@{user_id}> leveled up! **Level {old_level}** → **Level {new_level}**"
# Global instance
leveling_system = None

def get_leveling_system(bot) -> LevelingSystem:
    """Get or create the global leveling system instance."""
    global leveling_system
    if leveling_system is None:
        leveling_system = LevelingSystem(bot)
    return leveling_system
