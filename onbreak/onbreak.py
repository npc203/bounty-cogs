from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils import AsyncIter

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class OnBreak(commands.Cog):
    """
    Staff break thing
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=123593,
            force_registration=True,
        )
        self.config.register_guild(rid=None, log=None)
        self.config.register_user(inactive=[])

    async def cog_check(self, ctx):
        if not ctx.guild:
            return True
        return await self.config.guild_from_id(
            ctx.guild.id
        ).rid() or not ctx.command.name.startswith("breako")

    @commands.command()
    async def breakon(self, ctx):
        """Enable break for you"""
        for guild in self.bot.guilds:
            if m := guild.get_member(ctx.author.id):
                rid = await self.config.guild_from_id(guild.id).rid()
                if discord.utils.find(lambda x: x.id == rid, m.roles):
                    break
        else:
            return await ctx.send("You are not a staff")

        try:
            await m.remove_roles(guild.get_role(rid), reason="On break")
            async with self.config.user_from_id(m.id).inactive() as f:
                if guild.id not in f:
                    f.append(guild.id)
            if log_channel := self.bot.get_channel(
                await self.config.guild_from_id(guild.id).log()
            ):
                await log_channel.send(
                    embed=discord.Embed(
                        title=f"On Break : {m.name}",
                        description=f"{m.mention} is now on break",
                        color=discord.Color.red(),
                    )
                )
            await ctx.send(f"I've set you as `on break` in  guild `{guild.name}`")
        except discord.HTTPException:
            await ctx.send("Something went wrong, kindly report to the owner")
        except discord.Forbidden:
            await ctx.send("I dont have enough permissions!")

    @commands.command()
    async def breakoff(self, ctx):
        """Disable break for you"""
        async with self.config.user_from_id(ctx.author.id).inactive() as r:
            if r:
                guild = self.bot.get_guild(r[0])
                m = guild.get_member(ctx.author.id)
                things = await self.config.guild_from_id(guild.id).all()
                try:
                    await m.add_roles(
                        guild.get_role(things["rid"]),
                        reason="Back from break",
                    )
                    if log_channel := self.bot.get_channel(things["log"]):
                        await log_channel.send(
                            embed=discord.Embed(
                                title=f"Back from Break : {m.name}",
                                description=f"{m.mention} is now back from break",
                                color=discord.Color.green(),
                            )
                        )
                    await ctx.send("Welcome back from your break")
                except discord.HTTPException:
                    await ctx.send("Something went wrong, kindly report to the owner")
                except discord.Forbidden:
                    await ctx.send("I dont have enough permissions!")

            else:
                await ctx.send("You aren't in break")

    @commands.admin_or_permissions(administrator=True)
    @commands.command()
    async def staffrole(self, ctx, role: discord.Role = None):
        """Set staff role"""
        if role:
            await self.config.guild_from_id(ctx.guild.id).rid.set(role.id)
            await ctx.send("Sucessfully added staff role as " + role.name)
        else:
            await self.config.guild_from_id(ctx.guild.id).rid.set(None)
            await ctx.send("Sucessfully disabled staff role")

    @commands.admin_or_permissions(administrator=True)
    @commands.command()
    async def breaklog(self, ctx, channel: discord.TextChannel = None):
        """On Break logs are sent in this channel"""
        if channel:
            await self.config.guild_from_id(ctx.guild.id).log.set(channel.id)
            await ctx.send(f"Sucessfully set the channel to log as <#{channel.id}>")
        else:
            await self.config.guild_from_id(ctx.guild.id).log.set(None)
            await ctx.send(f"Sucessfully reset the channel to log")

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
