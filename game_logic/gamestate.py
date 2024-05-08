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
from game_logic.errors import InvalidMove, IllegalMove, UndefinedBehavior

if TYPE_CHECKING:
    from PIL import Image


class Gamestate:
    __spec__: Tuple[str] = (
        '_current_player',
        '_rule_set',
        '_board',
        '_game_over',
        '_result',
    )

    def __init__(self):
        self._current_player: int = 0
        self._rule_set = DefaultRuleset()
        self._board = Board(self._rule_set)

        self._game_over: bool = False
        self._result: Optional[Literal[0, 1, 2]] = None

    def play_move(self, move: Literal[0, 1, 2, 3, 4, 5], animate: bool = True) -> List[Image.Image] | Image.Image:
        if move >= 6 or move < 0:
            raise InvalidMove(move)
        if not self.valid_mask[move]:
            raise IllegalMove(move)
        
        if animate:
            return self._animate_move(move)
        else:
            return self._play_move(move)

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
        return not any(self.valid_mask)
        return self._game_over
    
    @property
    def result(self) -> Optional[Literal[0, 1, 2]]:
        return 1 - self.current_player
        return self._result
    
    def next_player(self) -> None:
        self._current_player = 1 - self._current_player
    
    def get_board(self, side: Optional[Literal[0, 1]] = None, numsize: int = 35) -> Image.Image:
        return self._board.get_board_image(side if side else self._current_player, numsize)

    def _do_capture(self, hole_index: int, side: Literal[0, 1]) -> None:
        if self._rule_set['capture_both']:
            self._board[self._rule_set['PLAYER_TO_STORE_INDEX'][side]] += self._board[hole_index]
            self._board[hole_index] = 0
        opposite_hole_index: int = ((2 * self._rule_set['PLAYER_TO_STORE_INDEX'][0]) - hole_index)
        self._board[self._rule_set['PLAYER_TO_STORE_INDEX'][side]] += self._board[opposite_hole_index]
        self._board[opposite_hole_index] = 0
    
    def _play_move(self, relative_hole_index: int, side: Optional[Literal[0, 1]] = None) -> Image.Image:
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
                return self._board.get_board_image(player)
        elif self._board[hole_index] == 1:
            if self._rule_set['allow_captures']:
                if self._rule_set['capture_on_one_cycle']:
                    if first_cycle:
                        self._do_capture(hole_index, player)
                        return self._board.get_board_image(opp_player)
                else:
                    self._do_capture(hole_index, player)
                    return self._board.get_board_image(opp_player)
        else:
            if self._rule_set['do_relay_sowing']:
                relative_hole_index: int = self.absolute_index_to_relative(hole_index)
                return self._play_move(relative_hole_index)

        self.next_player()
        return self._board.get_board_image(opp_player)

    def _animate_move(self, relative_hole_index: int, side: Optional[Literal[0, 1]] = None, prev_board_stack: Optional[List[Board]] = None) -> List[Image.Image]:
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
                return [board.get_board_image(player) for board in board_stack]
        elif self._board[hole_index] == 1:
            if self._rule_set['allow_captures']:
                if self._rule_set['capture_on_one_cycle']:
                    if first_cycle:
                        self._do_capture(hole_index, player)
                        board_stack.append(self._board)
                        return [board.get_board_image(opp_player) for board in board_stack]
                else:
                    self._do_capture(hole_index, player)
                    board_stack.append(self._board)
                    return [board.get_board_image(opp_player) for board in board_stack]
        else:
            if self._rule_set['do_relay_sowing']:
                relative_hole_index: int = self.absolute_index_to_relative(hole_index)
                return self._animate_move(relative_hole_index, prev_board_stack=board_stack)

        self.next_player()
        return [board.get_board_image(opp_player) for board in board_stack]

    def _do_capture(self, hole_index: int, side: Literal[0, 1]) -> None:
        if self._rule_set['capture_both']:
            seeds: int = self._board[hole_index] 
            self._board[hole_index] = 0
            self._board[self._rule_set['PLAYER_TO_STORE_INDEX'][side]] += seeds
    
        opposite_hole_index: int = ((2 * self._rule_set['PLAYER_TO_STORE_INDEX'][0]) - hole_index)
        seeds: int = self._board[opposite_hole_index]
        self._board[opposite_hole_index] = 0
        self._board[self._rule_set['PLAYER_TO_STORE_INDEX'][side]] += seeds

        self.next_player()

    def relative_index_to_absolute(self, relative_hole_index: int):
        if self._current_player == 1:
            relative_hole_index += self._rule_set['NUMBER_OF_HOLES_PER_SIDE'] + 1
        return relative_hole_index
    
    def absolute_index_to_relative(self, absolute_hole_index: int):
        return absolute_hole_index % (self._rule_set['NUMBER_OF_HOLES_PER_SIDE'] + 1)
    
    def __str__(self) -> str:
        return str(self._board) + ' ' + str(self.current_player)
