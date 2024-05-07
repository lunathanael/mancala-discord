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

from typing import Dict, Set, Tuple, Optional, Any, List, TypedDict, Literal, Callable, TYPE_CHECKING
from io import BytesIO

import discord
from discord.ext import commands
from discord.ui import Button, View

from errors import PlayerFound, PlayerNotFound
from game_logic.gamestate import Gamestate

if TYPE_CHECKING:
    from discord import User, Message, Color, Embed, File
    from PIL import Image


class MessageKwargs(TypedDict):
    content: str
    embed: Embed
    file: File


class MoveView(View):
    def __init__(self, match: Match):
        super().__init__(timeout=None)

        self.match: Match = match
        self.player: User = match.current_player

        valid_mask: List[bool] = match.gamestate.valid_mask
        for idx, validity in enumerate(valid_mask):
            if validity:
                button: Button = Button(label=str(idx), style=discord.ButtonStyle.green, )
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
            await self.match.send_move_reply(move=idx, gif=True)
            self.stop()
        return legal_move
    
    def illegal_move_gen(self, idx: int) -> Callable:
        async def illegal_move(interaction: discord.Interaction) -> None:
            await interaction.response.send_message(f"The hole you selected:{idx} is empty!", ephemeral=True, delete_after=5)
        return illegal_move


class Match:
    """Represents a match.

    A Match stores information about the players and the arguments passed to the game.


    Attributes
    -----------
    msg: :class:`discord.Message`
        The current Match msg.
    player_1: Optional[:class:`discord.User`]
        The user acting as the first player in the match, or :class:`None` for AI agent.
    player_2: Optional[:class:`discord.User`]
        The user acting as the second player in the match, or :class:`None` for AI agent.
    autonomous: :class:`bool`
        If the match consists of two AI agents.
    gamestate: `Gamestate`
        The match's current game state.
    kwargs: Dict[:class:`str`, :class:`Any`]
        Keyword arguments used for match details such as custom ruleset or AI parameters.
    """

    __slots__: Tuple[str] = (
        'msg',
        'player_1',
        'player_2',
        'previous_player',
        'difficulty',
        'kwargs',
        'autonomous',
        'gamestate',
    )

    VALID_EMOJIS: List[str] = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    INVALID_EMOJIS: List[str] = ["❤", "🩷", "🧡", "💛", "💚", "💙"]

    def __init__(self, msg: Message, player_1: Optional[User] = None, player_2: Optional[User] = None, **kwargs: Dict[str, Any]):
        self.msg: Message = msg
        self.player_1: Optional[User] = player_1
        self.player_2: Optional[User] = player_2
        self.previous_player: Optional[str] = None
        self.difficulty: int = kwargs.pop('difficulty', 6)

        self.kwargs: Dict[str, Any] = kwargs
        self.autonomous: bool = player_1 is None and player_2 is None

        self.gamestate: Gamestate = Gamestate()

    @property
    def number_of_holes(self) -> int:
        return self.gamestate.number_of_holes

    @property
    def current_player(self) -> User:
        if self.gamestate.current_player:
            return self.player_2
        else:
            return self.player_1
        
    @property
    def other_player(self) -> User:
        if self.gamestate.current_player:
            return self.player_1
        else:
            return self.player_2

    @property
    def embed_color(self) -> Color:
        return self.current_player.accent_color if (self.current_player and self.current_player.accent_color) else Match.default_embed_colors()[self.gamestate.current_player]
    
    def msg_content(self, move: Optional[Literal[0, 1, 2, 3, 4, 5]] = None, gif: bool = False) -> MessageKwargs:
        if move is not None:
            img: List[Image.Image] | Image.Image = self.gamestate.play_move(move, animate=gif)
        else:
            gif = False
            img: Image.Image = self.gamestate.get_board()

        content: str = f"{self.current_player.mention}, it's your turn!" if self.current_player else "AI is thinking..."
        embed: discord.Embed = discord.Embed(
            title=f"{self.player_1.display_name if self.player_1 else f'AI level {self.difficulty}'} vs. {self.player_2.display_name if self.player_2 else f'AI level {self.difficulty}'}",
            description=f"{self.previous_player} played hole {move + 1}.\n" if self.previous_player else ""
                        f"React to choose a move!",
            color=self.embed_color
        )

        self.previous_player = self.current_player.mention if self.current_player else "AI"

        if gif:
            output_gif = BytesIO()
            img[0].save(output_gif, save_all=True, format='GIF', append_images=img, duration=400)
            output_gif.seek(0)

            file = discord.File(output_gif, filename="image.gif")
            embed.set_image(url="attachment://image.gif")
        else:
            file_image: Image.Image = self.gamestate.get_board()
            output_image: BytesIO = BytesIO()
            file_image.save(output_image, save_all=True, format='png')
            output_image.seek(0)

            file: discord.File = discord.File(output_image, filename="image.png")
            embed.set_image(url="attachment://image.png")

        view: Optional[MoveView] = MoveView(self) if self.current_player else None

        return MessageKwargs(
            {
                'content': content,
                'embed': embed,
                'file': file,
                'view': view
            }
        )
    
    async def add_emojis(self) -> None:
        valid_mask: List[bool] = self.gamestate.valid_mask
        for idx, validity in enumerate(valid_mask):
            if validity:
                await self.msg.add_reaction(Match.VALID_EMOJIS[idx])
            else:
                await self.msg.add_reaction(Match.INVALID_EMOJIS[idx])
    
    async def send_initial_message(self) -> None:
        self.msg = await self.msg.reply(**self.msg_content(gif=False))

    async def send_move_reply(self, move: Literal[0, 1, 2, 3, 4, 5], gif: bool = True) -> None:
        self.msg = await self.msg.reply(**self.msg_content(move=move, gif=gif))

    @staticmethod
    def default_embed_colors() -> Tuple[Color]:
        return (discord.Color.blue(), discord.Color.red())


