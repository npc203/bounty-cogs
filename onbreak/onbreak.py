from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

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
        self.config.register_guild(rids=[], log=None)
        self.config.register_user(inactive=[])

    async def cog_check(self, ctx):
        if not ctx.guild:
            return True
        return bool(await self.config.guild_from_id(
            ctx.guild.id
        ).rids()) or not ctx.command.name.startswith("breako")

    @commands.command()
    async def breakon(self, ctx):
        """Enable break for you"""
        for guild in self.bot.guilds:
            if m := guild.get_member(ctx.author.id):
                rids = await self.config.guild_from_id(guild.id).rids()
                if x:= list(filter(lambda x: x.id in rids, m.roles)):
                    break
        else:
            return await ctx.send("You are not a staff")

        try:
            await m.remove_roles(*x, reason="On break")
            async with self.config.user_from_id(m.id).inactive() as f:
                # I have no clue why the heck I am doing this, but just to be sure, to avoid loose ends
                if any(i[0]==guild.id for i in f):
                    return await ctx.send("You are already in break")
                else:
                    f.append((guild.id,*map(lambda r:r.id,x)))

            if log_channel := self.bot.get_channel(
                await self.config.guild_from_id(guild.id).log()
            ):
                await log_channel.send(
                    embed=discord.Embed(
                        title=f"On Break : {m.name}",
                        description=f"{m.mention} is now on break",
                        color=discord.Color.red(),
                    ).add_field(name="Roles removed:",value="\n".join(i.mention for i in x))
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
                suc = []
                for i in range(len(r)):
                    guild = self.bot.get_guild(r[i][0])
                    m = guild.get_member(ctx.author.id)
                    log_conf = await self.config.guild_from_id(guild.id).log()
                    try:
                        roles = list(map(lambda x: guild.get_role(x),r[i][1:]))
                        print(roles)
                        await m.add_roles(
                            *roles,
                            reason="Back from break",
                        )
                        if log_channel := self.bot.get_channel(log_conf):
                            await log_channel.send(
                                embed=discord.Embed(
                                    title=f"Back from Break : {m.name}",
                                    description=f"{m.mention} is now back from break",
                                    color=discord.Color.green(),
                                ).add_field(name="Roles added",value="\n".join(i.mention for i in roles))
                            )
                        suc.append(i)
                    except discord.HTTPException:
                        await ctx.send(f"Something went wrong, kindly report to the owner of {guild.name}!")
                    except discord.Forbidden:
                        await ctx.send(f"I dont have enough permissions on {guild.name}!")
                r[:] = [i for j, i in enumerate(r) if j not in suc]
                await ctx.send("Welcome back from your break")
            else:
                await ctx.send("You aren't in break")
    
    @commands.admin_or_permissions(administrator=True)
    @commands.command()
    async def breakshow(self, ctx):
        """Show settings"""
        things = await self.config.guild_from_id(ctx.guild.id).all()
        emb = discord.Embed(title="OnBreak settings")
        emb.add_field(name="All staff roles",value="\n".join(f"<@&{i}>" for i in things["rids"]) or "None",inline=False)
        emb.add_field(name="Log channel",value=f"<#{things['log']}>" or "None",inline=False)
        await ctx.send(embed=emb)
       
    @commands.admin_or_permissions(administrator=True)
    @commands.group()
    async def breakrole(self, ctx):
        """Set staff role for break"""
    
    @breakrole.command()
    async def add(self,ctx,role: discord.Role):
        """Add staff role"""
        async with self.config.guild_from_id(ctx.guild.id).rids() as a:
            if role.id not in a:
                a.append(role.id)
                await ctx.send("Sucessfully added staff role as " + role.name)
            else:
                await ctx.send("Role already present")
       
    
    @breakrole.command()
    async def remove(self,ctx,role: discord.Role):
        """Remove staff role"""
        async with self.config.guild_from_id(ctx.guild.id).rids() as a:
            if role.id in a:
                a.remove(role.id)
                await ctx.send("Sucessfully removed the staff role " + role.name)
            else:
                await ctx.send("Role not present")
        

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
