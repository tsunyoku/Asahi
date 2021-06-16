from discord.ext import commands
from discord import Status, ActivityType, Activity
from cmyui import log, Ansi

from objects import glob

class asahiBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log('==== Asahi Discord bot started ====', Ansi.GREEN)
        if (len(glob.players) - 1) > 0:
            activity = Activity(type=ActivityType.watching, name=f'over {len(glob.players) - 1} online user(s)')
        else:
            total_users = await glob.db.fetchval('SELECT COUNT(*) FROM users')
            activity = Activity(type=ActivityType.watching, name=f'over {total_users} total users')

        await self.bot.change_presence(status=Status.dnd, activity=activity)

def setup(bot):
    bot.add_cog(asahiBot(bot))