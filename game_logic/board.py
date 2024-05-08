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

from typing import List, Tuple, TypeAlias, Literal, TYPE_CHECKING
from random import randint
from os import listdir
from os.path import join
import copy

from PIL import Image, ImageDraw, ImageFont

from game_logic.errors import InvalidMove

if TYPE_CHECKING:
    from game_logic.ruleset import Ruleset


class Seed:
    __spec__: Tuple[str] = (
        'ico',
        'pos_offset',
    )

    def __init__(self, costume: Image.Image, offset: Tuple[int]):
        self.ico: Image.Image = costume.rotate(offset[2]).convert('RGBA')
        self.pos_offset: Tuple[int] = (offset[0], offset[1])


class Board:

    __spec__: Tuple[str] = (
        'rule_set',
        'store',
        'holes',
        'buffer',
    )

    Hole: TypeAlias = List[Seed]
    Coordinate: TypeAlias = Tuple[int, int]
    board_ico: Image.Image = Image.open(f'assets/board.png')
    seed_icos: List[Image.Image] = [Image.open(join('assets/', f)) for f in listdir('assets/') if "seed" in f]

    def __init__(self, rule_set: Ruleset, variance: int = 15, size: int = 80):
        self.rule_set: Ruleset = rule_set
        self.store: Tuple[Board.Hole] = ([], [])
        self.buffer: List[Seed] = []

        self.holes: Tuple[List[Board.Hole], List[Board.Hole]] = ([[], [], [], [], [], []], [[], [], [], [], [], []])
        for x in range(2):
            for y in range(6):
                for z in range(rule_set['seeds_per_hole']):
                    offset: int = (randint(-variance, variance), randint(-variance, variance), randint(0, 360))
                    costume: Image.Image = self.seed_icos[randint(0, len(self.seed_icos) - 1)].resize((size, size))
                    self.holes[x][y].append(Seed(costume, offset))

    def get_board_image(self, facing: Literal[0, 1], digit_size: int = 35, digit_offset: float = 0) -> Image.Image:
        leap: int = 130

        p: Tuple[Board.Coordinate] = ((285, 280), (935, 130))
        p2: Tuple[Board.Coordinate] = ((1115, 250), (140, 250))
        score: Tuple[Board.Coordinate] = ((1100, 60), (135, 55))

        board: Image.Image = self.board_ico.copy()

        font: ImageFont.FreeTypeFont = ImageFont.truetype(r'C:\Windows\Fonts\Arial.ttf', digit_size)

        # Loop which generates an image depending on which way the board should be facing
        for x in range(2):
            for j, i in enumerate(self.holes[(x + facing) % 2]):
                for ii in i:
                    direction: List[int] = [1, -1]

                    pos: Board.Coordinate = (p[x][0] + leap * j * direction[x], p[x][1])
                    board.paste(ii.ico, (pos[0] + ii.pos_offset[0], pos[1] + ii.pos_offset[1]), ii.ico)

                    draw: ImageDraw = ImageDraw.Draw(board)

                    direction[0] = 1.9 + digit_offset
                    direction[1] -= digit_offset
                    draw.text((pos[0], pos[1] + 50 * direction[x]), str(len(i)), fill="black", font=font, align="right")

            for l in self.store[(x + facing) % 2]:
                board.paste(l.ico, (p2[x][0] + l.pos_offset[0], p2[x][1] + l.pos_offset[1]), l.ico)

                draw: ImageDraw = ImageDraw.Draw(board)
                draw.text(score[x], str(len(self.store[(x + facing) % 2])), fill="black", font=font, align="right")

        return self.add_transparency(board)

    @staticmethod
    def add_transparency(im: Image.Image) -> Image.Image:
        alpha: Image.Image = im.getchannel('A')
        im = im.convert('RGB').convert('P', palette=Image.Palette.ADAPTIVE, colors=255)
        mask: Image.Image = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)

        im.paste(255, mask)
        im.info['transparency'] = 255
        return im
        
    def get_holes(self, side: Literal[0, 1]) -> List[int]:
        return self.holes[side]

    def __getitem__(self, hole_index: int) -> int:
        if hole_index < 0 or hole_index >= self.rule_set['NUMBER_OF_TOTAL_HOLES']:
            raise InvalidMove
        
        side: Literal[0, 1] = hole_index > self.rule_set['PLAYER_TO_STORE_INDEX'][0]
        relative_hole_index: int = hole_index % (self.rule_set['NUMBER_OF_HOLES_PER_SIDE'] + 1)

        hole: Board.Hole = self.store[side] if relative_hole_index == self.rule_set['NUMBER_OF_HOLES_PER_SIDE'] else self.holes[side][relative_hole_index]

        return len(hole)

    def __setitem__(self, hole_index: int, value: int) -> None:
        if hole_index < 0 or hole_index >= self.rule_set['NUMBER_OF_TOTAL_HOLES']:
            raise InvalidMove
        
        side: Literal[0, 1] = hole_index > self.rule_set['PLAYER_TO_STORE_INDEX'][0]
        relative_hole_index: int = hole_index % (self.rule_set['NUMBER_OF_HOLES_PER_SIDE'] + 1)
        
        hole: Board.Hole = self.store[side] if relative_hole_index == self.rule_set['NUMBER_OF_HOLES_PER_SIDE'] else self.holes[side][relative_hole_index]

        while value > len(hole):
            hole.append(self.buffer.pop(-1))
        
        while value < len(hole):
            self.buffer.append(hole.pop(-1))

    def copy(self) -> Board:
        return copy.deepcopy(self)

    def __str__(self) -> str:
        board_count: List[int] = []

        for hole_idx in range(self.rule_set['NUMBER_OF_TOTAL_HOLES']):
            board_count.append(self[hole_idx])
            
        return ' '.join(map(str, board_count))
