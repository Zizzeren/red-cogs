import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
import os
import logging

class Unban:
    """Add code here"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def unban(self, ctx, userid : int):
        """Unbans a member."""
        try:
            user = await self.bot.get_user_info(userid)
            await self.bot.unban(ctx.message.server, user)
            await self.bot.say("Unbanned {}.".format(user.mention))
            logger.info("{}({}) unbanned {}"
                    "".format(ctx.message.author.name, 
                              ctx.message.author.id, 
                              userid))
        except discord.errors.HTTPException:
            await self.bot.say("Unban failed.")
        except discord.errors.Forbidden:
            await self.bot.say("I'm not allowed to do that.")

def check_folders():
    folders = ("data", "data/mod/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)

def setup(bot):
    global logger
    check_folders()
    logger = logging.getLogger("mod")
    if logger.level == 0:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename='data/mod/mod.log', encoding='utf-8', mode='a')
        handler.setFormatter(
            logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    n = Unban(bot)
    bot.add_cog(n)
