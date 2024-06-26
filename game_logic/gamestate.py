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

from typing import List, Tuple, Literal, Optional, Any, Coroutine, TYPE_CHECKING
import asyncio
from concurrent.futures import ThreadPoolExecutor

from game_logic.ruleset import DefaultRuleset
from game_logic.board import Board
from game_logic.errors import InvalidMove, IllegalMove

if TYPE_CHECKING:
    from PIL import Image


class Gamestate:
    """Represents a mancala game.

    A Game stores information about the current game.


    Attributes
    -----------
    valid_mask: List[:class:`bool`]
        A mask representing which moves are valid.
    current_player: Literal[0, 1]
        The current player to move.
    number_of_holes: int
        A wrapper function to extract the number of holes from the ruleset.
    game_over: :class:`bool`
        If the game is over.
    result: Optional[Literal[0, 1, 2]]
        The game's output:
            :class:`None` representing a non-terminal game.
            0 representing the first player's victory.
            1 representing the second player's victory.
    """

    __spec__: Tuple[str] = (
        '_current_player',
        '_rule_set',
        '_board',
        '_game_over',
        '_result',
        '_score_1',
        '_score_2',
        '_board_stack'
    )

    def __init__(self):
        self._current_player: int = 0
        self._rule_set = DefaultRuleset()
        self._board = Board(self._rule_set)

        self._game_over: bool = False
        self._result: Optional[Literal[0, 1, 2]] = None

        self._score_1: Optional[int] = None
        self._score_2: Optional[int] = None

        self._board_stack: List[Board] = []

    @property
    def valid_mask(self) -> List[bool]:
        return [len(hole) > 0 for hole in self._board.get_holes(self._current_player)]

    @property
    def current_player(self) -> Literal[0, 1]:
        return self._current_player

    @property
    def number_of_holes(self) -> int:
        return self._rule_set['NUMBER_OF_HOLES_PER_SIDE']

    @property
    def game_over(self) -> bool:
        return self._game_over

    @property
    def result(self) -> Optional[Literal[0, 1, 2]]:
        return self._result

    @staticmethod
    async def stack_boards(board_stack: List[Board], side: Literal[0, 1], digit_size: int = 35) -> List[Image.Image]:
        tasks: list[Coroutine[Any, Any, Image.Image]] = [
            board.get_board_image(side, digit_size) 
            for board in board_stack
        ]
        return await asyncio.gather(*tasks)

    async def stack_all_boards(self, digit_size: int = 35) -> List[Image.Image]:
        return await Gamestate.stack_boards(self._board_stack, self.current_player, digit_size)

    def score(self, side: Literal[0, 1]) -> int:
        if side:
            return self._score_1
        else:
            return self._score_2

    def terminate(self) -> None:
        self._game_over = True
        self._current_player = 0 # Display board from player 1 view

    def next_player(self) -> None:
        self._current_player = 1 - self._current_player

    async def get_board(self, side: Optional[Literal[0, 1]] = None, digit_size: int = 35) -> Image.Image:
        return await self._board.get_board_image(side if side else self._current_player, digit_size)

    async def play_move(self,
                  move: Literal[0, 1, 2, 3, 4, 5],
                  animate: bool = True) -> List[Image.Image] | Image.Image:
        if move >= 6 or move < 0:
            raise InvalidMove(move)
        if not self.valid_mask[move]:
            raise IllegalMove(move)

        if animate:
            board_stack: List[Board] = self._animate_move(move)
            self._board_stack.extend(board_stack)
        else:
            board_stack: Board = self._play_move(move)
            self._board_stack.append(board_stack)

        return await self._check_terminal(board_stack, animate)

    async def _check_terminal(self,
                        board_stack: List[Board] | Board,
                        animate: bool) -> List[Image.Image] | Image.Image:
        side_1: List[Board.Hole] = self._board.get_holes(0)
        side_2: List[Board.Hole] = self._board.get_holes(1)

        if not (any(len(hole) for hole in side_1) and any(len(hole) for hole in side_2)):
            self.terminate()
            seeds: int = 0
            for i in range(self._rule_set['NUMBER_OF_TOTAL_HOLES']):
                if i in self._rule_set['PLAYER_TO_STORE_INDEX']:
                    self._board[i] += seeds
                    seeds = 0
                else:
                    seeds += self._board[i]
                    self._board[i] = 0

            self._score_1: int = len(self._board.get_store(0))
            self._score_2: int = len(self._board.get_store(1))

            if self._score_1 == self._score_2:
                self._result = 2
            elif self._score_1 < self._score_2:
                self._result = 1
            else:
                self._result = 0
            
            if animate:
                board_stack.append(self._board)
            else:
                board_stack = self._board
        if animate:
            return await Gamestate.stack_boards(board_stack, self._current_player)
        else:
            return await board_stack.get_board_image(self._current_player)

    def _do_capture(self, hole_index: int, side: Literal[0, 1]) -> bool:
        opposite_hole_index: int = (2 * self._rule_set['PLAYER_TO_STORE_INDEX'][0]) - hole_index
        seeds: int = self._board[opposite_hole_index]
        if not (self.is_valid_move(hole_index) and seeds):
            return False

        self.next_player()

        self._board[opposite_hole_index] = 0
        if self._rule_set['capture_both']:
            seeds += self._board[hole_index]
            self._board[hole_index] = 0

        self._board[self._rule_set['PLAYER_TO_STORE_INDEX'][side]] += seeds
        return True

    def _play_move(self, relative_hole_index: int, side: Optional[Literal[0, 1]] = None) -> Board:
        player: Literal[0, 1] = side if side is not None else self._current_player
        opp_player: Literal[0, 1] = 1 - player

        hole_index: int = self.relative_index_to_absolute(relative_hole_index)
        seed_count: int = self._board[hole_index]

        self._board[hole_index] = 0

        first_cycle: bool = True
        while seed_count > 0:
            hole_index += 1

            if hole_index == self._rule_set['NUMBER_OF_TOTAL_HOLES']:
                hole_index = 0
            if hole_index == self._rule_set['PLAYER_TO_STORE_INDEX'][player]:
                first_cycle = False

            if hole_index == self._rule_set['PLAYER_TO_STORE_INDEX'][opp_player]:
                continue

            self._board[hole_index] += 1
            seed_count -= 1

        if hole_index == self._rule_set['PLAYER_TO_STORE_INDEX'][player]:
            if self._rule_set['allow_multiple_laps']:
                return self._board
        elif self._board[hole_index] == 1:
            if self._rule_set['allow_captures']:
                if self._rule_set['capture_on_one_cycle']:
                    if first_cycle:
                        if self._do_capture(hole_index, player):
                            return self._board
                else:
                    if self._do_capture(hole_index, player):
                        return self._board
        else:
            if self._rule_set['do_relay_sowing']:
                relative_hole_index: int = self.absolute_index_to_relative(hole_index)
                return self._play_move(relative_hole_index)

        self.next_player()
        return self._board

    def _animate_move(self,
                      relative_hole_index: int,
                      side: Optional[Literal[0, 1]] = None,
                      prev_board_stack: Optional[List[Board]] = None) -> List[Board]:
        player: Literal[0, 1] = side if side is not None else self._current_player
        opp_player: Literal[0, 1] = 1 - player

        board_stack: List[Board] = prev_board_stack if prev_board_stack is not None else [self._board.copy()]

        hole_index: int = self.relative_index_to_absolute(relative_hole_index)
        seed_count: int = self._board[hole_index]

        self._board[hole_index] = 0
        board_stack.append(self._board.copy())

        first_cycle: bool = True
        while seed_count > 0:
            hole_index += 1

            if hole_index == self._rule_set['NUMBER_OF_TOTAL_HOLES']:
                hole_index = 0
            if hole_index == self._rule_set['PLAYER_TO_STORE_INDEX'][player]:
                first_cycle = False

            if hole_index == self._rule_set['PLAYER_TO_STORE_INDEX'][opp_player]:
                continue

            self._board[hole_index] += 1
            seed_count -= 1
            board_stack.append(self._board.copy())

        if hole_index == self._rule_set['PLAYER_TO_STORE_INDEX'][player]:
            if self._rule_set['allow_multiple_laps']:
                return board_stack
        elif self._board[hole_index] == 1:
            if self._rule_set['allow_captures']:
                if self._rule_set['capture_on_one_cycle']:
                    if first_cycle:
                        if self._do_capture(hole_index, player):
                            board_stack.append(self._board.copy())
                            return board_stack
                else:
                    if self._do_capture(hole_index, player):
                        board_stack.append(self._board.copy())
                        return board_stack
        else:
            if self._rule_set['do_relay_sowing']:
                relative_hole_index: int = self.absolute_index_to_relative(hole_index)
                return self._animate_move(relative_hole_index, prev_board_stack=board_stack)

        self.next_player()
        return board_stack

    def relative_index_to_absolute(self, relative_hole_index: int):
        if self._current_player == 1:
            relative_hole_index += self._rule_set['NUMBER_OF_HOLES_PER_SIDE'] + 1
        return relative_hole_index

    def absolute_index_to_relative(self, absolute_hole_index: int):
        return absolute_hole_index % (self._rule_set['NUMBER_OF_HOLES_PER_SIDE'] + 1)

    def is_valid_move(self, absolute_hole_index: int) -> bool:
        l_bound: int = self._rule_set['PLAYER_TO_STORE_INDEX'][0] + 1 if self.current_player else 0
        r_bound: int = l_bound + self._rule_set['NUMBER_OF_HOLES_PER_SIDE']
        return l_bound <= absolute_hole_index <= r_bound

    def __str__(self) -> str:
        return str(self._board) + ' ' + str(self.current_player)
