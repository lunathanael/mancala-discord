"""
The MIT License (MIT)

Copyright (c) 2024-present lunathanael

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

import os
from typing import List, Optional, Literal, TYPE_CHECKING

import discord
from discord.ext import commands
from dotenv import load_dotenv

from match import MatchManager
from errors import PlayerFound
from views import ConfirmationView

if TYPE_CHECKING:
    from match import Match


# Load API token from .env and initialize bot intents.
load_dotenv()
DISCORD_API_TOKEN: str = os.getenv('DISCORD_BOT_API_TOKEN')

intents: discord.Intents = discord.Intents.default()
intents.message_content = True
activity: discord.BaseActivity = discord.Game(name="/challenge someone to a game of Mancala!")
bot: commands.Bot = commands.Bot(command_prefix='>',
                                 intents=intents,
                                 activity=activity,
                                 status=discord.Status.online)

match_manager: MatchManager


@bot.event
async def on_ready():
    """Log the bot ready event. """
    print(f'We have logged in as {bot.user}')


@bot.hybrid_command()
@commands.guild_only()
@commands.is_owner()
async def sync(
  ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    print("Syncing commands...")
    if not guilds:
        synced: List[discord.app_commands.AppCommand] = []
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.reply(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret: int = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.reply(f"Synced the tree to {ret}/{len(guilds)}.")


@bot.hybrid_command(name='challenge', description='Request a mancala match.')
@discord.app_commands.describe(opponent='The opponent, selecting the bot for AI. (Required)',
                       second='Select `True` to go second. (Optional)',
                       difficulty="The AI's difficulty. (Optional)")
async def challenge(ctx: commands.Context,
                    opponent: discord.User = commands.parameter(description='Please select an opponent, selecting the bot for AI. (Required)'),
                    second: Optional[bool] = commands.parameter(description='Select `True` to go second. (Optional)', default=False),
                    difficulty: Optional[Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]] = commands.parameter(description="The AI's difficulty. (Optional)", default=6)):

    if opponent == bot.user:
        opponent = None
    elif opponent.bot:
        await ctx.reply(f"I don't think {opponent.mention} know how to play. 😕")
        return
    elif opponent == ctx.author:
        await ctx.reply("You can't challenge yourself. (for now) 😅")
        return

    player_1: Optional[discord.User] = opponent if second else ctx.author
    player_2: Optional[discord.User] = ctx.author if second else opponent

    if opponent is None or player_1 == player_2:
        msg: discord.Message = await ctx.send("Starting match...")
    else:
        embed: discord.Embed = discord.Embed(
            title="Challenge request",
            description=f"# **{ctx.author.display_name}** has challenged **{opponent.display_name}** to a board game!\n\n"
                        f"## {player_1.mention} vs {player_2.mention}\n\n"
                        f"### Do you accept the challenge?",
            color=discord.Color.blue())
        embed.set_footer(text="Made with ❤️ by utop1a.", icon_url=r"https://imgur.com/a/96jpwM5")

        view: ConfirmationView = ConfirmationView(match_manager=match_manager, player_1=player_1, player_2=player_2)
        try:
            msg: discord.Message = await ctx.send(opponent.mention, embed=embed, view=view)
        except discord.errors.Forbidden:
            msg: discord.Message = await ctx.send(content=f"{ctx.author.mention}I don't have the required permissions! (Files, Embed)", embed=None, view=None)
            return

    try:
        await match_manager.add_challenge(
            msg=msg,
            challenger=ctx.author,
            challenged=opponent,
            player_1=player_1,
            player_2=player_2,
            difficulty=difficulty)
    except PlayerFound:
        embed: discord.Embed = discord.Embed(
            title="Challenge request failed.",
            description="You have a challenge pending or are already in a match!",
            color=discord.Color.red()
        )
        embed.set_footer(text="Made with ❤️ by utop1a.", icon_url=r"https://imgur.com/a/96jpwM5")
        await msg.edit(content=None, embed=embed, view=None)
    else:
        if opponent is None or player_1 == player_2:
            match: Match = await match_manager.add_match(player_1=player_1, player_2=player_2)
            try:
                await match.send_reply(move=None, gif=False)
            except discord.errors.Forbidden:
                match.terminate()
                await msg.edit(content=f"{ctx.author.mention}I don't have the required permissions! (Files, Embed)", embed=None, view=None)


def main():
    """Initialize match container and run the bot."""
    global match_manager

    match_manager = MatchManager(bot=bot)
    bot.run(DISCORD_API_TOKEN)


if __name__ == "__main__":
    main()
