import math
from game_map import Map
import os
import logging.config, logging
from typing import Callable
from graphics import Res
import tkinter as tk
import tk_io
import game_io
from game_io import Button, EventPlayer, user_event_player
from lib_rq import RenderEngine, Camera, _update_game
import asyncio
import ctypes
import functools



logger = logging.getLogger(__name__)
RES = Res.R256x144
user_res: Res = None
user_dev: bool = None
user_x_sens: float = 0.25
user_y_sens: float = 0.25
root_win: tk_io.GameWin = None


def xset_shield(fn):
    def inner(*args, **kwargs):
        try:
            # Holding down a button should not send repeating input
            os.system("xset r off")
            fn(*args, **kwargs)
        finally:
            os.system("xset r on")
    return inner


def mouse_motion(event_player, vp: tk_io.PlayerView, event):
    center_x = vp.winfo_width() / 2
    center_y = vp.winfo_height() / 2
    dx = (event.x - center_x) * user_x_sens
    event_player.facing_direction[0] += math.radians(dx)
    dy = event_player.facing_direction[1] + math.radians(
        (event.y - center_y) * user_y_sens
    )
    if abs(dy) < (math.pi / 4):
        event_player.facing_direction[1] = dy

RENDER_SCALE = 2

def main(
    map: Map,
    dev=False, # Set to True to bypass option menu
    logconf=None,
    ncores=8,
    player=None
):
    global root_win, user_res, user_dev
    event_player = game_io.user_event_player(map=map)
    event_player.bind(map.player if player is None else player)
    event_player.syncdown()
    Camera.bind(event_player)

    root_win = win = tk_io.GameWin(className=" ")
    win.geometry(str(RES))
    if not dev:
        _get_user_options()
        logconf = "logging.json"
    else:
        user_res = Res.R640x360
    
    viewport = _init_game_ui(); _bind_keys(viewport)
    frame_time = tk.DoubleVar()
    evp_x = tk.DoubleVar()
    evp_y = tk.DoubleVar()
    evp_z = tk.DoubleVar()
    evp_r0 = tk.DoubleVar()
    evp_fx = tk.DoubleVar()
    evp_fy = tk.DoubleVar()
    evp_fz = tk.DoubleVar()

    set_attrs = lambda evp: (
        evp_x.set(evp.position[0]),
        evp_y.set(evp.position[1]),
        evp_z.set(evp.position[2]),
        evp_r0.set(map.player.exposure_factor),
        evp_fx.set(int(math.degrees(evp.facing_direction[0])) % 360),
        evp_fy.set(int(math.degrees(evp.facing_direction[1])) % 360),
        evp_fz.set(int(math.degrees(evp.facing_direction[2])) % 360),
    )
           
    # Init the dev ui but don't show it unless user_dev flag is set
    grid_dev = _init_dev_ui(
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
    if user_dev or dev:
        grid_dev()
    _init_logging(
        ("__main__", logging.DEBUG),
        ("game_io", logging.DEBUG),
        ("tk_io", logging.DEBUG),
        ("graphics", logging.DEBUG),
        logconf=logconf,
    )
   
    # lock mouse to center, enable io handlers
    viewport.acquire()
    logger.info(f"Map @ {map.width}x{map.height}")
    camera_size = ctypes.sizeof(Camera)
    map_size = ctypes.sizeof(map.ByteMap)

    viewport.on_motion = functools.partial(mouse_motion, event_player)

    _update_game()
    def arguments(buf: bytearray):
        return (
            Camera.from_buffer(buf),
            map.ByteMap.from_buffer(buf, camera_size),
        )
    with RenderEngine(
            user_res,
            ncores, 
            camera_size + map_size,
            arguments,
            RENDER_SCALE,
    ) as gpu:
        timer = tk_io.loop_time()
        data_in, data_out = bytearray(), bytearray()
        
        def render():
            frame_time.set(timer())
            set_attrs(user_event_player())

            # sync so map.pretty_print shows upated position
            game_io.user_event_player().syncup()
            data = map.byte_dump()
            data_in[:camera_size] = bytearray(Camera())
            data_in[camera_size:camera_size + map_size] = data
            gpu(data_in, data_out)
            viewport.draw(data_out)
        
        async def print_loop():
            while True:
                map.move_all()
                await asyncio.sleep(1/30)

        loop = asyncio.get_event_loop()
        loop.create_task(print_loop())
        loop.create_task(event_player.move(map))
        win.mainloop(render)

def _get_user_options():
    """Initialize menu for user to select options"""
    resolutions = list(Res)
    frame = tk_io.MenuWin()
    res_menu = tk.OptionMenu(
        frame,
        optvar := tk.StringVar(),
        *resolutions,
    )
    tk.Label(master=frame, text="Rolla Quest 3D", font=(20)).pack(
        pady=5
    )
    def set_user_res(dev):
        global user_res
        global user_dev
        user_dev = dev
        user_res = {
            str(r): r for r in Res
        }.get(optvar.get(), RES)
        frame.destroy()
    
    bt_frame = tk.Frame(frame)
    bt_start = tk.Button(
        master=bt_frame,
        text=" START ",
        command=lambda: set_user_res(False)
    )
    bt_dev = tk.Button(
        master=bt_frame,
        text="dev",
        command=lambda: set_user_res(True)
    )
    bt_start.pack(side=tk.LEFT, fill=tk.X)
    bt_dev.pack(side=tk.LEFT)
    res_menu.pack(expand=True, fill=tk.BOTH)
    bt_frame.pack(expand=True, fill=tk.BOTH)
    optvar.set(list(Res)[0])
    frame.pack(expand=True)
    frame.mainloop() # Block until user presses start

def _init_game_ui():
    root_win.geometry("") # enable auto resize of window
    viewport_container = tk.Frame(
        width=user_res.width,
        height=user_res.height,
    )
    stat = tk_io.PlayerStat(
        master=viewport_container,
        borderwidth=1,
        relief=tk.RIDGE
    )
    compass = tk_io.PlayerCompass(
        master=viewport_container,
        borderwidth=1,
        relief=tk.RIDGE,
    )
    viewport_outer = tk.Frame(
        master=viewport_container,
        width=user_res.width * RENDER_SCALE,
        height=user_res.height * RENDER_SCALE,
    )
    menu = tk_io.GameMenu(
        master=viewport_outer,
    )
    menu.place(x=0, y=0)
    root_win.update()    # calculates size
    
    w, h = menu.winfo_width(), menu.winfo_height(),
    menu.place(
        x=(user_res.width * RENDER_SCALE) // 2 - w // 2,
        y=(user_res.height * RENDER_SCALE)// 2 - h // 2,
    )
    viewport = tk_io.PlayerView(
        master=viewport_outer,
        res=user_res,
        render_scale = RENDER_SCALE,
    )
    compass.grid(
        row=0,
        column=0,
        columnspan=3,
        sticky="we",
    )
    viewport_outer.grid(
        row=1,
        rowspan=3,
        column=0,
        columnspan=3,
        sticky="nswe"
    )
    viewport.place(x=0, y=0)
    stat.grid(
        row=1,
        column=0,
        sticky="nw"
    )
    stat.lift()
    viewport_container.grid(
        row=0,
        column=1,
        sticky="nswe",
    )
    def on_escape_1(event):
        root_win.push_escape(on_escape_2)
        # Show the menu, and release io lock
        menu.lift()
        viewport.release()

    def on_escape_2(event):
        root_win.push_escape(on_escape_1)
        menu.lower()
        viewport.acquire()

    root_win.push_escape(on_escape_1)
    return viewport


def _init_dev_ui(
    fmt_str, *,
    variables=[],
) -> Callable[[], None]:
    devinfo = tk_io.DevInfo(
        variables=variables
    )
    logviewer = tk_io.TextHandler()
    logviewer.setFormatter(logging.Formatter(fmt_str, "%H:%M:%S"))
    rootlog = logging.getLogger()
    rootlog.addHandler(logviewer)

    def grid_fn():
        devinfo.grid(
            row=0,
            column=0,
            sticky="nswe"
        )
        logviewer.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="nswe",
        )
    return grid_fn

