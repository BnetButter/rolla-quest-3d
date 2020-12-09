#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
from typing import Tuple, Dict


def get_chunk_size() -> Tuple[int, int]:
    cols, lines = os.get_terminal_size()
    # Subtract one line for the input prompt and another for the HUD
    return lines - 3, cols - 1


# Choose 1) 'WASD', 2) Vim, or 3) arrow-based keybindings for navigating through the world.
KEY_DICT: Dict["str", "str"]
key_bind = "3"

if key_bind == "1":
    # qwerty wasd
    KEY_DICT = {"up": "w", "down": "s", "left": "a", "right": "d"}
elif key_bind == "2":
    # vim kjhl
    KEY_DICT = {"up": "k", "down": "j", "left": "h", "right": "l"}
else:
    # arrows esc sequences
    KEY_DICT = {
        "up": "\033[A",
        "down": "\033[B",
        "left": "\033[D",
        "right": "\033[C",
    }

COLORS: Dict[str, str] = {
    "mst_green": "\033[38;5;28m",
    "orange": "\033[38;5;202m",
    "blue": "\033[38;5;21m",
    "cash_green": "\033[38;5;70m",
    "red": "\033[38;5;196m",
    "brown": "\033[38;5;94m",
    "yellow": "\033[38;5;226m",
    "teal": "\033[38;5;43m",
}


def getch() -> str:
    try:
        import sys
        import tty
        import termios
    except ImportError:
        raise ImportError("You're on Windows, aren't you?")
    stdin_fd = sys.stdin.fileno()  # We know this is a tty
    old_cfg = termios.tcgetattr(stdin_fd)  # save off the current config
    try:
        tty.setraw(stdin_fd)
        char = sys.stdin.read(1)
        if ord(char) == 3:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_cfg)
            print("Ctrl-C quitting")
            sys.exit(0)
        elif ord(char) == 27:
            char += sys.stdin.read(2)
        return char
    finally:
        # Reset the terminal once we receive the Ctrl-C
        termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_cfg)
