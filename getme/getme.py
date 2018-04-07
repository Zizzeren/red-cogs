import discord
from discord.ext import commands

msg = "If you have any suggestions, or want me for your own server, please come join my discord server! https://discord.gg/RkxpjK3"

class Getme:
    """Want me? Get me!"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def getme(self, ctx):
        """Want me? Get me!"""
        await self.bot.say(msg)

def setup(bot):
    n = Getme(bot)
    bot.add_cog(n)
