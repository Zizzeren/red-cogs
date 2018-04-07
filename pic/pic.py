import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help
import os
import math
import aiohttp
from random import choice as randchoice
from PIL import Image
import time
from datetime import datetime
import re
from fuzzywuzzy import fuzz
import pprint

units = (("second", 1), ("minute", 60), ("hour", 3600),
        ("day", 86400), ("week", 604800), ("month", 2592000))
strftime = "%Y-%m-%d %H:%M:%S UTC"
valid_name_regex = re.compile("[A-Za-z0-9-]+$")
fuzzy_partial_ratio_threshold = 90
response_timeout = 30
rename_emoji = u"👍"
no_rename_emoji = u"👎"
global_emoji = u"🌐"
local_emoji = u"⚓"
template_aliases = [
        "template",
        "templates",
        "temp",
        "temps"
        ]
source_aliases = [
        "source",
        "sources",
        "sauce",
        "sauces",
        "aioli",
        "bbq"
        ]

data_folder = "data/pic2/"
templates_folder = data_folder + "templates/"
sources_folder = data_folder + "sources/"
# servers_folder will include templates/ and sources/
servers_folder = data_folder + "servers/"
temp_folder = "data/pic2/tmp"
templates_file = data_folder + "templates.json"
sources_file = data_folder + "sources.json"
servers_file = data_folder + "servers.json"
log_channels_file = data_folder + "log_channels.json"
# trusted users can delete images from servers they're not in
trusted_users_file = data_folder + "trusted_users.json"

servers_format = {
    "server.id": 
    {
        "name": "Name of server",
        "templates": { "as templates_format" },
        "sources":   { "as sources_format" },
        "can_add_global": True, #by default, allows bans later
    }
}
templates_format = {
    "name": 
    {
        "location": "relative path on disk",
        "paste_points":
            [
                [ "points marking out corners..." ],
                [ "another set of points..." ],
            ],
        "added_by": 
            {
                "server": { "id", "name" },
                "member": { "id", "name#discriminator" },
                "date"  : "time.time()"
            }
    }
}
sources_format = {
    "name":
    {
        "location": "relative path on disk",
        "added_by":
            {
                "server": { "id", "name" },
                "member": { "id", "name#discriminator" },
                "date"  : "time.time()"
            }
    }
}
trusted_users_format = [
    "member.id",
    "member.id"
]