class Challenge:
    """Represents a Challenge request
    
     Attributes
    -----------
    msg: :class:`discord.Message`
        The original challenge message.
    challenger: Optional[:class:`discord.User`]
        The user starting the challenge.
    challenged: Optional[:class:`discord.User`]
        The user challenged.
    player_1: Optional[:class:`discord.User`]
        The user acting as the first player in the match, or :class:`None` for AI agent.
    player_2: Optional[:class:`discord.User`]
        The user acting as the second player in the match, or :class:`None` for AI agent.
    kwargs: Dict[:class:`str`, :class:`Any`]
        Keyword arguments used for match details such as custom ruleset or AI parameters.
    """

    __slots__: Tuple[str] = (
        'msg',
        'challenger',
        'challenged',
        'player_1',
        'player_2',
        'kwargs',
    )

    def __init__(self, 
                 msg: Message,
                 challenger: Optional[User] = None, 
                 challenged: Optional[User] = None, 
                 player_1: Optional[User] = None, 
                 player_2: Optional[User] = None, 
                 **kwargs: Dict[str, Any]):
        self.msg = msg
        self.challenger: Optional[User] = challenger
        self.challenged: Optional[User] = challenged
        self.player_1: Optional[User] = player_1
        self.player_2: Optional[User] = player_2
        self.kwargs: Dict[str, Any] = kwargs

    async def edit_msg(self, **kwargs) -> Message:
        return await self.msg.edit(**kwargs)

    def to_match(self) -> Match:
        return Match(
            msg=self.msg,
            player_1=self.player_1,
            player_2=self.player_2,
            **self.kwargs
        )


