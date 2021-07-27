from discord.ext import commands
from discord import Embed, Member
from random import choices
from string import ascii_uppercase, ascii_lowercase, digits
from objects import glob

from constants.privs import Privileges
from constants.mods import Mods
from constants.modes import lbModes

valid_args = ['-rx', '-ap', '-m']

class asahiBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def link(self, ctx) -> None:
        if (user := await glob.players.get(discord=ctx.author.id, sql=True)):
            return await ctx.send(f'You already have your Discord account linked to a user called {user.name}!')

        # generate random validation code for the user
        code = ''.join(choices(ascii_uppercase + ascii_lowercase + digits, k=16))
        glob.codes[code] = ctx.author.id

        try:
            await ctx.send('Linking initiated! Please check your DMs for further instructions.')
            return await ctx.author.send(f'Please enter this command to the ingame bot ({glob.bot.name}) in order to link your account:\n```{glob.config.prefix}link {code}```')
        except Exception:
            return await ctx.send('There was an error when trying to DM you! Please ensure I am able to DM you and try again.')

    @commands.command()
    async def profile(self, ctx) -> None: # the way this is handled sucks ass and i'll clean this up later
        args = (ctx.message.content.strip(f'{glob.config.bot_prefix}profile')).split(' ')
        u = None

        if args[0] not in valid_args:
            u = args[0]

        del args[0]

        if not u:
            user = await glob.players.get(discord=ctx.author.id, sql=True)
        elif (m := ctx.message.mentions):
            user = await glob.players.get(discord=m[0].id, sql=True)
        else:
            user = await glob.players.get(name=u, sql=True)

        if not user:
            return await ctx.send("Couldn't find this user!")

        if user.priv & Privileges.Disallowed:
            return await ctx.send('This user is banned/restricted!')

        m = 0

        if '-m' in args:
            m = int(args[args.index('-m') + 1])

        if '-rx' in args: rx = Mods.RELAX
        elif '-ap' in args: rx = Mods.AUTOPILOT
        else: rx = Mods.NOMOD

        mode = lbModes(m, rx)
        stats = user.stats[mode.value]

        embed = Embed(title='')
        embed.set_author(name=f'{mode!r} profile for {user.full_name} - {stats.pp}pp (#{stats.rank} // {user.country_iso.upper()}#{stats.country_rank})', url=f'https://{glob.config.domain}/u/{user.id}', icon_url=f'https://countryflags.io/{user.country_iso}/flat/64.png')
        embed.set_thumbnail(url=f'https://a.{glob.config.domain}/{user.id}')

        # TODO: finish embed lol
        return await ctx.send(embed=embed)

def setup(bot) -> None:
    bot.add_cog(asahiBot(bot))
