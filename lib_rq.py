from game_map import Map
from typing import List, Tuple
from game_io import EventPlayer
from graphics import GPU, BYTES_PER_PIX
from ctypes import c_uint16, c_uint8, c_float
import ctypes
import textwrap
import math
import logging

logger = logging.getLogger(__name__)

Vector = c_float * 3            # typedef float Vector[3];
Pixel = c_uint8 * BYTES_PER_PIX # typedef uint8_t Pixel[BYTES_PER_PIX];


# Easy way to cast to/from bytearray. Much better than the insanity that is
# struct.pack
class Camera(ctypes.Structure):
    FOV = 90
    DIST = 100
    
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

    _bound_entity: EventPlayer = None
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
    def bind(cls, evp: EventPlayer):
        cls._bound_entity = evp
    
# TODO sin/cos table
def cos(r):
    return math.cos(r)

def sin(r):
    return math.sin(r)

GREY_SCALE = [
    bytearray([x, x, x]) for x in [
        225, 200, 190, 180, 125,75,50,25,10
    ]
]


GROUND_COLOR = [63, 166, 90]
SKY_COLOR = [79, 217, 245]

D_SCALE = 10
VERTICAL_OFFSET = 0.5

class RenderEngine(GPU):

    def get_apparent_height(self, scale, dist):
        return (((self.height*scale) / (2 * math.pi * (dist+1))) * 360) // 2

    def get_pixel_offset(self, row, col):
        return (row * self.width * BYTES_PER_PIX) + (col * BYTES_PER_PIX)

    def device(self, idx:int, b_in:bytearray, b_out:bytearray):
        """
        idx: core index
        in: input data
        out: output data
        """
        camera: Camera
        camera, map = self.arg_factory(b_in)

        radians_per_pixel = math.radians(camera.fov) / self.width
        radian_offset = math.radians(camera.fov / 2)
        facing_offset = camera.facing[0]
        start, end = self.block_X * idx, self.block_X * (idx + 1)
        
        
        dist_to = [
            (ord(' '), -1, 0, bytearray([0,0,0]))
            for _ in range(self.block_X)
        ]
        # Y shearing. Move the world view up/down depending on y direction
        mid_y = (self.height // 2) - (
            sin(camera.facing[1]) * 1.5 * self.height
        )   
        c_x, c_z = camera.position[0], camera.position[2]
        f_y = camera.position[1]

        # O(n) so not a big deal
        for i in range(start, end):
            radx = radians_per_pixel * i + radian_offset + facing_offset
            for j in range(camera.DIST):
                rc_x = j * sin(radx) + c_x
                rc_y = j * cos(radx) + c_z
                x, y = int(math.floor(rc_x)), int(math.floor(rc_y))
                ch = chr(map[y][x])

                # pull projected image closer as we change pitch. Doesn't change
                # much but it doesn't add that much time to render time either
                dist = j * D_SCALE * cos(f_y) 

                if ch in Map.BOUND_CHAR:
                    dist_to[i - start] = (
                        map[y][x],
                        dist,
                        self.get_apparent_height(0.5,dist),
                        GREY_SCALE[int(math.log(dist))]
                    )
                    break
                elif ch in Map.WALL_CHAR:
                    dist_to[i - start] = (
                        map[y][x],
                        dist,
                        self.get_apparent_height(1, dist),
                        GREY_SCALE[int(math.log(dist))]
                    )
                    break
                elif ch in Map.REPR_CHAR:
                    dist_to[i - start] = (
                        map[y][x],
                        dist,
                        self.get_apparent_height(1, dist),
                        bytearray(Map.REPR_CHAR[ch])
                    )
                    break
        

        # O(n^2). :(
        for i in range(self.height):
            for j, (ch, wall_dist, size, color) in enumerate(dist_to):
                d = i - mid_y
                dist_from_mid = abs(d)

                off = self.get_pixel_offset(i, j + start)
                # Draw sky, ground
                if d > 0:
                    set_color(b_out, off, bytearray(GROUND_COLOR))
                else:
                    set_color(b_out, off, bytearray(SKY_COLOR))
                # Draw sprites
                if dist_from_mid <= size:
                    set_color(b_out,off,color)



class EventContext:

    def __getattr__(self, name):
        if name == "__dict__":
            return super.__getattr__(name)
        if name in self.__dict__:
            logger.error(f"{name} not available in context")


def OngoingEachPlayer(map, conditions=[]):
    def wrapper(func):
        return func
    return wrapper

def set_color(data, offset, color):
    data[offset: offset + BYTES_PER_PIX] = color

__help_text = ""
def set_help_text(help_text):
    global __help_text
    __help_text = textwrap.dedent(help_text)

def get_help_text():
    return __help_text

    