#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys

# Temporarily add the current path to the system path for importing the student's source code.
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".admin_files"
    )
)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# python3 seemingly respects only abspaths, while ipython3 is ok with relative, like '..' here.
import test_utils


@test_utils.test_wrapper
def test() -> bool:
    # To debug in pudb3
    # Highlight the line of code below below
    # Type 't' to jump 'to' it
    # Type 's' to 'step' deeper
    # Type 'n' to 'next' over
    # Type 'f' or 'r' to finish/return a function call and go back to caller
    import random
    import characters

    base_row = 200
    base_col = 200
    oracle = characters.The0racle(base_row, base_col)
    player = characters.Player(base_row, base_col)
    cases = [
        (0, 1, "E"),
        (-1, 1, "NE"),
        (-1, 0, "N"),
        (-1, -1, "NW"),
        (0, -1, "W"),
        (1, -1, "SW"),
        (1, 0, "S"),
        (1, 1, "SE"),
    ]
    result = True
    for case in cases:
        offset = random.randint(5, 13) * 10
        oracle.row = base_row + (case[0] * offset) + random.randint(-10, 10)
        oracle.col = base_col + (case[1] * offset) + random.randint(-10, 10)
        # To debug
        # print('oracle.row: ', oracle.row, 'oracle.col: ', oracle.col)
        # print('player.row: ', player.row, 'player.col: ', player.col)
        # print('case: ', case)
        # print("oracle.get_direction: ", oracle.get_direction(player))
        if oracle.get_direction(player) != case[2]:
            result = False
    return result


if __name__ == "__main__":
    test()
