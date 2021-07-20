import json
from pathlib import Path

from redbot.core.bot import Red
from redbot.core import Config, commands
from redbot.core.commands.help import HelpSettings, dpy_commands, NoCommand, NoSubCommand
import discord


class MMhelp(commands.RedHelpFormatter):
    async def send_help(self, ctx, help_for=None, *, from_help_command=False):

        help_settings = await HelpSettings.from_context(ctx)

        if help_for is None or isinstance(help_for, dpy_commands.bot.BotBase):
            emb = discord.Embed(
                title="Help",
                description="You can get help with commands by typing `{0}help [command]`".format(
                    ctx.prefix
                ),
            ).set_thumbnail(url=ctx.bot.user.avatar_url)
            emb.add_field(
                name="Matchmaking commands",
                value=(
                    """ `.tutorial` will start the tutorial.
                        `.match   ` will start a match process.
                        `.tokens  ` will display your current token balance.
                        `.matches ` will display everyone you previously matched with.
                        `.profile ` will display your public matchmaking profile.
                        """
                ),
            )
            await ctx.send(embed=emb)
            return

        if isinstance(help_for, str):
            try:
                help_for = self.parse_command(ctx, help_for)
            except NoCommand:
                await self.command_not_found(ctx, help_for, help_settings=help_settings)
                return
            except NoSubCommand as exc:
                if help_settings.verify_exists:
                    await self.subcommand_not_found(
                        ctx, exc.last, exc.not_found, help_settings=help_settings
                    )
                    return
                help_for = exc.last

        if isinstance(help_for, commands.Cog):
            await self.format_cog_help(ctx, help_for, help_settings=help_settings)
        else:
            await self.format_command_help(ctx, help_for, help_settings=help_settings)


def setup(bot):
    try:
        bot.set_help_formatter(MMhelp())
    except RuntimeError:
        pass


def teardown(bot):
    bot.reset_help_formatter()