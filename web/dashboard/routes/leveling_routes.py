import json
import logging
from datetime import datetime
import os

from quart import Blueprint, jsonify, request

from database_modules.database import get_leveling_db_connection
from database_modules.database_pool import get_leveling_pool
from modules.leveling_system import get_leveling_system
from .. import state
from ..name_resolution import bulk_resolve_names

leveling_bp = Blueprint("dashboard_leveling", __name__)


@leveling_bp.route("/api/leveling/live-feed")
async def api_leveling_live_feed():
    """Get live XP award feed with resolved names."""
    try:
        guild_id = request.args.get("guild_id")
        limit = int(request.args.get("limit", 50))

        conn = await get_leveling_db_connection()

        if guild_id:
            query = """
                SELECT xt.user_id, xt.guild_id, xt.channel_id, xt.xp_awarded,
                       xt.message_length, xt.word_count, xt.char_count, xt.timestamp,
                       xt.daily_cap_applied
                FROM xp_transactions xt
                WHERE xt.guild_id = ?
                ORDER BY xt.timestamp DESC
                LIMIT ?
            """
            params = (guild_id, limit)
        else:
            query = """
                SELECT xt.user_id, xt.guild_id, xt.channel_id, xt.xp_awarded,
                       xt.message_length, xt.word_count, xt.char_count, xt.timestamp,
                       xt.daily_cap_applied
                FROM xp_transactions xt
                ORDER BY xt.timestamp DESC
                LIMIT ?
            """
            params = (limit,)

        async with conn.execute(query, params) as cursor:
            transactions = await cursor.fetchall()

        await conn.close()

        user_ids = set()
        guild_ids = set()

        for tx in transactions:
            user_ids.add(tx[0])
            guild_ids.add(tx[1])

        resolved_names = await bulk_resolve_names(list(user_ids), list(guild_ids))

        feed_data = []
        for tx in transactions:
            feed_data.append({
                "user_id": tx[0],
                "user_name": resolved_names.get(f"user_{tx[0]}", f"Unknown User ({tx[0][-4:]})"),
                "guild_id": tx[1],
                "guild_name": resolved_names.get(f"guild_{tx[1]}", f"Unknown Guild ({tx[1][-4:]})"),
                "channel_id": tx[2],
                "xp_awarded": tx[3],
                "message_length": tx[4],
                "word_count": tx[5],
                "char_count": tx[6],
                "timestamp": tx[7],
                "daily_cap_applied": bool(tx[8]) if tx[8] is not None else False
            })

        return jsonify(feed_data)

    except Exception as e:
        logging.error(f"Error getting live feed: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/leaderboard")
async def api_leveling_leaderboard():
    """Get leaderboard data with resolved names."""
    try:
        guild_id = request.args.get("guild_id")
        limit = int(request.args.get("limit", 25))

        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        class MockBot:
            pass

        leveling = get_leveling_system(MockBot())
        leaderboard = await leveling.get_leaderboard(guild_id, limit)

        user_ids = [entry["user_id"] for entry in leaderboard]
        resolved_names = await bulk_resolve_names(user_ids, [guild_id])

        for entry in leaderboard:
            entry["user_name"] = resolved_names.get(f"user_{entry['user_id']}", f"Unknown User ({entry['user_id'][-4:]})")
            entry["guild_name"] = resolved_names.get(f"guild_{guild_id}", f"Unknown Guild ({guild_id[-4:]})")

        return jsonify(leaderboard)

    except Exception as e:
        logging.error(f"Error getting leaderboard: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/user-stats")
async def api_leveling_user_stats():
    """Get user statistics with resolved names."""
    try:
        user_id = request.args.get("user_id")
        guild_id = request.args.get("guild_id")

        if not user_id or not guild_id:
            return jsonify({"error": "user_id and guild_id parameters required"}), 400

        class MockBot:
            pass

        leveling = get_leveling_system(MockBot())
        user_data = await leveling.get_user_level_data(user_id, guild_id)
        rank_data = await leveling.get_user_rank(user_id, guild_id)
        range_data = await leveling.get_user_range(user_id, guild_id)

        if user_data:
            resolved_names = await bulk_resolve_names([user_id], [guild_id])

            stats = {
                **user_data,
                "user_name": resolved_names.get(f"user_{user_id}", f"Unknown User ({user_id[-4:]})"),
                "guild_name": resolved_names.get(f"guild_{guild_id}", f"Unknown Guild ({guild_id[-4:]})"),
                "rank_info": rank_data or {},
                "range_info": range_data or None
            }
            return jsonify(stats)
        else:
            return jsonify({"error": "User not found"}), 404

    except Exception as e:
        logging.error(f"Error getting user stats: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/config", methods=["GET"])
async def api_leveling_config_get():
    """Get leveling configuration with proper database values."""
    try:
        guild_id = request.args.get("guild_id")
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute("""
            SELECT enabled, base_xp, max_xp, word_multiplier, char_multiplier,
                   min_cooldown_seconds, max_cooldown_seconds, min_message_chars,
                   min_message_words, daily_xp_cap, blacklisted_channels,
                   whitelisted_channels, level_up_announcements, announcement_channel_id,
                   dm_level_notifications
            FROM leveling_config
            WHERE guild_id = ?
        """, (guild_id,)) as cursor:
            result = await cursor.fetchone()

        await conn.close()

        if result:
            config = {
                "guild_id": guild_id,
                "enabled": bool(result[0]) if result[0] is not None else True,
                "base_xp": result[1] if result[1] is not None else 5,
                "max_xp": result[2] if result[2] is not None else 25,
                "word_multiplier": result[3] if result[3] is not None else 0.5,
                "char_multiplier": result[4] if result[4] is not None else 0.1,
                "min_cooldown_seconds": result[5] if result[5] is not None else 30,
                "max_cooldown_seconds": result[6] if result[6] is not None else 60,
                "min_message_chars": result[7] if result[7] is not None else 5,
                "min_message_words": result[8] if result[8] is not None else 2,
                "daily_xp_cap": result[9] if result[9] is not None else 1000,
                "blacklisted_channels": result[10] if result[10] is not None else "[]",
                "whitelisted_channels": result[11] if result[11] is not None else "[]",
                "level_up_announcements": bool(result[12]) if result[12] is not None else True,
                "announcement_channel_id": result[13],
                "dm_level_notifications": bool(result[14]) if result[14] is not None else False
            }
        else:
            config = {
                "guild_id": guild_id,
                "enabled": True,
                "base_xp": 5,
                "max_xp": 25,
                "word_multiplier": 0.5,
                "char_multiplier": 0.1,
                "min_cooldown_seconds": 30,
                "max_cooldown_seconds": 60,
                "min_message_chars": 5,
                "min_message_words": 2,
                "daily_xp_cap": 1000,
                "blacklisted_channels": "[]",
                "whitelisted_channels": "[]",
                "level_up_announcements": True,
                "announcement_channel_id": None,
                "dm_level_notifications": False
            }

        return jsonify(config)

    except Exception as e:
        logging.error(f"Error getting config: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/config", methods=["POST"])
