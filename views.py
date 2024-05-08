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

from typing import Optional, List, Callable, Awaitable, TYPE_CHECKING
import asyncio

import discord
from discord.ui import Button, View

if TYPE_CHECKING:
    from match import MatchManager, Challenge, Match


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
    async def yes_button(self, interaction: discord.Interaction, button: Button):
        challenge: Challenge = await self.match_manager.find_challenge(player_1=self.player_1, player_2=self.player_2)

        if interaction.user == challenge.challenger:
            await interaction.response.send_message("You cannot accept your own challenge.", ephemeral=True)
            return

        embed: discord.Embed = discord.Embed(
            title="Challenge Accepted!",
            description=f"**{challenge.challenged.display_name}** accepted **{challenge.challenger.display_name}**'s challenge.\n\n",
            color=discord.Color.green()
        )

        match: Awaitable[Match] = self.match_manager.add_match(player_1=self.player_1, player_2=self.player_2)
        await asyncio.gather(
            match,
            challenge.edit_msg(embed=embed, view=None)
        )

        asyncio.gather(
            interaction.response.send_message("Challenge accepted!", ephemeral=True, delete_after=5),
            match.send_reply(move=None, gif=False)
        )

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

        await asyncio.gather(
            challenge.edit_msg(embed=embed, view=None),
            self.match_manager.delete_challenge(player_1=self.player_1, player_2=self.player_2),
            interaction.response.send_message(response_msg, ephemeral=True, delete_after=5)
        )
        self.stop()


class MoveView(View):
    def __init__(self, match: Match):
        super().__init__(timeout=None)

        self.match: Match = match
        self.player: discord.User = match.current_player

        valid_mask: List[bool] = match.gamestate.valid_mask
        for idx, validity in enumerate(valid_mask):
            if validity:
                button: Button = Button(label=str(idx), style=discord.ButtonStyle.green)
                button.callback = self.legal_move_gen(idx)
            else:
                button: Button = Button(emoji='❌', style=discord.ButtonStyle.red)
                button.callback = self.illegal_move_gen(idx)
            button.idx = idx
            self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.player:
            if interaction.user == self.match.other_player:
                await interaction.response.send_message("Wait your turn!", ephemeral=True, delete_after=5)
            else:
                await interaction.response.send_message("You are not allowed to interact with this game.", ephemeral=True, delete_after=5)
            return False
        return True

    def legal_move_gen(self, idx: int) -> Callable:
        async def legal_move(interaction: discord.Interaction) -> None:
            await interaction.message.edit(view=None)
            await self.match.send_reply(move=idx, gif=True)
            self.stop()
        return legal_move

    def illegal_move_gen(self, idx: int) -> Callable:
        async def illegal_move(interaction: discord.Interaction) -> None:
            await interaction.response.send_message(f"The hole you selected:{idx} is empty!", ephemeral=True, delete_after=5)
        return illegal_move
