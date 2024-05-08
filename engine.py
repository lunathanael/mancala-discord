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

from typing import Dict, Literal, Optional, TYPE_CHECKING
import subprocess
import threading
import queue


from errors import EngineTimedOut, EngineFailedParse, EngineSearchNotFound, EngineSearchFailed
from game_logic.gamestate import Gamestate

if TYPE_CHECKING:
    pass


class EngineInterface:

    ENGINE_DICT: Dict[str, int] = {
        'human': 0,
        'random': 1,
        'min_max': 2, 
        'alpha_beta': 3, 
        'simple_threaded_ab': 4,
	    'heuristic_ab': 5
    }
    
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
        self.stdout_thread: threading.Thread = threading.Thread(target=EngineInterface.enqueue_output, 
                                                                args=(self.process.stdout, self.output_queue),
                                                                daemon=True)
        self.stdout_thread.start()

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
                                    'heuristic_ab'] = 'alpha_beta', 
                     engine_depth: int = 6, 
                     timeout: Optional[float] = None) -> int:

        if game_state is not None:
            await self.parse_gamestate(game_state)

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
        except ValueError:
            raise EngineFailedParse(out_msg)
        else:
            if move == -1:
                raise EngineSearchFailed(params.strip(), out_msg)
            else:
                return move
