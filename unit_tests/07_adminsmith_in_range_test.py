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

    # Needs the last test to make sure AdminSmith does some moving.
    party_row, party_col = 200, 200
    adminsmith = characters.AdminSmith(party_row, party_col)
    other_adminsmith = characters.AdminSmith(party_row, party_col)
    result = True
    moves = {
        KEY_DICT["up"]: (-1, 0),
        KEY_DICT["left"]: (0, -1),
        KEY_DICT["down"]: (1, 0),
        KEY_DICT["right"]: (0, 1),
    }
    for _ in range(random.randint(50, 100)):
        direction = moves[adminsmith.move()]
        adminsmith.row += direction[0]
        adminsmith.col += direction[1]
        if other_adminsmith.distance(adminsmith) > 3:
            result = False
    return result


if __name__ == "__main__":
    test()