async def api_leveling_config_update():
    """Update leveling configuration."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")

        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400

        conn = await get_leveling_db_connection()

        await conn.execute("""
            UPDATE leveling_config SET
                enabled = ?,
                base_xp = ?,
                max_xp = ?,
                word_multiplier = ?,
                char_multiplier = ?,
                min_cooldown_seconds = ?,
                max_cooldown_seconds = ?,
                min_message_chars = ?,
                min_message_words = ?,
                daily_xp_cap = ?,
                blacklisted_channels = ?,
                whitelisted_channels = ?,
                level_up_announcements = ?,
                announcement_channel_id = ?,
                dm_level_notifications = ?
            WHERE guild_id = ?
        """, (
            data.get("enabled", True),
            data.get("base_xp", 5),
            data.get("max_xp", 25),
            data.get("word_multiplier", 0.5),
            data.get("char_multiplier", 0.1),
            data.get("min_cooldown_seconds", 30),
            data.get("max_cooldown_seconds", 60),
            data.get("min_message_chars", 5),
            data.get("min_message_words", 2),
            data.get("daily_xp_cap", 1000),
            data.get("blacklisted_channels", "[]"),
            data.get("whitelisted_channels", "[]"),
            data.get("level_up_announcements", True),
            data.get("announcement_channel_id"),
            data.get("dm_level_notifications", False),
            guild_id
        ))

        await conn.commit()
        await conn.close()

        try:
            leveling_instance = None
            if state.bot_instance:
                leveling_instance = get_leveling_system(state.bot_instance)
            else:
                import modules.leveling_system as leveling_module  # type: ignore

                leveling_instance = getattr(leveling_module, "leveling_system", None)
            if leveling_instance and hasattr(leveling_instance, "clear_guild_config_cache"):
                leveling_instance.clear_guild_config_cache(str(guild_id))
        except Exception as cache_error:
            logging.error(f"Error clearing leveling config cache for guild {guild_id}: {cache_error}")

        return jsonify({"success": True, "message": "Configuration updated successfully"})

    except Exception as e:
        logging.error(f"Error updating config: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/manual-adjust", methods=["POST"])
async def api_leveling_manual_adjust():
    """Manual XP/level adjustment."""
    try:
        data = await request.get_json()
        user_id = data.get("user_id")
        guild_id = data.get("guild_id")
        adjustment_type = data.get("type")
        amount = data.get("amount")
        reason = data.get("reason", "Manual adjustment")

        if not all([user_id, guild_id, adjustment_type, amount is not None]):
            return jsonify({"error": "Missing required parameters"}), 400

        conn = await get_leveling_db_connection()

        if adjustment_type == "add_xp":
            await conn.execute("""
                UPDATE user_levels
                SET current_xp = current_xp + ?,
                    total_xp = total_xp + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND guild_id = ?
            """, (amount, amount, user_id, guild_id))

        elif adjustment_type == "remove_xp":
            await conn.execute("""
                UPDATE user_levels
                SET current_xp = MAX(0, current_xp - ?),
                    total_xp = MAX(0, total_xp - ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND guild_id = ?
            """, (amount, amount, user_id, guild_id))

        elif adjustment_type == "set_level":
            class MockBot:
                pass

            leveling = get_leveling_system(MockBot())
            required_xp = leveling.get_xp_required_for_level(amount)

            await conn.execute("""
                UPDATE user_levels
                SET current_level = ?,
                    current_xp = 0,
                    total_xp = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND guild_id = ?
            """, (amount, required_xp, user_id, guild_id))

        await conn.execute("""
            INSERT INTO xp_transactions
            (user_id, guild_id, channel_id, xp_awarded, message_length, word_count, char_count)
            VALUES (?, ?, 'MANUAL', ?, 0, 0, 0)
        """, (user_id, guild_id, amount if adjustment_type != "set_level" else 0))

        await conn.commit()
        await conn.close()

        return jsonify({"success": True, "message": f"Successfully applied {adjustment_type}"})

    except Exception as e:
        logging.error(f"Error in manual adjustment: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/ranks", methods=["GET"])
async def api_leveling_ranks_get():
    """Get guild rank titles with enhanced data."""
    try:
        guild_id = request.args.get("guild_id")
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute("""
            SELECT rt.id, rt.min_level, rt.max_level, rt.title, rt.description,
                   rt.color_hex, rt.emoji, rt.role_id, rt.created_at,
                   COUNT(ul.user_id) as user_count
            FROM rank_titles rt
            LEFT JOIN user_levels ul ON ul.guild_id = rt.guild_id
                AND ul.current_level >= rt.min_level
                AND (rt.max_level IS NULL OR ul.current_level <= rt.max_level)
            WHERE rt.guild_id = ?
            GROUP BY rt.id
            ORDER BY rt.min_level ASC
        """, (guild_id,)) as cursor:
            ranks = await cursor.fetchall()

        await conn.close()

        rank_list = []
        for rank in ranks:
            rank_list.append({
                "id": rank[0],
                "level_min": rank[1],
                "level_max": rank[2],
                "name": rank[3],
                "description": rank[4],
                "color": rank[5],
                "emoji": rank[6],
                "discord_role_id": rank[7],
                "created_at": rank[8],
                "user_count": rank[9] or 0
            })

        return jsonify(rank_list)

    except Exception as e:
        logging.error(f"Error getting ranks: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/ranks", methods=["POST"])
async def api_leveling_ranks_create():
    """Create a new rank title with validation."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")
        min_level = data.get("level_min")
        max_level = data.get("level_max")
        title = data.get("name")

        if not all([guild_id, min_level is not None, title]):
            return jsonify({"error": "guild_id, min_level, and title are required"}), 400

        if min_level < 0:
            return jsonify({"error": "min_level must be non-negative"}), 400

        if max_level is not None and max_level < min_level:
            return jsonify({"error": "max_level must be greater than or equal to min_level"}), 400

        conn = await get_leveling_db_connection()

        overlap_query = """
            SELECT id, title FROM rank_titles
            WHERE guild_id = ? AND (
                (min_level <= ? AND (max_level IS NULL OR max_level >= ?)) OR
                (? IS NOT NULL AND min_level <= ? AND (max_level IS NULL OR max_level >= ?))
            )
        """
        async with conn.execute(overlap_query, (
            guild_id, min_level, min_level,
            max_level, max_level, max_level
        )) as cursor:
            overlapping = await cursor.fetchone()

        if overlapping:
            await conn.close()
            return jsonify({
                "error": f"Level range conflicts with existing rank '{overlapping[1]}'"
            }), 400

        await conn.execute("""
            INSERT INTO rank_titles
            (guild_id, min_level, max_level, title, description, color_hex, emoji, role_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            guild_id, min_level, max_level, title,
            data.get("description"), data.get("color_hex", "#7289DA"),
            data.get("emoji"), data.get("role_id")
        ))

        await conn.commit()

        async with conn.execute("SELECT last_insert_rowid()") as cursor:
            rank_id = (await cursor.fetchone())[0]

        await conn.close()

        return jsonify({
            "success": True,
            "rank_id": rank_id,
            "message": f"Rank '{title}' created successfully"
        })

    except Exception as e:
        logging.error(f"Error creating rank: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/ranks/<int:rank_id>", methods=["PUT"])
async def api_leveling_ranks_update(rank_id):
    """Update a rank title with validation."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")

        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute(
            "SELECT id, title FROM rank_titles WHERE id = ? AND guild_id = ?",
            (rank_id, guild_id)
        ) as cursor:
            existing_rank = await cursor.fetchone()

        if not existing_rank:
            await conn.close()
            return jsonify({"error": "Rank not found or access denied"}), 404

        min_level = data.get("min_level")
        max_level = data.get("max_level")

        if min_level is not None and min_level < 0:
            await conn.close()
            return jsonify({"error": "min_level must be non-negative"}), 400

        if max_level is not None and min_level is not None and max_level < min_level:
            await conn.close()
            return jsonify({"error": "max_level must be greater than or equal to min_level"}), 400

        valid_fields = ["min_level", "max_level", "title", "description", "color_hex", "emoji", "role_id"]
        update_fields = []
        update_values = []

        for field in valid_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                update_values.append(data[field])

        if not update_fields:
            await conn.close()
            return jsonify({"error": "No valid fields to update"}), 400

        update_values.extend([rank_id, guild_id])

        await conn.execute(f"""
            UPDATE rank_titles
            SET {', '.join(update_fields)}
            WHERE id = ? AND guild_id = ?
        """, update_values)

        await conn.commit()
        await conn.close()

        return jsonify({
            "success": True,
            "message": "Rank updated successfully"
        })

    except Exception as e:
        logging.error(f"Error updating rank: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/ranks/<int:rank_id>", methods=["DELETE"])
