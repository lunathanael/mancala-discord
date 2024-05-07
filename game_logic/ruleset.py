from __future__ import annotations

from typing import TypedDict, Tuple


class Ruleset(TypedDict):
    allow_captures: bool
    capture_both: bool
    capture_on_one_cycle: bool
    do_relay_sowing: bool
    allow_multiple_laps: bool

    seeds_per_hole: int

    NUMBER_OF_HOLES_PER_SIDE: int
    NUMBER_OF_TOTAL_HOLES: int
    PLAYER_TO_STORE_INDEX: Tuple[int]

def DefaultRuleset() -> Ruleset:
    ruleset: Ruleset = {
        'allow_captures': True,
        'capture_both': True,
        'capture_on_one_cycle': False,
        'do_relay_sowing': False,
        'allow_multiple_laps': True,

        'seeds_per_hole': 4,

        'NUMBER_OF_HOLES_PER_SIDE': 6,
        'NUMBER_OF_TOTAL_HOLES' : 14,
        'PLAYER_TO_STORE_INDEX': (6, 13),
    }
    return ruleset
