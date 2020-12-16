import math
from game_map import Map
import os
import logging.config, logging
from typing import Callable, TYPE_CHECKING, Tuple
from graphics import Res
import tkinter as tk
import tk_io
from game_io import EventPlayer
import asyncio
import ctypes
import rq_ui
from graphics import GPU, BYTES_PER_PIX
from ctypes import (
    c_float,
    c_uint8,
    c_uint16
)
logger = logging.getLogger(__name__)
RES = Res.R256x144
opts = rq_ui.user_options()

if TYPE_CHECKING:
    from lib_rq import Camera
class Sprite:
    """Render vertical columns"""

    def __init__(self, repr_char, color=[0, 0, 0], h0=1.0, h1=1.0):
        self.repr_char = repr_char
        self.color = color

        # First line beneath horizon
        self.h0: float = h0
        # second line
        self.h1: float = h1
        # relative height relative to screen when object's distance is 0
        self.relH = 0

    def adjusted_color(self, percfloat):
        """Apply grey scale"""
        return bytearray(int(x * percfloat) for x in self.color)


sprites = {
    "M": Sprite("M", [0, 247, 255]),
    "V": Sprite("V", [128, 128, 128]),
    "C": Sprite("C", [255, 0, 0], h0=1.0),
    "0": Sprite("0", [128, 128, 128]),
    "M": Sprite("M", [0, 247, 255]),
    "G": Sprite("G", [0, 255, 0]),
    "1": Sprite("1", [255, 171,0]),
    "P": Sprite("1", [0, 0, 255])
}
def xset_shield(fn):
    def inner(*args, **kwargs):
        try:
            # Holding down a button should not send repeating input
            os.system("xset r off")
            fn(*args, **kwargs)
        finally:
            os.system("xset r on")
    return inner

RENDER_SCALE = 2

@xset_shield
def main(
    map: Map,
    dev=False, # Set to True to bypass option menu
    logconf=None,
    ncores=8,
    player=None
):
    from lib_rq import Camera
    import lib_rq
    
    opts = rq_ui.user_options()
    opts.dev = dev
    opts.logconf = logconf if logconf is not None else opts.logconf
    opts.ncores = ncores
    opts.renderscale = RENDER_SCALE

    players = [EventPlayer(entity, map=map) for entity in map.entities]

    Camera.bind(players[0])

    win = tk_io.GameWin(className=" ")
    win.geometry(str(RES))
    if not dev:
        rq_ui.get_user_options()
       
    else:
        opts.res = Res.R640x360

    viewport = rq_ui.init_game_ui(); rq_ui.bind_keys(viewport, Camera)
    frame_time = tk.DoubleVar()
    evp_x = tk.DoubleVar()
    evp_y = tk.DoubleVar()
    evp_z = tk.DoubleVar()
    evp_r0 = tk.DoubleVar()
    evp_fx = tk.DoubleVar()
    evp_fy = tk.DoubleVar()
    evp_fz = tk.DoubleVar()

    set_vars = lambda: (
        evp_x.set(Camera.POSITION[0]),
        evp_y.set(Camera.POSITION[1]),
        evp_z.set(Camera.POSITION[2]),
        evp_r0.set(map.player.exposure_factor),
        evp_fx.set(int(math.degrees(Camera.FACING[0])) % 360),
        evp_fy.set(int(math.degrees(Camera.FACING[1])) % 360),
        evp_fz.set(int(math.degrees(Camera.FACING[2])) % 360),
    )
           
    # Init the dev ui but don't show it unless user_dev flag is set
    grid_dev = rq_ui.init_dev_ui(
        "%(levelname)-8s %(asctime)s - %(message)s",
        variables=[
            (frame_time, "Frame Time"),
            (evp_x, "pos.X | entity.col"),
            (evp_z, "pos.Z | entity.row"),
            (evp_y, "pos.Y"),
            (evp_fx, "facing.X"),
            (evp_fy, "facing.Y"),
            (evp_fz, "facing.Z"),
            (evp_r0, "~HP  | r0"),
        ]
    )
    if opts.dev:
        grid_dev()
    
    _init_logging(
        ("__main__", logging.DEBUG),
        ("game_io", logging.DEBUG),
        ("tk_io", logging.DEBUG),
        ("graphics", logging.DEBUG),
        logconf=opts.logconf,
    )
   
    # lock mouse to center, enable io handlers
    viewport.acquire()
    logger.info(f"Map @ {map.width}x{map.height}")
    camera_size = ctypes.sizeof(Camera)
    map_size = ctypes.sizeof(map.ByteMap)

    viewport.on_motion = Camera.mouse_motion

    lib_rq.init_global_event_scripts(map)
    win.update()
    def arguments(buf: bytearray):
        return (
            Camera.from_buffer(buf),
            map.ByteMap.from_buffer(buf, camera_size),
        )
    
    try:
        with RenderEngine(
                opts.res,
                ncores, 
                camera_size + map_size,
                arguments,
                opts.renderscale,
        ) as gpu:
            timer = tk_io.loop_time()
            data_in, data_out = bytearray(), bytearray()
            
            def render():
                frame_time.set(timer())
                set_vars()

                data = map.byte_dump()
                data_in[:camera_size] = bytearray(Camera())
                data_in[camera_size:camera_size + map_size] = data
                gpu(data_in, data_out)
                viewport.draw(data_out)
            win.mainloop(render)

    except lib_rq.ReloadEvent:
        # Need to make sure the with statement above properly exits before
        # restarting. Otherwise the shared memory never gets released
        import os, sys
        python = sys.executable
        os.execl(python, python, *sys.argv)

