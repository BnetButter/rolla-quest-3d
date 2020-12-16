import enum
from game_map import Map
import logging
import math
import tkinter as tk
from typing import Callable, List
from characters import Entity
import asyncio

logger = logging.getLogger(__name__)

DIRECTIONS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


class Button(enum.IntEnum):
    PRIMARY_FIRE = 1 << 0
    SECONDARY_FIRE = 1 << 1
    CROUCH = 1 << 2
    JUMP = 1 << 3
    INTERACT = 1 << 4
    ABILITY_1 = 1 << 5
    ABILITY_2 = 1 << 6
    ABILITY_3 = 1 << 7
    NEXT = 1 << 8
    PREV = 1 << 9
    RELOAD = 1 << 10
    MELEE = 1 << 11


def debug(f):
    def inner(self, button, *args):
        logger.debug(f"{type(self).__name__}.{f.__name__}({button}, *args)")
        return f(self, button, *args)

    return inner


class EventPlayer:
    """Based on Overwatch Workshop's Event Player entity"""

    throttle: List[int]
    facing_direction: List[float]  # in rad
    position: List[float]
    held_buttons: int = 0
    enabled_buttons: int = 0
    entity: Entity
    velocity: float
    id: int = 0
    using_ability: int = 0
    camer_bound: bool = False

    def __init__(self, entity=None, map=None):
        self._on_next: Callable[[EventPlayer, tk.Event], None]
        self._on_prev: Callable[[EventPlayer, tk.Event], None]
        self._on_next = debug(lambda a, b: None)
        self._on_prev = debug(lambda a, b: None)
        self._throttle_forced = False
        self.throttle = [0, 0, 0]
        self.position = [0.0, 0.0, 0.0]
        self.facing_direction = [0.0, 0.0, 0.0]
        self.held_buttons = 0
        self.entity = entity
        self.velocity = 0.5
        self.id = type(self).id
        self.map = map
        type(self).id += 1
        buttons = list(Button)
        for bt in buttons:
            self.enabled_buttons |= bt
        self.map = map
        entity.event_player = self
        import lib_rq
        lib_rq.init_eventplayer_scripts(self, map)
        self.syncdown()


    @property
    def repr_char(self):
        return self.entity.repr_char

    @property
    def col(self):
        return int(self.position[0])

    @property
    def row(self):
        return int(self.position[2])

    @col.setter
    def col(self, v):
        self.position[0] = float(v)
        self.entity.col = int(v)

    @row.setter
    def row(self, v):
        self.position[1] = float(v)
        self.entity.col = int(v)


    async def move(self, condition: Callable[[], bool]):
        map = self.map
        prev_walls = {
            (self.row + i, self.col + j)
            for i, j in DIRECTIONS
            if chr(map.protomap[self.row + i][self.col + j]) in Map.WALL_CHAR
            or chr(map.protomap[self.row + i][self.col + j]) in Map.BOUND_CHAR
        }
        prev_row = self.position[2]
        prev_col = self.position[0]

        while condition():
            await asyncio.sleep(1 / 60)
            rad = self.facing_direction[0]
            
            n_x, n_y = prev_col, prev_row

            n_x += math.cos(rad) * self.velocity * self.throttle[2]
            n_y -= math.sin(rad) * self.velocity * self.throttle[2]
            n_x += math.cos(rad + math.pi / 2) * self.velocity * self.throttle[0]
            n_y -= math.sin(rad + math.pi / 2) * self.velocity * self.throttle[0]

            # check collision
            if (int(n_y), int(n_x)) in prev_walls:
                continue
            else:
                prev_row = self.position[2] = n_y
                prev_col = self.position[0] = n_x
                prev_walls = set(
                    (self.row + i, self.col + j)
                    for i, j in DIRECTIONS
                    if chr(map.protomap[self.row + i][self.col + j]) in Map.WALL_CHAR
                    or chr(map.protomap[self.row + i][self.col + j]) in Map.BOUND_CHAR
                )
                # sync so map.pretty_print shows upated position
                self.syncup()
    
    def start_forcing_throttle(self, throttle):
        self._throttle_forced = True
        self.throttle[0], self.throttle[1], self.throttle[2] = throttle

    def stop_forcing_throttle(self):
        self.throttle[0], self.throttle[1], self.throttle[2] = 0, 0, 0
        self._throttle_forced = False

    def is_button_held(self, button: Button):
        return bool(self.held_buttons & button)
    
    def set_throttle(self, index, value):
        if self._throttle_forced:
            return
        self.throttle[index] = value
        logger.debug(f"throttle: {self.throttle}")

    def set_button(self, button: Button, state: bool):
        if state:
            self.held_buttons |= button
        else:
            self.held_buttons &= ~button
        logger.debug(
            f"is_button_held({str(button)}) -> " f"{bool(self.held_buttons & button)}"
        )

    @property
    def on_next(self):
        return self._on_next

    @on_next.setter
    def on_next(self, fn):
        if fn is None:
            self._on_next = debug(lambda a, b: None)
        else:
            self._on_next = debug(fn)

    @property
    def on_prev(self):
        return self._on_prev

    @on_prev.setter
    def on_prev(self, fn):
        if fn is None:
            self._on_prev = debug(lambda a, b: None)
        else:
            self._on_prev = debug(fn)

    def handle_next(self, event, *args):
        self._on_next(self, event)

    def handle_prev(self, event, *args):
        self._on_prev(self, event)

    def syncup(self):
        """Copy EventPlayer values to Entity"""
        self.entity.row = int(self.position[2])
        self.entity.col = int(self.position[0])

    def syncdown(self):
        """Copy Entity values to EventPlayer"""
        self.position[2] = float(self.entity.row)
        self.position[0] = float(self.entity.col)


_user_event_player: EventPlayer = None
def user_event_player(entity=None, **kwargs):
    global _user_event_player
    if _user_event_player is None:
        _user_event_player = EventPlayer(entity, **kwargs)
    return _user_event_player

_user_keybinds = None


def get_user_keybinds(filename=None):
    """Returns user configured keybind"""
    # https://www.tcl.tk/man/tcl8.6/TkCmd/keysyms.htm
    global _user_keybinds
    if filename is None:
        if _user_keybinds is None:
            _user_keybinds = {
                "Movement": ("w", "s", "a", "d"),
                Button.PRIMARY_FIRE: "1",  # Left mouse button
                Button.SECONDARY_FIRE: "3",  # Right mouse button
                Button.NEXT: "4",
                Button.PREV: "5",
                Button.JUMP: "space",
                Button.CROUCH: "Control_L",
                Button.INTERACT: "f",
                Button.ABILITY_1: "Shift_L",
                Button.ABILITY_2: "e",
                Button.ABILITY_3: "q",
                Button.MELEE: "v",
                Button.RELOAD: "r",
            }
            return _user_keybinds
    else:
        raise NotImplementedError("user config not implemented")
