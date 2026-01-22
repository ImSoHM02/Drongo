from .broadcast import request_immediate_broadcast
from .stats_service import real_time_stats


class DashboardAPI:
    """API class for bot integration."""

    @staticmethod
    def update_stat(key: str, value):
        """Update a statistic from the bot."""
        real_time_stats.update_stat(key, value)

    @staticmethod
    def log_message(author: str, guild: str, channel: str):
        """Log a message from the bot."""
        real_time_stats.add_message_log(str(author), str(guild), str(channel))
        request_immediate_broadcast()

    @staticmethod
    def log_event(event: str, event_type: str = "info"):
        """Log an event from the bot."""
        real_time_stats.add_event_log(str(event), event_type)

    @staticmethod
    def set_status(status: str):
        """Set bot status."""
        real_time_stats.set_status(status)

    @staticmethod
    def increment_command_count():
        """Increment command counter."""
        real_time_stats.stats["commands_executed"] += 1
        real_time_stats.add_event_log("Command executed", "command")


dashboard_api = DashboardAPI()
