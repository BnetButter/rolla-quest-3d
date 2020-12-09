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
    import math
    import characters

    oracle = characters.The0racle(200, 200)
    freqs = [40, 30, 20, 10, 5, 3, 1, 1, 1, 1, 1]
    result = True
    for freq in freqs:
        moves = [oracle.move() for _ in range(50)]
        actual_moves = len([move for move in moves if move])
        if actual_moves > math.ceil(50 / freq) or actual_moves < math.floor(50 / freq):
            result = False
    return result


if __name__ == "__main__":
    test()
