import discord
from discord.ext import commands
from .utils import checks
import logging
import asyncio

class CleanupCollapse:
    """Delete messages between two specified messages"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("mod")

    async def mass_purge(self, messages):
        while messages:
            if len(messages) > 1:
                await self.bot.delete_messages(messages[:100])
                messages = messages[100:]
            else:
                await self.bot.delete_message(messages[0])
                messages = []
            await asyncio.sleep(1.5)

    @commands.command(pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def cleanupbetween(self, ctx, first: int, last: int):
        """Deletes all messages between two specified messages

        To get a message id, enable developer mode in Discord's
        settings, 'appearance' tab. Then right click a message
        and copy its id.

        This command only works on bots running as bot accounts.
        """

        channel = ctx.message.channel
        author = ctx.message.author
        server = channel.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        if not is_bot:
            await self.bot.say("This command can only be used on bots with "
                               "bot accounts.")
            return

        to_delete = [ctx.message]
        after = await self.bot.get_message(channel, first)
        before = await self.bot.get_message(channel, last)

        if not has_permissions:
            await self.bot.say("I'm not allowed to delete messages.")
            return
        elif not after or not before:
            await self.bot.say("Message not found.")
            return

        async for message in self.bot.logs_from(channel, limit=2000,
                                                after=after, before=before):
            to_delete.append(message)

        self.logger.info("{}({}) deleted {} messages in channel {}"
                    "".format(author.name, author.id,
                              len(to_delete), channel.name))

        await self.mass_purge(to_delete)

def setup(bot):
    n = CleanupCollapse(bot)
    bot.add_cog(n)
