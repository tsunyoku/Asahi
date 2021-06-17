from discord.ext import commands, tasks
from discord import Status, ActivityType, Activity
from cmyui import log, Ansi
from random import choice

from objects import glob

class asahiBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @tasks.loop(minutes=1)
    async def set_status(self):
        statuses = [
            {'type': ActivityType.watching, 'message': f'over {len(glob.players) - 1} online user(s)'},
            {'type': ActivityType.playing, 'message': "with Asahi's code"}
        ]

        status = choice(statuses)
        activity = Activity(type=status['type'], name=status['message'])

        await self.bot.change_presence(status=Status.dnd, activity=activity)

    @commands.Cog.listener()
    async def on_ready(self):
        if glob.config.debug:
            log('==== Asahi Discord bot started ====', Ansi.GREEN)
        
        await self.set_status.start()

def setup(bot):
    bot.add_cog(asahiBot(bot))