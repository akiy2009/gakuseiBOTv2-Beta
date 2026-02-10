import time
import uuid
import discord
from discord.ext import commands, tasks


class TimerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.timers: dict[str, dict] = {}
        self.timer_checker.start()

    def cog_unload(self):
        self.timer_checker.cancel()

    # =========================
    # タイマー監視タスク
    # =========================
    @tasks.loop(seconds=30)
    async def timer_checker(self):
        now = time.time()
        remove_ids = []

        for timer_id, data in self.timers.items():
            if now >= data["trigger_time"]:
                channel = self.bot.get_channel(data["channel_id"])
                if channel:
                    await channel.send(
                        f"<@{data['user_id']}> ⏰ **{data['message']}**"
                    )
                remove_ids.append(timer_id)

        for tid in remove_ids:
            del self.timers[tid]

    @timer_checker.before_loop
    async def before_timer_checker(self):
        await self.bot.wait_until_ready()

    # =========================
    # /timer
    # =========================
    @discord.app_commands.command(
        name="timer",
        description="指定時間後に通知する"
    )
    async def timer(
        self,
        interaction: discord.Interaction,
        minutes: int,
        message: str
    ):
        if minutes <= 0:
            await interaction.response.send_message(
                "時間は1分以上にしてね",
                ephemeral=True
            )
            return

        trigger_time = time.time() + minutes * 60
        timer_id = str(uuid.uuid4())[:8]

        self.timers[timer_id] = {
            "user_id": interaction.user.id,
            "channel_id": interaction.channel.id,
            "trigger_time": trigger_time,
            "message": message
        }

        embed = discord.Embed(
            title="タイマーセット完了",
            color=discord.Color.green()
        )
        embed.add_field(name="時間", value=f"{minutes} 分後", inline=False)
        embed.add_field(name="メッセージ", value=message, inline=False)
        embed.set_footer(text=f"ID: {timer_id}")

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =========================
    # /timer_list
    # =========================
    @discord.app_commands.command(
        name="timer_list",
        description="自分のタイマー一覧を見る"
    )
    async def timer_list(self, interaction: discord.Interaction):
        now = time.time()
        lines = []

        for tid, data in self.timers.items():
            if data["user_id"] == interaction.user.id:
                remaining = max(
                    0, int((data["trigger_time"] - now) // 60)
                )
                lines.append(f"`{tid}`：残り {remaining} 分")

        if not lines:
            await interaction.response.send_message(
                "タイマーは登録されてないよ",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="あなたのタイマー一覧",
            description="\n".join(lines),
            color=discord.Color.blue()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =========================
    # /timer_cancel
    # =========================
    @discord.app_commands.command(
        name="timer_cancel",
        description="タイマーを解除する"
    )
    async def timer_cancel(
        self,
        interaction: discord.Interaction,
        timer_id: str
    ):
        data = self.timers.get(timer_id)

        if not data:
            await interaction.response.send_message(
                "そのIDのタイマーは存在しないよ",
                ephemeral=True
            )
            return

        if data["user_id"] != interaction.user.id:
            await interaction.response.send_message(
                "自分のタイマーしか解除できないよ",
                ephemeral=True
            )
            return

        del self.timers[timer_id]

        await interaction.response.send_message(
            "タイマーを解除したよ",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(TimerCog(bot))