import tk_io
from typing import (
    Callable,
)
from graphics import Res
from game_io import Button
import tkinter as tk
import logging
import game_io
logger = logging.getLogger(__name__)

class UserOptions:
    dev: bool = False
    res: Res = Res.R256x144,
    logconf: str = "logging.json"
    renderscale: int = 1
    x_sens: float = 0.25
    y_sens: float = 0.25


_user_options = None
def user_options():
    global _user_options
    if _user_options is None:
        _user_options = UserOptions()
    return _user_options

def get_user_options():
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
    opt = user_options()
    
    def set_user_res(dev):
        opt.dev = dev
        opt.res = {
            str(r): r for r in Res
        }.get(optvar.get(), Res.R256x144)
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

def init_game_ui():
    root_win = tk_io.root_win()
    root_win.geometry("") # enable auto resize of window
    opt = user_options()

    
    wh, hh = opt.res.width * opt.renderscale, opt.res.height * opt.renderscale

    viewport_container = tk.Frame(
        width=wh,
        height=hh,
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
        width=wh,
        height=hh,
    )
    menu = tk_io.GameMenu(
        master=viewport_outer,
    )
    menu.place(x=0, y=0)
    root_win.update()    # calculates size
    
    w, h = menu.winfo_width(), menu.winfo_height(),
    menu.place(
        x=wh // 2 - w // 2,
        y=hh// 2 - h // 2,
    )
    viewport = tk_io.PlayerView(
        master=viewport_outer,
        res=opt.res,
        render_scale = opt.renderscale,
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


def init_dev_ui(
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


def bind_keys(viewport: tk_io.IOLock, camera):
    keybinds = game_io.get_user_keybinds()
    root_win = tk_io.root_win()
    up, down, left, right = keybinds["Movement"]
    root_win.bind_key_press_release(
        up,
        lambda ev: camera.set_throttle(2, 1),
        lambda ev: camera.set_throttle(2, 0),
        viewport,
    )
    root_win.bind_key_press_release(
        down,
        lambda ev: camera.set_throttle(2, -1),
        lambda ev: camera.set_throttle(2, 0),
        viewport,
    )
    root_win.bind_key_press_release(
        left,
        lambda ev: camera.set_throttle(0, -1),
        lambda ev: camera.set_throttle(0, 0),       
        viewport,
    )
    root_win.bind_key_press_release(
        right,
        lambda ev: camera.set_throttle(0, 1),
        lambda ev: camera.set_throttle(0, 0),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.JUMP],
        lambda ev: (
            camera.set_button(Button.JUMP, True),
            camera.set_throttle(1, 1)
        ),
        lambda ev:(
            camera.set_button(Button.JUMP, False),
            camera.set_throttle(1, 0)
        ),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.CROUCH],
        lambda ev: (
            camera.set_button(Button.CROUCH, True),
            camera.set_throttle(1, -1)
        ),
        lambda ev:(
            camera.set_button(Button.CROUCH, False),
            camera.set_throttle(1, 0)
        ),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.ABILITY_1],
        lambda ev: camera.set_button(Button.ABILITY_1, True),
        lambda ev: camera.set_button(Button.ABILITY_1, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.ABILITY_2],
        lambda ev: camera.set_button(Button.ABILITY_2, True),
        lambda ev: camera.set_button(Button.ABILITY_2, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.ABILITY_3],
        lambda ev: camera.set_button(Button.ABILITY_3, True),
        lambda ev: camera.set_button(Button.ABILITY_3, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.INTERACT],
        lambda ev: camera.set_button(Button.INTERACT, True),
        lambda ev: camera.set_button(Button.INTERACT, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.PRIMARY_FIRE],
        lambda ev: camera.set_button(Button.PRIMARY_FIRE, True),
        lambda ev: camera.set_button(Button.PRIMARY_FIRE, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.SECONDARY_FIRE],
        lambda ev: camera.set_button(Button.SECONDARY_FIRE, True),
        lambda ev: camera.set_button(Button.SECONDARY_FIRE, False),  
        viewport,   
    )
    root_win.bind_key_press_release(
        keybinds[Button.RELOAD],
        lambda ev: camera.set_button(Button.RELOAD, True),
        lambda ev: camera.set_button(Button.RELOAD, False),
        viewport,
    )
    root_win.bind_key_press_release(
        keybinds[Button.MELEE],
        lambda ev: camera.set_button(Button.MELEE, True),
        lambda ev: camera.set_button(Button.MELEE, False),
        viewport,
    )
    root_win.bind(
        f"<{keybinds[Button.NEXT]}>",
        viewport.protect(lambda ev: camera.on_next(camera, ev))
    )
    root_win.bind(
        f"<{keybinds[Button.PREV]}>",
        viewport.protect(lambda ev: camera.on_prev(camera, ev))
    )