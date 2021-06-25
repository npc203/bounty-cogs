import json
from pathlib import Path

from redbot.core.bot import Red

from .info import Info, get_info, set_info


with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red) -> None:
    cog = Info(bot)
    set_info(bot.get_command("info"))
    if get_info():
        bot.remove_command(get_info().name)
    bot.add_cog(cog)
