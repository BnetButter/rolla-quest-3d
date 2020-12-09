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
    import characters
    from rq_utils import KEY_DICT

    the_mask = characters.Mask(0, 0)
    moves = []
    # The count of Monte Carlo says you're probably right...
    for _ in range(1000):
        moves.append(the_mask.move())
    counts = [moves.count(direction) for direction in KEY_DICT.values()]
    result = all(count > 150 and count < 350 for count in counts)
    return result


if __name__ == "__main__":
    test()
