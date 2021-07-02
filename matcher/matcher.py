from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config


class Matcher(commands.Cog):
    """
    Matchmaking for fun
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=674674390,
            force_registration=True,
        )
        self.config.register_user(
            primary={
                "name": None,
                "age": None,
                "gender": None,
                "timezone": None,
                "location": None,  # Likely country
                "marital status": None,
                "job": [],
                "hobby": [],
                "education": None,  # No idea what the heck is this
                "pfp": None,
            },
            secondary={
                "keywords": [],
            },
            hide=[],  # A list, the user can use to hide stuff they don't wanna show
        )

    @commands.command()
    async def profile(self, ctx):
        """See your profile"""
        data = await self.config.user_from_id(ctx.author.id).all()
        emb = discord.Embed(title=f"{ctx.author}'s Profile")
        emb.set_thumbnail(
            url=data["primary"].pop("pfp") if data["primary"]["pfp"] else ctx.author.avatar_url
        )

        for name, value in data["primary"].items():
            emb.add_field(name=name.title(), value=value or "None")

        await ctx.send(embed=emb)

    @commands.command()
    async def match(self, ctx):
        """Find a match to you"""
        # TODO add coins/tokens to avail this

    @commands.command()
    async def setup(self, ctx):
        """Set your profile things"""
        # TODO

    @commands.admin()
    @commands.group()
    async def matchset(self, ctx):
        """Settings to setup matcher"""

    @matchset.command()
    async def selfie(self, ctx, channel: discord.TextChannel):
        """Add a selfie channel to take pfp"""

    @matchset.command()
    async def edit(self, ctx, cmd, add_or_remove, person: discord.Member, *things):
        """Edit various stuff of a person, if the bot get's it wrong"""
    
    @commands.command()
    async def fuck(self,ctx,a:discord.User):
        

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
