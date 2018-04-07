import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from PIL import Image
from random import randint
import aiohttp

class NeedsMoreJpeg:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def needsmorejpeg(self, ctx, *args):
        """Do stuff"""
        if len(ctx.message.attachments) > 0:
            url = ctx.message.attachments[0]["url"]
        else:
            url = " ".join(args)

        try:
            async with aiohttp.get(url) as r:
                data = await r.content.read()
            filename = '/tmp/{}.jpeg'.format(randint(0,1000))
            with open(filename, 'wb') as f:
                f.write(data)
            img = Image.open(open(filename, 'rb'))
            img.save(filename, quality=1, optimize=True)
            await self.bot.send_file(ctx.message.channel, filename)
        except Exception as e:
            await self.bot.say("Doesn't look like an image to me.")

def setup(bot):
    n = NeedsMoreJpeg(bot)
    bot.add_cog(n)
