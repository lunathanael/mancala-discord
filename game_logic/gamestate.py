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

from typing import List, Tuple, Literal, Optional, TYPE_CHECKING

from game_logic.ruleset import DefaultRuleset
from game_logic.board import Board

if TYPE_CHECKING:
    from PIL import Image


class Gamestate:
    __spec__: Tuple[str] = (
        '_current_player',
        '_rule_set',
        '_board',
    )

    def __init__(self):
        self._current_player: int = 0
        self._rule_set = DefaultRuleset()
        self._board = Board(self._rule_set)

    def get_valid_moves(self) -> List[int]:
        pass

    def play_move(self, move: int):
        pass
    
    @property
    def current_player(self) -> Literal[0, 1]:
        return self._current_player
    
    def get_board(self, side: Literal[0, 1], numsize: int = 35) -> Image.Image:
        return self._board.get_board(side, numsize)
    