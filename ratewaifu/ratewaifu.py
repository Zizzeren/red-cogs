import discord
from discord.ext import commands
import random
import hashlib

special_cases = {
        "scbot": 11,
        "<@294972852837548034>": 11,
        "mee6": 0,
        "<@159985870458322944>": 0,
        "zizzeren": 10,
        "<@100376596296249344>": 10,
        "sebs": 9,
        "<@154812768707543040>": 9,
        "anime": 10,
        "sc": 10,
        "steam controller": 10,
        "turbo touch": 9,
        "turbotouch360": 9,
        "tt360": 9,
        "<@295080429420281856>": 9,
        }

class Ratewaifu:
    """Rates how shit your waifu is."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ratewaifu(self, *waifu : str):
        """Rates how shit your waifu is.

        This is 100% accurate."""
        
#Used to be rand((waifu : discord.Member).member.id)
        
        waifu = " ".join(waifu)
        if waifu.lower() not in special_cases:
            rand = hash(waifu.lower()) % 10 + 1
            await self.bot.say("I rate {} **{}/10**".format(waifu, str(rand)))
        else:
            await self.bot.say("I rate {} **{}/10**".format(
                waifu, special_cases[waifu.lower()]))

def setup(bot):
    bot.add_cog(Ratewaifu(bot))
