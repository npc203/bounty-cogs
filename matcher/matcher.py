from typing import Literal

import discord
from redbot.core import commands, data_manager
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box
from fuzzywuzzy import fuzz, process
import inspect
import pycountry
import asyncio
import pytz
import yake
import json
from collections import defaultdict
from discord.ext import tasks
from redbot.core.utils import menus


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
        self.filter_kw = yake.KeywordExtractor(lan="en", n=3, dedupLim=0.9, features=None)
        self.main_update_loop.start()
        self.config.register_user(
            primary={
                "Age Verified": False,
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
            secondary={"keywords": [], "likes": [], "dislikes": [], "exp": [], "hobbies": []},
            hide=[],  # A list, the user can use to hide stuff they don't wanna show
        )
        self.cache = defaultdict(lambda: {"likes": set(), "exp": set(), "hobbies": set()})
        with open(data_manager.bundled_data_path(self) / "all.json", "r", encoding="utf8") as f:
            self.search_words = json.load(f)

    def cog_unload(self):
        self.main_update_loop.cancel()

    @commands.Cog.listener(name="on_reaction_add")
    async def reaction_stuff(self, reaction: discord.Reaction, user: discord.User):
        if user.bot:
            return
        # print(reaction, flush=True)
        # Matchmaking arrow thing
        if (
            reaction.message.id == 867010712663752714
            and reaction.custom_emoji
            and reaction.emoji.id == 823917870089764895
        ):
            await reaction.message.remove_reaction(reaction.emoji, user)
            msg = await user.send(
                "Welcome to matchmaking! Here's a short, comprehensive guide on how it works"
            )
            ctx = await self.bot.get_context(msg)
            ctx.author = user
            await self.startup_guide(ctx, msg)

    async def startup_guide(self, ctx, check_msg=None):
        tut = [
            "This is your profile. Here you can see the primary modules that are displayed by other users when you match.\nhttp://prntscr.com/1cpsann",
            "As you chat in the server, the bot will collect data about you.\n"
            "These modules are secondary, and are not displayed to your matches.\n"
            "The bot collects this data in order to narrow down what the closest match is to you.\n"
            "It collects this data over time, so you have to continually talk in the server for the bot to get to know you.\nhttp://prntscr.com/1cpsqtc",
            "The accuracy of matching and data accumulation increases over time.\nhttp://prntscr.com/1cptglk",
            "You can erase your data using `.mydata forgetme`\nNote: If you leave the server without erasing your data, It WILL be saved until you erase it.",
            "Use `.setup` to start setting up your basic profile details and to get started with matching",
        ]
        if test := self.bot.get_guild(858756375541448704).get_member(ctx.author.id):
            print(*map(lambda x: x.name, test.roles))
            if not discord.utils.find(lambda m: m.id == 859147972000481320, test.roles):
                return await ctx.send("You are not eligible for matchmaking!")
        else:
            return await ctx.send("You are not eligible for matchmaking")

        check_msg = await ctx.send(
            f"Welcome to matchmaking, Kindly read this guide and react with a tick mark to continue \n\n Please react below with a  \U00002705  to get started, or a  \U0000274e  if you are not ready."
        )
        await menus.start_adding_reactions(check_msg, ["\U00002705", "\U0000274e"])
        try:
            resp = await self.bot.wait_for(
                "reaction_add",
                check=lambda x, user: ctx.author.id == user.id
                and x.message.id == check_msg.id
                and x.emoji in ["\U0000274e", "\U00002705"],
                timeout=300,
            )
        except asyncio.TimeoutError:
            return

        if resp[0].emoji == "\U0000274e":
            return await ctx.send(
                "\U0000274e You have not completed your setup, react to the message in the server again to start."
            )
        for ind, val in enumerate(tut, 1):
            await check_msg.edit(
                content=f"**Page: {ind}/{len(tut)}**\n{val}\n\n React with \U00002705 to continue."
            )
            try:
                resp = await self.bot.wait_for(
                    "reaction_add",
                    check=lambda x, user: ctx.author.id == user.id
                    and x.message.id == check_msg.id
                    and x.emoji in ["\U0000274e", "\U00002705"],
                    timeout=300,
                )
            except asyncio.TimeoutError:
                return

            reaction = resp[0].emoji
            if reaction == "\U0000274e":
                return await ctx.send(
                    "\U0000274e You have not completed your setup, react to the message in the server again to start."
                )

        await ctx.send(
            f"<a:verifycyan:859079239538311198> You have read the guide successfully , continue with `.setup` to set up your profile."
        )

    @commands.command()
    async def tutorial(self, ctx):
        """Shows a basic tutorial on how to use the bot"""
        await self.startup_guide(ctx)

    @tasks.loop(seconds=5)
    async def main_update_loop(self):
        # HOTFIX, fix later
        for k, v in self.cache.copy().items():
            if any(v.values()):
                async with self.config.user_from_id(k).secondary() as conf:
                    for i, j in v.items():
                        conf[i] = list(set(conf[i]).union(j))
        self.cache = defaultdict(lambda: {"likes": set(), "exp": set(), "hobbies": set()})

    @commands.admin()
    @commands.command()
    async def ageverify(self, ctx, user: discord.User):
        async with self.config.user_from_id(user.id).primary() as conf:
            if not conf["Age Verified"]:
                conf["Age Verified"] = True
                await ctx.send(f"Age is verified for {user.name}")
                await ctx.guild.get_member(user.id).add_roles(
                    ctx.guild.get_role(859147972000481320),
                    ctx.guild.get_role(859147973061509120),
                    reason="verification system",
                )
            else:
                await ctx.send("Already verified >_>")

    @commands.Cog.listener(name="on_message_without_command")
    async def secondary_kw(self, msg):
        if msg.author.bot and msg.guild is not None:
            return
        text = msg.content
        kw = set(i[0] for i in self.filter_kw.extract_keywords(text))

        fin_likes = []
        fin_hobbies = []
        fin_exp = []

        for i in kw:
            if len(i) <= 2:
                continue
            for j in self.search_words["likes"]:
                if i.lower() == j:
                    fin_likes.append(j)
                    break
            for j in self.search_words["exp"]:
                if i.lower() == j:
                    fin_exp.append(j)
                    break
            for j in self.search_words["hobbies"]:
                if i.lower() == j:
                    fin_hobbies.append(j)
                    break

        self.cache[msg.author.id]["likes"].update(fin_likes)
        self.cache[msg.author.id]["exp"].update(fin_exp)
        self.cache[msg.author.id]["hobbies"].update(fin_hobbies)
        # self.cache[msg.author.id]["exp"].update([w for i in kw for w in self.search_words["exp"] if i.lower() in w])
        # del kw,fin

    @commands.has_role(859147972000481320)
    @commands.command()
    async def profile(self, ctx):
        """See your profile"""
        data = await self.config.user_from_id(ctx.author.id).all()
        if None in data.values():
            await ctx.send("You need to setup a profile, set it using .setup")
        else:
            await ctx.send(embed=await self.emb_profile(data, ctx))

    async def emb_profile(self, data, ctx):
        emb = discord.Embed(title=f"{ctx.author}'s Profile", color=await ctx.embed_color())
        pfp = data["primary"].pop("pfp")
        emb.set_thumbnail(url=pfp or ctx.author.avatar_url)
        for name, value in data["primary"].items():
            val = str(value).title() if type(value) is not list else ", ".join(value)
            if name == "age":
                val = val if int(val) < 30 else "30+"
            emb.add_field(
                name=name.title(),
                value=val or "Not set yet",
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
            user = self.bot.get_user(score[0])
            await ctx.send(
                f"The closest match the bot can find is {user.name}, I've just dm'ed them, have a chat with them"
            )
            await user.send(
                f"You have been matched with {str(ctx.author)} , Feel free to DM them, have a nice day."
                "To disable further matchamakings, kindly use `.match disable`"
            )
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
                "What is your gender? (pick from the options)\n1) Male\n2) Female\n3) Transgender\n4) Cisgender\n5) Nonbinary\n6) Other",
                "gender",
                (
                    lambda x: (
                        x.lower(),
                        x.lower()
                        in (
                            "male",
                            "female",
                            "cisgender",
                            "homosexual",
                            "bisexual",
                            "transgender",
                            "genderfluid",
                            "nonbinary",
                            "gay",
                            "lesbian",
                            "other",
                        ),
                    )
                ),
            ),
            (
                "What is your timezone? Contient/City (e.g America/New_York)",
                "timezone",
                self.get_timezone,
            ),  # TODO
            (
                "Which country do you live in?",
                "location",
                self.check_country,
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
                f"Set up your profile by answering the following {len(q)} questions:\n You can always cancel anytime by typing `cancel`"
            )
        except discord.Forbidden:
            return await ctx.send("I can't send messages to you")

        conf = self.config.user_from_id(ctx.author.id)
        succ = []
        prev = None
        for ind, val in enumerate(q, 1):
            await ctx.author.send(
                (f"Your answer was: {str(prev).capitalize()}" if prev else "")
                + f"\n{ind}. {val[0]}"
            )
            for _ in range(3):
                try:
                    resp = await self.bot.wait_for(
                        "message",
                        check=lambda x: ctx.author == x.author and x.guild is None,
                        timeout=300,
                    )
                except asyncio.TimeoutError:
                    return await ctx.author.send("\U0000274e Timed out, try again later.")

                if "cancel" == resp.content.lower():
                    return await ctx.author.send("\U0000274e You have cancelled your setup.")

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
                    await ctx.author.send(
                        ":negative_squared_cross_mark: Ill-formatted value, Try Again."
                    )
            else:
                return await ctx.author.send(
                    ":negative_squared_cross_mark: Too many wrong values, Aborting."
                )
                break
        if succ:
            async with self.config.user_from_id(ctx.author.id).primary() as conf:
                for i, j in succ:
                    conf[i] = j

        await ctx.author.send(
            f"<a:verifycyan:859079239538311198> You have set your profile! , check it out using {ctx.prefix}profile."
        )

    @commands.admin()
    @commands.guild_only()
    @commands.group()
    async def matchset(self, ctx):
        """Settings to set up matcher"""

    @matchset.command()
    async def selfie(self, ctx, channel: discord.TextChannel):
        """Add a selfie channel to take pfp"""
        # TODO

    @matchset.command(name="show")
    async def matchset_guild_show(self, ctx):
        """Shows guild settings about matchmaking"""
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
        await ctx.send(f"`{str(person)}`'s tokens is now {number}, previously it was {prev}.")

    @matchset.command()
    async def accuracy(self, ctx, number: int):
        """Set the match level accuracy, between 1 and 100"""
        if 0 < number <= 100:
            await self.config.guild_from_id(ctx.guild.id).accuracy.set(number)
        else:
            await ctx.send("Accuracy should be a number between 1 and 100.")

    @matchset.group(aliases=["1"])
    async def primary(self, ctx):
        """Edit primary settings of a person"""

    @primary.command(name="edit")
    async def primary_edit(self, ctx, person: discord.User, thing, *, change):
        """Edit primary settings of a person"""
        if value_get := getattr(self.config.user_from_id(person.id).primary, thing, None):
            value = await value_get()
            if isinstance(value, list):
                await value_get.set([i.strip() for i in value.split(",")])
                await ctx.send(
                    f"Changed {thing} for {str(person)} \nfrom: {value}\nto: {change.split(',')}"
                )
            else:
                await value_get.set(change)
                await ctx.send(f"Changed {thing} for {str(person)} \nfrom: {value}\nto: {change}")
        else:
            await ctx.send("Value not found")

    @matchset.group(aliases=["2"])
    async def secondary(self, ctx):
        """Edit secondary settings of a person"""

    @matchset.command(name="edit")
    async def secondary_edit(self, ctx, person: discord.User, thing, *, change):
        """Edit Secondary data of any person"""
        if value_get := getattr(self.config.user_from_id(person.id).secondary, thing, None):
            value = await value_get()
            if isinstance(value, list):
                await value_get.set([i.strip() for i in value.split(",")])
                await ctx.send(
                    f"Changed {thing} for {str(person)} \nfrom: {value}\nto: {change.split(',')}"
                )
            else:
                await value_get.set(change)
                await ctx.send(f"Changed {thing} for {str(person)} \nfrom: {value}\nto: {change}")
        else:
            await ctx.send("Value not found")

    @secondary.command(name="show")
    async def secondary_show(self, ctx, person: discord.User):
        """Show the secondary keywords of the specified person"""
        details = await self.config.user_from_id(person.id).secondary.all()
        emb = discord.Embed(title=f"All secondary data from {person.name}")
        emb.set_thumbnail(url=person.avatar_url)
        for i, j in details.items():
            emb.add_field(name=i, value=box((", ".join(j)) or "Nothing here yet.."), inline=False)
        await ctx.send(embed=emb)

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

    def check_country(self, x):
        try:
            country = pycountry.countries.search_fuzzy(x)[0]
        except LookupError:
            return None, False
        if parsed := getattr(country, "official_name", None):
            return parsed, True
        return country.name, True

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
