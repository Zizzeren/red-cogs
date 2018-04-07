import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help
from cogs.utils.chat_formatting import pagify
import os
import traceback

format = {
    "server.id": {
        "CHANNEL": "int(channelid)",
        "ENABLED": False,
        "FILTER": {
            "phrase": [ "member1.id", "member2.id" ],
            "phrase2": [ "member1.id", "member2.id" ]
            },
        "WHITELIST": {
            "PHRASES": [ "phrasegood", "phrase2good" ],
            "USERS": [ "member1.id", "member2.id" ],
            "ROLES"  : [ "role1.id", "role2.id" ]
            }
}}

settings_path = "data/filterping/settings.json"

class Filterping:
    """Like !filter, but it'll ping a certain set of members in
    a particular channel when the filter goes off."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json(settings_path)
        try:
            self.censored_words = dataIO.load_json("data/self-censor.json")
        except:
            self.censored_words = []
        self.defaults = {
                    "CHANNEL": None,
                    "ENABLED": False,
                    "FILTER" : {},
                    "WHITELIST": {
                        "PHRASES": [],
                        "USERS": [],
                        "ROLES": []
                        }
                }

    def censor(self, msg):
        msgLower = msg.lower()
        for cuss in self.censored_words:
            index = 0
            while index != -1:
                index = 0
                endIndex = 0
                index = msgLower.find(cuss)
                if index != -1:
                    index += 1 # don't censor the first character
                    endIndex = index + 1
                    # or the last
                    if endIndex + 1 < len(msgLower):
                        while msgLower[endIndex + 1] in 'abcdefghijklmnopqrstuvwxyz':
                            endIndex += 1
                            if endIndex + 1 == len(msgLower):
                                break
                    msg = msg[:index] + ("-" * (endIndex - index)) + msg[endIndex:]
                    msgLower = msg.lower()
        return msg

    async def on_message(self, message):
        server = message.server
        author = message.author
        channel = message.channel
        content = message.content.lower()
        if author.id == self.bot.user.id:
            return
        if server is None:
            return
        if server.id not in self.settings:
            return
        if "filterping" in message.content:
            return
        if self.settings[server.id]["ENABLED"] is False:
            return
        if self.settings[server.id]["CHANNEL"] is None:
            return
        if author.id in self.settings[server.id]["WHITELIST"]["USERS"]:
            return
        for r in self.settings[server.id]["WHITELIST"]["ROLES"]:
            try:
                role = discord.utils.get(author.roles, id=r)
            except:
                pass
            try:
                if role is not None:
                    return
            except NameError:
                return
        for s in self.settings[server.id]["WHITELIST"]["PHRASES"]:
            if s in content:
                return
        
        bad_words = None
        pings = []
        for s,p in self.settings[server.id]["FILTER"].items():
            if s in content:
                bad_words = s
                pings = p
                break
        
        if bad_words is not None:
            try:
                msg = "{} said a filtered phrase in {}: {}\nMessage: {}\n{}"\
                    .format(
                        author.mention, 
                        message.channel.mention, 
                        self.censor(bad_words),
                        self.censor(message.content),
                        ", ".join(
                            [a.mention for a in 
                                [server.get_member(uid) for uid in pings]
                             if a is not None]))
                if len(msg) > 2000:
                    msg = "{} said a filtered phrase in {}: {}\n{}".format(
                        author.mention, 
                        message.channel.mention, 
                        self.censor(bad_words),
                        ", ".join(
                            [a.mention for a in 
                                [server.get_member(uid) for uid in pings]
                             if a is not None]))
                await self.bot.send_message(server.get_channel(
                    self.settings[server.id]["CHANNEL"]),
                    msg)
            except Exception as e:
                #await self.bot.send_message(message.channel,
                #        "I was supposed to ping some users about that message, but I failed!")
                print("Filterping exception:")
                print(e)
                print(''.join(traceback.format_exception(etype=type(ex), value=ex, tb=ex.__traceback__)))

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(administrator=True)
    async def filterping(self, ctx):
        """Change settings for filterping."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            server = ctx.message.server
            if server.id in self.settings:
                await self.bot.say("Filterping is currently {}!".format(
                    "ENABLED" if \
                        self.settings[server.id]["ENABLED"]\
                        else "disabled"))

    @filterping.command(pass_context=True, no_pm=True)
    async def toggle(self, ctx, phrase_id = None):
        """Enables/Disables filterping"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = self.defaults

        state = not self.settings[server.id]["ENABLED"]
        self.settings[server.id]["ENABLED"] = state
        dataIO.save_json(settings_path, self.settings)
        await self.bot.say("Filterping is now {}.".format(
            "ENABLED" if state else "disabled"))

    @filterping.command(pass_context=True, no_pm=True)
    async def list(self, ctx):
        """List all the current filtered words. Sends to DMs."""
        server = ctx.message.server
        author = ctx.message.author
        if server.id not in self.settings:
            self.settings[server.id] = self.defaults
        msg = "Filterping is currently {}.\nCurrent filter list:\n".format(
            "ENABLED" if self.settings[server.id]["ENABLED"] else "disabled")

        items = []
        for m in self.settings[server.id]["FILTER"].keys():
            pings = []
            for p in self.settings[server.id]["FILTER"][m]:
                p_member = server.get_member(p)
                if p_member is not None:
                    pings.append(p_member.name)
            items.append("{}: pings {}".format(
                m, ", ".join(pings) if len(pings) > 0 else "nobody"))
        msg += "\n".join(items)
        
        if len(self.settings[server.id]["FILTER"].keys()) > 0:
            try:
                for page in pagify(msg, delims=["\n"], shorten_by=8):
                    await self.bot.send_message(author, page)
                    await self.bot.say("Sent to DMs.")
            except discord.Forbidden:
                await self.bot.say("I can't send DMs to you.")
        else:
            await self.bot.say("This server has no filters set up.")

    @filterping.command(pass_context=True, no_pm=True)
    async def add(self, ctx, phrase: str, *pings: discord.Member):
        """Add words to the filter. Quote sentences.
        You can optionally provide a starting list of members to ping.
        If the phrase is already in the filter, the pings will be added."""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = self.defaults
        phrase = phrase.lower()

        already_in = False
        if phrase in self.settings[server.id]["FILTER"]:
            ol_pings = set(self.settings[server.id]["FILTER"][phrase])
            pings = set([p.id for p in pings])
            nu_pings = list(ol_pings | pings)
            already_in = True
        else:
            nu_pings = [p.id for p in pings]

        self.settings[server.id]["FILTER"][phrase] = nu_pings

        dataIO.save_json(settings_path, self.settings)
        await self.bot.say("Added {} to filter.".format(
            "pings" if already_in else "phrase"))

    @filterping.command(pass_context=True, no_pm=True)
    async def remove(self, ctx, phrase: str, *pings: discord.Member):
        """Remove words from the filter. Quote sentences.
        If you specify no members, the phrase will be removed entirely.
        If you specify members, then they will be removed from the ping list
            for that phrase, but the phrase will remain."""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = self.defaults
        phrase = phrase.lower()

        if phrase not in self.settings[server.id]["FILTER"]:
            await self.bot.say("That phrase is not filtered.")
            return
        if len(pings) == 0:
            del self.settings[server.id]["FILTER"][phrase]
            dataIO.save_json(settings_path, self.settings)
            await self.bot.say("Deleted that phrase.")
            return

        count = 0
        ol_pings = self.settings[server.id]["FILTER"][phrase]
        for p in pings:
            if p.id in ol_pings:
                ol_pings.remove(p.id)
                count += 1
        self.settings[server.id]["FILTER"][phrase] = ol_pings
        await self.bot.say("Removed {} member{} from that ping list.".format(
            count, 's' if count > 1 else ''))

        dataIO.save_json(settings_path, self.settings)

    @filterping.command(pass_context=True, no_pm=True)
    async def channel(self, ctx, channel: discord.Channel = None):
        """Set the channel to send pings to."""
        server = ctx.message.server
        if channel is None:
            channel = ctx.message.channel
        if server.id not in self.settings:
            self.settings[server.id] = self.defaults
            
        self.settings[server.id]["CHANNEL"] = channel.id
        dataIO.save_json(settings_path, self.settings)
        await self.bot.say("Will now send pings to {}".format(channel.mention))

    @filterping.command(pass_context=True, no_pm=True)
    async def whitelist(self, ctx, which, action, *args):
        """Control whitelist settings.
        Items in the whitelist will cause a message to not generate pings
        if any of the items in the whitelist are present.

        Takes two subcommands, <which> and <action>.
        <which> should be one of 'user', 'role', or 'phrase'.
        <action> should be one of 'add', 'remove', or 'list'.

        The rest of the command should be the items to add or remove.
        For users, this can be IDs or pings.
        For roles, this can be IDs, pings, or names.
        For phrases, this is the phrase itself.
        """
        if which not in ['role', 'phrase', 'user']:
            await self.bot.say(
                "<which> should be 'role', 'phrase', or 'user'")
            return
        if action not in ['add', 'remove', 'list']:
            await self.bot.say(
                "<action> should be 'add', 'remove', or 'list'")
            return
        server = ctx.message.server

        items = []
        if which == 'user':
            coll = "USERS"
            for a in args:
                uid = ''.join([s for s in a if s.isdigit()])
                if server.get_member(uid) is not None:
                    items.append(uid)

        elif which == 'role':
            coll = "ROLES"
            items = []
            for a in args:
                rid = ''.join([s for s in a if s.isdigit()])
                rid_real = discord.utils.find(
                                lambda m: m.id == rid or m.name == a, 
                                server.roles)
                if rid_real is not None:
                    items.append(rid_real.id)

        elif which == 'phrase':
            coll = "PHRASES"
            items = [a.lower() for a in args if len(a) > 0]

        if server.id not in self.settings:
            self.settings[server.id] = self.defaults

        count = 0
        if action == 'add':
            for item in items:
                if item not in self.settings[server.id]["WHITELIST"][coll]:
                    self.settings[server.id]["WHITELIST"][coll].append(item)
                    count += 1
            if count != 0:
                await self.bot.say("Added {}{} to whitelist".format(
                    which, 's' if count > 1 else ''))
            else:
                await self.bot.say("No {}s added to whitelist.".format(which))
            dataIO.save_json(settings_path, self.settings)

        elif action == 'remove':
            for item in items:
                if item in self.settings[server.id]["WHITELIST"][coll]:
                    self.settings[server.id]["WHITELIST"][coll].remove(item)
                    count += 1
            if count != 0:
                await self.bot.say("Removed {} {}{} from whitelist.".format(
                    count, which, 's' if count > 1 else ''))
            else:
                await self.bot.say("No {}s removed from whitelist.".format(
                    which))
            dataIO.save_json(settings_path, self.settings)
            
        elif action == 'list':
            items = []
            if which == 'user':
                items = [u.name for u in 
                            [server.get_member(uid) for uid in
                                self.settings[server.id]["WHITELIST"][coll]]
                            if u is not None]
            elif which == 'role':
                items = [r.name for r in
                            [discord.utils.find(lambda x: x.id == rid, 
                                                server.roles) for rid in
                                self.settings[server.id]["WHITELIST"][coll]]
                            if r is not None]
            elif which == 'phrase':
                items = self.settings[server.id]["WHITELIST"][coll]

            msg = "Listing all whitelisted {}s:\n".format(which)
            for item in items:
                word = "{}, ".format(item)
                if len(msg) + len(word) < 1900:
                    msg += word
                else:
                    await self.bot.say(msg[:-2])
                    msg = word
            await self.bot.say(msg)

def check_folders():
    if not os.path.exists("data/filterping"):
        print("Creating data/filterping folder...")
        os.makedirs("data/filterping")

def check_files():
    if not dataIO.is_valid_json(settings_path):
        print("Creating default {}...".format(settings_path))
        dataIO.save_json(settings_path, {})

def setup(bot):
    check_folders()
    check_files()
    n = Filterping(bot)
    bot.add_cog(n)
