from discord.ext import commands
from random import choices
from string import ascii_uppercase, ascii_lowercase, digits
from objects import glob

class asahiBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    def link(self, ctx, username):
        if (user := await glob.players.get(discord=ctx.author.id, sql=True)):
            return await ctx.send(f'You already have your Discord account linked to a user called {user.name}!')

        if (user := await glob.players.get(name=username, sql=True)):
            if user.discord:
                return await ctx.send('Another Discord account is already linked to this user!')

            if glob.codes.get(user):
                return await ctx.send('You have already initiated the linking process! Please check our DMs to finalise it.')

            # generate random validation code for the user
            glob.codes[user] = {'code': ''.join(random.choices(ascii_uppercase + ascii_lowercase + string.digits, k=16)), 'discord': ctx.author.id}

            try:
                await ctx.send('Linking initiated! Please check your DMs for further instructions.')
                return await ctx.author.send(f'Please enter this command to the ingame bot ({glob.bot.name}) in order to link your account:\n`{glob.config.prefix}link {glob.codes[user]}')
            except Exception:
                return await ctx.send('There was an error when trying to DM you! Please ensure I am able to DM you and try again.')

        return await ctx.send('Couldn\'t find this user!')

def setup(bot):
    bot.add_cog(asahiBot(bot))