class Pic:
    """Use template images, and replace transparent bits with other sources."""

    def __init__(self, bot):
        self.bot = bot

        self.templates     = dataIO.load_json(templates_file)
        self.sources       = dataIO.load_json(sources_file)
        self.servers       = dataIO.load_json(servers_file)
        self.trusted_users = dataIO.load_json(trusted_users_file)
        log_channels       = dataIO.load_json(log_channels_file)
        self.addlog = log_channels[0]
        self.migratelog = log_channels[1]

    async def get_type(self, which):
        which = which.lower()
        if which in template_aliases:
            return "templates"
        if which in source_aliases:
            return "sources"
        return None

    async def seconds_to_higher_units(self, seconds):
        divisor = 1
        current_unit = "second"
        for unit, val in units:
            if seconds > val:
                divisor = val
                current_unit = unit
        return "{} {}{}".format(
                seconds // divisor,
                current_unit,
                "s" if seconds // divisor > 1 else "")

    async def check_server_stored(self, server: discord.Server):
        if server is None:
            return
        if server.id not in self.servers:
            self.servers[server.id] = \
            {
                    "name": server.name,
                    "templates": { },
                    "sources": { },
                    "can_add_global": True
            }
            dataIO.save_json(servers_file, self.servers)

    async def valid_name(self, name):
        return valid_name_regex.match(name) is not None and name != "random"

    async def is_trusted_user(self, member: discord.Member):
        if member.id == self.bot.settings.owner:
            return True
        return member.id in self.trusted_users

    async def rename_image(self, server, which, name, newname):
        if server is None:
            if which == "templates":
                oldloc = self.templates[name]["location"]
                newloc = \
                        os.path.join(os.path.dirname(oldloc), '') +\
                        newname +\
                        os.path.splitext(oldloc)[1]
                os.rename(oldloc, newloc)
                self.templates[name]["location"] = newloc
                self.templates[newname] = self.templates[name]
                del self.templates[name]
                dataIO.save_json(templates_file, self.templates)
            else:
                oldloc = self.sources[name]["location"]
                newloc = \
                        os.path.join(os.path.dirname(oldloc), '') +\
                        newname +\
                        os.path.splitext(oldloc)[1]
                os.rename(oldloc, newloc)
                self.sources[name]["location"] = newloc
                self.sources[newname] = self.sources[name]
                del self.sources[name]
                dataIO.save_json(sources_file, self.sources)
        else:
            oldloc = self.servers[server.id][which][name]["location"]
            newloc = \
                    os.path.join(os.path.dirname(oldloc), '') +\
                    newname +\
                    os.path.splitext(oldloc)[1]
            os.rename(oldloc, newloc)
            self.servers[server.id][which][name]["location"] = newloc
            self.servers[server.id][which][newname] = \
                    self.servers[server.id][which][name]
            del self.servers[server.id][which][name]
            dataIO.save_json(servers_file, self.servers)

    async def select_duplicate(self, server, member, which, name):
        msg = await self.bot.say("I found two {} with that name. "\
                .format(which) 
                +"Do you want to rename and use the {} in this server?"\
                        .format(which[:-1]))
        await self.bot.add_reaction(msg, rename_emoji)
        await self.bot.add_reaction(msg, no_rename_emoji)
        result = await self.bot.wait_for_reaction(
                [rename_emoji, no_rename_emoji],
                user=member,
                message=msg)
        
        if result.reaction.emoji == rename_emoji:
            await self.bot.say("What do you want it to be called?")
            response = await self.bot.wait_for_message(author=member)
            if not await self.valid_name(response.content):
                await self.bot.say("That's not a valid name.")
                return (None, None)
            await self.rename_image(server, which, name, response.content)
            await self.bot.say("I've renamed that image.")
            return (self.servers[server.id][which][response.content], server)
        else:
            msg = await self.bot.say("Which {} do you want?\n"\
                    .format(which[:-1])+\
                    "{} = Local, {} = Global".format(local_emoji,global_emoji))
            await self.bot.add_reaction(msg, local_emoji)
            await self.bot.add_reaction(msg, global_emoji)
            result = await self.bot.wait_for_reaction(
                    [local_emoji, global_emoji],
                    user=member,
                    message=msg)

            if result.reaction.emoji == local_emoji:
                return (self.servers[server.id][which][name], server)
            elif which == "templates":
                return (self.templates[name], None)
            else:
                return (self.sources[name], None)

    async def search_for(self, server, member, which, name, dospellcheck=True):
        which = await self.get_type(which)
        name = name.lower()
        await self.check_server_stored(server)
        if which is None:
            return (None, None)
        if which == "templates":
            globalcoll = self.templates
        if which == "sources":
            globalcoll = self.sources
        if server is None:
            localcoll = { }
        else:
            localcoll = self.servers[server.id][which]

        if name in globalcoll and name in localcoll:
            return await self.select_duplicate(server, member, which, name)
        elif name in globalcoll:
            return (globalcoll[name], None)
        elif name in localcoll:
            return (localcoll[name], server)
        elif dospellcheck:
            # Do fuzzy string search to try find the best match.
            best_value = -1
            best_name = ""
            best_location = "global"

            for key in globalcoll.keys():
                match_value = fuzz.partial_ratio(name, key)
                if match_value > best_value:
                    best_value = match_value
                    best_name = key
                    best_location = "global"
            for key in localcoll.keys():
                match_value = fuzz.partial_ratio(name, key)
                if match_value > best_value:
                    best_value = match_value
                    best_name = key
                    best_location = "local"
            if best_value > fuzzy_partial_ratio_threshold:
                if best_location == "global":
                    return (globalcoll[best_name], None)
                else:
                    return (localcoll[best_name], server)
            else:
                return (None, None)
        else:
            return (None, None)

    async def get_random(self, server: discord.Server, which):
        if which == "templates":
            coll = self.templates.keys()
        else:
            coll = self.sources.keys()
        if server is not None:
            if server.id in self.servers:
                coll = list(coll) + list(self.servers[server.id][which].keys())
        return randchoice(list(coll))

    async def acquire_image(self, url, name):
        try:
            async with aiohttp.get(url) as r:
                data = await r.content.read()
            filename = "{}{}".format(temp_folder, name)
            with open(filename, 'wb') as f:
                f.write(data)
            img = Image.open(open(filename, 'rb'))
            name_and_format = "{}.{}".format(filename, img.format.lower())
            os.rename(filename, name_and_format)
            return name_and_format
        except Exception as e:
            print(e)
            print(url)
            return None

    async def wait_for_image(self, msg_author: discord.Member, name):
        "Returns a filename, or None."
        # If there was no response, it's not an image.
        response = await self.bot.wait_for_message(timeout=response_timeout,
                author=msg_author)
        if response is None:
            return None

        # If the response didn't include an image or mention, it's not an image
        img_url = ""
        if len(response.mentions) is not 0:
            img_url = response.mentions[0].avatar_url
        elif len(response.attachments) is not 0:
            if "url" in response.attachments[0]:
                img_url = response.attachments[0]["url"]
        else:
            return None

        return await self.acquire_image(img_url, name)

    async def get_paste_points(self, img_location):
        img = Image.open(img_location)
        #Enforce RGBA format
        img = img.convert("RGBA")

        # Go through all the pixels and write down their locations,
        # sorted by colour, with location given as (x,y)
        colours = {}
        width = img.size[0]
        for index, colour in enumerate(list(img.getdata())):
            if colour[3] != 0:
                if colour not in colours:
                    colours[colour] = []
                colours[colour].append((index % width, index // width))

        # For every colour, try find squares
        paste_points = []
        for colour, values in colours.items():
            if len(values) % 4 is not 0:
                await self.bot.say(
                    "Wrong number of pixels of this colour. " +\
                    "Got {} pixels of colour {}".format(len(values), colour))
                return None

            # We must be stuck with at least one set of squares. Find them.
            squares = []
            values_i = values[:]
            while len(values_i) != 0:
                # The first pixel must be part of a square.
                first = values_i[0]
                # We find the other corners that share x and y values
                # with the first pixel we found
                shared_x = [ p for p in values_i if p[0] == first[0] ]
                shared_y = [ p for p in values_i if p[1] == first[1] ]

                # Then we check the rest of the list for one that matches
                # the last corner location.
                square = None
                points = None
                for x in shared_x:
                    for y in sorted(shared_y):
                        for v in sorted(values_i):
                            if v[0] == y[0] and v[1] == x[1] and\
                                    first[0] != v[0] and first[1] != v[1]:
                                points = [first, x, y, v]
                                square = [first[0], first[1], v[0], v[1]]

                if square is None:
                    await self.bot.say(
                        "Couldn't match all those pixels into squares. " +\
                        "Colour: {}\nPixel locations: {}".format(
                            colour, values_i))
                    return None

                squares.append(square)
                failed=False
                for point in points:
                    values_i.remove(point)

            # At this point, squares now contains a set of borders for the
            # source corresponding to this colour.
            paste_points.append(squares)

        return paste_points

    async def get_new_template(self, msg_author: discord.Member, name):
        "Return a data structure representing the new template, or None."
        await self.bot.say(
                "Please respond with the image to use as `{}`".format(name))
        result = await self.wait_for_image(msg_author, name)
        await self.bot.say(
                "Please give me an image with pixels marking out the bounds " +
                "of each source image, once pasted on the image you just " +
                "you just gave me.")
        paste_points_image = await self.wait_for_image(msg_author, "pastes")
        if paste_points_image is None:
            return None

        # Enforce non-ridiculousness limits on the image
        result_img = Image.open(result)
        paste_points_img = Image.open(paste_points_image)
        if result_img.size != paste_points_img.size:
            await self.bot.say("Images must be the same size.")
            return None
        if result_img.size > (3500,3500):
            await self.bot.say("That image is too big.")
            return None

        paste_points = await self.get_paste_points(paste_points_image)
        if result is None or paste_points is None:
            return None
        return {
                "location": result,
                "paste_points": paste_points,
                "added_by": {
                    "member": {
                        "id": msg_author.id,
                        "name": "{}#{}".format(
                            msg_author.name, msg_author.discriminator)
                        },
                    "date": time.time()
                    }
                }

    async def get_new_source(self, msg_author: discord.Member, name):
        "Returns a data structure representing the new source, or None."
        await self.bot.say(
                "Please respond with the image to use as `{}`, or a mention."\
                        .format(name))
        result = await self.wait_for_image(msg_author, name)
        if result is None:
            return None
        return {
                "location": result,
                "added_by": {
                    "member": {
                        "id": msg_author.id,
                        "name": "{}#{}".format(
                            msg_author.name, msg_author.discriminator)
                        },
                    "date": time.time()
                    }
                }

    async def make_image(self, template, sources):
        """Takes a template and a list of sources, returns the filename
        containing the result, or None."""
        try:
            # Set up Image objects
            template_i = Image.open(template["location"])
            sources_i = [ Image.open(s["location"]) for s in sources ]
            base_image = Image.new("RGBA", template_i.size, (0,0,0,0))
            template_i = template_i.convert("RGBA")
            sources_i = [ s.convert("RGBA") for s in sources_i ]

            # Paste the sources
            processed = 0
            for source_locations in template["paste_points"]:
                source = sources_i[processed % len(sources_i)]
                for square in source_locations:
                    temp_source = source.resize((square[2] - square[0],
                                                 square[3] - square[1]))
                    base_image.paste(temp_source, square, temp_source)
                processed += 1

            # Paste the template on top
            base_image.paste(template_i, None, template_i)

            # Save the new image, and return its location.
            t_name = os.path.basename(template["location"])
            t_name = os.path.splitext(t_name)[0]
            s_names = ""
            for source in sources:
                name = os.path.basename(source["location"])
                name = os.path.splitext(name)[0]
                if len(s_names + name) > 200:
                    s_names = "{}_and-many-more".format(s_names)
                    break
                s_names = "{}_{}".format(s_names, name)

            filename = temp_folder + "{}_{}.png".format(
                    t_name, s_names[1:])
            base_image.save(filename, "PNG")
            return filename

        except Exception as e:
            print(e)
            await self.bot.say("I couldn't make that image... Error type {}"\
                    .format(type(e).__name__))
            return None

    @commands.group(pass_context=True)
    async def pic(self, ctx):
        """Create images using templates (with holes) and sources (without)"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @pic.command(pass_context=True)
    async def migrate(self, ctx, which, name):
        """Migrate an image from local storage to global, or vice versa."""
        which = await self.get_type(which)
        if which is None:
            await self.bot.say(
                    "<which> should be either 'source' or 'template'")
            return

        server = ctx.message.server
        author = ctx.message.author
        await self.check_server_stored(server)

        result,rserver = await self.search_for(server, author, which, name)
        if result is None:
            await self.bot.say("Couldn't find a {} with that name.".format(
                which[:-1]))
            return
        rname = os.path.basename(result["location"])
        rname = os.path.splitext(rname)[0]
        
        can_remove = await self.is_trusted_user(author)
        if result["added_by"]["member"]["id"] == author.id:
            can_remove = True
        elif server is not None:
            if result["added_by"]["server"] is not None:
                if result["added_by"]["server"]["id"] == server.id:
                    can_remove = True

        if not can_remove:
            await self.bot.say("You're not allowed to migrate that {}.".format(
                which[:-1]))
            return

        is_global = None
        if rserver is None:
            is_global = True
            rserverid = result["added_by"]["server"]["id"]
        else:
            is_global = False

        if is_global:
            folder = servers_folder + rserverid + "/{}/".format(which)
            if not os.path.exists(folder):
                print("Creating {} folder...".format(folder))
                os.makedirs(folder)
            new_name = "{}{}".format(folder,
                                     os.path.basename(result["location"]))
            os.rename(result["location"], new_name)
            result["location"] = new_name

            if which == "templates":
                del self.templates[rname]
                dataIO.save_json(templates_file, self.templates)
            else:
                del self.sources[rname]
                dataIO.save_json(sources_file, self.sources)
            self.servers[rserverid][which][rname] = result
            dataIO.save_json(servers_file, self.servers)

        else:
            if which == "templates":
                folder = templates_folder
            else:
                folder = sources_folder
            new_name = "{}{}".format(folder,
                                    os.path.basename(result["location"]))
            os.rename(result["location"], new_name)
            result["location"] = new_name

            del self.servers[rserver.id][which][rname]
            dataIO.save_json(servers_file, self.servers)
            if which == "templates":
                self.templates[rname] = result
                dataIO.save_json(templates_file, self.templates)
            else:
                self.sources[rname] = result
                dataIO.save_json(sources_file, self.sources)

        await self.bot.say("Successfully migrated the {} {}.".format(
            which[:-1], rname))
        if self.migratelog is not None:
            await self.bot.send_file(self.bot.get_channel(self.migratelog),
                    result["location"],
                    content = "MIGRATED {}: {}\nOriginally added by {}\n"\
                        .format(
                            which, name, pprint.pformat(result["added_by"]))
                        + "Migrated by {}".format(pprint.pformat(
                            {
                                "member": {
                                        "id": author.id,
                                        "name": author.name
                                    },
                                "server": {
                                        "id": server.id,
                                        "name": server.name
                                    }
                            })))
        

    @pic.command(pass_context=True)
    async def add(self, ctx, which, name):
        """Add an image to be seen globally.
        For any NSFW stuff or in-jokes noone else will get, consider using
        addlocal instead.

        <which> should be either 'source' or 'template'.
        <name> should be what you want the image to be referred to as."""
        which = await self.get_type(which)
        if which is None:
            await self.bot.say(
                    "<which> should be either 'source' or 'template'")
            return

        name = name.lower()
        if not await self.valid_name(name):
            await self.bot.say("That's not a valid name.")
            return
        server = ctx.message.server
        author = ctx.message.author
        await self.check_server_stored(server)

        if server is not None:
            if not self.servers[server.id]["can_add_global"]:
                await self.addlocal(ctx, which, name)
                return
            if name in self.servers[server.id][which]:
                await self.bot.say(
                    "I already have a {} in this server called `{}`"\
                            .format(which[:-1], name))
                return

        if which == "templates":
            if name in self.templates:
                await self.bot.say("I've already got a template called `{}`"\
                        .format(name))
                return
            folder = templates_folder
            result = await self.get_new_template(author, name)
            if result is None:
                return
        if which == "sources":
            if name in self.sources:
                await self.bot.say("I've already got a source called `{}`"\
                        .format(name))
                return
            folder = sources_folder
            result = await self.get_new_source(author, name)
            if result is None:
                await self.bot.say("Please send an image{} next time.".format(
                    "/mention" if which == "sources" else ""))
                return

        if server is None:
            result["added_by"]["server"] = None
        else:
            result["added_by"]["server"] = {
                    "id": server.id,
                    "name": server.name
                }
        new_name = "{}{}".format(folder, 
                                 os.path.basename(result["location"]))
        os.rename(result["location"], new_name)
        result["location"] = new_name

        if which == "templates":
            self.templates[name] = result
            dataIO.save_json(templates_file, self.templates)
        if which == "sources":
            self.sources[name] = result
            dataIO.save_json(sources_file, self.sources)

        await self.bot.say("Added `{}` as {}.".format(name, which[:-1]))
        if self.addlog is not None:
            await self.bot.send_file(self.bot.get_channel(self.addlog),
                    result["location"],
                    content = "ADDED {}: {} by {}".format(
                        which, name, pprint.pformat(result["added_by"])))

    @pic.command(pass_context=True, no_pm=True)
    async def addlocal(self, ctx, which, name):
        """Add an image that can only be used in this server.

        <which> should be either 'source' or 'template'.
        <name> should be what you want the image to be referred to as."""
        which = await self.get_type(which)
        if which is None:
            await self.bot.say(
                    "<which> should be either 'source' or 'template'")
            return

        name = name.lower()
        server = ctx.message.server
        author = ctx.message.author
        await self.check_server_stored(server)

        if name in self.servers[server.id][which]:
            await self.bot.say(
                    "I've already got a {} in this server called `{}`"\
                    .format(name))
            return

        if which == "templates":
            if name in self.templates:
                await self.bot.say(
                    "I've already got a global template called `{}`."\
                    .format(name))
                return
            folder = servers_folder + server.id + "/templates/"
            result = await self.get_new_template(author, name)
        if which == "sources":
            if name in self.sources:
                await self.bot.say(
                    "I've already got a global source called `{}`."\
                    .format(name))
                return
            folder = servers_folder + server.id + "/sources/"
            result = await self.get_new_source(author, name)

        if result is None:
            await self.bot.say("Please send an image{} next time.".format(
                "/mention" if which == "source" else ""))
            return
        result["added_by"]["server"] = {
                "id": server.id,
                "name": server.name
            }
        if not os.path.exists(folder):
            print("Creating {} folder...".format(folder))
            os.makedirs(folder)
        new_name = "{}{}".format(folder,
                                 os.path.basename(result["location"]))
        os.rename(result["location"], new_name)
        result["location"] = new_name

        if which == "templates":
            self.servers[server.id]["templates"][name] = result
        if which == "sources":
            self.servers[server.id]["sources"][name] = result
        dataIO.save_json(servers_file, self.servers)

        await self.bot.say(
                "Added `{}` as a {} that will only be seen in this server."\
                        .format(name, which[:-1]))

    @pic.command(pass_context=True)
    async def remove(self, ctx, which, name):
        """Remove an image from my storage.
        You can only remove an image that was added by someone in your
        server. If you want to report someone else's image, come to my
        server with !getme.

        <which> should be either 'source' or 'template'.
        <name> should be the name of the image."""
        which = await self.get_type(which)
        if which is None:
            await self.bot.say(
                    "<which> should be either 'source' or 'template'")
            return
        name = name.lower()
        server = ctx.message.server
        author = ctx.message.author
        await self.check_server_stored(server)

        result,rserver = await self.search_for(server, author, which, name)
        if result is None:
            await self.bot.say("Couldn't find a {} with that name.".format(
                which[:-1]))
            return
        rname = os.path.basename(result["location"])
        rname = os.path.splitext(rname)[0]

        can_remove = await self.is_trusted_user(author)
        if result["added_by"]["member"]["id"] == author.id:
            can_remove = True
        elif server is not None:
            if result["added_by"]["server"] is not None:
                if result["added_by"]["server"]["id"] == server.id:
                    can_remove = True

        if not can_remove:
            await self.bot.say("Sorry, I can't allow you to remove an image "+\
                    "added by someone in a different server.")
            return

        def check(msg):
            return msg.content.lower() == "yes"

        await self.bot.send_file(ctx.message.channel, result["location"],
                content="Are you sure you want to remove this {}: `{}`? "\
                        .format(which[:-1], rname) +\
                "Reply with `yes` to confirm.")
        confirmation = await self.bot.wait_for_message(
                timeout=response_timeout,
                author=author,
                check=check)
        if confirmation is None:
            await self.bot.say("Not deleting that {}.".format(which[:-1]))
            return

        if self.addlog is not None:
            await self.bot.send_file(self.bot.get_channel(self.addlog),
                    result["location"],
                    content = "REMOVED {}: {}, added_by:\n{}\nRemoved by:\n{}"\
                        .format(
                            which, 
                            rname, 
                            pprint.pformat(result["added_by"]),
                            pprint.pformat({
                                "member":{
                                    "id": author.id,
                                    "name": "{}#{}".format(author.name,
                                                           author.discriminator)
                                },
                                "server":{
                                    "id": server.id,
                                    "name": server.name
                                }
                            })))

        os.remove(result["location"])
        if rserver is None:
            if which == "templates":
                del self.templates[rname]
                dataIO.save_json(templates_file, self.templates)
            else:
                del self.sources[rname]
                dataIO.save_json(sources_file, self.sources)
        else:
            del self.servers[rserver.id][which][rname]
            dataIO.save_json(servers_file, self.servers)
        await self.bot.say("Removed that image.")

    @pic.command(pass_context=True)
    async def rename(self, ctx, which, oldname, newname):
        """Rename an image.

        <which> should be either 'source' or 'template'.
        <oldname> should be the current name of the image.
        <newname> should be the new name of the image."""
        server = ctx.message.server
        author = ctx.message.author
        await self.check_server_stored(server)
        which = await self.get_type(which)
        oldname = oldname.lower()
        newname = newname.lower()
        result,rserver = await self.search_for(server, author, which, oldname)

        if result is None:
            await self.bot.say("I couldn't find that image.")
            return

        if which == "templates":
            if newname in self.templates:
                await self.bot.say(
                        "I already have a template with that name.")
                return
        else:
            if newname in self.sources:
                await self.bot.say(
                        "I already have a source with that name.")
                return
        if server is not None:
            if newname in self.servers[server.id][which]:
                await self.bot.say("I already have a {} with that name."\
                        .format(which[:-1]))
                return

        if not await self.is_trusted_user(author):
            if result["added_by"]["server"] is None or server is None:
                await self.bot.say("I can't let you rename an image from "+\
                        "another server, sorry.")
                return
            elif result["added_by"]["server"]["id"] != server.id:
                await self.bot.say("I can't let you rename an image from "+\
                        "another server, sorry.")
                return

        if not await self.valid_name(newname):
            await self.bot.say("That's not a valid name.")
            return

        await self.rename_image(rserver, which, oldname, newname)
        await self.bot.say("Renamed that image.")

    @pic.command(pass_context=True)
    async def list(self, ctx, which):
        """Lists the images I have stored.

        <which> should be either 'source' or 'template'.
        Use !pic show to see a specific image, or you can go to 
        https://drive.google.com/drive/u/2/folders/1WQlPbNjoJYI4QIpcwfr_wDK3iBLQDvCB
        to see them all."""
        server = ctx.message.server

        which = await self.get_type(which)
        if which is None:
            await self.bot.say(
                    "<which> should be either 'source' or 'template'")
            return

        if which == "templates":
            globalcoll = self.templates
        if which == "sources":
            globalcoll = self.sources

        localcoll = None
        if server is not None:
            if server.id in self.servers:
                if len(self.servers[server.id][which]) > 0:
                    localcoll = self.servers[server.id][which]

        msg = "Listing all global {}: \n```".format(which)
        for name in sorted(globalcoll):
            word = "{}, ".format(name)
            if len(msg) + len(word) < 1900:
                msg += word
            else:
                await self.bot.say("{}```".format(msg[:-2]))
                msg = "```{}".format(word)
        if len(msg) is not 3:
            await self.bot.say("{}```".format(msg[:-2]))

        if localcoll is not None:
            msg = "Listing all local {}: \n```".format(which)
            for name in sorted(localcoll):
                word = "{}, ".format(name)
                if len(msg) + len(word) < 1900:
                    msg += word
                else:
                    await self.bot.say("{}```".format(msg[:-2]))
                    msg = "```{}".format(word)
            if len(msg) is not 3:
                await self.bot.say("{}```".format(msg[:-2]))

    @pic.command(pass_context=True)
    async def show(self, ctx, which, name):
        """Show an image.

        <which> should be either 'source' or 'template'.
        <name> should be the name of the image."""
        await self.bot.send_typing(ctx.message.channel)
        which = await self.get_type(which)
        if which is None:
            await self.bot.say(
                "<which> should be either 'source' or 'template'")
            return

        name = name.lower()
        server = ctx.message.server
        author = ctx.message.author
        await self.check_server_stored(server)

        result,_ = await self.search_for(server, author, which, name)
        if result is None:
            await self.bot.say("Couldn't find a {} with that name.".format(
                which[:-1]))
            return
        await self.bot.send_file(ctx.message.channel, result["location"])

    @pic.command(pass_context=True)
    async def addedby(self, ctx, which, name):
        """Show who an image was added by, and what server they were in.
        If the user wasn't in this server, I won't show their information.

        <which> should be either 'source' or 'template'.
        <name> should be the name of the image."""
        server = ctx.message.server
        author = ctx.message.author
        which = await self.get_type(which)
        if which is None:
            await self.bot.say(
                "<which> should be either 'source' or 'template'")
            return
        name = name.lower()
        await self.check_server_stored(server)

        result,rserver = await self.search_for(server, author, which, name)
        if result is None:
            await self.bot.say("Couldn't find a {} with that name.".format(
                which[:-1]))
            return
        added_by = result["added_by"]

        include_userdetails = True
        trusted = await self.is_trusted_user(author)
        if not trusted:
            if added_by["server"] is None or server is None:
                include_userdetails = False
            elif added_by["server"]["id"] != server.id:
                include_userdetails = False


        member_string = "\n  User: {} ({})".format(
            added_by["member"]["name"], added_by["member"]["id"])\
                    if include_userdetails else "someone"
        if added_by["server"] is None:
            server_string = "None - Added in private messages"
        else:
            server_string = added_by["server"]["name"] + \
                (" ({})".format(added_by["server"]["id"]) if trusted else "")
        then = datetime.utcfromtimestamp(int(added_by["date"]))
        now = datetime.utcnow()
        age_dt = now - then
        age = age_dt.total_seconds()
        age_s = await self.seconds_to_higher_units(int(age))
        date_string = then.strftime(strftime)

        msg = \
"""The image was added by:
```hs{}
Server: {}
  Date: {} ({} ago)
```""".format(
            member_string,
            server_string,
            date_string,
            age_s)
        await self.bot.say(msg)

    @pic.command(pass_context=True)
    @commands.cooldown(1, 5, commands.BucketType.server)
    async def create(self, ctx, template, *sources):
        """Create an image from a specified template and source.
        You can say 'random' in place of template or any source (or both).

        <template> should be the name of the template you want to use.
        <sources> should be the names of all the sources you want.
        You can use a ping in place of any source."""
        await self.bot.send_typing(ctx.message.channel)
        template = template.lower()
        sources = [ s.lower() for s in sources ]
        server = ctx.message.server
        author = ctx.message.author
        await self.check_server_stored(server)

        if template == "random":
            template = await self.get_random(server, "templates")

        template,_ = await self.search_for(
                server, author, "templates", template)
        if template is None:
            await self.bot.say("I couldn't find that template.")
            return
        # Can't use await in list comprehension :'(
        if len(sources) == 0:
            sources = [ "random" ] * len(template["paste_points"])
        sources_data = []
        for source in sources:
            # If it's random, be random.
            if source == "random":
                source = await self.get_random(server, "sources")
                result = await self.search_for(
                        server, author, "sources", source)
            # Otherwise, have a look for a source that was spelt right
            else:
                result = await self.search_for(
                        server, author, "sources", source, dospellcheck=False)
            # Then, check for a member
            if result[0] is None:
                target = discord.utils.find(
                        lambda m: source == m.name.lower() or
                                  source == m.mention or
                                  source == m.display_name.lower() or
                                  source == m.id,
                        server.members if server is not None else \
                                [author, self.bot.user])
                if target is not None:
                    sources_data.append({
                        "location": await self.acquire_image(
                            target.avatar_url, target.id)
                        })
                # Finally, do some spellcheck
                else:
                    result = await self.search_for(
                            server, author, "sources", source)
                    sources_data.append(result[0])
            else:
                sources_data.append(result[0])
        sources = sources_data
        if None in sources:
            await self.bot.say("I couldn't find one of those sources.")
            return

        filename = await self.make_image(template, sources)
        if filename is None:
            return
        await self.bot.send_file(ctx.message.channel, filename)

        try:
            os.remove(filename)
        except Exception as e:
            print(e)

    @pic.command(pass_context=True)
    @checks.is_owner()
    async def addtrusted(self, ctx, member: discord.Member):
        """Add a trusted member. 
        They can remove images when not in the server it was added in."""
        self.trusted_users.append(member.id)
        dataIO.save_json(trusted_users_file, self.trusted_users)
        await self.bot.say("Added trusted user.")

    @pic.command(pass_context=True)
    @checks.is_owner()
    async def removetrusted(self, ctx, member: discord.Member):
        """Remove a trusted member."""
        self.trusted_users.remove(member.id)
        dataIO.save_json(trusted_users_file, self.trusted_users)
        await self.bot.say("Removed trusted user.")

    @pic.command(pass_context=True)
    async def istrusted(self, ctx, member: discord.Member):
        """Check if a user is trusted or not."""
        result = await self.is_trusted_user(member)
        await self.bot.say(result)

    @pic.command(pass_context=True)
    @checks.is_owner()
    async def banserverfromglobal(self, ctx, server: discord.Server):
        """Toggle banning a server from creating global images.
        Makes them only able to create local ones instead."""
        await self.check_server_stored(server)

        new_state = not self.servers[server.id]["can_add_global"]
        self.servers[server.id]["can_add_global"] = new_state

        await self.bot.say("Server {} is now {} to add global images.".format(
            server.name, "allowed" if new_state else "not allowed"))

    @pic.command(pass_context=True)
    @checks.is_owner()
    async def setlog(self, ctx, which, channel: discord.Channel=None):
        """Set a logging channel for migrations and additions."""
        if which == "add":
            if channel is None:
                self.addlog = None
                await self.bot.say("Turned off add logging.")
            else:
                self.addlog = channel.id
                await self.bot.say("Set add log channel.")
        if which == "migrate":
            if channel is None:
                self.migratelog = None
                await self.bot.say("Turned off migrate logging.")
            else:
                self.migratelog = channel.id
                await self.bot.say("Set migrate log channel.")
        dataIO.save_json(log_channels_file, [self.addlog, self.migratelog])

    @pic.command(pass_context=True, no_pm=True)
    async def info(self, ctx):
        """Info about how much stuff I'm storing"""
        this_server = ctx.message.server
        await self.check_server_stored(this_server)

        global_src_count = len(self.sources)
        global_tmp_count = len(self.templates)

        server_count = 0
        local_src_count = 0
        local_tmp_count = 0
        for server in self.servers:
            if len(self.servers[server]["sources"]) > 0 or \
                    len(self.servers[server]["templates"]) > 0:
                server_count += 1
                local_src_count += len(self.servers[server]["sources"])
                local_tmp_count += len(self.servers[server]["templates"])

        this_server_global_src = 0
        this_server_global_tmp = 0
        for source in self.sources:
            if self.sources[source]["added_by"]["server"] is None:
                continue
            if self.sources[source]["added_by"]["server"]["id"] == \
                                                                this_server.id:
                this_server_global_src += 1
        for template in self.templates:
            if self.templates[template]["added_by"]["server"] is None:
                continue
            if self.templates[template]["added_by"]["server"]["id"] == \
                                                                this_server.id:
                this_server_global_tmp += 1

        await self.bot.say(
            "I'm storing `{}` global templates, and `{}` global sources.\n"\
                    .format(global_tmp_count, global_src_count) +\
            "I'm storing `{}` private templates and `{}` private sources "\
                    .format(local_tmp_count, local_src_count) +\
            "across `{}` servers.\n".format(server_count)+\
            "This server has `{}` local templates and `{}` local sources. "\
                    .format(len(self.servers[this_server.id]["templates"]),
                            len(self.servers[this_server.id]["sources"]))+\
            "You've also added `{}` of the global templates, "\
                    .format(this_server_global_tmp)+\
            "and `{}` of the global sources.".format(this_server_global_src))

def check_folders():
    if not os.path.exists(templates_folder):
        print("Creating {} folder...".format(templates_folder))
        os.makedirs(templates_folder)
    if not os.path.exists(sources_folder):
        print("Creating {} folder...".format(sources_folder))
        os.makedirs(sources_folder)
    if not os.path.exists(servers_folder):
        print("Creating {} folder...".format(servers_folder))
        os.makedirs(servers_folder)
    if not os.path.exists(temp_folder):
        print("Creating {} folder...".format(temp_folder))
        os.makedirs(temp_folder)

def check_files():
    if not dataIO.is_valid_json(templates_file):
        print("Creating default {}...".format(templates_file))
        dataIO.save_json(templates_file, {})
    if not dataIO.is_valid_json(sources_file):
        print("Creating default {}...".format(sources_file))
        dataIO.save_json(sources_file, {})
    if not dataIO.is_valid_json(servers_file):
        print("Creating default {}...".format(servers_file))
        dataIO.save_json(servers_file, {})
    if not dataIO.is_valid_json(trusted_users_file):
        print("Creating default {}...".format(trusted_users_file))
        dataIO.save_json(trusted_users_file, [])
    if not dataIO.is_valid_json(log_channels_file):
        print("Creating default {}...".format(log_channels_file))
        dataIO.save_json(log_channels_file, [None, None])

def setup(bot):
    check_folders()
    check_files()
    n = Pic(bot)
    bot.add_cog(n)
