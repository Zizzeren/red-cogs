import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from random import choice as rndchoice
import os
import time

class RandomStatus:
    """Cycles random statuses

    If a custom status is already set, it won't change it until
    it's back to none. (!set status)"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO("data/rndstatus/settings.json", "load")
        self.statuses = fileIO("data/rndstatus/statuses.json", "load")
        self.last_change = None

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def rndstatus(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @rndstatus.command(name="add")
    async def _add(self, *statuses : str):
        """Adds a random status to Red's set

        Accepts multiple statuses
        Must be enclosed in double quotes in case of multiple words.
        Example:
        !rndstatus add \"Tomb Raider II\" \"Transistor\" \"with your heart.\" """
        if statuses == () or "" in statuses:
            await self.bot.say("Try an actual string!")
            return
        self.statuses = list(set(self.statuses) | set(statuses))
        fileIO("data/rndstatus/statuses.json", "save", self.statuses)
        #await self.bot.change_status(None)
        await self.bot.say("Added `" + ", ".join(statuses) + "` to rndstatus list.")

    @rndstatus.command(name="remove")
    async def _remove(self, *statuses : str):
        """Remove a status from Red's set

        Accepts multiple statuses
        Must be enclosed in double quotes in case of multiple words.
        Example:
        !rndstatus remove \"Tomb Raider II\" \"Transistor\" \"with your heart.\" """
        if statuses == () or "" in statuses:
            await self.bot.say("Try an actual string!")
            return
        self.statuses = list(set(self.statuses) - set(statuses)) 
        fileIO("data/rndstatus/statuses.json", "save", self.statuses)
        #await self.bot.change_status(None)
        await self.bot.say("Removed `" + ", ".join(statuses) + "` from rndstatus list.")

    @rndstatus.command(name="list")
    async def _list(self):
        """Lists the current rndstatus list."""

        await self.bot.say("Current statuses: \n```" + " | ".join(sorted(self.statuses, key=lambda s: s.lower())) + "```")

    @rndstatus.command(pass_context=True)
    async def next(self, ctx):
        """Switch status forcibly."""
        if not ctx.message.channel.is_private:
            current_status = str(ctx.message.server.me.game)
            self.last_change = int(time.perf_counter())
            new_status = self.random_status(ctx.message)
            if new_status != None:
                if current_status != new_status:
                    await self.bot.change_presence(game=discord.Game(name=new_status))
            await self.bot.say("Updated status.")
        else:
            await self.bot.say("That command is not available in DMs.")

    @rndstatus.command(pass_context=True)
    async def delay(self, ctx, seconds : int):
        """Sets interval of random status switch

        Must be 20 or superior, or use [p]rndstatus delay ? to check current value."""

        if seconds < 20:
            await send_cmd_help(ctx)
            return
        self.settings["DELAY"] = seconds
        fileIO("data/rndstatus/settings.json", "save", self.settings)
        await self.bot.say("Interval set to {}".format(str(seconds)))

    async def switch_status(self, message):
        if not message.channel.is_private:
            current_status = str(message.server.me.game)

            if self.last_change == None: #first run
                self.last_change = int(time.perf_counter())
                if len(self.statuses) > 0 and (current_status in self.statuses or current_status == "None"):
                    new_status = self.random_status(message)
                    await self.bot.change_presence(game=discord.Game(name=new_status))

            if message.author.id != self.bot.user.id:
                if abs(self.last_change - int(time.perf_counter())) >= self.settings["DELAY"]:
                    self.last_change = int(time.perf_counter())
                    new_status = self.random_status(message)
                    if new_status != None:
                        if current_status != new_status:  
                            if current_status in self.statuses or current_status == "None": #Prevents rndstatus from overwriting song's titles or
                                await self.bot.change_presence(game=discord.Game(name=new_status)) #custom statuses set with !set status

    def random_status(self, msg):
        current = str(msg.server.me.game)
        new = str(msg.server.me.game)
        if len(self.statuses) > 1:
            while current == new:
                new = rndchoice(self.statuses)
        elif len(self.statuses) == 1:
            new = self.statuses[0]
        else:
            new = None
        return new

def check_folders():
    if not os.path.exists("data/rndstatus"):
        print("Creating data/rndstatus folder...")
        os.makedirs("data/rndstatus")

def check_files():
    settings = {"DELAY" : 300}
    default = ["her Turn()", "Tomb Raider II", "Transistor", "NEO Scavenger", "Python", "with your heart."]

    f = "data/rndstatus/settings.json"
    if not fileIO(f, "check"):
        print("Creating empty settings.json...")
        fileIO(f, "save", settings)

    f = "data/rndstatus/statuses.json"
    if not fileIO(f, "check"):
        print("Creating empty statuses.json...")
        fileIO(f, "save", default)

def setup(bot):
    check_folders()
    check_files()
    n = RandomStatus(bot)
    bot.add_listener(n.switch_status, "on_message")
    bot.add_cog(n)