async def api_leveling_ranks_delete(rank_id):
    """Delete a rank title."""
    try:
        guild_id = request.args.get("guild_id")
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute(
            "SELECT title FROM rank_titles WHERE id = ? AND guild_id = ?",
            (rank_id, guild_id)
        ) as cursor:
            existing_rank = await cursor.fetchone()

        if not existing_rank:
            await conn.close()
            return jsonify({"error": "Rank not found or access denied"}), 404

        await conn.execute(
            "DELETE FROM rank_titles WHERE id = ? AND guild_id = ?",
            (rank_id, guild_id)
        )

        await conn.commit()
        await conn.close()

        return jsonify({
            "success": True,
            "message": f"Rank '{existing_rank[0]}' deleted successfully"
        })

    except Exception as e:
        logging.error(f"Error deleting rank: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/rewards", methods=["GET"])
async def api_leveling_rewards_get():
    """Get guild level rewards."""
    try:
        guild_id = request.args.get("guild_id")
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        class MockBot:
            pass

        leveling = get_leveling_system(MockBot())
        rewards = await leveling.get_guild_rewards(guild_id)

        return jsonify(rewards)

    except Exception as e:
        logging.error(f"Error getting rewards: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/rewards", methods=["POST"])
async def api_leveling_rewards_create():
    """Create a new level reward."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")

        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400

        class MockBot:
            pass

        leveling = get_leveling_system(MockBot())
        result = await leveling.create_level_reward(
            guild_id=guild_id,
            level=data.get("level"),
            reward_type=data.get("reward_type"),
            reward_data=data.get("reward_data", {}),
            is_milestone=data.get("is_milestone", False),
            milestone_interval=data.get("milestone_interval")
        )

        return jsonify(result)

    except Exception as e:
        logging.error(f"Error creating reward: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/rewards/<int:reward_id>", methods=["PUT"])
async def api_leveling_rewards_update(reward_id):
    """Update a level reward."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")

        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400

        class MockBot:
            pass

        leveling = get_leveling_system(MockBot())
        result = await leveling.update_level_reward(guild_id, reward_id, **data)

        return jsonify(result)

    except Exception as e:
        logging.error(f"Error updating reward: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/rewards/<int:reward_id>", methods=["DELETE"])
async def api_leveling_rewards_delete(reward_id):
    """Delete a level reward."""
    try:
        guild_id = request.args.get("guild_id")
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        class MockBot:
            pass

        leveling = get_leveling_system(MockBot())
        result = await leveling.delete_level_reward(guild_id, reward_id)

        return jsonify(result)

    except Exception as e:
        logging.error(f"Error deleting reward: {e}")
        return jsonify({"error": str(e)}), 500


def _is_authorized_admin(admin_id: str) -> bool:
    """Validate admin identity against AUTHORIZED_USER_ID if provided."""
    authorized = os.getenv("AUTHORIZED_USER_ID")
    if not authorized:
        return True  # fallback if not set
    return str(admin_id) == str(authorized)


