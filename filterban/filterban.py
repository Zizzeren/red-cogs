import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help
from cogs.utils.chat_formatting import pagify
import os
import datetime
import time

settings_format = {
    "server.id": {
        "ACTION": "kick/ban/role",
        "WARNINGS": 3,
        "COOLDOWN": 60,
        "DELETE_MESSAGE_DAYS": 0,
        "ENABLED": False,
        "CHANNEL": None,
        "FILTER": {
            "phrase_hash": {
                "TEXT": "don'tsaythis",
                "ACTION": "kick",
                "ROLE": 123456789012345678,
                "WARNINGS": 4,
                "COOLDOWN": 60,
                "DELETE_MESSAGE_DAYS": 0,
                "ENABLED": False,
                "SEND_WARNING": True,
                "GLOBAL_VALUE": 2,
                "WARNING_MESSAGE": "msg"
                }
            },
        "MEMBERS": {
            "member.id": {
                "WARNINGS": {
                    "GLOBAL": {
                            "WARNINGS": 0,
                            "LIFETIME_WARNINGS": 0,
                            "LAST_WARNING_TIME": 0
                        },
                    "phrase_hash": {
                            "WARNINGS": 0,
                            "LIFETIME_WARNINGS": 0,
                            "LAST_WARNING_TIME": 0
                        }
                    }
                }
            }
        }
}

settings_path = "data/filterban/settings.json"
warning_message_default = "{mention} said something against the rules. Be careful in the future. You have **{num_g} warnings** left before you are {action_g} for all infractions on this server. You have **{num_p} warnings** left for that phrase, after which you will be {action_p}."
action_message = "{} was **{}ed** for saying something against the rules."
failed_action_message = "I was instructed to {}, but something prevented me. Do I have permission?"
units_l = (("second", 1), ("minute", 60), ("hour", 3600),
        ("day", 86400), ("week", 604800), ("month", 2592000))

filter_info_message = \
"""Enabled: {}
ID: `{}`
Text: {}
Action: {}
Cooldown: {}
Warning limit: {}
Should send warning messages: {}
Global warning value: {}
Number of days of messages to delete on ban: {}
Warning message: {}"""

