import discord
from discord.ext import commands

class Bigmoji:
    """Embiggen an emoji"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def bigmoji(self, ctx, emoji):
        """Embiggen an emoji"""
        if emoji is None:
            return
        if ':' not in str(emoji):
            await self.bot.say("That's not a custom emoji.")
            return
        id = str(emoji).split(':')[-1][:-1]
        await self.bot.say(
                "https://cdn.discordapp.com/emojis/{}.png"\
                        .format(id))

def setup(bot):
    n = Bigmoji(bot)
    bot.add_cog(n)
