import collections
from typing import Callable, DefaultDict, TYPE_CHECKING, Tuple, Union
import textwrap
import asyncio
import ctypes
from ctypes import c_uint8, c_uint16, c_float
from rq_ui import user_options
import math
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from game_io import EventPlayer
    from tk_io import PlayerView
    from tkinter import Event


class ReloadEvent(Exception):
    """Reload"""

Vector = c_float * 3  # typedef float Vector[3];
opts = user_options()



# Easy way to cast to/from bytearray. Much better than the insanity that is
# struct.pack. Controls should be bound to camera entity and syncup
class Camera(ctypes.Structure):
    """
    The Camera class is the true camera. The Camera instances are arguments to 
    be passed to the GPU
    """
    FOV = 90
    DIST = 10
    POSITION = [0.0, 0.0, 0.0]
    FACING = [0.0, 0.0, 0.0]
    THROTTLE = [0, 0, 0]
    

    # attributes accessed by GPU process
    position: Tuple[float, float, float]
    facing: Tuple[float, float, float]
    fov: float
    dist: int
    repr_char: int

    @classmethod
    def is_bound(cls) -> bool:
        return cls._bound_entity is not None
    

    _fields_ = [
        ("position", Vector),
        ("facing", Vector),
        ("fov", c_float),
        ("dist", c_uint16),
        ("repr_char", c_uint8),
    ]

    _bound_entity: "EventPlayer" = None
    

    @classmethod
    def bound_entity(cls):
        return cls._bound_entity

    def __init__(self):
        if self._bound_entity is None:
            super().__init__(
                Vector(*self.POSITION),
                Vector(*self.FACING),
                self.FOV,
                self.DIST,
                ord(' '),
            )
        else:
            super().__init__(
                Vector(*self.POSITION),
                Vector(*self.FACING),
                self.FOV,
                self.DIST,
                ord(self._bound_entity.repr_char),
            )

    @classmethod
    def bind(cls, evp: "EventPlayer"):
        """Bind camera to an EventPlayer"""
        # Store reference to event player's attributes. The user controls the
        # event player through the camera. Conversely, the game controls the
        # camera through the event player
        if cls._bound_entity is not None:
            cls._bound_entity.camer_bound = False

        cls.POSITION = evp.position
        cls.FACING = evp.facing_direction
        cls.THROTTLE = evp.throttle
        cls._bound_entity = evp

        asyncio.get_event_loop().create_task(
            evp.move(lambda: evp == cls._bound_entity)
        )
        evp.camera_bound = True
        logger.info(f"Camera bound to {type(evp.entity).__name__} @ {evp.col, evp.row}")

    @classmethod
    def unbind(cls):
        """Free look"""
        if cls._bound_entity is not None:
            cls._bound_entity.camera_bound = False
        # Now the camera
        cls.POSITION = list(cls.POSITION)
        cls.FACING = list(cls.FACING)
        cls.THROTTLE = list(cls.THROTTLE)
        cls._bound_entity = None


    @classmethod
    def set_throttle(cls, index, value):
        if cls._bound_entity is not None:
            cls._bound_entity.set_throttle(index, value)
        else:
            cls.THROTTLE[index] = value
    
    @classmethod
    def set_button(cls, *args, **kwargs):
        if cls._bound_entity is not None:
            cls._bound_entity.set_button(*args, **kwargs)

    @classmethod
    def on_next(cls, *args, **kwargs):
        if cls._bound_entity is not None:
            cls._bound_entity.on_next(*args, **kwargs)
        else:
            pass
    
    @classmethod
    def on_prev(cls, *args, **kwargs):
        if cls._bound_entity is not None:
            cls._bound_entity.on_prev(*args, **kwargs)
        else:
            pass
    
    @classmethod
    def mouse_motion(cls, vp: "PlayerView", event: "Event"):
        center_x = vp.winfo_width() / 2
        center_y = vp.winfo_height() / 2
        dx = (event.x - center_x) * opts.x_sens
        cls.FACING[0] += math.radians(dx)
        dy = cls.FACING[1] + math.radians(
            (event.y - center_y) * opts.y_sens
        )
        # limit vertical view to +/- 45 deg of horizon
        if abs(dy) < (math.pi / 4):
            cls.FACING[1] = dy

__event_scripts: DefaultDict[Callable, list] = collections.defaultdict(list)
__global_event_lock = asyncio.Condition()

def init_global_event_scripts(map):
    loop = asyncio.get_event_loop()
    for routine in __event_scripts[OngoingGlobal]:
        loop.create_task(routine(map))
    async def f():
        while True:
            await asyncio.sleep(1/120)
            async with __global_event_lock:
                __global_event_lock.notify_all()
    return loop.create_task(f())

def init_eventplayer_scripts(evp: "EventPlayer", map):
    loop = asyncio.get_event_loop()
    for routine in __event_scripts[OngoingEachPlayer]:
        loop.create_task(routine(evp))
    

def OngoingGlobal(*conditions: Callable[["EventPlayer"], None]):
    def wrapper(func):
        if not asyncio.iscoroutinefunction(func):
            func = asyncio.coroutine(func)
        async def global_routine(map):
            while True:
                async with __global_event_lock:
                    await __global_event_lock.wait_for(
                        lambda: all(f(map) for f in conditions)
                    )
                    task = asyncio.create_task(func(map))
                    await __global_event_lock.wait_for(
                        lambda: task.done() and not all(f(map) for f in conditions)
                    )
        __event_scripts[OngoingGlobal].append(global_routine)
    return wrapper

def OngoingEachPlayer(*conditions: Callable[["EventPlayer"], None]):
    def wrapper(func):
        if not asyncio.iscoroutinefunction(func):
            func = asyncio.coroutine(func)
        async def eventplayer_routine(event_player: "EventPlayer"):
            while True:
                async with __global_event_lock:
                    # wait for all conditions to eval true
                    await __global_event_lock.wait_for(
                        lambda: all(f(event_player) for f in conditions)
                    )
                    # schedule a new task. a simple await here will cause
                    # the wait and wait_for functions to block.
                    task = asyncio.create_task(func(event_player))

                    # wait for tasks to eval false and for the task to finish
                    # before trying to restart the event script.
                    await __global_event_lock.wait_for(
                        lambda: task.done() and not all(f(event_player) for f in conditions)
                    )
        __event_scripts[OngoingEachPlayer].append(eventplayer_routine)
    return wrapper

Number = Union[int, float]

def players_within_radius(map, row, col, radius, ignore_walls=True):
    pass

def chase_variable_at_rate(
        getter:Callable[[], Number],
        setter:Callable[[Number], None],
        destination: Callable[[], Number],
        rate: float,
) -> asyncio.Task:
    """
    getter: a function that returns the value of the target variable
    setter: a function that sets the value of the target variable
    destination: a function that returns the value of the target variable's destination
    rate: the speed at which the target chases the destination per 0.1s
    """
    async def chaser():
        while True:
            target = getter()
            dest = destination()
            if target < dest:
                setter(target + rate)
            elif target > dest:
                setter(target - rate)
            await asyncio.sleep(1/10)

    return asyncio.create_task(chaser())


async def wait_for(condition: Callable[[], bool], timeout: float):
    return await __global_event_lock.wait_for(condition, timeout)




__help_text = ""

def wait(t):
    return asyncio.sleep(t)

def set_help_text(help_text):
    global __help_text
    __help_text = textwrap.dedent(help_text)

def get_help_text():
    return __help_text
