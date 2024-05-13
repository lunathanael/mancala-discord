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

from typing import Tuple, Dict, Literal, Optional, TypeAlias, TYPE_CHECKING
import subprocess
import threading
import queue


from errors import EngineTimedOut, EngineFailedParse, EngineSearchNotFound, EngineSearchFailed
from game_logic.gamestate import Gamestate

if TYPE_CHECKING:
    pass


class EngineInterface:
    __spec__: Tuple[str] = (
        'process',
        'output_queue',
        'out_thread',
    )

    ENGINE_DICT: Dict[str, int] = {
        'human': 0,
        'random': 1,
        'min_max': 2, 
        'alpha_beta': 3, 
        'simple_threaded_ab': 4,
	    'heuristic_ab': 5,
        'beta_alpha': 6,
    }

    ENGINE_DIFFICULTIES: TypeAlias = Literal[ 
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
        -1, -2, -3, -3, -4, -5, -6, -7, -8, -9, -10,
    ]

    @staticmethod
    def enqueue_output(out: subprocess.Popen.stdout, output_queue: queue.Queue):
        for line in iter(out.readline, ''):
            output_queue.put(line)
        out.close()

    def __init__(self, executable_dir: str = r"Mancala.exe"):
        self.process: subprocess.Popen = subprocess.Popen([executable_dir],
                                               stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE,
                                               text=True,
                                               bufsize=1)
        self.output_queue: queue.Queue = queue.Queue()
        self.out_thread: threading.Thread = threading.Thread(target=EngineInterface.enqueue_output,
                                                                args=(self.process.stdout, self.output_queue),
                                                                daemon=True)
        self.out_thread.start()

    def __del__(self) -> int:
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.terminate()
        return self.process.wait()

    async def parse_gamestate(self, game_state: Gamestate) -> None:
        board_str: str = str(game_state)

        self.process.stdin.write("board " + board_str + "\n")
        self.process.stdin.flush()

        try:
            error_msg: str = await self.read_line(timeout=0.5)
            raise EngineFailedParse(error_msg)
        except EngineTimedOut:
            pass

    async def read_line(self, timeout: Optional[float] = None) -> str:
        try:
            output: str = self.output_queue.get(timeout=timeout)
            return output
        except queue.Empty as e:
            raise EngineTimedOut from e

    async def search(self, *,
                     game_state: Optional[Gamestate] = None,
                     engine: Literal['human',
                                    'random',
                                    'min_max', 
                                    'alpha_beta', 
                                    'simple_threaded_ab',
                                    'heuristic_ab',
                                    'beta_alpha'] = 'alpha_beta', 
                     engine_depth: int = 6,
                     timeout: Optional[float] = None) -> int:

        if game_state is not None:
            await self.parse_gamestate(game_state)

        if engine_depth == 0:
            engine = 'random'
        if engine_depth < 0:
            engine = 'beta_alpha'
            engine_depth = -engine_depth

        engine_depth = int(engine_depth * 2)

        if engine not in EngineInterface.ENGINE_DICT:
            raise EngineSearchNotFound(engine)

        engine_index: int = EngineInterface.ENGINE_DICT[engine]

        params: str = f"search {engine_index} {engine_depth}\n"
        self.process.stdin.write(params)
        self.process.stdin.flush()

        out_msg: str = await self.read_line(timeout)
        out_msg = out_msg.strip()

        try:
            move: int = int(out_msg)
        except ValueError as e:
            raise EngineFailedParse(out_msg) from e
        else:
            if move == -1:
                raise EngineSearchFailed(params.strip(), out_msg)
            else:
                return move

if __name__ == "__main__":
    engine = EngineInterface()
    import asyncio
    from timeit import default_timer as timer
    i = 1
    while True:
        depth = i / 2
        start = timer()
        hole = asyncio.run(engine.search(engine_depth=depth))
        print(f"info {hole} {i} {timer() - start}")
        i += 1

