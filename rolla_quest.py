#!/usr/bin/python3
# -*- coding: utf-8 -*-
from game_io import Button
import sys
import game_map
import ascii_art
import lib_rq, rq_engine
import logging
from game_io import EventPlayer
import asyncio
from characters import *

logger = logging.getLogger(__name__)

assert (
    "linux" in sys.platform
), "This code should be run on Linux, just a reminder to follow instructions..."

lib_rq.set_help_text(
    f"""
{ascii_art.joe}

Welcome to Rolla Quest III: The Zoom, Re-infected
    0) avoid contact with characters who get you sick or attack you"
    1) meet with those characters who help you"
    2) find the vaccine drive near Shrenk Hall (Biology department), then"
    3) bring it to the Oracle near the CompSci building!"

Controls:
    Move: WASD,
    Look: Mouse,
    
    Sprint: Ability 1
        Move fast

    Hack drone: Ability 3
        Temporarily take control of the nearest PoliceDrone entity
""")

@lib_rq.OngoingGlobal()
def move_all(map: game_map.Map):
    while True:
        # Move and draw
        yield from lib_rq.wait(1/10)
        map.move_all()

@lib_rq.OngoingEachPlayer(
    lambda player: player.is_button_held(Button.ABILITY_1),
    lambda player: isinstance(player.entity, Player),
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


@lib_rq.OngoingEachPlayer(
    lambda player: isinstance(player.entity, AdminSmith),
    lambda player: min(
        player.entity.distance(other)
        for other in AdminSmith.adminsmiths if other != player.entity
    ) > 3,
)
def chase_smith(player: EventPlayer):
    nearest = min(
        (sm for sm in AdminSmith.adminsmiths if sm != player.entity),
        key=lambda k: player.entity.distance(k)
    )
    this_row, this_col = player.entity.row, player.entity.col
    near_row, near_col = nearest.col, nearest.row
    if this_row > near_row:
        player.entity.move_up()
    elif this_row < near_row:
        player.entity.move_down()
    if this_col > near_col:
        player.entity.move_right()
    elif this_col < near_col:
        player.entity.move_left()
    player.syncdown()


@lib_rq.OngoingEachPlayer(
    lambda player: isinstance(player.entity, Player),
    lambda player: player.held_buttons & Button.ABILITY_3, 
    lambda player: not (player.using_ability & Button.ABILITY_3)
)
def hack_drone(player):
    player.using_ability |= Button.ABILITY_3
    nearest_drone = min(
        (entity for entity in player.map.entities if entity != player.entity and isinstance(entity, PoliceDrone)), 
        key=lambda e: player.entity.distance(e)
    )
    lib_rq.Camera.bind(nearest_drone.event_player)
    yield from lib_rq.wait(10)
    
    lib_rq.Camera.bind(player)
    yield from lib_rq.wait(10)

    player.using_ability &= ~Button.ABILITY_3
    


def main() -> None:
    rq_map = game_map.Map("maps/reversed_mst_campus.txt")
    rq_engine.main(rq_map)


if __name__ == "__main__":
    main()