@leveling_bp.route("/api/leveling/admin/add_xp", methods=["POST"])
async def api_leveling_admin_add_xp():
    """Admin endpoint to add raw XP to a user."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")
        user_id = data.get("user_id")
        xp = int(data.get("xp", 0))
        admin_id = str(data.get("admin_id", ""))

        if not guild_id or not user_id:
            return jsonify({"error": "guild_id and user_id are required"}), 400
        if xp <= 0:
            return jsonify({"error": "xp must be positive"}), 400
        if not _is_authorized_admin(admin_id):
            return jsonify({"error": "unauthorized"}), 403

        class MockBot:
            pass

        leveling = get_leveling_system(MockBot())
        pool = await get_leveling_pool()

        today = datetime.utcnow().date().isoformat()
        user_data = await leveling.get_user_level_data(user_id, guild_id)
        new_daily = (
            user_data.get("daily_xp_earned", 0) + xp
            if user_data and user_data.get("daily_reset_date") == today
            else xp
        )

        if user_data:
            await pool.execute_write(
                """
                UPDATE user_levels
                SET total_xp = total_xp + ?,
                    current_xp = current_xp + ?,
                    daily_xp_earned = ?,
                    daily_reset_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND guild_id = ?
                """,
                (xp, xp, new_daily, today, user_id, guild_id),
            )
        else:
            await pool.execute_write(
                """
                INSERT INTO user_levels (user_id, guild_id, current_xp, current_level, total_xp, messages_sent, daily_xp_earned, daily_reset_date)
                VALUES (?, ?, ?, 0, ?, 0, ?, ?)
                """,
                (user_id, guild_id, xp, xp, new_daily, today),
            )

        await pool.execute_write(
            """
            INSERT INTO xp_transactions (user_id, guild_id, channel_id, xp_awarded, reason, message_length, word_count, char_count, daily_cap_applied)
            VALUES (?, ?, 'ADMIN', ?, 'admin_add_xp', 0, 0, 0, 0)
            """,
            (user_id, guild_id, xp),
        )

        cache_key = f"{user_id}:{guild_id}"
        leveling._user_cache.pop(cache_key, None)
        leveling._user_cache_expiry.pop(cache_key, None)

        level_up_result = await leveling.check_level_up(user_id, guild_id)
        updated_data = await leveling.get_user_level_data(user_id, guild_id)

        total_xp = updated_data["total_xp"] if updated_data else xp
        current_level = (
            updated_data["current_level"]
            if updated_data
            else leveling.calculate_level_from_xp(total_xp)
        )

        return jsonify(
            {
                "success": True,
                "total_xp": total_xp,
                "current_level": current_level,
                "level_up": bool(level_up_result and level_up_result.get("level_up")),
                "new_level": level_up_result.get("new_level") if level_up_result else current_level,
                "old_level": level_up_result.get("old_level") if level_up_result else current_level,
            }
        )
    except Exception as e:
        logging.error(f"Error adding XP: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/admin/add_levels", methods=["POST"])
async def api_leveling_admin_add_levels():
    """Admin endpoint to add levels to a user."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")
        user_id = data.get("user_id")
        levels = int(data.get("levels", 0))
        admin_id = str(data.get("admin_id", ""))

        if not guild_id or not user_id:
            return jsonify({"error": "guild_id and user_id are required"}), 400
        if levels <= 0:
            return jsonify({"error": "levels must be positive"}), 400
        if not _is_authorized_admin(admin_id):
            return jsonify({"error": "unauthorized"}), 403

        class MockBot:
            pass

        leveling = get_leveling_system(MockBot())
        user_data = await leveling.get_user_level_data(user_id, guild_id)
        current_level = user_data["current_level"] if user_data else 0
        total_xp = user_data["total_xp"] if user_data else 0

        new_level = current_level + levels
        required_xp = leveling.get_xp_required_for_level(new_level)
        xp_to_add = required_xp - total_xp

        if xp_to_add > 0:
            pool = await get_leveling_pool()
            await pool.execute_write(
                "UPDATE user_levels SET total_xp = ?, current_xp = ? WHERE user_id = ? AND guild_id = ?",
                (
                    required_xp,
                    required_xp - leveling.get_xp_required_for_level(new_level),
                    user_id,
                    guild_id,
                ),
            )
            level_up_result = await leveling.check_level_up(user_id, guild_id)
        else:
            level_up_result = None

        return jsonify(
            {
                "success": True,
                "new_level": new_level,
                "total_xp": required_xp,
                "level_up": bool(level_up_result and level_up_result.get("level_up")),
            }
        )
    except Exception as e:
        logging.error(f"Error adding levels: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/admin/remove_levels", methods=["POST"])
