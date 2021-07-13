from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from fuzzywuzzy import fuzz, process
import inspect
import pycountry
import asyncio
import pytz


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
        self.config.register_guild(accuracy=80, tokenrate=300)
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
            token=0,
            secondary={
                "keywords": [],
            },
            hide=[],  # A list, the user can use to hide stuff they don't wanna show
        )

    @commands.command()
    async def profile(self, ctx):
        """See your profile"""
        data = await self.config.user_from_id(ctx.author.id).all()
        await ctx.send(embed=await self.emb_profile(data, ctx))

    async def emb_profile(self, data, ctx):
        emb = discord.Embed(title=f"{ctx.author}'s Profile", color=await ctx.embed_color())
        pfp = data["primary"].pop("pfp")
        emb.set_thumbnail(url=pfp or ctx.author.avatar_url)
        for name, value in data["primary"].items():
            emb.add_field(
                name=name.title(),
                value=(str(value).title() if type(value) is not list else ", ".join(value))
                or "Not set yet",
            )
        return emb

    @commands.command()
    async def match(self, ctx):
        """Find a match to you"""
        x = await self.config.all_users()  # TODO remove DMs
        full_client = x.pop(ctx.author.id, None)
        if not full_client:
            return await ctx.send(
                f"You have not set a profile, kindly set it up using `{ctx.prefix}setup`"
            )

        if full_client["token"] <= 0:
            return await ctx.send("You don't have any tokens! buy one from the shop")

        target = full_client["primary"]
        if not target:
            return await ctx.send("You need to set a profile to match with others")

        if len(tuple(map(bool, target.values()))) < (len(target) // 2):
            return await ctx.send("You have too many blank fields, fill them")

        # TODO reduce the token/coins here
        target.pop("pfp", None)
        score = (None, 0)
        for user, data in x.items():
            tmp = [user, 0]
            for key, val in target.items():
                if bool(val):
                    tmp[1] += fuzz.ratio(val, data["primary"][key])
            if tmp[1] > score[1]:
                score = tmp

        accuracy = await self.config.guild_from_id(ctx.guild.id).accuracy()
        # print(score, flush=True)
        if score[0] and score[1] > len(target) * 100 / accuracy:
            await ctx.send(f"The closest match the bot can find is {self.bot.get_user(score[0])}")
        else:
            await ctx.send("No close matches found")

    @commands.command()
    async def setup(self, ctx):
        """Set your profile things"""

        # q[question,conf_attr,function(msg)->(value_to_write:str.check:bool)]
        q = [
            ("What is your name?", "name", (lambda x: (x, len(x) < 70))),
            ("How old are you?", "age", (lambda x: (x, x.isdigit() and int(x) < 80))),
            (
                "What is your gender? (Use 'other' if you don't want to mention it)",
                "gender",
                (
                    lambda x: (
                        x.lower(),
                        x.lower()
                        in (
                            "male",
                            "female",
                            "heterosexual",
                            "homosexual",
                            "bisexual",
                            "transgender",
                            "demisexual",
                            "genderfluid",
                            "nonbinary",
                            "gay",
                            "other",
                        ),
                    )
                ),
            ),
            ("What is your timezone? Contient/City", "timezone", self.get_timezone),  # TODO
            (
                "Which country do you live in?",
                "location",
                lambda x: (lambda country: (country.official_name, True))(
                    pycountry.countries.search_fuzzy(x)[0]
                ),
            ),  # TODO
            (
                "Are you married/single/taken?",
                "marital status",
                (lambda x: (x, x.lower() in ("single", "married", "taken"))),
            ),
            (
                "What are your hobbies (separated by comma)?",
                "hobby",
                (lambda x: (x.split(","), True)),
            ),
            (
                "What's your job(s) (separated by comma if multiple)",
                "job",
                (lambda x: (x.split(","), True)),
            ),
        ]
        try:
            await ctx.author.send(
                f"Setup your profile by answering the following {len(q)} questions:\n You can always cancel anytime by typing `cancel`"
            )
        except discord.Forbidden:
            return await ctx.send("I can't send messages to you")

        conf = self.config.user_from_id(ctx.author.id)
        succ = []
        prev = None
        for ind, val in enumerate(q, 1):
            await ctx.author.send(
                (f"Your answer was: {prev}" if prev else "") + f"\n{ind}. {val[0]}"
            )
            for _ in range(3):
                try:
                    resp = await self.bot.wait_for(
                        "message",
                        check=lambda x: ctx.author == x.author and x.guild is None,
                        timeout=300,
                    )
                except asyncio.TimeoutError:
                    return await ctx.author.send("Timed out, try again later")

                if "cancel" == resp.content.lower():
                    return await ctx.author.send("You have cancelled your setup")

                # Parse le questions
                if inspect.iscoroutinefunction(val[2]):
                    ans = await val[2](ctx, resp.content)
                else:
                    ans = val[2](resp.content)

                if ans[1]:
                    succ.append((val[1], ans[0]))
                    prev = ans[0]
                    break
                elif ans[0] is None:
                    pass
                else:
                    await ctx.author.send("Ill-formatted value, Try Again")
            else:
                return await ctx.author.send("Too many wrong values, Aborting")
                break
        if succ:
            async with self.config.user_from_id(ctx.author.id).primary() as conf:
                for i, j in succ:
                    conf[i] = j

        await ctx.author.send(
            f"You have set your profile! , check it out using {ctx.prefix}profile"
        )

    @commands.admin()
    @commands.group()
    async def matchset(self, ctx):
        """Settings to setup matcher"""

    @matchset.command()
    async def selfie(self, ctx, channel: discord.TextChannel):
        """Add a selfie channel to take pfp"""
        # TODO

    @matchset.command()
    async def show(self, ctx):
        """Shows info about the setup"""
        a = await self.config.guild_from_id(ctx.guild.id).all()
        emb = discord.Embed(title="Info", color=await ctx.embed_color())
        for i, j in a.items():
            emb.add_field(name=i, value=j)
        await ctx.send(embed=emb)

    @matchset.command(name="token")
    async def set_tokens(self, ctx, person: discord.User, number: int):
        """Force reset a token to a new value for a person"""
        prev = await self.config.user_from_id(person.id).token()
        await self.config.user_from_id(person.id).token.set(number)
        await ctx.send(f"`{str(person)}`'s tokens is now {number}, previously it was {prev}")

    @matchset.command()
    async def accuracy(self, ctx, number: int):
        """Set the match lvl accuracy, between 1 and 100"""
        if 0 < number <= 100:
            await self.config.guild_from_id(ctx.guild.id).accuracy.set(number)
        else:
            await ctx.send("Accuracy should be a number between 1 and 100")

    @matchset.command(name="primary")
    async def primary(self, ctx, person: discord.User, thing, *, change):
        """Edit primary settings of a person"""
        await self.config.user_from_id(person.id)

    async def get_timezone(self, ctx, x):
        if res := self.fuzzy_timezone_search(x):
            if len(res) == 1:
                return res[0], True
            else:
                await ctx.author.send(
                    embed=discord.Embed(
                        title="Pick a timezone from:",
                        description="click [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) to get a list of all valid timezones\n"
                        + ("\n".join(res)),
                    ).set_footer(text="And try again")
                )
                return None, False
        else:
            await ctx.author.send(
                "Couldn't find timezone, pick one from <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones> and type again"
            )
            return None, False

    # thanks aika/vex
    # https://github.com/aikaterna/aikaterna-cogs/blob/v3/timezone/timezone.py#L35
    def fuzzy_timezone_search(self, tz: str):
        fuzzy_results = process.extract(
            tz.replace(" ", "_"), pytz.common_timezones, limit=500, scorer=fuzz.partial_ratio
        )
        matches = [x[0] for x in fuzzy_results if x[1] > 98]
        return matches

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)
