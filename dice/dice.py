import discord
from discord.ext import commands
from discord.errors import HTTPException
from random import randint
import itertools
from collections import Counter

class Roll:
    """Roll some dice."""

    def __init__(self, bot):
        self.bot = bot
        self.max_dice_in_group = 50
        self.include_frequencies = True
        # Set to true if you want '1d20 6' to eval to '1d20+6'
        self.allow_terms_without_operators = False
        # Set to true if you want '-1d20 6' to eval to '-1d20+6',
        # or false for it to eval to '-1d20-6', inheriting the
        # sign of the term before it.
        self.terms_without_operators_are_addition = True

    @commands.command(pass_context=True)
    async def dice(self, ctx, *, message):
        """ Roll some D&D-style dice.
        Example: '1d20+3 - 2d4'
        This means to roll a 20-sided die, add 3, then subtract the
        result of 2 4-sided dice."""
        author = ctx.message.author
        parts = message.split(" ")
        #[ [1, "1d20"], [-1, "3"] ]
        # Add = 1, Subtract = -1
        out = []
        msg = ""

        add = 1
        maxIndex = len(parts)
        i = 0
        # Iterate through all the chunks of the message, split around spaces.
        # We keep a list of the dice in out, and whether or not we should
        # add or subtract them.

        # We loop in a weird manner because occasionally we'll get a message
        # chunk that includes a whole bunch of dice without spaces,
        # like '1d20+3+1d4' and we want to expand the size of parts to include 
        # them all as separate values.
        while i < maxIndex:
            # If the string is empty, skip it.
            if len(parts[i]) is 0:
                i += 1
                continue
            # If this chunk didn't have a + or - before it, default to +,
            # depending on settings.
            if i > 0 and parts[i-1] is not '-' and parts[i-1] is not '+'\
                    and (parts[i][0] is not '-' and parts[i][0] is not '+'):
                if self.allow_terms_without_operators:
                    if self.terms_without_operators_are_addition:
                        add = 1
                        pass
                else:
                    msg = "Please include a + or - before each term."
                    await self.bot.say(msg)
                    return

            # Split up any message fragments that have a bunch of terms in them
            # like '1d20+3+1d4'.
            if len(parts[i]) is not 1 and ('+' in parts[i] or '-' in parts[i]):
                # Black magic from http://stackoverflow.com/a/13186224.
                # It goes something like this:
                # Replace everything that is + or - with ' ',
                # then go through that string, split it around the spaces,
                # and insert what was originally in the string into the array
                # where it should be.
                # The result ends out like this:
                # '1+1d20-1-1+1' -> [1,+,1d20,-,1,-,1,+,1]
                splitters = "+-"
                trans = str.maketrans(splitters, ' ' * len(splitters))
                s = parts[i].translate(trans)
                
                result = []
                position = 0
                for _, letters in itertools.groupby(s, lambda c: c == ' '):
                    letter_count = len(list(letters))
                    result.append(parts[i][position:position+letter_count])
                    position += letter_count

                parts[i:i+1] = result
                maxIndex = len(parts)

            # If the string starts with a +, like '+2d4',
            # we want to add the oncoming dice.
            if parts[i][0] is '+':
                add = 1
                # Remove the + and continue.
                if len(parts[i]) is not 1:
                    parts[i] = parts[i][1:]
                else:
                    i += 1
                    continue
            # If the string starts with a -, we should subtract.
            if parts[i][0] is '-':
                add = -1
                if len(parts[i]) is not 1:
                    parts[i] = parts[i][1:]
                else:
                    i += 1
                    continue

            # If this is a flat value, just add it into the list.
            if parts[i].isdigit():
                out.append([add, parts[i]])
                i += 1
                continue
            # If it's not a flat value, but it doesn't look like dice,
            # complain at the user.
            if 'd' not in parts[i]:
                await self.bot.say("Please roll some dice, like `1d20+3`")
                return
            # Split the die around the 'd', and handle the case where we are
            # given 'd20', changing it to '1d20'.
            count,_,size = parts[i].partition('d')
            if len(count) is 0:
                parts[i] = '1d'+size
                count = '1'
            # If there are extraneous nondigit characters, like in 'ad20', 
            # complain at the user.
            if not count.isdigit() or not size.isdigit():
                await self.bot.say("Please roll some dice, like `2d20+4`")
                return
            # If there are too many dice in a group, complain at the user.
            if int(count) > self.max_dice_in_group:
                msg = "Please don't roll more than {} dice in one go!".format(
                        self.max_dice_in_group)
                await self.bot.say(msg)
                return
            # If one of the dice given is a d0, complain at the user.
            if int(size) is 0:
                await self.bot.say("I can't roll a die with 0 sides...")
                return
            # Finally, this seems to be a reasonable die. 
            out.append([add, parts[i]])
            i += 1

        total = 0
        totalave = 0
        maximum = 0
        minimum = 0
        flat = 0
        rolls = []
        for roll in out:
            die = roll[1]
            # If this is a die, roll them all and chuck the results in a list.
            if 'd' in die:
                A,B = die.split('d')
                rolls.append(
                        [roll[0],
                            roll[1], 
                            [randint(1, int(B)) for a in range(int(A))]])
                total += roll[0] * sum(rolls[-1][2])
                totalave += roll[0] * (int(A) * ((int(B) + 1) / 2))
                # If this die should be subtracted, we want to invert the 
                # min and max values, because the maximum value of dice that 
                # count as negative is actually the minimum rolls on the dice.
                # eg -1d20: -20 < -1
                this_max = roll[0] * (int(A) * int(B))
                this_min = roll[0] * (int(A))
                if roll[0] is 1:
                    maximum += this_max
                    minimum += this_min
                else:
                    minimum += this_max
                    maximum += this_min
            # Otherwise, just process the flat value.
            else:
                total += roll[0] * int(roll[1])
                totalave += roll[0] * int(roll[1])
                flat += roll[0] * int(roll[1])
                maximum += roll[0] * int(roll[1])
                minimum += roll[0] * int(roll[1])

        # Finally, make the message, and say it to the user.
        # This loop lists off all the dice groups that were rolled,
        # and the individual dice that ended out coming up.
        # The second statement adds a count of the frequencies,
        # if requested.
        rolls_string = ""
        for roll in rolls:
            rolls_string += "**{}{}**: {}. Total: **{}**\n".format(
                    "-" if roll[0] is -1 else "",
                    str(roll[1]), 
                    ", ".join(str(s) for s in roll[2]),
                    sum(roll[2]))
            if self.include_frequencies:
                rolls_string += "   {}\n".format(
                        dict(Counter(roll[2])))

        msg = ""
        msg += "{} rolled **{}**!\n\n".format(author.mention, message)
        msg += rolls_string
        msg += "**Flat Bonus:** {}\n\n".format(flat)
        msg += "Total: :game_die: **{}!** :game_die:\n".format(total)
        msg += "The average result is **{}**, ".format(totalave)
        msg += "the minimum is **{}**, ".format(minimum)
        msg += "and the maximum is **{}**!".format(maximum)
        try:
            await self.bot.say(msg)
        except HTTPException:
            error_msg = "I've exceeded the character limit! "
            error_msg += "Try rolling fewer dice next time :slight_smile:"
            await self.bot.say(error_msg)

def setup(bot):
    n = Roll(bot)
    bot.add_cog(n)
