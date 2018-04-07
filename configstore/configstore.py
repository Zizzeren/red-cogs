import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
import os
import re
import requests
import urllib
import html
from fuzzywuzzy import fuzz

desktop_config_info = { 
    "name": "Desktop Configuration",
    "categories": [ 
        { "description": "Full controller support" } ],
    "developers": [ "Valve" ],
    "platforms": {
        "linux": True,
        "mac": True,
        "windows": True },
    "image":"http://cdn.akamai.steamstatic.com/steam/apps/353370/header.jpg",
    "short_description":
        "This configuration is used when no games are running."
    }
bpm_info = { 
    "name": "Big Picture Mode",
    "categories": [ 
        { "description": "Full controller support" } ],
    "developers": [ "Valve" ],
    "platforms": {
        "linux": True,
        "mac": True,
        "windows": True },
    "image":"https://cdn.discordapp.com/attachments/"+\
        "155070864222715904/310907469297745920/unknown.png",
    "short_description":
        "This configuration is used in Big Picture Mode."
    }
chord_info = {
    "name": "Steam Chord Configuration",
    "categories": [ 
        { "description": "Full controller support" } ],
    "developers": [ "Valve" ],
    "platforms": {
        "linux": True,
        "mac": True,
        "windows": True },
    "image":"",
    "short_description":
        "This configuration is used when the guide button is held."
    }

valid_link_regex_steam = re.compile(
        "^steam:\/\/controllerconfig\/[0-9]+\/[0-9]+$")
valid_link_regex_nonsteam = re.compile(
        "^steam:\/\/controllerconfig\/[a-zA-Z0-9%]+\/[0-9]+$")

webapi_storeinfo = "http://store.steampowered.com/api/appdetails?appids={}"

full_support_emoji = "<:ButtonA:230124566637314049>"
partial_support_emoji = \
        "<:APressIsAPressUCantSayItsHalf:269749772745703445>"
no_support_emoji = "<:SCangry:332229124502454283>"
nonsteam_emoji = "\u2753"

fuzzy_partial_ratio_threshold = 75

embed_interaction_timeout = 60
embed_row_limit = 10

