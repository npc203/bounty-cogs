import discord
from discord.ext import tasks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
import time
import asyncio
from typing import Union
from redbot.core.utils.chat_formatting import humanize_timedelta
import re


class VcAfk(commands.Cog):
    """
    Kicks people from VC if AFK
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=5345272839,
            force_registration=True,
        )

        self.config.register_global(
            msg="{user.mention} Are you still there? you got {timeout} seconds to respond"
        )
        self.config.register_guild(
            resptime=3600, timeout=180, call_channel=None, channels=[], roles=[]
        )
        self.active_users = {}  # uid: [channel,timestamp]
        self.main_update_loop.start()
        asyncio.create_task(self.fill_users())

    async def fill_users(self):
        await self.bot.wait_until_red_ready()
        data = await self.config.all_guilds()
        for item in data.values():
            for cid in item["channels"]:
                if item["call_channel"] is not None:
                    if channel := self.bot.get_channel(cid):
                        for member in channel.members:
                            for role in member.roles:
                                if role.id in item["roles"]:
                                    break
                            else:
                                self.active_users[member.id] = [channel, time.time()]

    def cog_unload(self):
        self.main_update_loop.cancel()

    async def handle_user_afk(self, uid, vc_channel):
        """Internal method to handle bot sending messages for a user"""
        self.active_users.pop(uid)

        things = await self.config.guild_from_id(vc_channel.guild.id).all()
        member = vc_channel.guild.get_member(uid)

        # if a role was imposed while in active_users
        if discord.utils.find(lambda role: role.id in things["roles"], member.roles):
            return

        txt_channel = self.bot.get_channel(things["call_channel"])
        await txt_channel.send(
            (await self.config.msg()).format(user=member, timeout=things["timeout"])
        )
        try:
            await self.bot.wait_for(
                "message",
                timeout=things["timeout"],
                check=lambda msg: msg.author.id == uid and msg.channel.id == txt_channel.id,
            )
            await txt_channel.send("Alright, you aren't afk")
            self.active_users[uid] = [vc_channel, time.time()]
        except asyncio.TimeoutError:
            try:
                await vc_channel.guild.get_member(uid).move_to(
                    None, reason="Kicked for being AFK in VC"
                )
                await txt_channel.send(
                    f"No response from {member.mention} , kicking from VC",
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.Forbidden:
                await txt_channel.send(
                    f"Something went wrong while attempting to kick <@{uid}> \n Please give me admin perms or cross check my permissions"
                )
                self.active_users[uid] = [vc_channel, time.time()]

    @tasks.loop(seconds=10)
    async def main_update_loop(self):
        for uid, (channel, timestamp) in self.active_users.items():
            if (time.time() - timestamp) > (
                await self.config.guild_from_id(channel.guild.id).resptime()
            ):
                asyncio.create_task(self.handle_user_afk(uid, channel))

    @commands.Cog.listener("on_voice_state_update")
    async def vc_updates(self, member, before, after):
        if member.bot:
            return

        # User left VC
        if after.channel is None:
            self.active_users.pop(member.id, None)
            return

        # User joined VC
        if before.channel is None and after.channel:
            things = await self.config.guild_from_id(after.channel.guild.id).all()

            # In an untracked channel:
            if after.channel.id not in things["channels"]:
                return

            # Has a whitelist role
            if discord.utils.find(lambda role: role.id in things["roles"], member.roles):
                return

            self.active_users[member.id] = [after.channel, time.time()]
            return

        self.active_users[member.id] = [after.channel, time.time()]

    @commands.Cog.listener("on_message")
    async def msg_updates(self, msg):
        if msg.author.bot or msg.guild is None or msg.author.voice is None:
            return

        if msg.author.id in self.active_users:
            self.active_users[msg.author.id][1] = time.time()

    @commands.group()
    async def vcafk(self, ctx):
        """Commands to setup VCafk"""

    @vcafk.command()
    async def show(self, ctx):
        """Shows the channels set up for VC tracking"""
        things = await self.config.guild_from_id(ctx.guild.id).all()
        msg = await self.config.msg()
        confirm = (
            f'`enabled` and prompts in <#{things["call_channel"]}>'
            if things["call_channel"]
            else "`disabled`"
        )
        embed = discord.Embed(
            title="Info Settings", description=f"VC tracking is {confirm} in this server"
        )
        embed.add_field(
            name="AFK time interval (time taken before the bot prompts)",
            value=f"{humanize_timedelta(seconds=things['resptime'])}",
            inline=False,
        )
        embed.add_field(
            name="Wait time (time waited by the bot for a response)",
            value=f"{humanize_timedelta(seconds=things['timeout'])}",
            inline=False,
        )
        if things["call_channel"]:
            embed.add_field(
                name="Prompt channel", value=f"<#{things['call_channel']}>", inline=False
            )
        embed.add_field(
            name="Custom message said by the bot",
            value=msg.format(user=ctx.author, timeout=things["timeout"]),
            inline=False,
        )
        if things["channels"]:
            embed.add_field(
                name="Tracked channels",
                value="\n".join(map(lambda x: f"<#{x}>", things["channels"])),
                inline=False,
            )
        if things["roles"]:
            embed.add_field(
                name="Whitelisted roles",
                value="\n".join(map(lambda x: f"<@&{x}>", things["roles"])),
                inline=False,
            )
        await ctx.send(embed=embed)

    @vcafk.command()
    async def enable(self, ctx, false_or_channel: Union[bool, discord.TextChannel]):
        """Enable or disable tracking this server
        Either use a channel"""
        if not false_or_channel:
            await self.config.guild_from_id(ctx.guild.id).call_channel.set(None)
            await ctx.send("Sucessfully disabled in this server")
        else:
            if type(false_or_channel) is discord.TextChannel:
                await self.config.guild_from_id(ctx.guild.id).call_channel.set(false_or_channel.id)
                await ctx.send(
                    f"Sucessfully enabled VC tracking, prompts users in <#{false_or_channel.id}>"
                )
            else:
                await ctx.send("Invalid choice: Either choose `false` or `A Text channel`")

    @vcafk.command()
    async def afktime(self, ctx, *, time_str: str):
        """How long the bot waits before asking if user is afk
        Example:
        `[p]vcafk afktime 1h 30m 2s`
        `[p]vcafk afktime 39m 1s`
        """
        time_in_seconds = self.convert_time(time_str)
        if not time_in_seconds:
            return await ctx.send_help()
        if time_in_seconds < 30:
            return await ctx.send("Minimum afktime is 30 seconds")
        await self.config.guild_from_id(ctx.guild.id).resptime.set(time_in_seconds)
        await ctx.send(
            f"Sucessfully set the afk time to {humanize_timedelta(seconds=time_in_seconds)}"
        )

    @vcafk.command()
    async def waittime(self, ctx, *, time_str: str):
        """User response waiting time when the question is asked
        Example:
        `[p]vcafk waittime 1h 30m`
        `[p]vcafk waittime 30m 1s`
        """

        time_in_seconds = self.convert_time(time_str)
        if not time_in_seconds:
            return await ctx.send_help()
        if time_in_seconds <= 1:
            return await ctx.send("Please type a number greater than 1 and in proper format")
        await self.config.guild_from_id(ctx.guild.id).timeout.set(time_in_seconds)
        await ctx.send(
            f"Sucessfully set the waittime to {humanize_timedelta(seconds=time_in_seconds)}"
        )

    @commands.is_owner()
    @commands.guild_only()
    @vcafk.command()
    async def msg(self, ctx, *, message):
        """Customise the message the bot asks
        Use: `{user.name}`, `{user.mention}`, `{user.display_name}` , `{timeout}` are nice to try out
        Example: [p]vcafk msg {user.mention} are ya living son? you have {timeout} seconds to reply"""
        await self.config.msg.set(message)
        await ctx.send(
            "Changed message to "
            + message.format(
                user=ctx.author, timeout=(await self.config.guild_from_id(ctx.guild.id).resptime())
            )
        )

    @vcafk.group()
    async def role(self, ctx):
        """Roles that bypass afk kicking"""

    @role.command(name="add")
    async def role_add(self, ctx, role: discord.Role):
        """Add role to the bypass list"""
        async with self.config.guild_from_id(ctx.guild.id).roles() as conf_roles:
            if role.id not in conf_roles:
                conf_roles.append(role.id)
            else:
                return await ctx.send("This role is already in the allowlist")

        channels = await self.config.guild_from_id(ctx.guild.id).channels()
        for cid in channels:
            if channel := self.bot.get_channel(cid):
                if isinstance(channel, discord.VoiceChannel):
                    for user in channel.members:
                        if user.id in self.active_users and role in user.roles:
                            self.active_users.pop(user.id)

        await ctx.send(f"Anyone with the role `{role}` are immune to VC afk kicking")

    # Removing this cause it pings maybe? might add if ya want
    # @role.command(name="list")
    # async def role_list(self, ctx):
    #     """List all roles that bypass afk kicking"""
    #     await ctx.send(
    #         "List of roles in allow\n"
    #         + (
    #             "\n".join(
    #                 map(
    #                     lambda x: f"<@{x}>",
    #                     await self.config.guild_from_id(ctx.guild.id).roles(),
    #                 )
    #             )
    #             or "None"
    #         )
    #     )

    @role.command(name="remove")
    async def role_remove(self, ctx, role: discord.Role):
        """Remove role from the bypass list"""
        async with self.config.guild_from_id(ctx.guild.id).roles() as conf_roles:
            try:
                conf_roles.remove(role.id)
            except ValueError:
                return await ctx.send("This role is not present in the allowlist")

        channels = await self.config.guild_from_id(ctx.guild.id).channels()
        for cid in channels:
            if channel := self.bot.get_channel(cid):
                if isinstance(channel, discord.VoiceChannel):
                    for user in channel.members:
                        if user.id not in self.active_users and role in user.roles:
                            self.active_users[user.id] = [channel, time.time()]

        await ctx.send(f"Removed the {role} role from allowlist")

    @vcafk.group()
    async def channel(self, ctx):
        """Set the voice channels to track"""

    @channel.command(name="add")
    async def channel_add(self, ctx, channel: discord.VoiceChannel):
        """Add a voice channel(s) to the list"""
        async with self.config.guild_from_id(ctx.guild.id).channels() as channels:
            if channel.id not in channels:
                channels.append(channel.id)
            else:
                return await ctx.send("This channel is already being tracked")

        roles = await self.config.guild_from_id(ctx.guild.id).roles()
        for member in channel.members:
            for role in member.roles:
                if role.id in roles:
                    break
                else:
                    self.active_users[member.id] = [channel, time.time()]

        await ctx.send(f"Sucessfully added the channel <#{channel.id}> to tracklist")

    @channel.command(name="list")
    async def channel_list(self, ctx):
        """List all the tracking vc's in this server"""
        await ctx.send(
            "List of tracked channels in this server\n"
            + (
                "\n".join(
                    map(
                        lambda x: f"<#{x}>",
                        await self.config.guild_from_id(ctx.guild.id).channels(),
                    )
                )
                or "None"
            )
        )

    @channel.command(name="remove")
    async def channel_remove(self, ctx, channel: discord.VoiceChannel):
        """A voice channel from the list"""
        async with self.config.guild_from_id(ctx.guild.id).channels() as channels:
            try:
                channels.remove(channel.id)
            except ValueError:
                return await ctx.send("This channel wasn't added in the tracking list")

        pop_users = []
        for uid, items in self.active_users.items():
            if channel.id == items[0].id:
                pop_users.append(uid)

        for uid in pop_users:
            self.active_users.pop(uid)

        await ctx.send(f"<#{channel.id}> is removed from the tracking list")

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        return

    def convert_time(self, text):
        # From dpy
        data = []
        t = 0
        reg = r"([0-9]+)(?: )?([ywdhms])+"
        if isinstance(text, str):
            data = re.findall(reg, text, re.IGNORECASE)
        if isinstance(text, int) or isinstance(text, float):
            t = text
        for d in data:
            if d[1].lower() == "y":
                t += 604800 * 4.3482 * 12 * int(d[0])
            if d[1] == "M":
                t += 604800 * 4.3482 * int(d[0])
            if d[1].lower() == "w":
                t += 604800 * int(d[0])
            if d[1].lower() == "d":
                t += 86400 * int(d[0])
            if d[1].lower() == "h":
                t += 3600 * int(d[0])
            if d[1] == "m":
                t += 60 * int(d[0])
            if d[1].lower() == "s":
                t += int(d[0])
        return t
