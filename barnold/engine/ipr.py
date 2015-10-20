# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import os
import sys
import threading
import multiprocessing as _mp

def _worker(data, redraw_event, tiles, abort):
    print("+++ _worker: started")

    dir = os.path.dirname(__file__)
    if dir not in sys.path:
        sys.path.append(dir)
    import numpy, ctypes, arnold

    ass = r"D:\Tools\Design\Blender\scenes\test\31-arnold.ass"
    arnold.AiBegin()
    try:
        #arnold.AiMsgSetConsoleFlags(arnold.AI_LOG_ALL)
        arnold.AiASSLoad(ass)

        def _callback(x, y, width, height, buffer, data):
            print("+++ _callback:", x, y, width, height, ctypes.cast(buffer, ctypes.c_void_p))
            if buffer:
                try:
                    if not abort.value:
                        _buffer = ctypes.string_at(buffer, width * height * 4 * 4)
                        tiles.put((x, y, width, height, _buffer))
                        print("+++ _callback:", tiles.qsize())
                        redraw_event.set()
                        return
                finally:
                    arnold.AiFree(buffer)
            elif not abort.value:
                return
            arnold.AiRenderAbort()

        n = arnold.AiNodeLookUpByName("__outdriver")
        cb = arnold.AtDisplayCallBack(_callback)
        arnold.AiNodeSetPtr(n, "callback", cb)

        options = arnold.AiUniverseGetOptions()

        xres = arnold.AiNodeGetInt(options, "xres")
        yres = arnold.AiNodeGetInt(options, "yres")
        bucket_size = xres if xres > yres else yres
        arnold.AiNodeSetInt(options, "bucket_size", bucket_size)

        for sl in range(-5, 1):
            arnold.AiNodeSetInt(options, "AA_samples", sl)
            res = arnold.AiRender(arnold.AI_RENDER_MODE_CAMERA)
            if res != arnold.AI_SUCCESS:
                break

        tiles.close()
        #abort.value = True
        #redraw_event.set()
    finally:
        arnold.AiEnd()
    print("+++ _worker: finished")

def _main():
    import bpy
    _mp.set_executable(bpy.app.binary_path_python)

    data = {}

    tiles = _mp.Queue()
    redraw_event = _mp.Event()
    abort = _mp.Value('b', False)

    def tag_redraw():
        while redraw_event.wait() and not abort.value:
            print("--- tag_redraw: event")
            redraw_event.clear()
            e = engine()
            if e is not None:
                e.tag_redraw()
            del e

    redraw_thread = threading.Thread(target=tag_redraw)
    process = _mp.Process(target=_worker, args=(data, redraw_event, tiles, abort))

    def stop():
        print(">>> stop (1): started")
        abort.value = True
        print(">>> stop (2): abort")
        redraw_event.set()
        print(">>> stop (3):", redraw_thread)
        redraw_thread.join()
        print(">>> stop (4):", redraw_thread)
        print(">>> stop (5):", process)
        process.join(3)
        print(">>> stop (6):", process)
        process.terminate()
        print(">>> stop (7):", process)

    redraw_thread.start()
    process.start()

    return stop, lambda: None if tiles.empty() else tiles.get()

if __name__ == "__main__":
    stop, tile = _main()
