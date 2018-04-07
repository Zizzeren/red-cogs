import discord
from discord.ext import commands

class Avatar:
    """Gets a user's avatar"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def avatar(self, ctx, user : discord.Member = None):
        """Gets a user's avatar"""
        if user is None:
            user = ctx.message.author

        await self.bot.say("{}'s avatar: {}".format(user.display_name,
            user.avatar_url))

def setup(bot):
    n = Avatar(bot)
    bot.add_cog(n)
