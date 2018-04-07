import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help
import os

class Modmail:
    """Contact the mods of a server you're in"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/modmail/settings.json")

    @commands.command(pass_context=True)
    async def modmail(self, ctx, *args):
        """Contact the mods of a server you're in.

        I'll try to figure out which server you mean, but I might
        have to ask you to provide a server ID. This can be obtained
        by turning on Developer Mode in the Discord client, and
        right-clicking on the server you want to report a user in.
        
        If you're reporting a user, it's good practice to get their
        ID, as well as their username and discriminator (user#1234)"""

        if len(args) == 0:
            await send_cmd_help(ctx)
            return

        author = ctx.message.author
        server_target = self.bot.get_server(args[0])
        if server_target is not None:
            args = args[1:]
        else:
            if ctx.message.server is not None:
                server_target = ctx.message.server
            else:
                for server in self.bot.servers:
                    if server.id in self.settings:
                        member = server.get_member(author.id)
                        if member is not None:
                            server_target = server
                            break

        if server_target is None:
            await self.bot.say("I couldn't figure out what server "+\
                "you want me to send this to. Please send the server ID.")
            response = await self.bot.wait_for_message(
                    timeout=30,
                    author=author)
            server_target = self.bot.get_server(response.content)
            if server_target is None:
                await self.bot.say("Cancelling modmail.")
                return
            

        await self.bot.say(
            "If this message should be sent to the mods of {}, "\
                .format(server_target.name) +\
            "please respond with `yes`. Otherwise, respond with a "+\
            "server ID.")
        response = await self.bot.wait_for_message(
                timeout = 30,
                author=author)

        if response.content.lower() != "yes":
            server_referenced = self.bot.get_server(response.content)
            if server_referenced is None:
                await self.bot.say("Cancelling modmail.")
                return
            server_target = server_referenced
            await self.bot.say(
                "If this message should be sent to the mods of {}, "\
                        .format(server_target.name) +\
                "please respond with `yes`.")
            response2 = await self.bot.wait_for_message(
                    timeout = 30,
                    author = author)
            if response2.content.lower() != "yes":
                await self.bot.say("Cancelling modmail.")
                return

        # By now, we know the message should be sent.
        if server_target.id not in self.settings:
            await self.bot.say("That server hasn't set up modmail. "+\
                    "Contact the mods to ask them to! :smile:")
            return
        await self.bot.send_message(self.bot.get_channel(
                    self.settings[server_target.id]),
            "{}#{} ({}) sent some modmail:\n".format(
                author.name, author.discriminator, author.id
                )\
                + " ".join(args))
        await self.bot.say("Modmail sent.")

    @commands.command(pass_context=True)
    @checks.admin_or_permissions(administrator=True)
    async def modmailset(self, ctx, ch: discord.Channel = None):
        """Set this server's channel for modmail."""
        if ch is None:
            ch = ctx.message.channel

        self.settings[ch.server.id] = ch.id
        dataIO.save_json("data/modmail/settings.json", self.settings)
        await self.bot.say("Set modmail channel to {}".format(ch.mention))

    @commands.command(pass_context=True)
    @checks.admin_or_permissions(administrator=True)
    async def modmailoff(self, ctx):
        """Turn off modmail for this server."""
        if ctx.message.server.id in self.settings:
            del self.settings[ctx.message.server.id]
            dataIO.save_json("data/modmail/settings.json", self.settings)
            await self.bot.say("Modmail off.")
        else:
            await self.bot.say("Modmail is already off.")

def check_folders():
    if not os.path.exists("data/modmail"):
        print("creating data/modmail folder...")
        os.makedirs("data/modmail")

def check_files():
    f = "data/modmail/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default modmail's settings.json...")
        dataIO.save_json(f, {})

def setup(bot):
    check_folders()
    check_files()
    n = Modmail(bot)
    bot.add_cog(n)
