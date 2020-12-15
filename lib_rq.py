import collections
from game_map import Map
from typing import Callable, DefaultDict, List, Tuple
from graphics import GPU, BYTES_PER_PIX
from ctypes import c_uint16, c_uint8, c_float
import ctypes
import textwrap
import math
import logging
import asyncio

logger = logging.getLogger(__name__)

Vector = c_float * 3            # typedef float Vector[3];
Pixel = c_uint8 * BYTES_PER_PIX # typedef uint8_t Pixel[BYTES_PER_PIX];


# Easy way to cast to/from bytearray. Much better than the insanity that is
# struct.pack
class Camera(ctypes.Structure):
    FOV = 90
    DIST = 10
    RENDER_SCALE = 1
    position: Tuple[float, float, float]
    facing: Tuple[float, float, float]
    fov: float
    dist: int

    _fields_ = [
        ("position", Vector),
        ("facing", Vector),
        ("fov",  c_float),
        ("dist", c_uint16),
    ]

    _bound_entity: "EventPlayer" = None
    def __init__(self):
        if self._bound_entity is None:
            super().__init__()
        else:
            super().__init__(
                Vector(*self._bound_entity.position),
                Vector(*self._bound_entity.facing_direction),
                self.FOV,
                self.DIST,
            )

    @classmethod
    def bind(cls, evp: "EventPlayer"):
        cls._bound_entity = evp
    
# TODO sin/cos table and grey scale table
def cos(r):
    return math.cos(r)

def sin(r):
    return math.sin(r)

GREY_SCALE = [
    bytearray([x, x, x]) for x in [
        200, 175, 150, 125, 100,75,50,25,10
    ]
]

D_SCALE = 10
GROUND_COLOR = [63, 166, 90]
SKY_COLOR = [79, 217, 245]
VERTICAL_OFFSET = 0.5

def squash(x):
    return x / (x + 1)

class RenderEngine(GPU):

    def get_apparent_height(self, scale, dist):
        return (((self.height) / (2 * math.pi * (dist+1))) * 360) // 2

    def get_pixel_offset(self, row, col):
        return (row * self.width * BYTES_PER_PIX * self.renderscale) + (col * BYTES_PER_PIX * self.renderscale)

    def device(self, idx:int, b_in:bytearray, b_out:bytearray):
        """
        idx: core index
        in: input data
        out: output data
        """
        camera: Camera
        camera, map = self.arg_factory(b_in)
        
        radians_per_pixel = math.radians(camera.fov) / self.width
        radian_offset = math.radians(camera.fov / 2) + math.radians(90-camera.fov)
        facing_offset = camera.facing[0]
        start, end = self.block_X * idx, self.block_X * (idx + 1)
        
        c_x, c_y, c_z = camera.position[0], camera.position[1], camera.position[2]
        f_y = camera.facing[1]


        dist_to = [
            (ord(' '), 100, 0, bytearray([0,0,0]))
            for _ in range(self.block_X)
        ]
        # Y shearing. Move the world view up/down depending on y direction.
        # Modeled as a camera rotating around the x axis.
        mid_y = (self.height // 2) - (
            sin(f_y)  * self.height
        )
        # Create the illusion of parallax as the camera pitches up and down
        cos_fy = cos(f_y)
    
        # O(n) so not a big deal
        for i in range(start, end):
            radx = radians_per_pixel * i + radian_offset + facing_offset
            for j in range(1, 100):
                rc_x = j * sin(radx) + c_x
                rc_y = j * cos(radx) + c_z
                x, y = int(math.floor(rc_x)), int(math.floor(rc_y))
                ch = chr(map[y][x])
                # Pull in screen as camera pitches
                dist = j * camera.dist * cos_fy
                gs = squash(dist)
                if ch in Map.BOUND_CHAR:
                    dist_to[i - start] = (
                        map[y][x],
                        j,
                        self.get_apparent_height(0.5,dist),
                        GREY_SCALE[int(math.log(dist))]
                    )
                    break
                elif ch in Map.WALL_CHAR:
                    dist_to[i - start] = (
                        map[y][x],
                        j,
                        self.get_apparent_height(1, dist),
                        GREY_SCALE[int(math.log(dist))]
                    )
                    break
                elif ch in Map.REPR_CHAR:
                    dist_to[i - start] = (
                        map[y][x],
                        j,
                        self.get_apparent_height(1, dist),
                        bytearray(int(gs * x) for x in Map.REPR_CHAR[ch])
                    )
                    break
        # O(n^2). :(
        for i in range(self.height):
            for j, (ch, wall_dist, size, color) in enumerate(dist_to):
                d = i - mid_y # in pixels
                dist_from_mid = abs(d)
                gs = squash(dist_from_mid)
                
                # Fake higher resolutions
                for k in range(self.renderscale):
                    off = self.get_pixel_offset(i * self.renderscale + k, j + start)
                    # Draw sky, ground
                    # This part can be optimized by drawing the entire scene before 
                    # entering this function. This way we only need to draw sprites
                    if d > 0:
                        
                        self.set_color(b_out, off, bytearray(int(gs * x) for x in GROUND_COLOR))
                    else:
                        self.set_color(b_out, off, bytearray(int(gs * x) for x in SKY_COLOR))
                    
                    # Draw sprites
                    if dist_from_mid <= size:
                        self.set_color(b_out, off, color)
    
    def set_color(self, d_out, offset, color):
        d_out[offset: offset + BYTES_PER_PIX * self.renderscale] = color * self.renderscale

scripted_events: DefaultDict[Callable, list] = collections.defaultdict(list)
global_event_lock = asyncio.Condition()

def _update_game():
    loop = asyncio.get_event_loop()
    for routine in scripted_events[OngoingGlobal]:
        loop.create_task(routine())
    async def f():
        while True:
            await asyncio.sleep(1/60)
            async with global_event_lock:
                global_event_lock.notify()
    return loop.create_task(f())


def OngoingGlobal(*conditions: Callable[["EventPlayer"], None]):
    def wrapper(func):
        if not asyncio.iscoroutinefunction(func):
            func = asyncio.coroutine(func)
        async def global_routine():
            while True:
                async with global_event_lock:
                    await global_event_lock.wait_for(
                        lambda: all(f() for f in conditions)
                    )
                    await func()
                    await asyncio.sleep(1/60)
                    await global_event_lock.wait_for(
                        lambda: not all(f() for f in conditions)
                    )
        scripted_events[OngoingGlobal].append(global_routine)
    return wrapper

def OngoingEachPlayer(*conditions: Callable[["EventPlayer"], None]):
    def wrapper(func):
        if not asyncio.iscoroutinefunction(func):
            func = asyncio.coroutine(func)
        async def eventplayer_routine(event_player:"EventPlayer"):
            while True:
                async with global_event_lock:            
                    await global_event_lock.wait_for(
                        lambda: all(f(event_player) for f in conditions)
                    )
                    await func(event_player)
                    await asyncio.sleep(1/60)
                    await global_event_lock.wait_for(
                        lambda: not all(f(event_player) for f in conditions)
                    )
        scripted_events[OngoingEachPlayer].append(eventplayer_routine)
    return wrapper


def set_color(data, offset, color):
    data[offset: offset + BYTES_PER_PIX] = color

__help_text = ""
def set_help_text(help_text):
    global __help_text
    __help_text = textwrap.dedent(help_text)

def get_help_text():
    return __help_text

    