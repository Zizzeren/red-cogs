import discord
from discord.ext import commands
from discord.errors import HTTPException
import requests
import random

# Warning: Long
parts = [
"lio","vjw","pme","eqc","skp","pkj","qox","mbd","fmu","rts","iue","ufi","hpl",
"edl","qnp","ode","iga","aux","slb","ltd","jnx","omh","jzm","hvt","jid","lpb",
"pyg","lsn","jih","pmv","qdx","dzh","amf","idu","rfc","exr","tpf","qrz","dhr",
"fym","cdl","scx","pmq","rum","api","jto","oqe","fvb","oja","mxd","unp","ujr",
"yig","rgz","vmj","eho","coe","hki","oay","smk","dep","qxy","htw","wxc","uvj",
"unm","uts","drm","atr","fmg","xbc","beo","tqa","xyu","qrd","nqk","zpq","jdl",
"wji","ebs","ofs","huv","ugp","jis","qgx","por","tjq","ydh","imw","tqg","arb",
"vtg","jvw","bfv","sqh","zlw","rsu","ybv","lyc","usw","kxl","lfm","hdc","byu",
"eun","wkj","vjg","ais","mhj","yed","mxb","oni","sva","bcl","slc","tkz","cqm",
"phf","aos","wut","bet","sap","knz","kel","hjz","ayp","xbu","cvu","pzn","gxr",
"tne","zxs","etp","fxb","btw","jxe","ipr","vrz","lvs","ipw","zmk","ekn","ndr",
"rto","ond","ljr","abg","eks","vtn","lxc","lzs","jrl","nif","bua","eub","ysi",
"lae","bpz","sot","czv","jha","stg","zuc","fhg","hym","jhm","jqi","axi","apm",
"doc","pzx","itd","vem","vpm","xwj","xhc","rzs","lpf","xze","lhj","eop","wen",
"mqy","reo","wic","tfv","cbm","cbx","fwn","piv","wmt","vob","agd","qej","erb",
"arz","nwa","xpa","jtg","hsw","vux","ekm","mgr","hel","dnh","ohi","jhr","pdw",
"sxj","dya","dth","lsz","tgl","uey","qzv","goi","zel","lvm","ljh","lkq","miz",
"uct","pbs","aih","qrd","wqd","sub","rfw","pjb","pew","kro","dps","mho","ejf",
"oth","vqn","stg","lpf","exc","dlf"
        ]

class RCG:
    """An interface for the C&H Random Comic Generator."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def rcg(self, ctx, name=None):
        """Get a random comic, or name a specific one."""
        await self.bot.send_typing(ctx.message.channel)
        if name is None:
            name = "{}{}{}".format(random.choice(parts), 
                                   random.choice(parts), 
                                   random.choice(parts))
        # Send a GET to generate the image
        r = requests.get("https://explosm.net/rcg/{}".format(name))
        if r.status_code != requests.codes.ok:
            await self.bot.say("That didn't work. I tried {}".format(name))
            return
        # Send the link to the image in chat.
        await self.bot.say("https://files.explosm.net/rcg/{}.png".format(name))

def setup(bot):
    n = RCG(bot)
    bot.add_cog(n)
