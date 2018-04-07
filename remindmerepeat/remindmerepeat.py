import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import os
import asyncio
import time
import datetime
import logging

class RemindMeRepeat:
    """Never forget anything anymore."""

    def __init__(self, bot):
        self.bot = bot
        self.reminders = fileIO("data/remindmerepeat/reminders.json", "load")
        self.units = {"second" : 1, "minute" : 60, "hour" : 3600, "day" : 86400, "week": 604800, "month": 2592000, "year" : 31536000}

    @commands.command(pass_context=True)
    async def schedule(self, ctx, here : str, start : str, quantity : int, time_unit : str, *text : str):
        """Sends you <text> when the time is up, then repeats it after the same duration ad infinitum.
        Use [p]override to cancel all notifications that you set up.

        <here> should be the exact string "here" if you want the reminder in
        this channel. Put anything else if you want a PM.

        Accepts: seconds, minutes, hours, days, weeks, months, years
        <start> is a date and time to start the notifications, in the exact
        format YYYY-MM-DD:HH:MM (Using 24 hour time), or "now".

        Example:
        [p]schedule nothere 2016-09-04:20:30 3 days Give cookies to Zizzeren
        This will give you a reminder beginning the 4th of September, 2016, 
        at 8:30pm bot time, repeating every 3 days at that time."""
        text = " ".join(text)
        time_unit = time_unit.lower()
        author = ctx.message.author
        s = ""
        
        if time_unit.endswith("s"):
            time_unit = time_unit[:-1]
            s = "s"          
        if not time_unit in self.units:
            await self.bot.say("Invalid time unit. Choose seconds/minutes/hours/days/weeks/months/years")
            return
        if quantity < 1:
            await self.bot.say("Quantity must not be 0 or negative.")
            return
        if len(text) > 1960:
            await self.bot.say("Text is too long.")
            return
        try:
            start = datetime.datetime.strptime(start, "%Y-%m-%d:%H:%M")
        except (ValueError):
            if start == "now":
                start = datetime.datetime.now()
            else:
                await self.bot.say("Start date is invalid. Need format `YYYY-MM-DD:HH:MM`, or `now`.")
                return
        channel = None
        if here == "here":
            channel = ctx.message.channel.id

        seconds = self.units[time_unit] * quantity
        future = int(start.timestamp() + seconds)
        
        self.reminders.append({"ID" : author.id, "CHANNEL" : channel, "DURATION" : seconds, "FUTURE" : future, "TEXT" : text})
        
        logger.info("{} ({}) set a reminder.".format(author.name, author.id))
        await self.bot.say("I will remind you of that every {} {} from {}.".format(str(quantity), time_unit + s, start.strftime("%Y-%m-%d:%H:%M")))
        
        fileIO("data/remindmerepeat/reminders.json", "save", self.reminders)

    @commands.command(pass_context=True)
    async def override(self, ctx):
        """Removes all your upcoming notifications"""
        author = ctx.message.author
        to_remove = []
        for reminder in self.reminders:
            if reminder["ID"] == author.id:
                to_remove.append(reminder)

        if not to_remove == []:
            for reminder in to_remove:
                self.reminders.remove(reminder)
            fileIO("data/remindmerepeat/reminders.json", "save", self.reminders)
            await self.bot.say("All your notifications have been removed.")
        else:
            await self.bot.say("You don't have any upcoming notification.")

    @commands.command(pass_context=True)
    async def time(self, ctx):
        """What time is it for me?"""
        await self.bot.say("The time here is {}!".format(datetime.datetime.now()))

    async def check_reminders(self):
        while "RemindMeRepeat" in self.bot.cogs:
            to_remove = []
            for reminder in self.reminders:
                if reminder["FUTURE"] <= int(time.time()):
                    try:
                        if reminder["CHANNEL"] is not None:
                            await self.bot.send_message(self.bot.get_channel(reminder["CHANNEL"]), "I was asked to remind you of this:\n{}".format(reminder["TEXT"]))
                        else:
                            await self.bot.send_message(discord.User(id=reminder["ID"]), "You asked me to remind you this:\n{}".format(reminder["TEXT"]))
                    except (discord.errors.Forbidden, discord.errors.NotFound):
                        to_remove.append(reminder)
                    except discord.errors.HTTPException:
                        pass
                    else:
                        to_remove.append(reminder)
            for reminder in to_remove:
                self.reminders.remove(reminder)
                future = int(time.time() + reminder["DURATION"])
                self.reminders.append({"ID" : reminder["ID"], "CHANNEL" : reminder["CHANNEL"], "DURATION" : reminder["DURATION"], "FUTURE" : future, "TEXT" : reminder["TEXT"]})
            if to_remove:
                fileIO("data/remindmerepeat/reminders.json", "save", self.reminders)
            await asyncio.sleep(5)

def check_folders():
    if not os.path.exists("data/remindmerepeat"):
        print("Creating data/remindmerepeat folder...")
        os.makedirs("data/remindmerepeat")

def check_files():
    f = "data/remindmerepeat/reminders.json"
    if not fileIO(f, "check"):
        print("Creating empty reminders.json...")
        fileIO(f, "save", [])

def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("remindmerepeat")
    if logger.level == 0: # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='data/remindmerepeat/reminders.log', encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    n = RemindMeRepeat(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.check_reminders())
    bot.add_cog(n)
