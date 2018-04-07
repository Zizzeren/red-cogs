import discord
from discord.ext import commands
from cogs.utils import checks
from .utils.dataIO import dataIO
from __main__ import send_cmd_help
import os
from datetime import datetime
import time
import pytz

class AutoInfo:
    """Automatically give user info when someone new joins"""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/autoinfo/settings.json"
        self.users_path = "data/autoinfo/users.json"
        self.invites_path = "data/autoinfo/invites.json"
        self.settings = dataIO.load_json(self.settings_path)
        self.users = dataIO.load_json(self.users_path)
        self.invites = dataIO.load_json(self.invites_path)
        self.units = (("second", 1), ("minute", 60), ("hour", 3600),
                ("day", 86400), ("week", 604800), ("month", 2592000))
        self.userinfo_format = \
"""User joined! {}
```hs
       User: {}#{}
         ID: {}
    Created: {}{}
Account Age: {}{}{}```"""
        self.young_acc_warning_message = \
            "\n    WARNING: This account is only {} old!"
        self.been_here_warning_message = \
            "\n    WARNING: This member left the server {} ago!"
        self.strftime="%Y-%m-%d %H:%M:%S UTC"

    def seconds_to_higher_units(self, seconds):
        """Returns the value of the highest unit"""
        divisor = 1
        units = "second"
        for unit, val in self.units:
            if seconds > val:
                divisor = val
                units = unit
        return "{} {}{}".format(
                seconds // divisor,
                units,
                "s" if seconds // divisor > 1 else "")

    async def _on_member_leave(self, member):
        server = member.server
        if server.id not in self.users:
            self.users[server.id] = {}
        self.users[server.id][member.id] = time.time()
        dataIO.save_json(self.users_path, self.users)

    async def _on_member_join(self, member):
        server = member.server
        invite = None
        inviter = None
        if server.id not in self.invites:
            try:
                server_invites = await self.bot.invites_from(server)
                self.invites[server.id] = \
                        {inv.code: inv.uses for inv in server_invites}
            except discord.errors.Forbidden:
                pass
        else:
            for inv in await self.bot.invites_from(member.server):
                if inv.code not in self.invites[server.id]:
                    self.invites[server.id][inv.code] = inv.uses
                    invite = "{}? (New invite)".format(inv.code)
                    inviter = inv.inviter
                elif int(inv.uses) > int(self.invites[server.id][inv.code]):
                    self.invites[server.id][inv.code] = inv.uses
                    invite = inv.code
                    inviter = inv.inviter
        dataIO.save_json(self.invites_path, self.invites)

        if server.id in self.settings:
            if self.settings[server.id]["CHANNEL"] is not None and \
               self.settings[server.id]["ENABLED"]:
                channel = self.bot.get_channel(
                        self.settings[server.id]["CHANNEL"])
                mention = member.mention
                username = member.name
                discriminator = member.discriminator
                member_id = member.id
                created = member.created_at
                tz = pytz.timezone('NZ')
                created_tzaware = tz.localize(created)
                created_utc = created_tzaware.astimezone(pytz.utc)
                
                now = datetime.utcnow()
                account_age_td = now - created
                account_age = account_age_td.total_seconds()
                account_age_s = self.seconds_to_higher_units(int(account_age))

                young_warning = ""
                if self.settings[server.id]["WARNING_AGE"] is not None:
                    if account_age < self.settings[server.id]["WARNING_AGE"]:
                        young_warning = self.young_acc_warning_message.format(
                                account_age_s)
                
                been_here_warning = ""
                if server.id not in self.users:
                    self.users[server.id] = {}
                    dataIO.save_json(self.users_path, self.users)

                if member.id in self.users[server.id]:
                    leave_datetime = datetime.utcfromtimestamp(
                            self.users[server.id][member.id])
                    leave_datetime_utc = tz.localize(leave_datetime)\
                            .astimezone(pytz.utc)
                    leave_age_tz = now - leave_datetime
                    leave_age = leave_age_tz.total_seconds()
                    leave_age_s = self.seconds_to_higher_units(int(leave_age))

                    been_here_warning = self.been_here_warning_message.format(
                            leave_age_s)

                msg = self.userinfo_format.format(
                    mention,
                    username, discriminator,
                    member_id,
                    created.strftime(self.strftime),
                    "\n     Invite: {}\n Invited By: {}#{} ({})".format(
                        invite,
                        inviter.name, inviter.discriminator, inviter.id
                        ) if invite else "",
                    account_age_s,
                    young_warning,
                    been_here_warning)
                await self.bot.send_message(channel, msg)

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def autoinfo(self, ctx):
        """Change settings for autoinfo
        
        Requires the manage roles permission"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {
                "ENABLED": False,
                "CHANNEL": None,
                "WARNING_AGE": None
            }
            dataIO.save_json(self.settings_path, self.settings)

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            await self.bot.say("Autoinfo is currently {} in channel {}".format(
                "enabled" if self.settings[server.id]["ENABLED"] \
                        else "disabled",
                self.bot.get_channel(
                    self.settings[server.id]["CHANNEL"]).mention if 
                        self.settings[server.id]["CHANNEL"] else "None"))

    @autoinfo.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def toggle(self, ctx, *args: str):
        """Enables/Disables autoinfo"""
        server = ctx.message.server
        new_state = not self.settings[server.id]["ENABLED"]
        if len(args) > 0:
            if args[0].lower() in [ "enable", "enabled", "true" ]:
                new_state = True
            elif args[0].lower() in [ "disable", "disabled", "false" ]:
                new_state = False

        self.settings[server.id]["ENABLED"] = new_state
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Autoinfo is now {}.".format(
            "enabled" if new_state else "disabled"))

    @autoinfo.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def channel(self, ctx, channel: discord.Channel=None):
        """Sets the channel to put userinfo in when a user joins."""
        server = ctx.message.server
        if channel is None:
            channel = ctx.message.channel

        self.settings[server.id]["CHANNEL"] = channel.id
        dataIO.save_json(self.settings_path, self.settings)
        await self.bot.say("Channel for autoinfo set to {}.".format(
            channel.mention))

    @autoinfo.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def warningage(self, ctx, age: int, units: str):
        """Set a minimum account age before I warn about a new account.

        If an account is younger than this age, the autoinfo will
        include a warning. Set to a negative number for no warning."""
        server = ctx.message.server
        units = units.lower()
        s = ""
        if units.endswith("s"):
            units = units[:-1]
            s = "s"
        units_d = dict(self.units)
        if not units in units_d:
            await self.bot.say("Invalid time unit. " +\
                    "Choose seconds/minutes/hours/days/weeks/months")
            return
        seconds = units_d[units] * age

        if age < 0:
            self.settings[server.id]["WARNING_AGE"] = None
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("Disabled warning for young accounts.")
        else:
            self.settings[server.id]["WARNING_AGE"] = seconds
            dataIO.save_json(self.settings_path, self.settings)
            await self.bot.say("I'll warn if an account less than "+\
                    "{} {}{}".format(age, units, s)+\
                    " old joins.")

def check_folders():
    if not os.path.exists("data/autoinfo"):
        print("creating data/autoinfo folder...")
        os.makedirs("data/autoinfo")

def check_files():
    f = "data/autoinfo/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default autoinfo's settings.json...")
        dataIO.save_json(f, {})
    f = "data/autoinfo/users.json"
    if not dataIO.is_valid_json(f):
        print("Creating default autoinfo's users.json...")
        dataIO.save_json(f, {})
    f = "data/autoinfo/invites.json"
    if not dataIO.is_valid_json(f):
        print("Creating default autoinfo's invites.json...")
        dataIO.save_json(f, {})

def setup(bot):
    check_folders()
    check_files()

    n = AutoInfo(bot)
    bot.add_cog(n)
    bot.add_listener(n._on_member_join, "on_member_join")
    bot.add_listener(n._on_member_leave, "on_member_remove")
