# modules/stats_display.py

from rich.live import Live
from rich.table import Table
from rich.text import Text
import threading
import time
from collections import deque

class StatsDisplay:
    def __init__(self, console):
        self.console = console
        self.stats = {
            "Messages Processed": 0,
            "Commands Executed": 0,
            "Active Users": 0,
            "Uptime": "0:00:00",
            "Status": "Disconnected"
        }
        self.start_time = None
        self.live = Live(console=self.console, refresh_per_second=4)
        self.running = False
        self.recent_messages = deque(maxlen=5)
        self.recent_events = deque(maxlen=5)

    def generate_table(self):
        table = Table(title="Bot Stats")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        for key, value in self.stats.items():
            table.add_row(key, str(value))
        
        table.add_row("Recent Messages", "")
        for msg in self.recent_messages:
            table.add_row("", msg)
        
        table.add_row("Recent Events", "")
        for event in self.recent_events:
            table.add_row("", event)
        
        return table

    def update_stats(self, key, value):
        self.stats[key] = value

    def log_message(self, author, guild, channel):
        message = Text(f"{author} in {guild}/{channel}", style="bold green")
        self.recent_messages.appendleft(str(message))

    def log_event(self, event):
        self.recent_events.appendleft(str(event))

    def set_status(self, status):
        self.update_stats("Status", status)
        self.log_event(Text(f"Bot {status}", style="bold yellow"))
        if status == "Connected":
            self.start_time = time.time()
        elif status == "Disconnected":
            self.start_time = None

    def run(self):
        self.running = True
        with self.live:
            while self.running:
                if self.start_time:
                    self.stats["Uptime"] = time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time))
                else:
                    self.stats["Uptime"] = "00:00:00"
                self.live.update(self.generate_table())
                time.sleep(0.25)

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()