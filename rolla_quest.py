#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import game_map
import ascii_art
import lib_rq, rq_engine

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
""")


def main() -> None:
    rq_map = game_map.Map("maps/mst_campus.txt")
    rq_engine.main(rq_map)

if __name__ == "__main__":
    main()
