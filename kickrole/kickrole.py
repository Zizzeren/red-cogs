from discord.ext import commands
import discord
from .utils import checks
from .utils.dataIO import dataIO
import os
import asyncio


class KickRole():
    """Allows kicking users by role. Code borrowed from palmtree5's banrole"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(kick_members=True)
    async def kickrole(self, ctx, role: discord.Role):
        """Kicks all members with the specified role.
        Make sure the bot's role is higher in the role
        hierarchy than the role you want it to kick"""
        server = ctx.message.server
        members_to_kick = [m for m in server.members if role in m.roles]

        kick_count = 0
        total_count = len(members_to_kick)
        msg = await self.bot.say("{}/{} members kicked.".format(kick_count, total_count))
        for member in members_to_kick:
            try:
                await self.bot.kick(member)
            except discord.Forbidden:
                await self.bot.say("I'm not allowed to do that.")
                return
            except Exception as e:
                print(e)
                await self.bot.say("An error occurred. Check your console or logs for details")
            else:
                kick_count += 1
                msg = await self.bot.edit_message(msg, "{}/{} members kicked.".format(kick_count, total_count))

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def bulkremoverole(self, ctx, role: discord.Role):
        server = ctx.message.server
        members = [m for m in server.members if role in m.roles]

        remove_count = 0
        total_count = len(members)

        msg = await self.bot.say("Removed {} from {}/{} members.".format(
            role.name, remove_count, total_count))

        for member in members:
            try:
                await self.bot.remove_roles(member, role)
            except discord.Forbidden:
                await self.bot.say("I'm not allowed to do that.")
                return
            except Exception as e:
                print(e)
                await self.bot.say("An error occurred. Check your console or logs for details")
            else:
                remove_count += 1
                msg = await self.bot.edit_message(msg,
                        "Removed {} from {}/{} members.".format(
                            role.name, remove_count, total_count))


def setup(bot):
    n = KickRole(bot)
    bot.add_cog(n)
