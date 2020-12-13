import abc
import collections
from io import TextIOWrapper
import logging
import tkinter as tk
from typing import Callable, List, Tuple
from graphics import Res
import time
import functools
import asyncio
import lib_rq

logger = logging.getLogger(__name__)
KeyPressHandler = Callable[[tk.Event], None]

def debug(fn):
    def inner(self, event: tk.Event):
        logger.debug(f"Mouse ({event.x}, {event.y})")
        fn(self, event)
    return inner


_root = None

class IOLock(abc.ABC):

    def protect(self, func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            if self.locked():
                func(*args, **kwargs)
        return inner

    @abc.abstractmethod
    def locked(self): ...
    
    @abc.abstractmethod
    def acquire(self): ...
    
    @abc.abstractmethod
    def release(self): ...


class GameWin(tk.Tk):
    """Root window object"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        global _root; _root = self # only one Tk instance per interpreter
        self._escape_stack = collections.deque()
        self._running = True
        self._loop = asyncio.get_event_loop()
        self.bind("<Escape>", self.handle_escape)
        self.bind("<Tab>", self.handle_tab)
        self.on_tab: Callable[[tk.Event], None] = lambda ev: None

    def push_escape(self, fn: Callable[[tk.Event], None]):
        if fn is None:
            self._escape_stack.appendleft(lambda ev: None)
        self._escape_stack.appendleft(fn)

    def handle_tab(self, ev):
        logger.debug("Pressed Tab")
        self.on_tab(ev)

    def handle_escape(self, ev):
        logger.debug("Pressed Esc")
        self._escape_stack.popleft()(ev)
    
    def bind_key_press_release(self, 
        bt: str,
        on_down:KeyPressHandler,
        on_up:KeyPressHandler,
        io_lock: IOLock = None
    ) -> Tuple[int, int]:
        if io_lock is not None:
            on_down = io_lock.protect(on_down)
            on_up = io_lock.protect(on_up)

        if bt.isdigit():
            return (self.bind(f"<Button-{bt}>", on_down),
                self.bind(f"<ButtonRelease-{bt}>", on_up))
        else:
            return (self.bind(f"<Key-{bt}>", on_down),
                self.bind(f"<KeyRelease-{bt}>", on_up))
    
    def center(self):
        self.update_idletasks()
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        this_w, this_h = self.winfo_width(), self.winfo_height()
        offset_x, offset_y = screen_w//2 - this_w//2, screen_h//2 - this_h//2
        self.geometry(f"+{offset_x}+{offset_y}")

    def destroy(self):
        self._running = False
        super().destroy()
    
    def mainloop(self, render: Callable[[], None]):
        async def _loop():
            while self._running:
                render()
                self.update()
                await asyncio.sleep(1/60)
            self._loop.stop()
        
        self._loop.create_task(_loop())
        self._loop.run_forever()
        


class PlayerView(tk.Canvas, IOLock):

    def __init__(self, *, res:Res = None, **kwargs):
        super().__init__(**kwargs)
        self._res = res
        self["width"] = res.width
        self["height"] = res.height
        self["bd"] = -2 # remove canvas border

        self._prev_img = tk.PhotoImage(
            width=res.width,
            height=res.height,
        )
        self._prev_cnv = self.create_image(
            (0, 0),
            image=self._prev_img,
            state="normal",
        )
        self._on_motion: Callable[[tk.Canvas, tk.Event]] = self._default_handler
        self._flag = True
        self._center = res.width // 2, res.height // 2
        self.bind("<Motion>", self.handle_motion)

    @staticmethod
    @debug
    def _default_handler(self, ev):
        """Do nothing"""
        pass

    def handle_motion(self, ev: tk.Event):
        w, h = self._center
        if ev.x == w and ev.y == h:
            return
        elif self._flag:
            self._on_motion(self, ev)
            self.event_generate("<Motion>", warp=True, x=w, y=h)

    @property
    def on_motion(self):
        return self._on_motion
    
    @on_motion.setter
    def on_motion(self, fn):
        if fn is None:
            self._on_motion = debug(self._default_handler)
        else:
            self._on_motion = debug(fn)

    def draw(self, data):
        self.delete(self._prev_cnv)
        self.delete(self._prev_img)

        if len(data) != self._res.size:
            data[:self._res.size] = bytearray([0 for _ in range(self._res.size)])
        img = self._prev_img = tk.PhotoImage(
            data=b"P6\n%d %d\n255\n%s" % (self._res.width, self._res.height, data)
        )
        self._prev_cnv = self.create_image(
            (self._res.width // 2, self._res.height // 2),
            image=img,
            state="normal"
        )

    def locked(self):
        return self._flag

    def acquire(self):
        x, y = self._center
        self._flag = True
        self.event_generate("<Motion>", warp=True, x=x, y=y)
        root_win().config(cursor="none")
        logger.info(f"io lock acquired")
    
    def release(self):
        self._flag = False
        root_win().config(cursor="")
        logger.info(f"io lock released")

    

class MenuWin(tk.Frame):
    _run = True

    def destroy(self):
        self._run = False
        super().destroy()

    def mainloop(self):
        while self._run:
            self.master.update()


class PlayerStat(tk.Frame):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._placeholder = tk.Label(
            master=self,
            text="Player Stat"    
        )
        self._placeholder.pack(expand=True)




class PlayerCompass(tk.Frame):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._placeholder = tk.Label(
            master=self,
            text="Player Compass"    
        )
        self._placeholder.pack(expand=True)


class DevInfo(tk.Frame):
    """
    Display program stats.
    """

    def __init__(self, *, variables: List[Tuple[tk.Variable, str]]=[], **kwargs):
        super().__init__(**kwargs)
        self["bg"] = "grey26"
        
        for i, (var, text) in enumerate(variables):
            tk.Label(
                master=self,
                text=text,
                background="grey26",
                foreground="white",
                relief=tk.RAISED,
                anchor="w",
            ).grid(
                row=(i * 2),
                column=0,
                sticky="nwe"
            )
            tk.Entry(
                master=self,
                textvariable=var,
                disabledbackground="grey26",
                disabledforeground="white",
                state=tk.DISABLED,
                bg="grey26",
            ).grid(
                row=(i * 2) + 1,
                column=0,
                sticky="nwe"
            )


class ScrollText(tk.Frame):

    def __init__(self, height=None, **kwargs):
        super().__init__(**kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.txt = tk.Text(self, height=height)
        self.txt.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        scrollb = tk.Scrollbar(self, command=self.txt.yview)
        scrollb.grid(row=0, column=1, sticky='nsew')
        self.txt['yscrollcommand'] = scrollb.set

class TextHandler(ScrollText, logging.Handler):
    """Display log records"""

    def __init__(self, **kwargs):
        super().__init__(height=8, **kwargs); logging.Handler.__init__(self)
        self.txt["state"] = tk.DISABLED
        self.txt["bg"] = "grey26"
        self.txt["fg"] = "white"

    def emit(self, record):
        message = self.format(record) + "\n"
        self.txt["state"] = tk.NORMAL
        self.txt.insert(tk.END, message)
        self.txt.see(tk.END)
        self.txt["state"] = tk.DISABLED

class GameMenu(tk.Frame):
    """
    Help:   Show the help window
    Quit:   exit the program
    Reload: exit the program and restart
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        quit_bt = tk.Button(
            master=self,
            text="Quit",
            command=self._quit
        )
        reload_bt = tk.Button(
            master=self,
            text="Reload",
            command=self._reload
        )
        help_bt = tk.Button(
            master=self,
            text="Help",
            command=self._help
        )
        
        help_bt.pack(expand=True, fill=tk.BOTH, padx=5, pady=2.5)
        quit_bt.pack(expand=True, fill=tk.BOTH, padx=5, pady=2.5)
        reload_bt.pack(expand=True, fill=tk.BOTH, padx=5, pady=2.5)

    def _quit(self):
        root_win().destroy()
        exit(0)
    
    topwin = None
    def _help(self):
        if self.topwin is None:
            self.topwin = tk.Toplevel(self)
            def on_destroy(*args):
                self.topwin.destroy()
                self.topwin = None
                
            self.topwin.protocol("WM_DELETE_WINDOW", on_destroy)
            help_text = ScrollText(master=self.topwin)
            help_text.txt.insert(tk.END, lib_rq.get_help_text())
            help_text.txt["state"] = tk.DISABLED
            help_text.pack()

    def _reload(self):
        import sys, os
        root_win().destroy()
        python = sys.executable
        os.execl(python, python, *sys.argv)


def loop_time() -> Callable[[], int]:
    last, current = 0, 0
    def update():
        nonlocal last, current
        diff = current - last
        last = current
        current = time.time()
        return diff
    return update


def root_win():
    return _root

