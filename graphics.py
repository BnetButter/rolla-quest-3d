import enum
import logging
from multiprocessing import Condition, Value
from multiprocessing.shared_memory import SharedMemory
import collections
import os
import signal
import abc
import contextlib
from typing import Callable

logger = logging.getLogger(__name__)

BYTES_PER_PIX = 3

class Res(enum.Enum):
    R256x144 = (256, 144)
    R640x360 = (640, 360)
    R1920x1080 = (1920,1080)

    def __str__(self):
        width, height = self.value
        return f"{width}x{height}"
    
    @property
    def width(self):
        return self.value[0]

    @property
    def height(self):
        return self.value[1]
    
    @property
    def size(self):
        return self.value[0] * self.value[1] * BYTES_PER_PIX

class GPU(collections.UserList):
    """If only OpenCL/CUDA was part of python..."""
    
    cores: int
    width: int
    height: int
    block_X: int
    

    def __init__(self, 
        resolution: Res,
        core_count: int,
        vram_size: int,
        arg_factory: Callable[[bytearray], None]
    ):
        super().__init__()
        self.arg_factory = arg_factory
        self._id = os.getpid()
        self._cond = Condition()
        self._value_cond = Condition()
        self._value = Value('i', 0, lock=self._value_cond)
        self._resolution = resolution
        self.cores = self._core_count = core_count
        self._vram_size = vram_size
        self.width = resolution.width
        self.height = resolution.height
        self.block_X = self.width // self.cores
        

        
    def __call__(self, b_in: bytearray, b_out: bytearray):
        # copy in bytes
        self._value.value = 0
        self._vram.buf[:len(b_in)] = b_in
        
        # wake up
        with self._cond:
            self._cond.notify_all()
        
        with self._value_cond:
            self._value_cond.wait(timeout=0.05)
            b_out[:self._raster_buff.size] = self._raster_buff.buf

    @abc.abstractmethod
    def device(self, idx, vram, raster):
        pass

    def __enter__(self):
        self._raster_buff = SharedMemory(
            create=True,
            size=self._resolution.height * self._resolution.width * 3,
        )
        self._vram = SharedMemory(
            create=True,
            size=self._vram_size,
        )
        counter = Value('i', 0)
        for id in range(self._core_count):
            if (child := os.fork()) == 0:
                
                @contextlib.contextmanager
                def sharedmem():            
                    shm = SharedMemory(self._raster_buff.name)
                    vram = SharedMemory(self._vram.name)
                    try:
                        yield shm, vram
                    finally:
                        shm.close()
                        vram.close()

                with sharedmem() as (shm, vram):
                    with counter:
                        counter.value += 1
                    while True:
                        try:
                            with self._cond:
                                self._cond.wait()
                        except KeyboardInterrupt:
                            exit(0)
                        try:
                            self.device(id, vram.buf, shm.buf)
                        except:
                            pass

                        with self._value:
                            self._value.value += 1
                            if self._value.value == self._core_count:
                                self._value_cond.notify_all()
            else:
                self.append(child)

        while counter.value < self._core_count:
            # block until all cores init
            pass
        
        logger.debug(
            f"@{self._resolution} core count: {self._core_count} "
            f"vram: {self._vram_size} bytes"
        )
        return self


    def __exit__(self, *args, **kwargs):
        if os.getpid() == self._id:
            for child in self:
                os.kill(child, signal.SIGINT)
                os.waitpid(child, 0)
            self._raster_buff.close()
            self._raster_buff.unlink()
            self._vram.close()
            self._vram.unlink()

