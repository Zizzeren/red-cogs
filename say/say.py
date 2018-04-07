import discord
import datetime
from discord.ext import commands
from __main__ import send_cmd_help
from cogs.utils import checks
import time
from random import randint

class XcomMessage(discord.Message):
    def __init__(self, *args, **kwargs):
        super(XcomMessage, self).__init__(*args, **kwargs)

class say:
    """Get your bot to say a message in a specified channel"""
    def __init__(self, bot):
        self.bot = bot

    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True)
    async def say(self, ctx, ch : discord.Channel = None, *text):
        """Bot says a message.
        
        say  [channel mention] [message] - Bot says a message in the specified channel
        NOTE: You must mention a channel even if that's your current channel"""
        if ch is None:
            await send_cmd_help(ctx)
            return
        this_server = ctx.message.server
        that_server = ch.server
        if this_server is not that_server:
            await self.bot.say("I can't let you send cross-server messages, sorry.")
            return

        message = " ".join(text)
        
        if ch is None:
            await send_cmd_help(ctx)
        else:
            await self.bot.send_message(ch, message)

    @commands.command(pass_context=True)
    async def xcom(self, ctx, ch : discord.Channel = None, *command):
        """Bot executes a command in another channel."""
        # Thanks to https://github.com/tekulvw/Squid-Plugins/tree/master/scheduler
        server = ctx.message.server
        if ch is None:
            await send_cmd_help(ctx)
            return
        if server != ch.server:
            await self.bot.say("I can't let you execute cross-server commands, sorry.")
            return

        if isinstance(ctx.message, XcomMessage):
            await self.bot.say(
                "I can't allow you to run xcom messages through xcom, sorry.")
            return

        prefix = self.bot.settings.get_prefixes(server)[0]
        data = {}
        data['timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime())
        data['id'] = randint(10**(17), (10**18)-1)
        data['content'] = prefix + " ".join(command)
        data['channel'] = ch
        data['author'] = {'id': ctx.message.author.id}
        data['nonce'] = randint(-2**32, (2**32)-1)
        data['channel_id'] = ch.id
        data['reactions'] = []
        #fake_message = discord.Message(**data)
        fake_message = XcomMessage(**data)

        self.bot.dispatch('message', fake_message)

def setup(bot):
    n = say(bot)
    bot.add_cog(n)