# TODO sin/cos table and grey scale table
def cos(r):
    return math.cos(r)


def sin(r):
    return math.sin(r)


GREY_SCALE = [bytearray([x, x, x]) for x in [200, 175, 150, 125, 100, 75, 50, 25, 10]]
D_SCALE = 10
GROUND_COLOR = [63, 166, 90]
SKY_COLOR = [79, 217, 245]


def squash(x):
    return x / (x + 1)


class RenderEngine(GPU):
    def get_apparent_height(self, scale, dist):
        return ((self.height / (2 * math.pi * (dist + 1))) * 360) // 2

    def get_pixel_offset(self, row, col):
        return (row * self.width * BYTES_PER_PIX * self.renderscale) + (
            col * BYTES_PER_PIX * self.renderscale
        )

    def device(self, idx: int, b_in: bytearray, b_out: bytearray):
        """
        idx: core index
        in: input data
        out: output data
        """
        # Process 1/ncores of the screen in parallel. Read in bytes, do math
        # write results to shared memory

        camera: Camera
        camera, map = self.arg_factory(b_in)

        radians_per_pixel = math.radians(camera.fov) / self.width
        radian_offset = math.radians(camera.fov / 2) + math.radians(90 - camera.fov)
        facing_offset = camera.facing[0]
        start, end = self.block_X * idx, self.block_X * (idx + 1)

        c_x, c_y, c_z = camera.position[0], camera.position[1], camera.position[2]
        f_y = camera.facing[1]

        dist_to = [
            (ord(" "), 100, 0, bytearray([0, 0, 0])) for _ in range(self.block_X)
        ]
        # Y shearing. Move the world view up/down depending on y direction.
        # Modeled as a camera rotating around the x axis.
        mid_y = (self.height // 2) - (sin(f_y) * self.height)
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
                        self.get_apparent_height(0.5, dist),
                        GREY_SCALE[int(math.log(dist))],
                    )
                    break
                elif ch in Map.WALL_CHAR:
                    dist_to[i - start] = (
                        map[y][x],
                        j,
                        self.get_apparent_height(1, dist),
                        GREY_SCALE[int(math.log(dist))],
                    )
                    break
                elif ch in sprites and map[y][x] !=  camera.repr_char:
                    dist_to[i - start] = (
                        map[y][x],
                        j,
                        self.get_apparent_height(1, dist),
                        bytearray(int(gs * x) for x in sprites[ch].color),
                    )
                    break
        # O(n^2). :(
        for i in range(self.height):
            for j, (ch, wall_dist, size, color) in enumerate(dist_to):
                d = i - mid_y  # in pixels
                dist_from_mid = abs(d)
                gs = squash(dist_from_mid)
                # Fake higher resolutions
                for k in range(self.renderscale):
                    off = self.get_pixel_offset(i * self.renderscale + k, j + start)
                    # Draw sky, ground
                    # This part can be optimized by drawing the entire scene before
                    # entering this function. This way we only need to draw sprites
                    if d > 0:
                        self.set_color(
                            b_out, off, bytearray(int(gs * x) for x in GROUND_COLOR)
                        )
                    else:
                        self.set_color(
                            b_out, off, bytearray(int(gs * x) for x in SKY_COLOR)
                        )
                    
                    if dist_from_mid <= size:
                        self.set_color(b_out, off, color)

    def set_color(self, d_out, offset, color):
        d_out[offset : offset + BYTES_PER_PIX * self.renderscale] = (
            color * self.renderscale
        )


def _init_logging(*logname_level, logconf=None):
    if logconf is not None:
        import json
        with open(logconf, "r") as fp:
            return logging.config.dictConfig(json.load(fp))
    else:
        for logname, level in logname_level:
            logging.getLogger(logname).setLevel(level)



if __name__ == "__main__":
    import argparse
    import game_map
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        "-d",
        "--dev",
        action="store_true",
        help="start in dev mode",
    )
    parser.add_argument(
        "--logconf",
        type=lambda arg: arg if os.path.exists(arg) else None,
        help="Path to logging configuration",
    )
    parser.add_argument(
        "--ncores",
        type=int,
        help="Number of stream processors",
        default=8,
    )
    optarg = parser.parse_args()
    main(game_map.Map("maps/reversed_mst_campus.txt"), **optarg.__dict__)

