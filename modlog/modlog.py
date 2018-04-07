from discord.ext import commands
from cogs.utils import checks
import datetime, pytz
from pytz import timezone
from cogs.utils.dataIO import fileIO, dataIO
import discord
import asyncio
import os
from random import choice, randint

inv_settings = {"Timezone": "UTC",
                "embed": False, "Channel": None, "toggleedit": False, "toggledelete": False, "toggleuser": False,
                "toggleroles": False,
                "togglevoice": False,
                "toggleban": False, "togglejoin": False, "toggleleave": False, "togglechannel": False,
                "toggleserver": False}


class ModLog:
    def __init__(self, bot):
        self.bot = bot
        self.direct = "data/modlogset/settings.json"
        try:
            self.censored_words = dataIO.load_json("data/self-censor.json")
        except:
            self.censored_words = []

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

    @checks.admin_or_permissions(administrator=True)
    @commands.group(name='modlogtoggle', pass_context=True, no_pm=True)
    async def modlogtoggles(self, ctx):
        """toggle which server activity to log"""
        if ctx.invoked_subcommand is None:
            db = fileIO(self.direct, "load")
            server = ctx.message.server
            await self.bot.send_cmd_help(ctx)
            try:
                e = discord.Embed(title="Setting for {}".format(server.name), colour=discord.Colour.blue())
                e.add_field(name="Delete", value=str(db[ctx.message.server.id]['toggledelete']))
                e.add_field(name="Edit", value=str(db[ctx.message.server.id]['toggleedit']))
                e.add_field(name="Roles", value=str(db[ctx.message.server.id]['toggleroles']))
                e.add_field(name="User", value=str(db[ctx.message.server.id]['toggleuser']))
                e.add_field(name="Voice", value=str(db[ctx.message.server.id]['togglevoice']))
                e.add_field(name="Ban", value=str(db[ctx.message.server.id]['toggleban']))
                e.add_field(name="Join", value=str(db[ctx.message.server.id]['togglejoin']))
                e.add_field(name="Leave", value=str(db[ctx.message.server.id]['toggleleave']))
                e.add_field(name="Channel", value=str(db[ctx.message.server.id]['togglechannel']))
                e.add_field(name="Server", value=str(db[ctx.message.server.id]['toggleserver']))
                e.set_thumbnail(url=server.icon_url)
                await self.bot.say(embed=e)
            except KeyError:
                return

    @checks.admin_or_permissions(administrator=True)
    @commands.group(pass_context=True, no_pm=True)
    async def modlogset(self, ctx):
        """Change modlog settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @modlogset.command(pass_context=True,no_pm=True)
    async def timezone(self, ctx, tz):
        """Set the timezone to put in messages."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        try:
            check_tz_exists = pytz.timezone(tz)
        except Exception as e:
            await self.bot.say("That timezone is not recognised. Check the following link to see compliant names: {}".format(
                "<https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>"))
            return
        if server.id not in db:
            db[server.id] = inv_settings
        db[server.id]['Timezone'] = tz
        fileIO(self.direct, "save", db)
        await self.bot.say("Timezone updated.")

    @modlogset.command(name='channel', pass_context=True, no_pm=True)
    async def _channel(self, ctx):
        """Set the channel to send notifications to."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if ctx.message.server.me.permissions_in(ctx.message.channel).send_messages:
            if server.id in db:
                db[server.id]['Channel'] = ctx.message.channel.id
                fileIO(self.direct, "save", db)
                await self.bot.say("Channel changed.")
                return
            if not server.id in db:
                db[server.id] = inv_settings
                db[server.id]["Channel"] = ctx.message.channel.id
                fileIO(self.direct, "save", db)
                await self.bot.say("I will now send toggled modlog notifications here")
        else:
            return

    @modlogset.command(pass_context=True, no_pm=True)
    async def embed(self, ctx):
        """Enables or disables embed modlog."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if db[server.id]["embed"] == False:
            db[server.id]["embed"] = True
            fileIO(self.direct, "save", db)
            await self.bot.say("Enabled embed modlog.")
        elif db[server.id]["embed"] == True:
            db[server.id]["embed"] = False
            fileIO(self.direct, "save", db)
            await self.bot.say("Disabled embed modlog.")

    @modlogset.command(pass_context=True, no_pm=True)
    async def disable(self, ctx):
        """Disables the modlog. Set a channel to enable."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if not server.id in db:
            await self.bot.say("Server not found, use modlogset to set a channnel")
            return
        del db[server.id]
        fileIO(self.direct, "save", db)
        await self.bot.say("I will no longer send modlog notifications here")

    @modlogtoggles.command(pass_context=True, no_pm=True)
    async def edit(self, ctx):
        """Toggles notifications when a member edits their message."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if db[server.id]["toggleedit"] == False:
            db[server.id]["toggleedit"] = True
            fileIO(self.direct, "save", db)
            await self.bot.say("Edit messages enabled")
        elif db[server.id]["toggleedit"] == True:
            db[server.id]["toggleedit"] = False
            fileIO(self.direct, "save", db)
            await self.bot.say("Edit messages disabled")

    @modlogtoggles.command(pass_context=True, no_pm=True)
    async def join(self, ctx):
        """Toggles notifications when a member joins the server."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if db[server.id]["togglejoin"] == False:
            db[server.id]["togglejoin"] = True
            fileIO(self.direct, "save", db)
            await self.bot.say("Enabled join logs.")
        elif db[server.id]['togglejoin'] == True:
            db[server.id]['togglejoin'] = False
            fileIO(self.direct, 'save', db)
            await self.bot.say("Disabled join logs.")

    @modlogtoggles.command(pass_context=True, no_pm=True)
    async def server(self, ctx):
        """Toggles notifications when the server updates."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if db[server.id]["toggleserver"] == False:
            db[server.id]["toggleserver"] = True
            fileIO(self.direct, "save", db)
            await self.bot.say("Enabled server logs.")
        elif db[server.id]['toggleserver'] == True:
            db[server.id]['toggleserver'] = False
            fileIO(self.direct, 'save', db)
            await self.bot.say("Disabled server logs.")

    @modlogtoggles.command(pass_context=True, no_pm=True)
    async def channel(self, ctx):
        """Toggles notifications when a channel updates."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if db[server.id]["togglechannel"] == False:
            db[server.id]["togglechannel"] = True
            fileIO(self.direct, "save", db)
            await self.bot.say("Enabled channel logs.")
        elif db[server.id]['togglechannel'] == True:
            db[server.id]['togglechannel'] = False
            fileIO(self.direct, 'save', db)
            await self.bot.say("Disabled channel logs.")

    @modlogtoggles.command(pass_context=True, no_pm=True)
    async def leave(self, ctx):
        """Toggles notifications when a member leaves the server."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if db[server.id]["toggleleave"] == False:
            db[server.id]["toggleleave"] = True
            fileIO(self.direct, "save", db)
            await self.bot.say("Enabled leave logs.")
        elif db[server.id]['toggleleave'] == True:
            db[server.id]['toggleleave'] = False
            fileIO(self.direct, 'save', db)
            await self.bot.say("Disabled leave logs.")

    @modlogtoggles.command(pass_context=True, no_pm=True)
    async def delete(self, ctx):
        """Toggles notifications when a member deletes their message."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if db[server.id]["toggledelete"] == False:
            db[server.id]["toggledelete"] = True
            fileIO(self.direct, "save", db)
            await self.bot.say("Delete messages enabled")
        elif db[server.id]["toggledelete"] == True:
            db[server.id]["toggledelete"] = False
            fileIO(self.direct, "save", db)
            await self.bot.say("Delete messages disabled")

    @modlogtoggles.command(pass_context=True, no_pm=True)
    async def user(self, ctx):
        """Toggles notifications when a member changes their profile."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if db[server.id]["toggleuser"] == False:
            db[server.id]["toggleuser"] = True
            fileIO(self.direct, "save", db)
            await self.bot.say("User messages enabled")
        elif db[server.id]["toggleuser"] == True:
            db[server.id]["toggleuser"] = False
            fileIO(self.direct, "save", db)
            await self.bot.say("User messages disabled")

    @modlogtoggles.command(pass_context=True, no_pm=True)
    async def roles(self, ctx):
        """Toggles notifications when roles change."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if db[server.id]["toggleroles"] == False:
            db[server.id]["toggleroles"] = True
            fileIO(self.direct, "save", db)
            await self.bot.say("Role messages enabled")
        elif db[server.id]["toggleroles"] == True:
            db[server.id]["toggleroles"] = False
            fileIO(self.direct, "save", db)
            await self.bot.say("Role messages disabled")

    @modlogtoggles.command(pass_context=True, no_pm=True)
    async def voice(self, ctx):
        """Toggles notifications when voice status changes."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if db[server.id]["togglevoice"] == False:
            db[server.id]["togglevoice"] = True
            fileIO(self.direct, "save", db)
            await self.bot.say("Voice messages enabled")
        elif db[server.id]["togglevoice"] == True:
            db[server.id]["togglevoice"] = False
            fileIO(self.direct, "save", db)
            await self.bot.say("Voice messages disabled")

    @modlogtoggles.command(pass_context=True, no_pm=True)
    async def ban(self, ctx):
        """Toggles notifications when a user is banned."""
        server = ctx.message.server
        db = fileIO(self.direct, "load")
        if db[server.id]["toggleban"] == False:
            db[server.id]["toggleban"] = True
            fileIO(self.direct, "save", db)
            await self.bot.say("Ban messages enabled")
        elif db[server.id]["toggleban"] == True:
            db[server.id]["toggleban"] = False
            fileIO(self.direct, "save", db)
            await self.bot.say("Ban messages disabled")

    async def on_message_delete(self, message):
        server = message.server
        db = fileIO(self.direct, "load")
        if not server.id in db:
            return
        if db[server.id]['toggledelete'] == False:
            return
        if message.author is message.author.bot:
            pass
        channel = db[server.id]["Channel"]
        tz = timezone(db[server.id]["Timezone"])
        time = datetime.datetime.now(tz)
        cleanmsg = message.content
        for i in message.mentions:
            cleanmsg = cleanmsg.replace(i.mention, str(i))
        attachments = None
        if len(message.attachments) != 0:
            attachments = [a['url'] for a in message.attachments]
        fmt = '%H:%M:%S'
        if db[server.id]["embed"] == True:
            name = message.author
            if type(name) == discord.Member:
                if name.nick:
                    name = " ~ ".join((name.name, name.nick))
                else:
                    name = name.name
            else:
                name = name.name
            delmessage = discord.Embed(description=name, colour=discord.Color.purple())
            infomessage = "A message by __{}__, was deleted in {}".format(
                message.author.nick if message.author.nick else message.author.name, message.channel.mention)
            delmessage.add_field(name="Info:", value=infomessage, inline=False)
            if len(cleanmsg) != 0:
                delmessage.add_field(name="Message:", value=self.censor(cleanmsg))
            if attachments is not None:
                delmessage.add_field(name="Attachments:", value = "\n".join(attachments))
            delmessage.set_footer(text="User ID: {}".format(message.author.id))
            delmessage.set_author(name="{} {} - Deleted Message".format(time.strftime(fmt), tz), url="http://i.imgur.com/fJpAFgN.png")
            delmessage.set_thumbnail(url="http://i.imgur.com/fJpAFgN.png")
            try:
                await self.bot.send_message(server.get_channel(channel), embed=delmessage)
            except Exception as e:
                print("Modlog - Failed to send embed")
                print(e)
                pass
        else:
            msg = ":pencil: `{} {}` **Channel** {} **{}'s** message has been deleted. Content: {}".format(
                time.strftime(fmt), tz, message.channel.mention, message.author, self.censor(cleanmsg))
            if attachments is not None:
                msg += "\nAttachments:\n{}".format("\n".join(attachments))
            await self.bot.send_message(server.get_channel(channel),
                                        msg)

    async def on_member_join(self, member):
        server = member.server
        db = fileIO(self.direct, 'load')
        if not server.id in db:
            return
        if db[server.id]['togglejoin'] == False:
            return
        channel = db[server.id]["Channel"]
        tz = timezone(db[server.id]["Timezone"])
        time = datetime.datetime.now(tz)
        fmt = '%H:%M:%S'
        users = len([e.name for e in server.members])
        if db[server.id]["embed"] == True:
            name = member
            name = " ~ ".join((name.name, name.nick)) if name.nick else name.name
            joinmsg = discord.Embed(description=name, colour=discord.Color.red())
            infomessage = "__{}__ has joined the server.".format(member.nick if member.nick else member.name)
            joinmsg.add_field(name="Info:", value=infomessage, inline=False)
            joinmsg.set_footer(text="User ID: {}".format(member.id))
            joinmsg.set_author(name="{} {} - Joined User".format(time.strftime(fmt), tz),
                               url="http://www.emoji.co.uk/files/twitter-emojis/objects-twitter/11031-inbox-tray.png")
            joinmsg.set_thumbnail(
                url="http://www.emoji.co.uk/files/twitter-emojis/objects-twitter/11031-inbox-tray.png")
            try:
                await self.bot.send_message(server.get_channel(channel), embed=joinmsg)
            except:
                pass
        if db[server.id]["embed"] == False:
            msg = ":white_check_mark: `{} {}` **{}** joined the server. Total users: {}.".format(time.strftime(fmt), tz,
                                                                                            member.name, users)
            await self.bot.send_message(server.get_channel(channel), msg)

    async def on_member_remove(self, member):
        server = member.server
        db = fileIO(self.direct, 'load')
        if not server.id in db:
            return
        if db[server.id]['toggleleave'] == False:
            return
        channel = db[server.id]["Channel"]
        tz = timezone(db[server.id]["Timezone"])
        time = datetime.datetime.now(tz)
        fmt = "%H:%M:%S"
        users = len([e.name for e in server.members])
        if db[server.id]["embed"] == True:
            name = member
            name = " ~ ".join((name.name, name.nick)) if name.nick else name.name
            leave = discord.Embed(description=name, colour=discord.Color.red())
            infomessage = "__{}__ has left the server.".format(member.nick if member.nick else member.name)
            leave.add_field(name="Info:", value=infomessage, inline=False)
            leave.set_footer(text="User ID: {}".format(member.id))
            leave.set_author(name="{} {} - User Left".format(time.strftime(fmt), tz),
                             url="http://www.emoji.co.uk/files/mozilla-emojis/objects-mozilla/11928-outbox-tray.png")
            leave.set_thumbnail(url="http://www.emoji.co.uk/files/mozilla-emojis/objects-mozilla/11928-outbox-tray.png")
            try:
                await self.bot.send_message(server.get_channel(channel), embed=leave)
            except:
                pass
        if db[server.id]["embed"] == False:
            msg = ":x: `{} {}` **{}** has left the server or was kicked. Total members {}.".format(time.strftime(fmt), tz,
                                                                                                member.name, users)
            await self.bot.send_message(server.get_channel(channel), msg)

    async def on_channel_update(self, before, after):
        server = before.server
        db = fileIO(self.direct, 'load')
        if not server.id in db:
            return
        if db[server.id]['togglechannel'] == False:
            return
        channel = db[server.id]["Channel"]
        tz = timezone(db[server.id]["Timezone"])
        time = datetime.datetime.now(tz)
        fmt = "%H:%M:%S"
        msg = ""
        if before.name != after.name:
            if before.type == discord.ChannelType.voice:
                if db[server.id]["embed"] == True:
                    fmt = "%H:%M:%S"
                    voice1 = discord.Embed(colour=discord.Color.blue())
                    infomessage = ":loud_sound: Voice channel name update. Before: **{}** After: **{}**.".format(
                        before.name, after.name)
                    voice1.add_field(name="Info:", value=infomessage, inline=False)
                    voice1.set_author(name="{} {} - Voice Channel Update".format(time.strftime(fmt), tz),
                                      icon_url="http://www.hey.fr/fun/emoji/twitter/en/icon/twitter/565-emoji_twitter_speaker_with_three_sound_waves.png")
                    voice1.set_thumbnail(
                        url="http://www.hey.fr/fun/emoji/twitter/en/icon/twitter/565-emoji_twitter_speaker_with_three_sound_waves.png")
                    try:
                        await self.bot.send_message(server.get_channel(channel), embed=voice1)
                    except:
                        pass
                else:
                    fmt = "%H:%M:%S"
                    await self.bot.send_message(server.get_channel(channel),
                                                ":loud_sound: `{} {}` Voice channel name update. Before: **{}** After: **{}**.".format(
                                                    time.strftime(fmt), tz, before.name, after.name))
            if before.type == discord.ChannelType.text:
                if db[server.id]["embed"] == True:
                    fmt = "%H:%M:%S"
                    text1 = discord.Embed(colour=discord.Color.blue())
                    infomessage = ":loud_sound: Text channel name update. Before: **{}** After: **{}**.".format(
                        before.name, after.name)
                    text1.add_field(name="Info:", value=infomessage, inline=False)
                    text1.set_author(name="{} {} - Voice Channel Update".format(time.strftime(fmt), tz),
                                     icon_url="https://s-media-cache-ak0.pinimg.com/originals/27/18/77/27187782801d15f756a27156105d1233.png")
                    text1.set_thumbnail(
                        url="https://s-media-cache-ak0.pinimg.com/originals/27/18/77/27187782801d15f756a27156105d1233.png")
                    await self.bot.send_message(server.get_channel(channel), embed=text1)
                else:
                    fmt = "%H:%M:%S"
                    await self.bot.send_message(server.get_channel(channel),
                                                ":page_facing_up: `{} {}` Text channel name update. Before: **{}** After: **{}**.".format(
                                                    time.strftime(fmt), tz, before.name, after.name))
        if before.topic != after.topic:
            if db[server.id]["embed"] == True:
                fmt = "%H:%M:%S"
                topic = discord.Embed(colour=discord.Colour.blue())
                infomessage = ":page_facing_up: `{} {}` Channel topic has been updated.\n**Before:** {}\n**After:** {}".format(
                    time.strftime(fmt), tz, before.topic, after.topic)
                topic.add_field(name="Info:", value=infomessage, inline=False)
                topic.set_author(name="{} {} - Channel Topic Update".format(time.strftime(fmt), tz),
                                 icon_url="https://s-media-cache-ak0.pinimg.com/originals/27/18/77/27187782801d15f756a27156105d1233.png")
                topic.set_thumbnail(
                    url="https://s-media-cache-ak0.pinimg.com/originals/27/18/77/27187782801d15f756a27156105d1233.png")
                try:
                    await self.send_message(server.get_channel(channel), embed=topic)
                except:
                    pass
            else:
                fmt = "%H:%M:%S"
                await self.bot.send_message(server.get_channel(channel),
                                            ":page_facing_up: `{} {}` Channel topic has been updated.\n**Before:** {}\n**After:** {}".format(
                                                time.strftime(fmt), tz, before.topic, after.topic))
        if before.position != after.position:
            if before.type == discord.ChannelType.voice:
                if db[server.id]["embed"] == True:
                    fmt = "%H:%M:%S"
                    voice2 = discord.Embed(colour=discord.Colour.blue())
                    voice2.set_thumbnail(
                        url="http://www.hey.fr/fun/emoji/twitter/en/icon/twitter/565-emoji_twitter_speaker_with_three_sound_waves.png")
                    voice2.set_author(name="{} {} - Voice Channel Position Update".format(time.strftime(fmt), tz),
                                      icon_url="http://www.hey.fr/fun/emoji/twitter/en/icon/twitter/565-emoji_twitter_speaker_with_three_sound_waves.png")
                    infomsg = ":loud_sound: Voice channel position update. Channel: **{}** Before: **{}** After: **{}**.".format(
                        before.name, before.position, after.position)
                    voice2.add_field(name="Info:", value=infomsg, inline=False)
                    try:
                        await self.bot.send_message(server.get_channel(channel), embed=voice2)
                    except:
                        pass
                else:
                    fmt = "%H:%M:%S"
                    await self.bot.send_message(server.get_channel(channel),
                                                ":loud_sound: `{} {}` Voice channel position update. Channel: **{}** Before: **{}** After: **{}**.".format(
                                                    time.strftime(fmt), tz, before.name, before.position, after.position))
            if before.type == discord.ChannelType.text:
                if db[server.id]["embed"] == True:
                    fmt = "%H:%M:%S"
                    text2 = discord.Embed(colour=discord.Colour.blue())
                    text2.set_thumbnail(
                        url="https://s-media-cache-ak0.pinimg.com/originals/27/18/77/27187782801d15f756a27156105d1233.png")
                    text2.set_author(name="{} {} - Text Channel Position Update".format(time.strftime(fmt), tz),
                                     icon_url="https://s-media-cache-ak0.pinimg.com/originals/27/18/77/27187782801d15f756a27156105d1233.png")
                    infomsg = ":page_facing_up: Text channel position update. Before: **{}** After: **{}**.".format(
                        before.position, after.position)
                    text2.add_field(name="Info:", value=infomsg, inline=False)
                    try:
                        await self.bot.send_message(server.get_channel(channel), embed=text2)
                    except:
                        pass
                else:
                    fmt = "%H:%M:%S"
                    await self.bot.send_message(server.get_channel(channel),
                                                ":page_facing_up: `{} {}` Text channel position update. Channel: **{}** Before: **{}** After: **{}**.".format(
                                                    time.strftime(fmt), tz, before.name, before.position, after.position))
        if before.bitrate != after.bitrate:
            if db[server.id]["embed"] == True:
                fmt = "%H:%M:%S"
                bitrate = discord.Embed(colour=discord.Colour.blue())
                bitrate.set_author(name="{} {} - Voice Channel Bitrate Update".format(time.strftime(fmt), tz),
                                   icon_url="http://www.hey.fr/fun/emoji/twitter/en/icon/twitter/565-emoji_twitter_speaker_with_three_sound_waves.png")
                bitrate.set_thumbnail(
                    url="http://www.hey.fr/fun/emoji/twitter/en/icon/twitter/565-emoji_twitter_speaker_with_three_sound_waves.png")
                infomsg = ":loud_sound: Voice Channel bitrate update. Before: **{}** After: **{}**.".format(
                    before.bitrate, after.bitrate)
                bitrate.add_field(name="Info:", value=infosg, inline=False)
                try:
                    await sef.bot.send_message(server.get_channel(channel), embed=bitrate)
                except:
                    pass
            else:
                await self.bot.send_message(server.get_channel(channel),
                                            ":loud_sound: `{} {}` Channel bitrate update. Before: **{}** After: **{}**.".format(
                                                time.strftime(fmt), tz, before.bitrate, after.bitrate))

    async def on_message_edit(self, before, after):
        server = before.server
        db = fileIO(self.direct, "load")
        if not server.id in db:
            return
        if db[server.id]['toggleedit'] == False:
            return
        if before.content == after.content:
            return
        if before.author.bot:
            return
        cleanbefore = before.content
        for i in before.mentions:
            cleanbefore = cleanbefore.replace(i.mention, str(i))
        cleanafter = after.content
        for i in after.mentions:
            cleanafter = cleanafter.replace(i.mention, str(i))
        channel = db[server.id]["Channel"]
        tz = timezone(db[server.id]["Timezone"])
        time = datetime.datetime.now(tz)
        fmt = '%H:%M:%S'
        if db[server.id]["embed"] == True:
            name = before.author
            name = " ~ ".join((name.name, name.nick)) if name.nick else name.name
            delmessage = discord.Embed(description=name, colour=discord.Color.green())
            infomessage = "A message by __{}__, was edited in {}".format(
                before.author.nick if before.author.nick else before.author.name, before.channel.mention)
            delmessage.add_field(name="Info:", value=infomessage, inline=False)
            delmessage.add_field(name="Before Message:", value=self.censor(cleanbefore), inline=False)
            delmessage.add_field(name="After Message:", value=self.censor(cleanafter))
            delmessage.set_footer(text="User ID: {}".format(before.author.id))
            delmessage.set_author(name="{} {} - Edited Message".format(time.strftime(fmt),tz), url="http://i.imgur.com/Q8SzUdG.png")
            delmessage.set_thumbnail(url="http://i.imgur.com/Q8SzUdG.png")
            try:
                await self.bot.send_message(server.get_channel(channel), embed=delmessage)
            except:
                pass
        else:
            msg = ":pencil: `{} {}` **Channel**: {} **{}'s** message has been edited.\nBefore: {}\nAfter: {}".format(
                time.strftime(fmt), tz, before.channel.mention, before.author, self.censor(cleanbefore), self.censor(cleanafter))
            await self.bot.send_message(server.get_channel(channel),
                                        msg)

    async def on_server_update(self, before, after):
        server = before
        db = fileIO(self.direct, "load")
        if not server.id in db:
            return
        if db[server.id]['toggleserver'] == False:
            return
        if before.bot:
            return
        channel = db[server.id]["Channel"]
        tz = timezone(db[server.id]["Timezone"])
        time = datetime.datetime.now(tz)
        fmt = '%H:%M:%S'
        if before.name != after.name:
            msg = ":globe_with_meridians: `{} {}` Server name update. Before: **{}** After: **{}**.".format(
                time.strftime(fmt), tz, before.name, after.name)
        if before.region != after.region:
            msg = ":globe_with_meridians: `{} {}` Server region update. Before: **{}** After: **{}**.".format(
                time.strftime(fmt), tz, before.region, after.region)
        await self.bot.send_message(server.get_channel(channel), msg)

    async def on_voice_state_update(self, before, after):
        server = before.server
        db = fileIO(self.direct, "load")
        if not server.id in db:
            return
        if db[server.id]['togglevoice'] == False:
            return
        if before.bot:
            return
        channel = db[server.id]["Channel"]
        tz = timezone(db[server.id]["Timezone"])
        time = datetime.datetime.now(tz)
        fmt = '%H:%M:%S'
        if db[server.id]["embed"] == True:
            name = before
            name = " ~ ".join((name.name, name.nick)) if name.nick else name.name
            updmessage = discord.Embed(description=name, colour=discord.Color.blue())
            infomessage = "__{}__'s voice status has changed".format(before.name)
            updmessage.add_field(name="Info:", value=infomessage, inline=False)
            updmessage.add_field(name="Voice Channel Before:", value=before.voice_channel)
            updmessage.add_field(name="Voice Channel After:", value=after.voice_channel)
            updmessage.set_footer(text="User ID: {}".format(before.id))
            updmessage.set_author(name="{} {} - Voice Channel Changed".format(time.strftime(fmt), tz),
                                  url="http://i.imgur.com/8gD34rt.png")
            updmessage.set_thumbnail(url="http://i.imgur.com/8gD34rt.png")
            try:
                await self.bot.send_message(server.get_channel(channel), embed=updmessage)
            except:
                pass
        else:
            await self.bot.send_message(server.get_channel(channel),
                                        ":person_with_pouting_face::skin-tone-3: `{} {}` **{}'s** voice status has updated. **Channel**: {}\n**Local Mute:** {} **Local Deaf:** {} **Server Mute:** {} **Server Deaf:** {}".format(
                                            time.strftime(fmt), tz, after.name, after.voice_channel, after.self_mute,
                                            after.self_deaf, after.mute, after.deaf))

    async def on_member_update(self, before, after):
        server = before.server
        db = fileIO(self.direct, "load")
        if not server.id in db:
            return
        if db[server.id]['toggleuser'] and db[server.id]['toggleroles'] == False:
            return
        channel = db[server.id]["Channel"]
        tz = timezone(db[server.id]["Timezone"])
        time = datetime.datetime.now(tz)
        fmt = '%H:%M:%S'
        if not before.nick == after.nick:
            if db[server.id]["embed"] == True:
                name = before
                name = " ~ ".join((name.name, name.nick)) if name.nick else name.name
                updmessage = discord.Embed(description=name, colour=discord.Color.orange())
                infomessage = "__{}__'s nickname has changed".format(before.name)
                updmessage.add_field(name="Info:", value=infomessage, inline=False)
                updmessage.add_field(name="Nickname Before:", value=before.nick)
                updmessage.add_field(name="Nickname After:", value=after.nick)
                updmessage.set_footer(text="User ID: {}".format(before.id))
                updmessage.set_author(name="{} {} - Nickname Changed".format(time.strftime(fmt), tz),
                                      url="http://i.imgur.com/I5q71rj.png")
                updmessage.set_thumbnail(url="http://i.imgur.com/I5q71rj.png")
                try:
                    await self.bot.send_message(server.get_channel(channel), embed=updmessage)
                except:
                    pass
            else:
                await self.bot.send_message(server.get_channel(channel),
                                            ":person_with_pouting_face::skin-tone-3: `{} {}` **{}** changed their nickname from **{}** to **{}**".format(
                                                time.strftime(fmt), tz, before.name, before.kick, after.nick))