class ConfigStore:
    """Stores steam controller configs for games."""

    def __init__(self, bot):
        self.bot = bot
        self.configs = fileIO("data/configstore/configs.json", "load")

    async def print_config_info(self, appid):
        if not appid in self.configs:
            await self.bot.say("Couldn't find that game. " +
                               "Be the first to add a config for it!")
            return

        # Make a message describing how much controller support the game has.
        controller_support_msg = "{} {} controller support!"
        if self.configs[appid]["controller_support"] == "full":
            controller_support_msg = controller_support_msg.format(
                    full_support_emoji, "Full")
        elif self.configs[appid]["controller_support"] == "partial":
            controller_support_msg = controller_support_msg.format(
                    partial_support_emoji, "Partial")
        elif self.configs[appid]["controller_support"] == "none":
            controller_support_msg = controller_support_msg.format(
                    no_support_emoji, "No")
        elif self.configs[appid]["controller_support"] == "nonsteam":
            controller_support_msg = "This is a non-steam game."

        embed = discord.Embed(title=self.configs[appid]["name"],
            color=0x000837)
        if self.configs[appid]["short_description"] != "":
            embed.add_field(name="Short Description", 
                    value=html.unescape(
                        self.configs[appid]["short_description"]))
        embed.add_field(name="{} config{} found!".format(
            len(self.configs[appid]["configs"]),
            "s" if len(self.configs[appid]["configs"]) != 1 else ""),
            value="{}\n{}".format(controller_support_msg,
                "\n".join(self.configs[appid]["configs"])))

        if "image" in self.configs[appid]:
            if self.configs[appid]["image"] != "":
                embed.set_thumbnail(url=self.configs[appid]["image"])

        await self.bot.say(embed=embed)

    async def short_game_info(self, appid):
        if not appid in self.configs:
            return None

        # Make a message describing how much controller support the game has.
        controller_support_msg = "Controller support: {} {}"
        if self.configs[appid]["controller_support"] == "full":
            controller_support_msg = controller_support_msg.format(
                    full_support_emoji, "Full")
        elif self.configs[appid]["controller_support"] == "partial":
            controller_support_msg = controller_support_msg.format(
                    partial_support_emoji, "Partial")
        elif self.configs[appid]["controller_support"] == "none":
            controller_support_msg = controller_support_msg.format(
                    no_support_emoji, "No")
        elif self.configs[appid]["controller_support"] == "nonsteam":
            controller_support_msg = "{} Non-steam game.".format(
                    nonsteam_emoji)

        return "**{}**: {} config{}. {}".format(
                self.configs[appid]["name"],
                len(self.configs[appid]["configs"]),
                "s" if len(self.configs[appid]["configs"]) != 1 else "",
                controller_support_msg)

    async def get_steam_game_info(self, appid):
        # Get some info about the game from the Steam Webstore API

        # Special cases
        if appid == "413080":
            return desktop_config_info
        if appid == "413090":
            return bpm_info
        if appid == "443510":
            return chord_info

        r = requests.get(webapi_storeinfo.format(appid))

        if r.status_code is not 200:
            if r.status_code == 400:
                await self.bot.say("Your config link seems to be malformed.")
                return None

            await self.bot.say(
                    "There seems to be a problem. Steam returned: " + str(r))
            return None
        try:
            appinfo = r.json()[appid]
        except ValueError:
            await self.bot.say("There seems to be a problem with the" +
                    "store.steampowered.com API. Please try again later.")
            return None

        if not appinfo["success"]:
            await self.bot.say(
                    "That config doesn't seem to be for a game " +
                    "that exists on steam!")
            return None
        appinfo = appinfo["data"]
        if "categories" not in appinfo:
            appinfo["categories"] = [ ]
        if "short_description" not in appinfo:
            appinfo["short_description"] = ""
        if appinfo["short_description"] == "":
            appinfo["short_description"] = \
                    appinfo["detailed_description"][:290] + "…"
        if "header_image" in appinfo:
            appinfo["image"] = appinfo["header_image"]
        else:
            appinfo["image"] = ""

        
        return appinfo

    async def check_valid_config_link(self, link):
        # Check if it looks like a valid config link.
        if valid_link_regex_steam.match(link):
            return True
        elif valid_link_regex_nonsteam.match(link):
            return False
        return None

    async def populate_steam_game_info(self, appid):
        # Get some information from the Steam API about the game.
        appinfo = await self.get_steam_game_info(appid)
        if appinfo is None:
            return None

        # This is a steam game.
        # We use a simpler form for controller support signaling.
        controller_support = "none"
        for cat in appinfo["categories"]:
            if cat["description"].lower() == "full controller support":
                controller_support = "full"
                break
            if cat["description"].lower() == "partial controller support":
                controller_support = "partial"
                break

        preexisting_configs = [ ]
        if appid in self.configs:
            preexisting_configs = self.configs[appid]["configs"]
            
        # Populate a new entry with the basic info and the provided config.
        self.configs[appid] = { 
                "name": appinfo["name"],
                "short_description": appinfo["short_description"],
                "controller_support": controller_support, 
                "image": appinfo["image"],
                "configs": preexisting_configs }
        fileIO("data/configstore/configs.json", "save", self.configs)
        return True

    async def populate_nonsteam_game_info(self, appname):
        preexisting_configs = [ ]
        if appname in self.configs:
            preexisting_configs = self.configs[appname]["configs"]

        self.configs[appname] = {
                "name": urllib.parse.unquote(appname).title(),
                "short_description": "",
                "controller_support": "nonsteam",
                "image": "",
                "configs": preexisting_configs }
        fileIO("data/configstore/configs.json", "save", self.configs)
        return True

    async def get_closest_appid_from_name(self, name : str):
        # We assume anything strictly numeric is an appID already.
        if name.isdigit():
            return name

        # If it's a string, we should go searching through all the name
        # tags within every entry in self.configs
        # We use fuzzy string search to find the closest, but if nothing
        # has a match better than the threshold specified, we fail.
        best_value = -1
        best_name = ""

        for key, value in self.configs.items():
            value_name = value["name"]
            match_value = fuzz.partial_ratio(name.lower(), value_name.lower())
            if match_value > best_value:
                best_value = match_value
                best_name = key
        if best_value > fuzzy_partial_ratio_threshold:
            return best_name
        
        await self.bot.say("Couldn't find a game with a name similar to that.")
        return None

    @commands.group(pass_context=True)
    async def config(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @config.command(name="add")
    async def _add(self, configlink : str):
        """Adds a config to the store. 
        Example:
        s!config add steam://controllerconfig/218410/743670418"""

        steam_game = await self.check_valid_config_link(configlink)
        if steam_game == None:
            await self.bot.say("That doesn't look like a config link to me!")
            return

        # grab the important components of the config link
        split = configlink.split("/")
        appid = split[3]

        # If we haven't seen this game before, get some basic info about it.
        if appid not in self.configs:
            # Use the right method according to whether it's a steam game.
            if steam_game is False:
                if await self.populate_nonsteam_game_info(appid) is None:
                    return
            else:
                if await self.populate_steam_game_info(appid) is None:
                    return
    
        # Add the new config to the list.
        if configlink in self.configs[appid]["configs"]:
            await self.bot.say("I've already got that config!")
            return
        self.configs[appid]["configs"].append(configlink)
        fileIO("data/configstore/configs.json", "save", self.configs)

        # Tell everyone about all the configs in the list.
        await self.print_config_info(appid)

    @config.command(name="remove")
    #@checks.admin_or_permissions(administrator=True)
    async def _remove(self, configlink : str):
        """Removes a config from the store.
        Example:
        s!config remove steam://controllerconfig/218410/743670418"""

        steam_game = await self.check_valid_config_link(configlink)
        if steam_game is None:
            await self.bot.say("That doesn't look like a config link to me!")
            return

        # grab the important components of the config link
        split = configlink.split("/")
        appid = split[3]

        if appid in self.configs:
            if configlink in self.configs[appid]["configs"]:
                self.configs[appid]["configs"].remove(configlink)
                if len(self.configs[appid]["configs"]) == 0:
                    del self.configs[appid]
                fileIO("data/configstore/configs.json", "save", self.configs)
                await self.bot.say("Removed that link from my store.")
            else:
                await self.bot.say("I couldn't find that config in my store!")
        else:
            await self.bot.say("I couldn't find that config in my store!")

    @config.command(name="refresh")
    async def _refresh(self, *msg : str):
        """Refreshes my internal storage of game information.

        Use this when a game receives an update that changes anything
        I say about it!"""

        appid = await self.get_closest_appid_from_name(" ".join(msg))
        if appid is None:
            return

        if appid not in self.configs:
            await self.bot.say("That game isn't even in my storage!")
            return

        if await self.populate_steam_game_info(appid) is None:
            return
        
        await self.bot.say("Refreshed information for the following entry:")
        await self.print_config_info(appid)

    @config.command(name="refreshall", pass_context=True)
    async def _refreshall(self, ctx):
        """Refreshes the game information for every game I know about."""
        await self.bot.send_typing(ctx.message.channel)

        # TODO: Refactor this to using the steam api's bulk request feature?
        count = 0
        for key, value in self.configs.items():
            if key.isnumeric():
                await self.populate_steam_game_info(key)
                count = count + 1

        await self.bot.say("Refreshed game info for {} game{}.".format(
            count,
            "s" if count != 1 else ""))

    async def create_list_embed(self, start_index):
        msg = ""
        names = ""
        config_counts = ""
        total_configs = 0
        controller_supports = ""

        # Get order of apps by their title, rather than appid.
        sorted_items = []
        for key, value in self.configs.items():
            sorted_items.append([value["name"], key, value])
            total_configs += len(value["configs"])
        sorted_items.sort(key=lambda x: x[0])

        # Now iterate over them all, adding them all to the 
        # text to go into the embed as we go.
        for _, key, value in sorted_items[\
                start_index:\
                start_index+embed_row_limit]:
            msg += "\n" + await self.short_game_info(key)
            # Ellipsise the game name if it's too long.
            names += "\n" + u"\U0001F3AE" + " " + value["name"][:20] + ".." \
                    if len(value["name"]) > 22 \
                    else "\n" + u"\U0001F3AE" + " " + value["name"]
            config_counts += "\n\u0023\u20E3   " + str(len(value["configs"]))
            if value["controller_support"] == "full":
                controller_supports += "\n{} {}".format(
                        full_support_emoji, "Full")
            elif value["controller_support"] == "partial":
                controller_supports += "\n{} {}".format(
                        partial_support_emoji, "Partial")
            elif value["controller_support"] == "none":
                controller_supports += "\n{} {}".format(
                        no_support_emoji, "None")
            elif value["controller_support"] == "nonsteam":
                controller_supports += "\n{} {}".format(
                        nonsteam_emoji, "Non-Steam Game")

        embed = discord.Embed(title="Listing all {} games, with {} configs"\
                .format(len(self.configs), total_configs),
                color=0x000837)
        embed.add_field(name="Game Name", 
                value=names, 
                inline=True)
        embed.add_field(name="Configs", 
                value=config_counts, 
                inline=True)
        embed.add_field(name="Controller Support", 
                value=controller_supports, 
                inline=True)
        embed.set_footer(text="Showing games {} - {} of {}. ".format(
                start_index, start_index + embed_row_limit, 
                len(self.configs)) +
                "Respond with \"previous\" or \"next\" to browse.")
        return embed

    @config.command(name="search")
    async def _search(self, *msg : str):
        if len(msg) == 0:
            await self.bot.say("Please name a game.")
        appid = await self.get_closest_appid_from_name(" ".join(msg))
        if appid is None:
            return
        await self.print_config_info(appid)

    @config.command(name="list", pass_context=True)
    async def _list(self, ctx, *msg : str):
        """Gets any configs for a particular game.
        If no game is given, I'll list off all of them."""

        # If a name is given, fuzzy search for the closest match.
        if len(msg) != 0:
            appid = await self.get_closest_appid_from_name(" ".join(msg))
            if appid is None:
                return
            await self.print_config_info(appid)
            return
        
        # If no game is given, list everything off.
        # We create an interactive embed that paginates based on user responses
        current_index = 0
        current_embed = await self.create_list_embed(0)
        current_message = await self.bot.say(embed=current_embed)

        # We only break out of this loop once the time since the last message
        # in the channel has exceeded the interaction timeout.
        while True:
            response = await self.bot.wait_for_message(
                    timeout=embed_interaction_timeout,
                    author=ctx.message.author,
                    channel=ctx.message.channel)

            if response is None:
                current_embed.set_footer(
                        text="Showing games {} - {} of {}. ".format(
                            current_index, current_index + embed_row_limit,
                            len(self.configs)))
                await self.bot.edit_message(current_message, 
                        embed=current_embed)
                break
            if response.author == self.bot.user or \
                    response.author != ctx.message.author:
                continue

            if response.content.lower() == "next":
                current_index = current_index + embed_row_limit \
                        if current_index + embed_row_limit < len(self.configs)\
                        else current_index
            elif response.content.lower() == "previous":
                current_index = current_index - embed_row_limit \
                        if current_index - embed_row_limit >= 0 \
                        else 0
            else:
                continue

            current_embed = await self.create_list_embed(current_index)
            current_message = await self.bot.edit_message(\
                    current_message, embed=current_embed)
            # We might not have permission to delete messages, so 
            # if it doesn't work, we don't care.
            try:
                await self.bot.delete_message(response)
            except:
                pass
            continue


def check_folders():
    if not os.path.exists("data/configstore"):
        print("Creating data/configstore folder...")
        os.makedirs("data/configstore")

def check_files():
    default = { }

    f = "data/configstore/configs.json"
    if not fileIO(f, "check"):
        print("Creating empty configs.json...")
        fileIO(f, "save", default)

def setup(bot):
    check_folders()
    check_files()
    n = ConfigStore(bot)
    bot.add_cog(n)
