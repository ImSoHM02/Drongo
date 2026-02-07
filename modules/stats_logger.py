class StatsLogger:
    def __init__(self, dashboard_manager):
        self.dashboard_manager = dashboard_manager

    def info(self, msg):
        self.dashboard_manager.log_event(f"INFO: {msg}")

    def warning(self, msg):
        self.dashboard_manager.log_event(f"WARNING: {msg}")

    def error(self, msg):
        self.dashboard_manager.log_event(f"ERROR: {msg}")
