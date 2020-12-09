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
    from rq_utils import KEY_DICT

    cases = [
        (-1, 0, KEY_DICT["down"]),
        (0, -1, KEY_DICT["right"]),
        (0, 1, KEY_DICT["left"]),
        (1, 0, KEY_DICT["up"]),
    ]
    oracle_row, oracle_col = 200, 200
    oracle = characters.The0racle(oracle_row, oracle_col)
    policedrone = characters.PoliceDrone(0, 0, oracle)
    result = True
    for case in cases:
        policedrone.row = oracle_row + (case[0] * random.randint(10, 100))
        policedrone.col = oracle_col + (case[1] * random.randint(10, 100))
        if policedrone.move() != case[2]:
            result = False
    return result


if __name__ == "__main__":
    test()