class Filterban:
    """Like !filter, but it'll ban users rather than just deleting 
    their messages. This is a very dangerous cog, and it should
    only be used at your own risk. You have been warned.
    
    This cog was created by request to help deal with doxxing, which
    is illegal. It would not exist otherwise. It should only be used
    in extreme circumstances."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json(settings_path)
        for s in self.settings:
            for f in self.settings[s]["FILTER"]:
                if "WARNING_MESSAGE" not in self.settings[s]["FILTER"]:
                    self.settings[s]["FILTER"][f]["WARNING_MESSAGE"] = warning_message_default
        dataIO.save_json(settings_path, self.settings)

    async def check_cooldowns(self, member: discord.Member):
        server = member.server
        now = time.time()
        for phrase_id,value in self.settings\
                    [server.id]["MEMBERS"][member.id]["WARNINGS"].items():
            diff = now - value["LAST_WARNING_TIME"]
            if phrase_id not in self.settings[server.id]["FILTER"]:
                continue
            cd = self.settings[server.id]["FILTER"][phrase_id]["COOLDOWN"]
            cooldowns = int(diff / cd)
            total = value["WARNINGS"] - cooldowns
            if total < 0:
                total = 0
            self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"]\
                    [phrase_id]["WARNINGS"] = total

        dataIO.save_json(settings_path, self.settings)

    async def try_take_action(self, message, phrase_id):
        member = message.author
        server = message.server
        settings = self.settings[server.id]

        global_value = self.settings[server.id]["FILTER"][phrase_id]\
                ["GLOBAL_VALUE"]

        if member.id not in settings["MEMBERS"]:
            self.settings[server.id]["MEMBERS"][member.id] = {
                    "WARNINGS": { "GLOBAL": {
                            "WARNINGS": global_value,
                            "LIFETIME_WARNINGS": global_value,
                            "LAST_WARNING_TIME": time.time()
                        }}}
        if phrase_id not in settings["MEMBERS"][member.id]["WARNINGS"]:
            self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"]\
                        [phrase_id] = {
                            "WARNINGS": 0,
                            "LIFETIME_WARNINGS": 0,
                            "LAST_WARNING_TIME": time.time()
                        }

        await self.check_cooldowns(member)

        self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"]\
                ["GLOBAL"]["WARNINGS"] += global_value
        self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"]\
                ["GLOBAL"]["LIFETIME_WARNINGS"] += global_value
        self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"]\
                ["GLOBAL"]["LAST_WARNING_TIME"] = time.time()
        self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"]\
                [phrase_id]["WARNINGS"] += 1
        self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"]\
                [phrase_id]["LIFETIME_WARNINGS"] += 1
        self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"]\
                [phrase_id]["LAST_WARNING_TIME"] = time.time()

        dataIO.save_json(settings_path, self.settings)
        mem = self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"]
        serv = self.settings[server.id]["FILTER"]
        action = None
        if mem["GLOBAL"]["WARNINGS"] > serv["GLOBAL"]["WARNINGS"]:
            action = serv["GLOBAL"]["ACTION"]
            days = serv["GLOBAL"]["DELETE_MESSAGE_DAYS"]
        if action is None:
            if mem[phrase_id]["WARNINGS"] > serv[phrase_id]["WARNINGS"]:
                action = serv[phrase_id]["ACTION"]
                days = serv[phrase_id]["DELETE_MESSAGE_DAYS"]
        if action is None:
            if serv[phrase_id]["SEND_WARNING"]:
                if serv["GLOBAL"]["ACTION"] == "kick":
                    action_text_g = "kicked"
                elif serv["GLOBAL"]["ACTION"] == "ban":
                    action_text_g = "banned"
                elif serv["GLOBAL"]["ACTION"] == "role":
                    action_text_g = "roled"
                if serv[phrase_id]["ACTION"] == "kick":
                    action_text_p = "kicked"
                elif serv[phrase_id]["ACTION"] == "ban":
                    action_text_p = "banned"
                elif serv[phrase_id]["ACTION"] == "role":
                    action_text_p = "roled"
                await self.bot.send_message(message.channel, serv[phrase_id]["WARNING_MESSAGE"]\
                        .format(
                            mention=member.mention,
                            name=member.name,
                            nick=member.nick,
                            id=member.id,
                            discriminator=member.discriminator,
                            channel=message.channel.mention,
                            num_g=10,
                            action_g="banned",
                            num_p=3,
                            action_p="kicked"
                            ))
            return
        else:
            try:
                channel = self.settings[server.id]["CHANNEL"]
                if action == "kick":
                    await self.bot.kick(member)
                    msg = "{} is kicked for saying something against the rules.".format(member.name)
                    await self.bot.send_message(message.channel, msg)
                    if channel:
                        await self.bot.send_message(server.get_channel(channel), msg)
                elif action == "ban":
                    await self.bot.ban(member, days)
                    msg = "{} is banned for saying something against the rules.".format(member.name)
                    await self.bot.send_message(message.channel, msg)
                    if channel:
                        await self.bot.send_message(server.get_channel(channel), msg)
                elif action == "role":
                    role = discord.utils.find(lambda x: x.id == serv[phrase_id]["ROLE"], server.roles)
                    await self.bot.add_roles(member, role)
                    msg = "{} had the {} role added for saying something against the rules."\
                            .format(member.name, role.name)
                    await self.bot.send_message(message.channel, msg)
                    if channel:
                        await self.bot.send_message(server.get_channel(channel), msg)

            except:
                await self.bot.send_message(message.channel,
                    failed_action_message.format(
                        "{} {}".format(action, member.mention)))
                return

    async def on_message(self, message):
        server = message.server
        if message.author.id == self.bot.user.id:
            return
        if message.author.bot:
            return
        if server is None:
            return
        if server.id not in self.settings:
            return
        if self.settings[server.id]["FILTER"]["GLOBAL"]["ENABLED"] is False:
            return
        if "filterban" in message.content:
            return
        
        bad_words = False
        content = message.content.lower()
        content_id = str(abs(hash(content)))
        if content_id in self.settings[server.id]["FILTER"]:
            if self.settings[server.id]["FILTER"][content_id]["ENABLED"]:
                bad_words = True
        if not bad_words:
            for phrase_id,value in self.settings[server.id]["FILTER"].items():
                if phrase_id != "GLOBAL":
                    if value["ENABLED"]:
                        if value["TEXT"] in content:
                            content_id = phrase_id
                            bad_words = True
        
        if bad_words:
            try:
                pass
                #await self.bot.delete_message(message)
            except:
                await self.bot.send_message(message.channel,
                        failed_action_message("delete that message"))

            await self.try_take_action(message, content_id)

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(administrator=True)
    async def filterban(self, ctx):
        """Change settings for filterban
        
        Requires administrator permissions."""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {
                "FILTER": {
                    "GLOBAL": {
                        "TEXT": "",
                        "ACTION": "kick",
                        "ROLE": None,
                        "WARNINGS": 2,
                        "COOLDOWN": 3600,
                        "DELETE_MESSAGE_DAYS": 0,
                        "ENABLED": False,
                        "GLOBAL_VALUE": 0
                        }
                    },
                "MEMBERS": {},
                "CHANNEL": None
            }
            dataIO.save_json(settings_path, self.settings)

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            await self.bot.say("Filterban is currently {}!".format(
                "ENABLED" if \
                    self.settings[server.id]["FILTER"]["GLOBAL"]["ENABLED"]\
                    else "disabled"))

    @filterban.command(pass_context=True, no_pm=True)
    async def forgive(self, ctx, member: discord.Member, *phrase_ids: str):
        """Forgives a user of their infractions.
        Does not reset their lifetime warnings.
        Specify a phrase id to forgive that phrase's warnings, or 'all'.
        If none is specified, only the global warnings are forgiven."""
        server = ctx.message.server
        if member.id not in self.settings[server.id]["MEMBERS"]:
            await self.bot.say("That member hasn't said anything bad.")
            return
        msg = ""
        if len(phrase_ids) == 0:
            ids = [ "GLOBAL" ]
            msg = " of only their global warnings"
        elif phrase_ids[0] == "all":
            ids = self.settings[server.id]["FILTER"].keys()
            msg = " of all their warnings"
        else:
            ids = phrase_ids
            msg = " of warnings for phrases `{}`".format(", ".join(ids))

        for phraseid in ids:
            if phraseid not in self.settings[server.id]["FILTER"]:
                await self.bot.say("Could not find phrase {}.".format(phraseid))
                continue
            if phraseid in self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"]:
                self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"][phraseid]["WARNINGS"] = 0

        dataIO.save_json(settings_path, self.settings)
        await self.bot.say("Forgiven that user{}.".format(msg))

    @filterban.command(pass_context=True, no_pm=True)
    async def showusers(self, ctx):
        """Lists which users have infractions on record."""
        server = ctx.message.server
        msg = ""
        member_id = 1
        for member,warnings in self.settings[server.id]["MEMBERS"].items():
            warnings = warnings["WARNINGS"]
            member = server.get_member(member)
            if member is None:
                continue
            await self.check_cooldowns(member)
            phrase_count = 0
            text = "\n**#{}**: {}#{} ({})".format(
                    member_id, member.name, member.discriminator, member.id)

            for phrase,data in warnings.items():
                if phrase not in self.settings[server.id]["FILTER"]:
                    continue
                phrase_count += 1
                text += "\nCurrently **{}** warnings for phrase `{}`, **{}** lifetime".format(
                    self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"][phrase]["WARNINGS"],
                    phrase,
                    self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"][phrase]["LIFETIME_WARNINGS"])

            if phrase_count > 0:
                member_id += 1
                msg += text

        if member_id == 1:
            await self.bot.say("Nobody has committed any infractions.")
            return
        try:
            for page in pagify(msg, delims=["\n"], shorten_by=8):
                await self.bot.send_message(ctx.message.author, page)
            await self.bot.say("Sent to DMs.")
        except discord.Forbidden:
            await self.bot.say("I can't send DMs to you.")

    @filterban.command(pass_context=True, no_pm=True)
    async def showuser(self, ctx, member: discord.Member):
        """Shows infraction information of a particular user."""
        server = ctx.message.server
        if member.id not in self.settings[server.id]["MEMBERS"]:
            await self.bot.say("That member has not committed any infractions.")
            return
        text = ""

        await self.check_cooldowns(member)

        for phraseid,data in self.settings[server.id]["FILTER"].items():
            if phraseid in self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"]:
                text += "\nCurrently **{}** warnings for phrase `{}`, **{}** lifetime".format(
                    self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"][phraseid]["WARNINGS"],
                    phraseid,
                    self.settings[server.id]["MEMBERS"][member.id]["WARNINGS"][phraseid]["LIFETIME_WARNINGS"])

        msg = """{}#{} ({}):{}""".format(
                member.name,member.discriminator,member.id,text)
        await self.bot.say(msg)
    
    @filterban.command(pass_context=True, no_pm=True)
    async def cooldown(self, ctx, time: int, unit: str, phrase_id = None):
        """Sets the length of time before a single warning expires.
        Specify a phrase ID to set cooldown for that phrase."""
        server = ctx.message.server
        unit = unit.lower()
        s = ""
        if unit.endswith("s"):
            unit = unit[:-1]
            s = "s"
        units_d = dict(units_l)
        if unit not in units_d:
            await self.bot.say("Invalid time unit. "+\
                "Choose seconds/minutes/hours/days/weeks/months")
            return
        seconds = units_d[unit] * time

        if phrase_id is None:
            phrase_id = "GLOBAL"
        if phrase_id not in self.settings[server.id]["FILTER"]:
            await self.bot.say("I couldn't find that phrase ID.")
            return

        self.settings[server.id]["FILTER"][phrase_id]["COOLDOWN"] = seconds
        dataIO.save_json(settings_path, self.settings)
        await self.bot.say(
            "A warning {}will now expire {} {}{} after the last infraction."\
                .format("for this phrase " if phrase_id != "GLOBAL" else "",
                    time, unit, s))

    @filterban.command(pass_context=True, no_pm=True)
    async def action(self, ctx, action: str, phrase_id = None):
        """Set the action to take when someone infracts too many times.
        <action> should be 'kick', 'ban', or 'role'.
        Set up the penalty role with 'filterban role'.
        Specify a phrase id, or leave it out to change the global action."""
        action = action.lower()
        if action not in ["kick", "ban", "role"]:
            await self.bot.say("Tell me to either kick, ban, or apply a role.")
            return
        server = ctx.message.server
        if phrase_id is None:
            phrase_id = "GLOBAL"
        if phrase_id not in self.settings[server.id]["FILTER"]:
            await self.bot.say("I couldn't find that phrase ID.")
            return

        self.settings[server.id]["FILTER"][phrase_id]["ACTION"] = action
        dataIO.save_json(settings_path, self.settings)
        await self.bot.say(
            "I will now {} users{}.".format(action,
                " for saying that phrase" if phrase_id != "GLOBAL" else ""))
        if action == "role":
            await self.bot.say("Don't forget to add a penalty role with 'filterban role'.")

    @filterban.command(pass_context=True, no_pm=True)
    async def role(self, ctx, role : discord.Role, phrase_id = None):
        """Set the role to apply on an infraction."""
        server = ctx.message.server
        if phrase_id is None:
            phrase_id = "GLOBAL"
        if phrase_id not in self.settings[server.id]["FILTER"]:
            await self.bot.say("I couldn't find that phrase ID.")

        self.settings[server.id]["FILTER"][phrase_id]["ROLE"] = role.id
        dataIO.save_json(settings_path, self.settings)
        await self.bot.say(
            "I will now apply that role to users{}.".format(
                " for saying that phrase" if phrase_id != "GLOBAL" else ""))

    @filterban.command(pass_context=True, no_pm=True)
    async def warnings(self, ctx, warnings: int, phrase_id = None):
        """Set the number of warnings before action is taken.
        I will warn this many times, then take action the next time.
        Specify a phrase id, or leave it out to change the global warnings."""
        server = ctx.message.server
        if phrase_id is None:
            phrase_id = "GLOBAL"
        if phrase_id not in self.settings[server.id]["FILTER"]:
            await self.bot.say("I couldn't find that phrase ID.")
            return
        
        self.settings[server.id]["FILTER"][phrase_id]["WARNINGS"] = warnings
        dataIO.save_json(settings_path, self.settings)
        await self.bot.say(
            "{} warnings will be given before action is taken{}.".format(
                warnings, " for that phrase" if phrase_id != "GLOBAL" else ""))

    @filterban.command(pass_context=True, no_pm=True)
    async def deletedays(self, ctx, days: int, phrase_id = None):
        """Set how many days of messages to delete if I ban a user.
        Specify a phrase id, or leave it out to change the global setting."""
        if days < 0:
            await self.bot.say("Less than 0 days? I don't understand...")
            return
        if days > 7:
            await self.bot.say("I can't set this higher than 7 days.")
            return
        server = ctx.message.server
        if phrase_id is None:
            phrase_id = "GLOBAL"
        if phrase_id not in self.settings[server.id]["FILTER"]:
            await self.bot.say("I couldn't find that phrase ID.")
            return

        self.settings[server.id]["FILTER"][phrase_id]["DELETE_MESSAGE_DAYS"]\
                = days
        dataIO.save_json(settings_path, self.settings)
        await self.bot.say(
            "I will delete {} days of messages when I ban someone{}.".format(
                days, " for that phrase" if phrase_id != "GLOBAL" else ""))

    @filterban.command(pass_context=True, no_pm=True)
    async def globalvalue(self, ctx, value: int, phrase_id):
        """Set how many warnings a particular phrase counts to global action.
        If your global warning limit is set to 5, then setting a phrase to have
        a global warning value of 3 will mean an offender has action taken 
        after 2 infractions. Value must be non-negative, but can be 0."""
        server = ctx.message.server
        if value < 0:
            await self.bot.say("Value must be non-negative.")
            return
        if phrase_id not in self.settings[server.id]["FILTER"]:
            await self.bot.say("I couldn't find that phrase ID.")
            return
        self.settings[server.id]["FILTER"][phrase_id]["GLOBAL_VALUE"] = value
        dataIO.save_json(settings_path, self.settings)
        await self.bot.say("That phrase now has a global warning value of {}."\
                .format(value))

    @filterban.command(pass_context=True, no_pm=True)
    async def toggle(self, ctx, phrase_id = None):
        """Enables/Disables filterban
        Specify a phrase id, or leave it out to toggle globally."""
        server = ctx.message.server

        if phrase_id is None:
            phrase_id = "GLOBAL"
        if phrase_id not in self.settings[server.id]["FILTER"]:
            await self.bot.say("I couldn't find that phrase ID.")
            return

        state = not self.settings[server.id]["FILTER"][phrase_id]["ENABLED"]
        self.settings[server.id]["FILTER"][phrase_id]["ENABLED"] = state
        dataIO.save_json(settings_path, self.settings)
        await self.bot.say("Filterban {}is now {}.".format(
            "for that phrase " if phrase_id != "GLOBAL" else "",
            "ENABLED" if state else "disabled"))

    @filterban.command(pass_context=True, no_pm=True)
    async def togglewarning(self, ctx, phrase_id):
        """Toggles warning for filtered phrases.
        Specify a phrase ID."""
        server = ctx.message.server
        if phrase_id not in self.settings[server.id]["FILTER"]:
            await self.bot.say("I couldn't find that phrase ID.")
            return

        state = not self.settings[server.id]["FILTER"][phrase_id]["SEND_WARNING"]
        self.settings[server.id]["FILTER"][phrase_id]["SEND_WARNING"] = state
        dataIO.save_json(settings_path, self.settings)
        await self.bot.say("I will now send {}warnings for that phrase.".format(
            "" if state else "no "))

    @filterban.command(pass_context=True, no_pm=True)
    async def channel(self, ctx, channel : discord.Channel = None):
        """Set a channel to send action notices to. Specify no channel to disable."""
        server = ctx.message.server
        self.settings[server.id]["CHANNEL"] = channel.id if channel else None
        dataIO.save_json(settings_path, self.settings)
        if channel:
            await self.bot.say("I will now send action notifications to {}.".format(channel.mention))
        else:
            await self.bot.say("I will no longer send action notifications.")

    @filterban.command(pass_context=True, no_pm=True)
    async def list(self, ctx):
        """List all the current filtered words. Sends to DMs."""
        server = ctx.message.server
        author = ctx.message.author
        msg = "Current filter list:\nFilterban is currently {}.\n".format(
                "ENABLED" if self.settings[server.id]["FILTER"]["GLOBAL"]["ENABLED"] else "disabled")
        if len(self.settings[server.id]["FILTER"]) > 0:
            for phrase_id,value in self.settings[server.id]["FILTER"].items():
                if phrase_id == "GLOBAL":
                    continue
                msg += "`{}` ({}): {}\n".format(
                        phrase_id, 
                        "enabled" if value["ENABLED"] else "disabled",
                        value["TEXT"])
            try:
                for page in pagify(msg, delims=["\n"], shorten_by=8):
                    await self.bot.send_message(author, page)
                    await self.bot.say("Sent to DMs.")
            except discord.Forbidden:
                await self.bot.say("I can't send DMs to you.")
        else:
            await self.bot.say("This server has no filters set up.")

    @filterban.command(pass_context=True, no_pm=True)
    async def show(self, ctx, phrase_id):
        """Show detailed information about a phrase. Sends to DMs."""
        server = ctx.message.server
        author = ctx.message.author
        if phrase_id not in self.settings[server.id]["FILTER"]:
            await self.bot.say("I couldn't find that phrase ID.")
            return
        info = self.settings[server.id]["FILTER"][phrase_id]
        msg = filter_info_message.format(
                info["ENABLED"],
                phrase_id,
                info["TEXT"],
                info["ACTION"],
                info["COOLDOWN"],
                info["WARNINGS"],
                info["SEND_WARNING"],
                info["GLOBAL_VALUE"],
                info["DELETE_MESSAGE_DAYS"],
                info["WARNING_MESSAGE"])
        await self.bot.send_message(author, msg)

    @filterban.command(pass_context=True, no_pm=True)
    async def add(self, ctx, *args: str):
        """Add words to the filter. Quote sentences."""
        if len(args) == 0:
            await send_cmd_help(ctx)
            return
        server = ctx.message.server
        msg = "Added phrases to filter.\n"
        count = 0
        for phrase in args:
            phrase = phrase.lower()
            if str(abs(hash(phrase))) in self.settings[server.id]["FILTER"]:
                await self.bot.say("I already have this phrase in my filter:"+\
                    " `{}`. Its ID is `{}`".format(phrase, abs(hash(phrase))))
                continue
            self.settings[server.id]["FILTER"][str(abs(hash(phrase)))] = {
                    "TEXT": phrase,
                    "ACTION": "kick",
                    "ROLE": None,
                    "WARNINGS": 2,
                    "COOLDOWN": 3600,
                    "DELETE_MESSAGE_DAYS": 0,
                    "SEND_WARNING": True,
                    "ENABLED": True,
                    "GLOBAL_VALUE": 1,
                    "WARNING_MESSAGE": warning_message_default
                }
            msg += "`{}`: {}\n".format(abs(hash(phrase)), phrase)
            count += 1
        if count != 0:
            dataIO.save_json(settings_path, self.settings)
            await self.bot.say(msg)

    @filterban.command(pass_context=True, no_pm=True)
    async def remove(self, ctx, *args: str):
        """Remove words from the filter. Provide phrase IDs.
        If you want to disable something temporarily, toggle it instead."""
        if len(args) == 0:
            await send_cmd_help(ctx)
            return
        server = ctx.message.server
        msg = "Deleted these phrases from the filter:\n"
        count = 0
        for phrase_id in args:
            if phrase_id in self.settings[server.id]["FILTER"]:
                msg += "`{}`: {}\n".format(
                    phrase_id, 
                    self.settings[server.id]["FILTER"][phrase_id]["TEXT"])
                count += 1
                del self.settings[server.id]["FILTER"][phrase_id]
        if count == 0:
            msg = "Failed to delete any phrases."
        dataIO.save_json(settings_path, self.settings)
        await self.bot.say(msg[:-1])

    @filterban.command(pass_context=True, no_pm=True)
    async def warningmessage(self, ctx, phrase_id, *args: str):
        """Set a custom warning message for a phrase. Provide phrase IDs.
        Provide no phrase to reset to the default.
        
        Supported placeholders:
            {mention} {name} {nick} {id} {discriminator}: Author attributes
            {channel}: Mention of the channel the message was sent in
            {num_g}: The number of global warnings remaining
            {num_p}: The number of warnings remaining for this phrase
            {action_g}: The action to take for global infractions
            {action_p}: The action to take for this phrase
            """
        server = ctx.message.server
        author = ctx.message.author
        if phrase_id not in self.settings[server.id]["FILTER"]:
            await self.bot.say("I couldn't find that phrase ID.")
            return
        if len(args) == 0:
            self.settings[server.id]["FILTER"][str(phrase_id)]["WARNING_MESSAGE"] =\
                    warning_message_default
            await self.bot.say("Message reset.")
        else:
            self.settings[server.id]["FILTER"][str(phrase_id)]["WARNING_MESSAGE"] =\
                    " ".join(args)
            await self.bot.say("Message set. Example:\n" +\
                    " ".join(args).format(
                            mention=author.mention,
                            name=author.name,
                            nick=author.nick,
                            id=author.id,
                            discriminator=author.discriminator,
                            channel=ctx.message.channel.mention,
                            num_g=10,
                            action_g="banned",
                            num_p=3,
                            action_p="kicked"
                        ))
        dataIO.save_json(settings_path, self.settings)

    @filterban.command(pass_context=True, no_pm=True)
    async def getid(self, ctx, phrase):
        """Get the ID of a phrase. This can return IDs that aren't stored."""
        await self.bot.say("`{}`".format(abs(hash(phrase))))

def check_folders():
    if not os.path.exists("data/filterban"):
        print("Creating data/filterban folder...")
        os.makedirs("data/filterban")

def check_files():
    if not dataIO.is_valid_json(settings_path):
        print("Creating default {}...".format(settings_path))
        dataIO.save_json(settings_path, {})

def setup(bot):
    check_folders()
    check_files()
    n = Filterban(bot)
    bot.add_cog(n)
