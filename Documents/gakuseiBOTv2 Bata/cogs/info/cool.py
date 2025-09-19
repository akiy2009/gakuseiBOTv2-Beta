# cooldown_manager.py

import time
from collections import defaultdict

class ServerCooldownManager:
    def __init__(self, limit=10, interval=10, cooldown_time=60):
        self.call_counts = defaultdict(list)  # {guild_id: [timestamp1, timestamp2, ...]}
        self.cooldowns = {}  # {guild_id: cooldown_end_time}
        self.limit = limit
        self.interval = interval  # 秒
        self.cooldown_time = cooldown_time  # 秒

    def is_under_cooldown(self, guild_id: int) -> bool:
        now = time.time()
        if guild_id in self.cooldowns and self.cooldowns[guild_id] > now:
            return True
        return False

    def record_call(self, guild_id: int):
        now = time.time()
        self.call_counts[guild_id] = [t for t in self.call_counts[guild_id] if now - t < self.interval]
        self.call_counts[guild_id].append(now)

        if len(self.call_counts[guild_id]) >= self.limit:
            self.cooldowns[guild_id] = now + self.cooldown_time
            self.call_counts[guild_id].clear()