def _init_logging(*logname_level, logconf=None):
    if logconf is not None:
        import json
        with open(logconf, "r") as fp:
            return logging.config.dictConfig(json.load(fp))
    else:
        for logname, level in logname_level:
            logging.getLogger(logname).setLevel(level)

def _bind_keys(viewport: tk_io.IOLock):
    keybinds = game_io.get_user_keybinds()
    user_player = game_io.user_event_player()
    up, down, left, right = keybinds["Movement"]
    root_win.bind_key_press_release(
        up,
        lambda ev: user_player.set_throttle(2, 1),
        lambda ev: user_player.set_throttle(2, 0),
        viewport,
    )
    root_win.bind_key_press_release(
        down,
        lambda ev: user_player.set_throttle(2, -1),
        lambda ev: user_player.set_throttle(2, 0),
        viewport,
    )
    root_win.bind_key_press_release(
        left,
        lambda ev: user_player.set_throttle(0, -1),
        lambda ev: user_player.set_throttle(0, 0),       
        viewport,
    )
    root_win.bind_key_press_release(
        right,
        lambda ev: user_player.set_throttle(0, 1),
        lambda ev: user_player.set_throttle(0, 0),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.JUMP],
        lambda ev: (
            user_player.set_button(Button.JUMP, True),
            user_player.set_throttle(1, 1)
        ),
        lambda ev:(
            user_player.set_button(Button.JUMP, False),
            user_player.set_throttle(1, 0)
        ),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.CROUCH],
        lambda ev: (
            user_player.set_button(Button.CROUCH, True),
            user_player.set_throttle(1, -1)
        ),
        lambda ev:(
            user_player.set_button(Button.CROUCH, False),
            user_player.set_throttle(1, 0)
        ),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.ABILITY_1],
        lambda ev: user_player.set_button(Button.ABILITY_1, True),
        lambda ev: user_player.set_button(Button.ABILITY_1, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.ABILITY_2],
        lambda ev: user_player.set_button(Button.ABILITY_2, True),
        lambda ev: user_player.set_button(Button.ABILITY_2, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.ABILITY_3],
        lambda ev: user_player.set_button(Button.ABILITY_3, True),
        lambda ev: user_player.set_button(Button.ABILITY_3, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.INTERACT],
        lambda ev: user_player.set_button(Button.INTERACT, True),
        lambda ev: user_player.set_button(Button.INTERACT, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.PRIMARY_FIRE],
        lambda ev: user_player.set_button(Button.PRIMARY_FIRE, True),
        lambda ev: user_player.set_button(Button.PRIMARY_FIRE, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.SECONDARY_FIRE],
        lambda ev: user_player.set_button(Button.SECONDARY_FIRE, True),
        lambda ev: user_player.set_button(Button.SECONDARY_FIRE, False),  
        viewport,   
    )
    root_win.bind_key_press_release(
        keybinds[Button.RELOAD],
        lambda ev: user_player.set_button(Button.RELOAD, True),
        lambda ev: user_player.set_button(Button.RELOAD, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.MELEE],
        lambda ev: user_player.set_button(Button.MELEE, True),
        lambda ev: user_player.set_button(Button.MELEE, False),
        viewport,
    )
    root_win.bind(
        f"<{keybinds[Button.NEXT]}>",
        viewport.protect(lambda ev: user_player.on_next(user_player, ev))
    )
    root_win.bind(
        f"<{keybinds[Button.PREV]}>",
        viewport.protect(lambda ev: user_player.on_prev(user_player, ev))
    )



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