class MatchManager:
    """Represents a container for managing matches.

    Attributes
    -----------
    matches: Set[:class:`Match`]
        A set containing all ongoing matches.
    player_dict: Dict[:class:`discord.User`, :class:`Match`]
        A dictionary mapping users to their active match.
    """

    __slots__: Tuple[str] = (
        'matches',
        'player_dict',
    )

    def __init__(self):
        self.matches: Set[Match] = set()
        self.player_dict: Dict[User, Match | Challenge] = dict()

    async def add_challenge(self, 
                            msg: Message,
                            challenger: Optional[User] = None, 
                            challenged: Optional[User] = None, 
                            player_1: Optional[User] = None, 
                            player_2: Optional[User] = None, 
                            **kwargs: Dict[str, Any]) -> Challenge:
        """|coro|

        Adds a match to the match manager.

        Parameters
        ------------
        msg: :class:`discord.Message`
            The original challenge message.
        challenger: Optional[:class:`discord.User`]
            The user starting the challenge.
        challenged: Optional[:class:`discord.User`]
            The user challenged.
        player_1: Optional[:class:`discord.User`]
            The user acting as the first player in the match, or :class:`None` for AI agent.
        player_2: Optional[:class:`discord.User`]
            The user acting as the second player in the match, or :class:`None` for AI agent.
        kwargs: Dict[:class:`str`, :class:`Any`]
            Keyword arguments used for match details such as custom ruleset or AI parameters.

        Returns
        --------
        :class:`~Challenge`
            Returns the newly added Challenge.

        Raises
        --------
        PlayerFound
            At least one of the users requested for the match is occupied in another match.
        """

        if player_1 and player_1 in self.player_dict:
            raise PlayerFound(player_1)
        if player_2 and player_2 in self.player_dict:
            raise PlayerFound(player_2)

        challenge: Challenge = Challenge(
            msg=msg,
            challenger=challenger,
            challenged=challenged,
            player_1=player_1, 
            player_2=player_2, 
            **kwargs)

        self.player_dict.update({player_1: challenge, player_2: challenge})

        return challenge

    async def add_match(self, 
                        player_1: Optional[User] = None, 
                        player_2: Optional[User] = None) -> Match:
        """|coro|

        Adds a match to the match manager.

        Parameters
        ------------
        player_1: Optional[:class:`discord.User`]
            The user acting as the first player in the match, or :class:`None` for AI agent.
        player_1: Optional[:class:`discord.User`]
            The user acting as the second player in the match, or :class:`None` for AI agent.

        Returns
        --------
        :class:`~Match`
            Returns the newly added Match.

        Raises
        --------
        PlayerFound
            At least one of the users requested for the match is occupied.
        """
        
        challenge: Challenge = await self.find_challenge(player_1=player_1, player_2=player_2)

        match: Match = challenge.to_match()

        self.matches.add(match)
        self.player_dict.update({player_1: match, player_2: match})
        
        return match

    async def find_challenge(self, 
                            player_1: Optional[User] = None, 
                            player_2: Optional[User] = None) -> Challenge:
        """|coro|

        Adds a match to the match manager.

        Parameters
        ------------
        player_1: Optional[:class:`discord.User`]
            The user acting as the first player in the challenge, or :class:`None` for AI agent.
        player_2: Optional[:class:`discord.User`]
            The user acting as the second player in the challenge, or :class:`None` for AI agent.

        Returns
        --------
        :class:`~Challenge`
            Returns the Challenge that found between the two users.

        Raises
        --------
        PlayerNotFound
            At least one of the users do not have a pending challenge.
        """

        if player_1 and player_1 not in self.player_dict:
            raise PlayerNotFound(player_1)
        if player_2 and player_2 not in self.player_dict:
            raise PlayerNotFound(player_2)
        
        challenge: Challenge = self.player_dict[player_1 if player_1 else player_2]

        return challenge
    
    async def delete_challenge(self, 
                            player_1: Optional[User] = None, 
                            player_2: Optional[User] = None) -> None:
        """|coro|

        Adds a match to the match manager.

        Parameters
        ------------
        player_1: Optional[:class:`discord.User`]
            The user acting as the first player in the challenge, or :class:`None` for AI agent.
        player_2: Optional[:class:`discord.User`]
            The user acting as the second player in the challenge, or :class:`None` for AI agent.

        Raises
        --------
        PlayerNotFound
            At least one of the users do not have a pending challenge.
        """
        
        if player_1:
            self.player_dict.pop(player_1, None)
        if player_2:
            self.player_dict.pop(player_2, None)

    async def edit_challenge_msg(self, player_1: Optional[User], player_2: Optional[User], **kwargs) -> Message:
        """|coro|

        Adds a match to the match manager.

        Parameters
        ------------
        player_1: Optional[:class:`discord.User`]
            The user acting as the first player in the challenge, or :class:`None` for AI agent.
        player_2: Optional[:class:`discord.User`]
            The user acting as the second player in the challenge, or :class:`None` for AI agent.

        Returns
        --------
        :class:`~Message`
            Returns the edited Message for the challenge found between the two users.

        Raises
        --------
        PlayerNotFound
            At least one of the users requested for the match is occupied in another match.
        """

        if player_1 and player_1 not in self.player_dict:
            raise PlayerNotFound(player_1)
        if player_2 and player_2 not in self.player_dict:
            raise PlayerNotFound(player_2)

        challenge: Challenge = self.player_dict[player_1 if player_1 else player_2]

        return await challenge.edit_msg(**kwargs)
