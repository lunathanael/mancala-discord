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

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from discord import User, Message


class MatchException(Exception):
    """Exception that's raised when an operation in the :class:`Match` fails.

    These are usually for exceptions that happened during the challenge and match parsing, such as invalid player.
    """

    pass


class PlayerFound(MatchException):
    """An exception that is raised when a new game is requested with an occupied player."""

    def __init__(self, user: User):
        self.player = user
        message: str = f'The match requested contains an occupied user with id: {user.id}.'
        super().__init__(message)


class PlayerNotFound(MatchException):
    """An exception that is raised when a new game is requested with an unexisting challenge."""

    def __init__(self, user: User):
        self.player = user
        message: str = f'A challenge could not be found containing the user {user.id}.'
        super().__init__(message)


class EngineExecutableError(MatchException):
    """An exception that is raised when and engine subprocess encountered a Process Error."""

    def __init__(self, message: Optional[str] = None, return_code: Optional[int] = None):
        self.message: Optional[str] = message
        self.return_code: Optional[int] = return_code
        message: str = f'The engine executable subprocess failed with message "{message}" and return code {return_code}.'
        super().__init__(message)


class EngineTimedOut(EngineExecutableError):
    """An exception that is raised when and engine subprocess timed out parsing an output."""

    def __init__(self):
        message: str = 'The engine executable timed out.'
        super().__init__(message, -1)


class EngineFailedParse(EngineExecutableError):
    """An exception that is raised when and engine subprocess failed to parse a command such as reading a :class:`Gamestate`."""

    def __init__(self, message: str):
        super().__init__(message, -2)


class EngineSearchNotFound(EngineExecutableError):
    """An exception that is raised when and engine subprocess requested a search with an invalid engine type."""

    def __init__(self, engine: str):
        message: str = f'The engine type {engine} is not yet supported.'
        super().__init__(message, -3)