#    async def on_member_update(self, before, after):
#        server = before.server
#        db = fileIO(self.direct, "load")
#        if not server.id in db:
#            return
#        if db[server.id]['toggleuser'] and db[server.id]['toggleroles'] == False:
#            return
#        channel = db[server.id]["Channel"]
#        time = datetime.datetime.now()
#        fmt = '%H:%M:%S'
#        if not before.roles == after.roles:
#            if db[server.id]["embed"] == True:
#                name = member
#                name = " ~ ".join((name.name, name.nick)) if name.nick else name.name
#                role = discord.Embed(description=name, colour=discord.Color.red())
#                infomessage = "__{}__ has left the server.".format(member.nick if member.nick else member.name)
#                role.add_field(name="Info:", value=infomessage, inline=False)
#                role.set_footer(text="User ID: {}".format(member.id))
#                role.set_author(name=time.strftime(fmt) + " - Leaving User",
#                                url="http://www.emoji.co.uk/files/mozilla-emojis/objects-mozilla/11928-outbox-tray.png")
#                role.set_thumbnail(
#                    url="http://www.emoji.co.uk/files/mozilla-emojis/objects-mozilla/11928-outbox-tray.png")
#                try:
#                    await self.bot.send_message(server.get_channel(channel), embed=leave)
#                except:
#                    await self.bot.send_message(server.get_channel(channel),
#                                                "How is embed going to work when I don't have embed links permissions?")
#            if db[server.id]["embed"] == False:
#                msg = ":person_with_pouting_face::skin-tone-3: `{}` **{}'s** roles have changed. Old: `{}` New: `{}`".format(
#                    time.strftime(fmt), before.name, ", ".join([r.name for r in before.roles]),
#                    ", ".join([r.name for r in after.roles]))
#                await self.bot.send_message(server.get_channel(channel),
#                                            msg)

    async def on_member_ban(self, member):
        server = member.server
        db = fileIO(self.direct, "load")
        if not server.id in db:
            return
        if db[server.id]['toggleban'] == False:
            return
        channel = db[server.id]["Channel"]
        tz = timezone(db[server.id]["Timezone"])
        time = datetime.datetime.now(tz)
        fmt = '%H:%M:%S'
        if db[server.id]["embed"] == True:
            name = member
            name = " ~ ".join((name.name, name.nick)) if name.nick else name.name
            banmessage = discord.Embed(description=name, colour=discord.Color.red())
            infomessage = "__{}__ has been banned from the server.".format(member.nick if member.nick else member.name)
            banmessage.add_field(name="Info:", value=infomessage, inline=False)
            banmessage.set_footer(text="User ID: {}".format(member.id))
            banmessage.set_author(name="{} {} - Banned User".format(time.strftime(fmt), tz), url="http://i.imgur.com/Imx0Znm.png")
            banmessage.set_thumbnail(url="http://i.imgur.com/Imx0Znm.png")
            try:
                await self.bot.send_message(server.get_channel(channel), embed=banmessage)
            except:
                await self.bot.send_message(server.get_channel(channel),
                                            "How is embed modlog going to work when I don't have embed links permissions?")
        else:
            msg = ":hammer: `{} {}` {}({}) has been banned!".format(time.strftime(fmt), tz, member, member.id)
            await self.bot.send_message(server.get_channel(channel),
                                        msg)


def check_folder():
    if not os.path.exists('data/modlogset'):
        print('Creating data/modlogset folder...')
        os.makedirs('data/modlogset')


def check_file():
    f = 'data/modlogset/settings.json'
    if not fileIO(f, 'check'):
        print('Creating default settings.json...')
        fileIO(f, 'save', {})


def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(ModLog(bot))
