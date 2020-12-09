#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import game_map
import ascii_art

assert (
    "linux" in sys.platform
), "This code should be run on Linux, just a reminder to follow instructions..."


def main() -> None:
    print("\033c")
    print("Welcome to Rolla Quest III: The Zoom, Re-infected\n")
    print(
        "To win, find the vaccine drive and bring it to the 0racle, and along the way: "
        + "\n\t0) avoid contact with characters who get you sick or attack you (S, C, P),"
        + "\n\t1) meet with those characters who help you (1, M), "
        + "\n\t2) find the vaccine drive (V) near Shrenk Hall (Biology department), then"
        + "\n\t3) bring it to the Oracle (0) near the CompSci building!\n"
    )
    print(ascii_art.joe)
    input("Press any key to start")

    rq_map = game_map.Map("maps/mst_campus.txt")
    while rq_map.move_all():
        pass


if __name__ == "__main__":
    main()
