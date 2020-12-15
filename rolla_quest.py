#!/usr/bin/python3
# -*- coding: utf-8 -*-
import asyncio
from game_io import Button
import sys
import game_map
import ascii_art
import lib_rq, rq_engine
import logging
from game_io import EventPlayer

logger = logging.getLogger(__name__)

assert (
    "linux" in sys.platform
), "This code should be run on Linux, just a reminder to follow instructions..."

lib_rq.set_help_text(f"""
{ascii_art.joe}

Welcome to Rolla Quest III: The Zoom, Re-infected
    0) avoid contact with characters who get you sick or attack you"
    1) meet with those characters who help you"
    2) find the vaccine drive near Shrenk Hall (Biology department), then"
    3) bring it to the Oracle near the CompSci building!"

Controls:
    Move: WASD,
    Look: Mouse,
    Sprint: Shift,
""")


@lib_rq.OngoingEachPlayer(
    lambda player: player.is_button_held(Button.ABILITY_1),
    lambda player: player.throttle[2] == 1
)
def sprint(player: EventPlayer):
    player.velocity = 1
    lib_rq.Camera.FOV = 120
    lib_rq.Camera.DIST = 15


@lib_rq.OngoingEachPlayer(
    lambda player: not player.is_button_held(Button.ABILITY_1)
)
def nosprint(player: EventPlayer):
    player.velocity = 0.5
    lib_rq.Camera.FOV = 90
    lib_rq.Camera.DIST = 10

    

def main() -> None:
    rq_map = game_map.Map("maps/reversed_mst_campus.txt")
    rq_engine.main(rq_map)

if __name__ == "__main__":
    main()
