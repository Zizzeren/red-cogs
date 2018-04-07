import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from random import choice
import os
from PIL import Image
import aiohttp
import glob

class Loss:
    """Is this loss?"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True)
    async def loss(self, ctx):
        if ctx.invoked_subcommand is not None:
            return
        which = None
        if which is not None:
            await self.bot.send_typing(ctx.message.channel)
            filename = glob.glob("data/loss/images/{}.*".format(which))
            if len(filename) != 0:
                await self.bot.send_file(ctx.message.channel, filename[0])
                return
        (_,_,filenames) = os.walk("data/loss/images").__next__()
        await self.bot.send_typing(ctx.message.channel)
        await self.bot.send_file(ctx.message.channel, 
                "data/loss/images/" + choice(filenames))

    @loss.command(pass_context=True)
    async def add(self, ctx, url: str = None):
        """Add an image."""
        img_url = url
        if url is None:
            if len(ctx.message.attachments) > 0:
                if "url" in ctx.message.attachments[0]:
                    img_url = ctx.message.attachments[0]["url"]

        if img_url is None:
            await self.bot.say("Please give me a url.")
            return

        try:
            async with aiohttp.get(img_url) as r:
                data = await r.content.read()
            _,_,filenames = os.walk("data/loss/images").__next__()
            file_count = len(filenames)
            temp = "data/loss/images/{}".format(file_count)
            with open(temp, 'wb') as f:
                f.write(data)
            img = Image.open(open(temp, 'rb'))
            fmt = img.format.lower()
            os.rename(temp, temp + "." + fmt)
            await self.bot.say("Added image.")
        except Exception as e:
            await self.bot.say("Exception occurred of type {}".format(
                type(e).__name__))
            print(e)

def check_folders():
    if not os.path.exists("data/loss/images"):
        print("Creating data/loss/images folder....")
        os.makedirs("data/loss/images")

def setup(bot):
    check_folders()
    n = Loss(bot)
    bot.add_cog(n)
