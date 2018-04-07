import discord
from discord.ext import commands
from discord.ext.commands import Bot
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
import os
import logging

old_dispatch = None

class Stats:
    """Collects stats about command usage"""

    def __init__(self, bot):
        self.bot = bot

    async def on_command(self, command, ctx):
        caller = ctx.message.author
        channel = ctx.message.channel
        server = ctx.message.server
        cmd_name = command.qualified_name
        cmd_cog = command.cog_name
        subcommand = ctx.subcommand_passed
        content = ctx.message.content
        parsable_logger.info("{};{};{};{};{};{}".format(
            "{}#{}({})".format(caller.name,caller.discriminator,caller.id),
            "{}({})".format(channel.name,channel.id) if channel else "None",
            "{}({})".format(server.name,server.id) if server else "None",
            "{} {}".format(cmd_name, subcommand) if subcommand else cmd_name,
            cmd_cog,
            content
            ))
        logger.info('"{}" in channel "{}" in server "{}" called command "{}" from cog "{}", in message "{}"'.format(
            "{}#{}({})".format(caller.name,caller.discriminator,caller.id),
            "{}({})".format(channel.name,channel.id) if channel else "None",
            "{}({})".format(server.name,server.id) if server else "None",
            "{} {}".format(cmd_name, subcommand) if subcommand else cmd_name,
            cmd_cog,
            content
            ))

def check_folders():
    folder = 'data/stats'
    if not os.path.exists(folder):
        print("Creating data/stats/ folder...")
        os.makedirs(folder)

def setup(bot):
    global logger
    global parsable_logger
    check_folders()
    logger = logging.getLogger("stats")
    parsable_logger = logging.getLogger("stats_parsable")
    if logger.level == 0:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename='data/stats/commands.log',encoding='utf-8',mode='a')
        handler.setFormatter(
            logging.Formatter('%(asctime)s %(message)s'))
        logger.addHandler(handler)
    if parsable_logger.level == 0:
        parsable_logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename='data/stats/commands_parsable.log',encoding='utf-8',mode='a')
        handler.setFormatter(
            logging.Formatter('%(asctime)s;%(message)s'))
        parsable_logger.addHandler(handler)
    n = Stats(bot)
    #bot.add_listener(n.on_command, "on_command")
    bot.add_cog(n)
