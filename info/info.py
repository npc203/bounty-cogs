from typing import Literal

import discord
import sys
from redbot.core import commands
from redbot.core.bot import Red
import datetime
from redbot.core.utils._internal_utils import fetch_latest_red_version_info
from redbot.core import __version__, version_info as red_version_info

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

old_info = None

get_info = lambda: old_info


def set_info(thing):
    global old_info
    old_info = thing


class Info(commands.Cog):
    """
    An info command cog
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def info(self, ctx):
        """Shows info about [botname]."""
        embed_links = await ctx.embed_requested()
        author_repo = "https://github.com/Twentysix26"
        org_repo = "https://github.com/Cog-Creators"
        red_repo = org_repo + "/Red-DiscordBot"
        red_pypi = "https://pypi.org/project/Red-DiscordBot"
        support_server_url = "https://discord.gg/red"
        dpy_repo = "https://github.com/Rapptz/discord.py"
        python_url = "https://www.python.org/"
        since = datetime.datetime(2016, 1, 2, 0, 0)
        days_since = (datetime.datetime.utcnow() - since).days
        bot_name = ctx.me.name

        app_info = await self.bot.application_info()
        if app_info.team:
            owner = app_info.team.name
        else:
            owner = app_info.owner

        pypi_version, py_version_req = await fetch_latest_red_version_info()
        outdated = pypi_version and pypi_version > red_version_info

        dpy_version = "[{}]({})".format(discord.__version__, dpy_repo)
        python_version = "[{}.{}.{}]({})".format(*sys.version_info[:3], python_url)
        red_version = "[{}]({})".format(__version__, red_pypi)

        intro = (
            "An anime-centric bot that provides moderation, playing audio, image searching, comprehensive automod system, and many more! "
            "I also have a [Dashboard]({}) to see what all I'm capable of."
        ).format("https://dash.lolifox.net")

        about = (
            "This bot is an instance of [Red, an open source Discord bot]({}) "
            "created by [Twentysix]({}) and [improved by many]({}).\n\n"
            "Red is backed by a passionate community who contributes and "
            "creates content for everyone to enjoy. [Join us today]({}) "
            "and help us improve!\n\n"
            "(c) Cog Creators"
        ).format(red_repo, author_repo, org_repo, support_server_url)

        help_txt = (
            "Do you need help? Start by running **`{prefix}help`** to get a menu to navigate."
            "If you need a specific cog, run **`{prefix}help CogName`**.\n\n"
            "If you're still having trouble, or have errors, let **`TwinShadow#0666`** know to get it fixed, "
            "or you can join [this server]({support}) to report the problem. "
            "Many of the cogs are 3rd party, bugs may take some time to be fixed."
        ).format(prefix=ctx.clean_prefix, support="https://discord.gg/somelink")

        embed = discord.Embed(title=f"{bot_name} Info", color=(await ctx.embed_colour()))
        embed.add_field(name=f"About {bot_name}", value=intro)
        embed.add_field(
            name=("Instance owned by team") if app_info.team else ("Instance owned by"),
            value=str(owner),
        )
        embed.add_field(name="Need Help?", value=help_txt, inline=False)

        embed.add_field(name="What is Red?", value=about, inline=False)
        embed.add_field(name="Python", value=python_version)
        embed.add_field(name="discord.py", value=dpy_version)
        embed.add_field(name=("Red version"), value=red_version)

        embed.set_thumbnail(url=ctx.me.avatar_url)
        await ctx.send(embed=embed)

    def cog_unload(self):
        if get_info():
            try:
                self.bot.remove_command("info")
            except Exception as e:
                print("Info cog errored out at:", e)
            self.bot.add_command(get_info())

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
