#!/usr/bin/python3
# -*- coding: utf-8 -*-

from typing import Callable
import sys


def test_wrapper(test: Callable[[], bool]) -> None:
    return_code = int(sys.argv[1])
    sys.argv[1] = "nice try..."
    result = False
    try:
        result = test()
    except Exception as e:
        raise e
    if result:
        sys.exit(return_code)
    else:
        sys.exit(1)
