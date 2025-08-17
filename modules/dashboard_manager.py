from web.dashboard_server import dashboard_api

class DashboardManager:
    def __init__(self, bot):
        self.bot = bot
        self.api = dashboard_api

    def update_stats(self, key, value):
        # Map old keys to new keys if necessary
        stat_map = {
            "Messages Processed": "messages_processed",
            "Commands Executed": "commands_executed",
        }
        api_key = stat_map.get(key, key.lower().replace(' ', '_'))
        self.api.update_stat(api_key, value)

    def log_message(self, author, guild, channel):
        self.api.log_message(str(author), str(guild), str(channel))

    def log_event(self, event):
        self.api.log_event(str(event))

    def set_status(self, status):
        self.api.set_status(status)
    
    def increment_command_count(self):
        """Increment command counter."""
        self.api.increment_command_count()

    def start(self):
        self.log_event("Dashboard manager started.")

    def stop(self):
        self.log_event("Dashboard manager stopped.")