async def api_leveling_admin_remove_levels():
    """Admin endpoint to remove levels from a user."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")
        user_id = data.get("user_id")
        levels = int(data.get("levels", 0))
        admin_id = str(data.get("admin_id", ""))

        if not guild_id or not user_id:
            return jsonify({"error": "guild_id and user_id are required"}), 400
        if levels <= 0:
            return jsonify({"error": "levels must be positive"}), 400
        if not _is_authorized_admin(admin_id):
            return jsonify({"error": "unauthorized"}), 403

        class MockBot:
            pass

        leveling = get_leveling_system(MockBot())
        user_data = await leveling.get_user_level_data(user_id, guild_id)
        if not user_data:
            return jsonify({"error": "User has no levels to remove"}), 400

        current_level = user_data["current_level"]
        new_level = max(0, current_level - levels)
        required_xp = leveling.get_xp_required_for_level(new_level)

        pool = await get_leveling_pool()
        await pool.execute_write(
            "UPDATE user_levels SET total_xp = ?, current_xp = 0, current_level = ? WHERE user_id = ? AND guild_id = ?",
            (required_xp, new_level, user_id, guild_id),
        )

        return jsonify({"success": True, "new_level": new_level, "total_xp": required_xp})
    except Exception as e:
        logging.error(f"Error removing levels: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/guilds")
async def api_leveling_guilds():
    """Get available guilds for leveling dashboard with resolved names."""
    try:
        if not state.bot_instance or not state.bot_instance.is_ready():
            return jsonify({"error": "Bot is not ready"}), 503

        # Get leveling user counts per guild for enrichment
        guild_counts = {}
        conn = await get_leveling_db_connection()
        async with conn.execute("""
            SELECT guild_id, COUNT(*) as user_count
            FROM user_levels
            GROUP BY guild_id
        """) as cursor:
            rows = await cursor.fetchall()
            guild_counts = {row[0]: row[1] for row in rows}
        await conn.close()

        guilds = []
        for guild in state.bot_instance.guilds:
            guild_id = str(guild.id)
            guilds.append({
                "id": guild_id,
                "name": guild.name,
                "user_count": guild_counts.get(guild_id, 0)
            })

        guilds.sort(key=lambda g: g["name"].lower())
        return jsonify(guilds)

    except Exception as e:
        logging.error(f"Error getting guilds: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/stats")
async def api_leveling_stats():
    """Get leveling system statistics."""
    try:
        guild_id = request.args.get("guild_id")

        conn = await get_leveling_db_connection()

        if guild_id:
            async with conn.execute("""
                SELECT
                    COUNT(*) as total_users,
                    AVG(current_level) as avg_level,
                    SUM(CASE WHEN DATE(last_xp_timestamp) = DATE('now') THEN daily_xp_earned ELSE 0 END) as xp_today,
                    COUNT(CASE WHEN DATE(last_xp_timestamp) = DATE('now') THEN 1 END) as active_today
                FROM user_levels
                WHERE guild_id = ?
            """, (guild_id,)) as cursor:
                result = await cursor.fetchone()
        else:
            async with conn.execute("""
                SELECT
                    COUNT(*) as total_users,
                    AVG(current_level) as avg_level,
                    SUM(CASE WHEN DATE(last_xp_timestamp) = DATE('now') THEN daily_xp_earned ELSE 0 END) as xp_today,
                    COUNT(CASE WHEN DATE(last_xp_timestamp) = DATE('now') THEN 1 END) as active_today
                FROM user_levels
            """) as cursor:
                result = await cursor.fetchone()

        await conn.close()

        if result:
            return jsonify({
                "total_users": result[0] or 0,
                "avg_level": round(result[1] or 0, 1),
                "xp_today": result[2] or 0,
                "active_users_today": result[3] or 0
            })
        else:
            return jsonify({
                "total_users": 0,
                "avg_level": 0,
                "xp_today": 0,
                "active_users_today": 0
            })

    except Exception as e:
        logging.error(f"Error getting leveling stats: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/message-templates", methods=["GET"])
async def api_message_templates_get():
    """Get guild message templates."""
    try:
        guild_id = request.args.get("guild_id")
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute("""
            SELECT id, template_type, template_name, message_content, embed_enabled,
                   embed_config, milestone_interval, min_level, max_level, enabled,
                   send_to_channel, send_as_dm, mention_user, priority, created_at, updated_at
            FROM level_up_message_templates
            WHERE guild_id = ?
            ORDER BY template_type, priority DESC, template_name
        """, (guild_id,)) as cursor:
            templates = await cursor.fetchall()

        await conn.close()

        template_list = []
        for template in templates:
            template_list.append({
                "id": template[0],
                "template_type": template[1],
                "template_name": template[2],
                "message_content": template[3],
                "embed_enabled": bool(template[4]),
                "embed_config": json.loads(template[5]) if template[5] else {},
                "milestone_interval": template[6],
                "min_level": template[7],
                "max_level": template[8],
                "enabled": bool(template[9]),
                "send_to_channel": bool(template[10]),
                "send_as_dm": bool(template[11]),
                "mention_user": bool(template[12]),
                "priority": template[13],
                "created_at": template[14],
                "updated_at": template[15]
            })

        return jsonify(template_list)

    except Exception as e:
        logging.error(f"Error getting message templates: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/message-templates", methods=["POST"])
async def api_message_templates_create():
    """Create a new message template."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")
        template_type = data.get("template_type")
        template_name = data.get("template_name")
        message_content = data.get("message_content")

        if not all([guild_id, template_type, template_name, message_content]):
            return jsonify({"error": "guild_id, template_type, template_name, and message_content are required"}), 400

        valid_types = ["default_levelup", "rank_promotion", "milestone_level", "first_level", "major_milestone"]
        if template_type not in valid_types:
            return jsonify({"error": f"Invalid template_type. Must be one of: {', '.join(valid_types)}"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute(
            "SELECT id FROM level_up_message_templates WHERE guild_id = ? AND template_type = ? AND template_name = ?",
            (guild_id, template_type, template_name)
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            await conn.close()
            return jsonify({"error": f"Template '{template_name}' already exists for {template_type}"}), 400

        await conn.execute("""
            INSERT INTO level_up_message_templates
            (guild_id, template_type, template_name, message_content, embed_enabled, embed_config,
             milestone_interval, min_level, max_level, enabled, send_to_channel, send_as_dm,
             mention_user, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            guild_id, template_type, template_name, message_content,
            data.get("embed_enabled", False),
            json.dumps(data.get("embed_config", {})),
            data.get("milestone_interval"),
            data.get("min_level"),
            data.get("max_level"),
            data.get("enabled", True),
            data.get("send_to_channel", True),
            data.get("send_as_dm", False),
            data.get("mention_user", True),
            data.get("priority", 0)
        ))

        await conn.commit()

        async with conn.execute("SELECT last_insert_rowid()") as cursor:
            template_id = (await cursor.fetchone())[0]

        await conn.close()

        return jsonify({
            "success": True,
            "template_id": template_id,
            "message": f"Template '{template_name}' created successfully"
        })

    except Exception as e:
        logging.error(f"Error creating message template: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/message-templates/<int:template_id>", methods=["PUT"])
async def api_message_templates_update(template_id):
    """Update a message template."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")

        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute(
            "SELECT id, template_name FROM level_up_message_templates WHERE id = ? AND guild_id = ?",
            (template_id, guild_id)
        ) as cursor:
            existing_template = await cursor.fetchone()

        if not existing_template:
            await conn.close()
            return jsonify({"error": "Template not found or access denied"}), 404

        valid_fields = [
            "template_type", "template_name", "message_content", "embed_enabled", "embed_config",
            "milestone_interval", "min_level", "max_level", "enabled", "send_to_channel",
            "send_as_dm", "mention_user", "priority"
        ]
        update_fields = []
        update_values = []

        for field in valid_fields:
            if field in data:
                if field == "embed_config":
                    update_fields.append(f"{field} = ?")
                    update_values.append(json.dumps(data[field]) if data[field] else "{}")
                else:
                    update_fields.append(f"{field} = ?")
                    update_values.append(data[field])

        if not update_fields:
            await conn.close()
            return jsonify({"error": "No valid fields to update"}), 400

        update_values.extend([template_id, guild_id])

        await conn.execute(f"""
            UPDATE level_up_message_templates
            SET {', '.join(update_fields)}
            WHERE id = ? AND guild_id = ?
        """, update_values)

        await conn.commit()
        await conn.close()

        return jsonify({
            "success": True,
            "message": "Template updated successfully"
        })

    except Exception as e:
        logging.error(f"Error updating message template: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/message-templates/<int:template_id>", methods=["DELETE"])
async def api_message_templates_delete(template_id):
    """Delete a message template."""
    try:
        guild_id = request.args.get("guild_id")
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute(
            "SELECT template_name FROM level_up_message_templates WHERE id = ? AND guild_id = ?",
            (template_id, guild_id)
        ) as cursor:
            existing_template = await cursor.fetchone()

        if not existing_template:
            await conn.close()
            return jsonify({"error": "Template not found or access denied"}), 404

        await conn.execute(
            "DELETE FROM level_up_message_templates WHERE id = ? AND guild_id = ?",
            (template_id, guild_id)
        )

        await conn.commit()
        await conn.close()

        return jsonify({
            "success": True,
            "message": f"Template '{existing_template[0]}' deleted successfully"
        })

    except Exception as e:
        logging.error(f"Error deleting message template: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/template-variables", methods=["GET"])
async def api_template_variables_get():
    """Get available template variables."""
    try:
        conn = await get_leveling_db_connection()

        async with conn.execute("""
            SELECT variable_name, description, example_value, variable_type, is_system_variable
            FROM template_variables
            ORDER BY is_system_variable DESC, variable_name
        """) as cursor:
            variables = await cursor.fetchall()

        await conn.close()

        variable_list = []
        for var in variables:
            variable_list.append({
                "variable_name": var[0],
                "description": var[1],
                "example_value": var[2],
                "variable_type": var[3],
                "is_system_variable": bool(var[4])
            })

        return jsonify(variable_list)

    except Exception as e:
        logging.error(f"Error getting template variables: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/message-templates/preview", methods=["POST"])
async def api_message_template_preview():
    """Preview a message template with sample data."""
    try:
        data = await request.get_json()
        message_content = data.get("message_content", "")
        guild_id = data.get("guild_id")

        if not message_content:
            return jsonify({"error": "message_content required"}), 400

        sample_data = {
            "{user}": "<@123456789012345678>",
            "{username}": "SampleUser",
            "{user_id}": "123456789012345678",
            "{level}": "15",
            "{old_level}": "14",
            "{xp}": "2,500",
            "{current_xp}": "120",
            "{xp_needed}": "380",
            "{rank}": "Veteran",
            "{old_rank}": "Member",
            "{guild}": "Sample Discord Server",
            "{guild_id}": "987654321098765432",
            "{channel}": "<#876543210987654321>",
            "{date}": datetime.now().strftime("%Y-%m-%d"),
            "{time}": datetime.now().strftime("%H:%M:%S"),
            "{total_members}": "150",
            "{server_rank}": "23",
            "{messages_sent}": "1,234",
            "{daily_xp}": "250",
            "{progress_bar}": "████████░░ 80%",
            "{congratulations}": "Well done!"
        }

        preview_content = message_content
        for variable, value in sample_data.items():
            preview_content = preview_content.replace(variable, str(value))

        return jsonify({
            "success": True,
            "preview_content": preview_content,
            "variables_used": [var for var in sample_data.keys() if var in message_content]
        })

    except Exception as e:
        logging.error(f"Error previewing message template: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/templates", methods=["GET"])
async def api_leveling_templates_get():
    """Get message templates (alias for message-templates)."""
    try:
        guild_id = request.args.get("guild_id")
        template_type = request.args.get("type", "default_levelup")

        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute("""
            SELECT id, template_type, template_name, message_content, embed_enabled,
                   embed_config, milestone_interval, min_level, max_level, enabled,
                   send_to_channel, send_as_dm, mention_user, priority, created_at, updated_at
            FROM level_up_message_templates
            WHERE guild_id = ? AND template_type = ?
            ORDER BY priority DESC, template_name
        """, (guild_id, template_type)) as cursor:
            templates = await cursor.fetchall()

        await conn.close()

        template_list = []
        for template in templates:
            template_list.append({
                "id": template[0],
                "type": template[1],
                "name": template[2],
                "content": template[3],
                "embed_enabled": bool(template[4]),
                "embed_config": json.loads(template[5]) if template[5] else {},
                "milestone_interval": template[6],
                "min_level": template[7],
                "max_level": template[8],
                "enabled": bool(template[9]),
                "send_to_channel": bool(template[10]),
                "send_as_dm": bool(template[11]),
                "mention_user": bool(template[12]),
                "priority": template[13],
                "created_at": template[14],
                "updated_at": template[15],
                "conditions": json.dumps({
                    "min_level": template[7],
                    "max_level": template[8]
                }) if template[7] or template[8] else ""
            })

        return jsonify(template_list)

    except Exception as e:
        logging.error(f"Error getting templates: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/templates", methods=["POST"])
async def api_leveling_templates_create():
    """Create message template (alias for message-templates)."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")
        template_type = data.get("type")
        template_name = data.get("name")
        message_content = data.get("content")

        if not all([guild_id, template_type, template_name, message_content]):
            return jsonify({"error": "guild_id, type, name, and content are required"}), 400

        valid_types = ["default_levelup", "rank_promotion", "milestone_level", "first_level", "major_milestone"]
        if template_type not in valid_types:
            return jsonify({"error": f"Invalid template type. Must be one of: {', '.join(valid_types)}"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute(
            "SELECT id FROM level_up_message_templates WHERE guild_id = ? AND template_type = ? AND template_name = ?",
            (guild_id, template_type, template_name)
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            await conn.close()
            return jsonify({"error": f"Template '{template_name}' already exists for {template_type}"}), 400

        conditions = data.get("conditions", "")
        min_level = None
        max_level = None

        if conditions:
            try:
                cond_data = json.loads(conditions)
                min_level = cond_data.get("min_level")
                max_level = cond_data.get("max_level")
            except (json.JSONDecodeError, TypeError):
                pass

        await conn.execute("""
            INSERT INTO level_up_message_templates
            (guild_id, template_type, template_name, message_content, embed_enabled, embed_config,
             milestone_interval, min_level, max_level, enabled, send_to_channel, send_as_dm,
             mention_user, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            guild_id, template_type, template_name, message_content,
            data.get("embed_enabled", False),
            json.dumps(data.get("embed_config", {})),
            data.get("milestone_interval"),
            min_level,
            max_level,
            data.get("enabled", True),
            data.get("send_to_channel", True),
            data.get("send_as_dm", False),
            data.get("mention_user", True),
            data.get("priority", 0)
        ))

        await conn.commit()

        async with conn.execute("SELECT last_insert_rowid()") as cursor:
            template_id = (await cursor.fetchone())[0]

        await conn.close()

        return jsonify({
            "success": True,
            "template_id": template_id,
            "message": f"Template '{template_name}' created successfully"
        })

    except Exception as e:
        logging.error(f"Error creating template: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/templates/<int:template_id>", methods=["GET"])
async def api_leveling_templates_get_single(template_id):
    """Get single template by ID."""
    try:
        guild_id = request.args.get("guild_id")
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute("""
            SELECT id, template_type, template_name, message_content, embed_enabled,
                   embed_config, milestone_interval, min_level, max_level, enabled,
                   send_to_channel, send_as_dm, mention_user, priority, created_at, updated_at
            FROM level_up_message_templates
            WHERE id = ? AND guild_id = ?
        """, (template_id, guild_id)) as cursor:
            template = await cursor.fetchone()

        await conn.close()

        if template:
            return jsonify({
                "id": template[0],
                "type": template[1],
                "name": template[2],
                "content": template[3],
                "embed_enabled": bool(template[4]),
                "embed_config": json.loads(template[5]) if template[5] else {},
                "milestone_interval": template[6],
                "min_level": template[7],
                "max_level": template[8],
                "enabled": bool(template[9]),
                "send_to_channel": bool(template[10]),
                "send_as_dm": bool(template[11]),
                "mention_user": bool(template[12]),
                "priority": template[13],
                "created_at": template[14],
                "updated_at": template[15],
                "conditions": json.dumps({
                    "min_level": template[7],
                    "max_level": template[8]
                }) if template[7] or template[8] else ""
            })
        else:
            return jsonify({"error": "Template not found"}), 404

    except Exception as e:
        logging.error(f"Error getting template: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/templates/<int:template_id>", methods=["PUT"])
async def api_leveling_templates_update(template_id):
    """Update template (alias for message-templates)."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")

        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute(
            "SELECT id, template_name FROM level_up_message_templates WHERE id = ? AND guild_id = ?",
            (template_id, guild_id)
        ) as cursor:
            existing_template = await cursor.fetchone()

        if not existing_template:
            await conn.close()
            return jsonify({"error": "Template not found or access denied"}), 404

        conditions = data.get("conditions", "")
        min_level = None
        max_level = None

        if conditions:
            try:
                cond_data = json.loads(conditions)
                min_level = cond_data.get("min_level")
                max_level = cond_data.get("max_level")
            except (json.JSONDecodeError, TypeError):
                pass

        field_mapping = {
            "type": "template_type",
            "name": "template_name",
            "content": "message_content",
            "embed_enabled": "embed_enabled",
            "embed_config": "embed_config",
            "milestone_interval": "milestone_interval",
            "enabled": "enabled",
            "send_to_channel": "send_to_channel",
            "send_as_dm": "send_as_dm",
            "mention_user": "mention_user",
            "priority": "priority"
        }

        update_fields = []
        update_values = []

        for frontend_field, db_field in field_mapping.items():
            if frontend_field in data:
                if frontend_field == "embed_config":
                    update_fields.append(f"{db_field} = ?")
                    update_values.append(json.dumps(data[frontend_field]) if data[frontend_field] else "{}")
                else:
                    update_fields.append(f"{db_field} = ?")
                    update_values.append(data[frontend_field])

        if "conditions" in data:
            if min_level is not None:
                update_fields.append("min_level = ?")
                update_values.append(min_level)
            if max_level is not None:
                update_fields.append("max_level = ?")
                update_values.append(max_level)

        if not update_fields:
            await conn.close()
            return jsonify({"error": "No valid fields to update"}), 400

        update_values.extend([template_id, guild_id])

        await conn.execute(f"""
            UPDATE level_up_message_templates
            SET {', '.join(update_fields)}
            WHERE id = ? AND guild_id = ?
        """, update_values)

        await conn.commit()
        await conn.close()

        return jsonify({
            "success": True,
            "message": "Template updated successfully"
        })

    except Exception as e:
        logging.error(f"Error updating template: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/templates/<int:template_id>", methods=["DELETE"])
async def api_leveling_templates_delete(template_id):
    """Delete template (alias for message-templates)."""
    try:
        guild_id = request.args.get("guild_id")
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute(
            "SELECT template_name FROM level_up_message_templates WHERE id = ? AND guild_id = ?",
            (template_id, guild_id)
        ) as cursor:
            existing_template = await cursor.fetchone()

        if not existing_template:
            await conn.close()
            return jsonify({"error": "Template not found or access denied"}), 404

        await conn.execute(
            "DELETE FROM level_up_message_templates WHERE id = ? AND guild_id = ?",
            (template_id, guild_id)
        )

        await conn.commit()
        await conn.close()

        return jsonify({
            "success": True,
            "message": f"Template '{existing_template[0]}' deleted successfully"
        })

    except Exception as e:
        logging.error(f"Error deleting template: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/templates/<int:template_id>/preview", methods=["GET"])
async def api_leveling_templates_preview(template_id):
    """Preview template with sample data."""
    try:
        guild_id = request.args.get("guild_id")
        if not guild_id:
            return jsonify({"error": "guild_id parameter required"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute(
            "SELECT message_content FROM level_up_message_templates WHERE id = ? AND guild_id = ?",
            (template_id, guild_id)
        ) as cursor:
            template = await cursor.fetchone()

        await conn.close()

        if not template:
            return jsonify({"error": "Template not found"}), 404

        sample_data = {
            "{user}": "<@123456789012345678>",
            "{username}": "SampleUser",
            "{user_id}": "123456789012345678",
            "{level}": "15",
            "{previous_level}": "14",
            "{xp}": "2,500",
            "{current_xp}": "120",
            "{xp_needed}": "380",
            "{rank}": "Veteran",
            "{previous_rank}": "Member",
            "{guild}": "Sample Discord Server",
            "{guild_id}": "987654321098765432",
            "{channel}": "<#876543210987654321>",
            "{date}": datetime.now().strftime("%Y-%m-%d"),
            "{time}": datetime.now().strftime("%H:%M:%S"),
            "{total_members}": "150",
            "{leaderboard_position}": "23",
            "{messages_sent}": "1,234",
            "{daily_xp}": "250",
            "{progress_bar}": "████████░░ 80%",
            "{congratulations}": "Well done!",
            "{range}": "Journeyman",
            "{tier}": "Journeyman"
        }

        preview_content = template[0]
        for variable, value in sample_data.items():
            preview_content = preview_content.replace(variable, str(value))

        return jsonify({
            "success": True,
            "preview": preview_content
        })

    except Exception as e:
        logging.error(f"Error previewing template: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/ranges/guild/<guild_id>", methods=["GET"])
async def api_get_guild_ranges(guild_id):
    """Get all level ranges for a guild."""
    try:
        conn = await get_leveling_db_connection()

        async with conn.execute("""
            SELECT id, min_level, max_level, range_name, description, created_at
            FROM level_range_names
            WHERE guild_id = ?
            ORDER BY min_level
        """, (guild_id,)) as cursor:
            ranges = await cursor.fetchall()

        await conn.close()

        range_list = []
        for range_data in ranges:
            range_list.append({
                "id": range_data[0],
                "min_level": range_data[1],
                "max_level": range_data[2],
                "range_name": range_data[3],
                "description": range_data[4],
                "created_at": range_data[5]
            })

        return jsonify({"ranges": range_list})

    except Exception as e:
        logging.error(f"Error getting guild ranges: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/ranges", methods=["POST"])
async def api_create_level_range():
    """Create a new level range."""
    try:
        data = await request.get_json()
        guild_id = data.get("guild_id")
        min_level = data.get("min_level")
        max_level = data.get("max_level")
        range_name = data.get("range_name")
        description = data.get("description", "")

        if not all([guild_id, min_level is not None, max_level is not None, range_name]):
            return jsonify({"error": "Missing required fields"}), 400

        try:
            min_level = int(min_level)
            max_level = int(max_level)

            if min_level < 1 or max_level < min_level:
                return jsonify({"error": "Invalid level range"}), 400

        except ValueError:
            return jsonify({"error": "Invalid level values"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute("""
            SELECT COUNT(*) FROM level_range_names
            WHERE guild_id = ? AND (
                (? >= min_level AND ? <= max_level) OR
                (? >= min_level AND ? <= max_level) OR
                (min_level >= ? AND min_level <= ?) OR
                (max_level >= ? AND max_level <= ?)
            )
        """, (guild_id, min_level, min_level, max_level, max_level,
              min_level, max_level, min_level, max_level)) as cursor:
            overlap_count = (await cursor.fetchone())[0]

        if overlap_count > 0:
            await conn.close()
            return jsonify({"error": "Range overlaps with existing ranges"}), 400

        await conn.execute("""
            INSERT INTO level_range_names
            (guild_id, min_level, max_level, range_name, description)
            VALUES (?, ?, ?, ?, ?)
        """, (guild_id, min_level, max_level, range_name, description))

        await conn.commit()
        await conn.close()

        return jsonify({"message": "Range added successfully"})

    except Exception as e:
        logging.error(f"Error creating level range: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/ranges/<int:range_id>", methods=["PUT"])
async def api_update_level_range(range_id):
    """Update an existing level range."""
    try:
        data = await request.get_json()
        min_level = data.get("min_level")
        max_level = data.get("max_level")
        range_name = data.get("range_name")
        description = data.get("description", "")

        if not all([min_level is not None, max_level is not None, range_name]):
            return jsonify({"error": "Missing required fields"}), 400

        try:
            min_level = int(min_level)
            max_level = int(max_level)

            if min_level < 1 or max_level < min_level:
                return jsonify({"error": "Invalid level range"}), 400

        except ValueError:
            return jsonify({"error": "Invalid level values"}), 400

        conn = await get_leveling_db_connection()

        async with conn.execute(
            "SELECT guild_id FROM level_range_names WHERE id = ?",
            (range_id,)
        ) as cursor:
            result = await cursor.fetchone()

        if not result:
            await conn.close()
            return jsonify({"error": "Range not found"}), 404

        guild_id = result[0]

        async with conn.execute("""
            SELECT COUNT(*) FROM level_range_names
            WHERE guild_id = ? AND id != ? AND (
                (? >= min_level AND ? <= max_level) OR
                (? >= min_level AND ? <= max_level) OR
                (min_level >= ? AND min_level <= ?) OR
                (max_level >= ? AND max_level <= ?)
            )
        """, (guild_id, range_id, min_level, min_level, max_level, max_level,
              min_level, max_level, min_level, max_level)) as cursor:
            overlap_count = (await cursor.fetchone())[0]

        if overlap_count > 0:
            await conn.close()
            return jsonify({"error": "Range overlaps with existing ranges"}), 400

        await conn.execute("""
            UPDATE level_range_names
            SET min_level = ?, max_level = ?, range_name = ?, description = ?
            WHERE id = ?
        """, (min_level, max_level, range_name, description, range_id))

        await conn.commit()
        await conn.close()

        return jsonify({"message": "Range updated successfully"})

    except Exception as e:
        logging.error(f"Error updating level range: {e}")
        return jsonify({"error": str(e)}), 500


@leveling_bp.route("/api/leveling/ranges/<int:range_id>", methods=["DELETE"])
async def api_delete_level_range(range_id):
    """Delete a level range."""
    try:
        conn = await get_leveling_db_connection()

        async with conn.execute(
            "SELECT id FROM level_range_names WHERE id = ?",
            (range_id,)
        ) as cursor:
            result = await cursor.fetchone()

        if not result:
            await conn.close()
            return jsonify({"error": "Range not found"}), 404

        await conn.execute("DELETE FROM level_range_names WHERE id = ?", (range_id,))

        await conn.commit()
        await conn.close()

        return jsonify({"message": "Range deleted successfully"})

    except Exception as e:
        logging.error(f"Error deleting level range: {e}")
        return jsonify({"error": str(e)}), 500
