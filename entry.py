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
from utils import to_lower
from errors import PlayerFound

if TYPE_CHECKING:
    from match import Challenge, Match, MessageKwargs

DISCORD_API_TOKEN: str
bot: commands.Bot
match_manager: MatchManager


def initialize_bot():
    """Load API token from .env and initialize bot intents."""
    global DISCORD_API_TOKEN, bot

    load_dotenv()
    DISCORD_API_TOKEN = os.getenv('DISCORD_BOT_API_TOKEN')

    intents: discord.Intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix='!', intents=intents)


initialize_bot()


@bot.event
async def on_ready():
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

class ConfirmationView(discord.ui.View):
    def __init__(self, match_manager: MatchManager, player_1: Optional[discord.User], player_2: Optional[discord.User]):
        super().__init__()
        self.timeout: float = 5 * 60
        self.match_manager: MatchManager = match_manager
        self.player_1: Optional[discord.User] = player_1
        self.player_2: Optional[discord.User] = player_2

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.player_1 and interaction.user != self.player_2:
            await interaction.response.send_message("You are not allowed to interact with this challenge.", ephemeral=True, delete_after=5)
            return False
        return True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="yes_button")
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        challenge: Challenge = await self.match_manager.find_challenge(player_1=self.player_1, player_2=self.player_2)

        if interaction.user == challenge.challenger:
            await interaction.response.send_message("You cannot accept your own challenge.", ephemeral=True)
            return
        
        embed: discord.Embed = discord.Embed(
            title="Challenge Accepted!",
            description=f"**{challenge.challenged.display_name}** accepted **{challenge.challenger.display_name}**'s challenge.\n\n",
            color=discord.Color.green()
        )

        await challenge.edit_msg(embed=embed, view=None)
        match: Match = await self.match_manager.add_match(player_1=self.player_1, player_2=self.player_2)

        await interaction.response.send_message("Challenge accepted!", ephemeral=True, delete_after=5)
        await match.send_reply(move=None, gif=False)

        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="no_button")
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        challenge: Challenge = await self.match_manager.find_challenge(player_1=self.player_1, player_2=self.player_2)

        if interaction.user == challenge.challenger:
            embed: discord.Embed = discord.Embed(
                title="Challenge Canceled.",
                description=f"**{challenge.challenger.display_name}** canceled their challenge.\n\n",
                color=discord.Color.red()
            )
            response_msg: str = "Challenge canceled."
        else:
            embed: discord.Embed = discord.Embed(
                title="Challenge Rejected.",
                description=f"**{challenge.challenged.display_name}** rejected **{challenge.challenger.display_name}**'s challenge.\n\n",
                color=discord.Color.red()
            )
            response_msg: str = "Challenge rejected."

        await challenge.edit_msg(embed=embed, view=None)
        await self.match_manager.delete_challenge(player_1=self.player_1, player_2=self.player_2)
        await interaction.response.send_message(response_msg, ephemeral=True, delete_after=5)
        self.stop()
   

@bot.hybrid_command(name='challenge', description='Request a mancala match.')
@discord.app_commands.describe(opponent='Please select an opponent, selecting the bot for AI. (Required)',
                       first='Select to be first player. (Optional) Default: True',
                       difficulty='If AI was selected, please choose a difficulty 1-20. (Optional) Default: 6')
async def challenge(ctx: commands.Context, opponent: discord.User, first: Optional[bool] = True, 
                  difficulty: Optional[Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]]=6):
    global match_manager

    if opponent == bot.user:
        opponent = None
    elif opponent.bot:
        await ctx.reply(f"I don't think {opponent.mention} know how to play. 😕")
        return
    elif opponent == ctx.author:
        await ctx.reply(f"You can't challenge yourself. (for now) 😅")
        return
    
    player_1: Optional[discord.User] = ctx.author if first else opponent
    player_2: Optional[discord.User] = opponent if first else ctx.author

    if opponent is None or player_1 == player_2:
        msg: discord.Message = await ctx.send("Starting match...")
    else:
        embed: discord.Embed = discord.Embed(
            title="Challenge request", 
            description=f"**{ctx.author.display_name}** has challenged **{opponent.display_name}** to a board game!\n\n"
                        f"{player_1.mention} vs {player_2.mention}\n\n"
                        f"Do you accept the challenge?", 
            color=discord.Color.blue())

        view: ConfirmationView = ConfirmationView(match_manager=match_manager, player_1=player_1, player_2=player_2)
        msg: discord.Message = await ctx.send(opponent.mention, embed=embed, view=view)

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
            description=f"You have a challenge pending or are already in a match!",
            color=discord.Color.red()
        )
        await msg.edit(content=None, embed=embed, view=None)
    else:
        if opponent is None or player_1 == player_2:
            match: Match = await match_manager.add_match(player_1=player_1, player_2=player_2)
            await match.send_reply(move=None, gif=False)


def main():
    """Initialize match container and run the bot."""
    global match_manager

    match_manager = MatchManager(bot=bot)
    bot.run(DISCORD_API_TOKEN)


if __name__ == "__main__":
    main()
