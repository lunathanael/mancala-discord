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

from typing import TYPE_CHECKING

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
        message = f'The match requested contains an occupied user with id: {user.id}.'
        super().__init__(message)


class PlayerNotFound(MatchException):
    """An exception that is raised when a new game is requested with an unexisting challenge."""

    def __init__(self, user: User):
        self.player = user
        message = f'A challenge could not be found containing the user {user.id}.'
        super().__init__(message)
