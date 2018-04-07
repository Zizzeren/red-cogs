import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help, user_allowed
import os
from copy import copy

class Emote:
    def get_prefix(self, server, msg):
        prefixes = self.bot.settings.get_prefixes(server)
        for p in prefixes:
            if msg.startswith(p):
                return p
        return None

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/emote/emotes.json")

    @checks.mod_or_permissions(administrator=True)
    @commands.command()
    async def emote(self, emote):
        if emote.lower() in self.settings:
            await self.bot.say(self.settings[emote.lower()])
            return
        await self.bot.say("I don't have that emote.")

    @checks.is_owner()
    @commands.command(pass_context=True)
    async def emoteadd(self, ctx, emote, name):
        name = name[1:] if name[0] == "\\" else name
        if name.lower() in self.settings:
            await self.bot.say("I've already got an emote under that name.")
            return
        self.settings[name.lower()] = emote
        dataIO.save_json("data/emote/emotes.json", self.settings)
        await self.bot.say("Added that emote.")

    @checks.is_owner()
    @commands.command(pass_context=True)
    async def emoteremove(self, ctx, name):
        if name.lower() in self.settings:
            del self.settings[name.lower()]
            dataIO.save_json("data/emote/emotes.json", self.settings)
            await self.bot.say("Removed that emote.")
            return
        await self.bot.say("Couldn't find that emote.")

    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True)
    async def emotelist(self, ctx):
        await self.bot.say(" ".join(sorted(self.settings.values())))

    async def on_message(self, message):
        if len(message.content) < 2 or message.channel.is_private:
            return
        msg = message.content
        server = message.server
        prefix = self.get_prefix(server, msg)
        if not prefix:
            return
        if user_allowed(message) and \
                msg[len(prefix):].lower() in self.settings:
            new_command = "emote " + msg[len(prefix):].lower()
            new_message = copy(message)
            new_message.content = prefix + new_command
            print(new_message.content)
            await self.bot.process_commands(new_message)

def check_folders():
    if not os.path.exists("data/emote"):
        print("Creating data/emote folder...")
        os.makedirs("data/emote")

def check_files():
    if not dataIO.is_valid_json("data/emote/emotes.json"):
        print("Creating default data/emote/emotes.json")
        dataIO.save_json("data/emote/emotes.json", {})

def setup(bot):
    check_folders()
    check_files()
    n = Emote(bot)
    bot.add_cog(n)
