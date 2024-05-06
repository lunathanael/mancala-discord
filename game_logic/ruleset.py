from __future__ import annotations

from typing import TypedDict


class Ruleset(TypedDict):
    allow_captures: bool
    capture_both: bool
    capture_on_one_cycle: bool
    do_relay_sowing: bool
    allow_multiple_laps: bool

    seeds_per_hole: int

def DefaultRuleset() -> Ruleset:
    ruleset: Ruleset = {
        'allow_captures': True,
        'capture_both': True,
        'capture_on_one_cycle': False,
        'do_relay_sowing': False,
        'allow_multiple_laps': True,
        'seeds_per_hole': 4,
    }
    return ruleset
