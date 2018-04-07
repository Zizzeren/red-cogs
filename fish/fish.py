import discord
from discord.ext import commands
import random

chance = 10000
fail_msg = "You caught nothing, don't try again, you'll never be great. You suck."
fishes = [
"arowana",
"twinfish",
"killifish",
"carp",
"bloat fish",
"koi carp",
"fur carp",
"freshwater ray",
"arapaima",
"sardine",
"beetle fish",
"water flea",
"coelacanth",
"blowfish",
"swordfish",
"mackerel",
"horseshoe crab",
"starfish",
"bream",
"basking shark"
]

class Fish:
    """fish"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def fish(self):
        """ fish """
        msg = "Congrats, you caught a {}".format(\
                random.choice(fishes)) \
                if random.randint(0, (chance - 1)) == 0\
                else fail_msg

        await self.bot.say(msg)

def setup(bot):
    n = Fish(bot)
    bot.add_cog(n)
