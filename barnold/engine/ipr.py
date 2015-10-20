# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import os
import sys
import threading
import multiprocessing as _mp

ABORT = 1
UPDATE = 2

def _worker(data, new_data, redraw_event, tiles, state):
    print("+++ _worker: started")

    dir = os.path.dirname(__file__)
    if dir not in sys.path:
        sys.path.append(dir)

    import numpy, ctypes, queue, arnold

    arnold.AiBegin()
    try:
        #arnold.AiMsgSetConsoleFlags(arnold.AI_LOG_ALL)
        #arnold.AiMsgSetConsoleFlags(0x000E)

        node = arnold.AiNode("box")

        opts = data['options']
        xres = opts['xres']
        yres = opts['yres']
        bucket_size = xres if xres > yres else yres

        options = arnold.AiUniverseGetOptions()
        arnold.AiNodeSetBool(options, "skip_license_check", True)
        arnold.AiNodeSetInt(options, "xres", xres)
        arnold.AiNodeSetInt(options, "yres", yres)
        arnold.AiNodeSetInt(options, "bucket_size", bucket_size)

        cam = opts['camera']
        node = arnold.AiNode(cam['node'])
        arnold.AiNodeSetMatrix(node, "matrix", arnold.AtMatrix(*cam['matrix']))
        arnold.AiNodeSetStr(node, "name", "__camera")
        arnold.AiNodeSetPtr(options, "camera", node)

        filter = arnold.AiNode("gaussian_filter")
        arnold.AiNodeSetStr(filter, "name", "__outfilter")

        driver = arnold.AiNode("driver_display")
        arnold.AiNodeSetStr(driver, "name", "__outdriver")
        arnold.AiNodeSetBool(driver, "rgba_packing", False)

        outputs_aovs = (
            b"RGBA RGBA __outfilter __outdriver",
        )
        outputs = arnold.AiArray(len(outputs_aovs), 1, arnold.AI_TYPE_STRING, *outputs_aovs)
        arnold.AiNodeSetArray(options, "outputs", outputs)

        def _callback(x, y, width, height, buffer, data):
            print("+++ _callback:", x, y, width, height, ctypes.cast(buffer, ctypes.c_void_p))
            if buffer:
                try:
                    if not state.value and new_data.empty():
                        _buffer = ctypes.string_at(buffer, width * height * 4 * 4)
                        tiles.put((x, y, width, height, _buffer))
                        print("+++ _callback:", tiles.qsize())
                        redraw_event.set()
                        return
                finally:
                    arnold.AiFree(buffer)
            elif not state.value and new_data.empty():
                return
            arnold.AiRenderAbort()

        cb = arnold.AtDisplayCallBack(_callback)
        arnold.AiNodeSetPtr(driver, "callback", cb)

        while state.value != ABORT:
            for sl in range(-5, 1):
                arnold.AiNodeSetInt(options, "AA_samples", sl)
                res = arnold.AiRender(arnold.AI_RENDER_MODE_CAMERA)
                if res != arnold.AI_SUCCESS:
                    break

            while True:
                try:
                    _data = new_data.get(timeout=1)
                    print(">>> worker: data", _data)
                    while not new_data.empty():
                        _data = new_data.get(timeout=1)
                        print(">>> worker: data", _data)
                    if _data is not None:
                        for name, params in _data['nodes'].items():
                            node = arnold.AiNodeLookUpByName(name)
                            for n, (t, v) in params.items():
                                if t == 'MATRIX':
                                    arnold.AiNodeSetMatrix(node, n, arnold.AtMatrix(*v))
                    break
                except queue.Empty:
                    print("+++ worker: data empty")

        tiles.close()
    finally:
        arnold.AiEnd()
    print("+++ _worker: finished")

def _main():
    import bpy
    _mp.set_executable(bpy.app.binary_path_python)

    tiles = _mp.Queue()
    new_data = _mp.Queue()

    def _tile():
        t = None
        while not tiles.empty():
            t = tiles.get()
        return t

    state = _mp.Value('i', 0)
    redraw_event = _mp.Event()

    def tag_redraw():
        while redraw_event.wait() and state.value != ABORT:
            print("--- tag_redraw: event")
            redraw_event.clear()
            e = engine()
            if e is not None:
                e.tag_redraw()
            del e

    redraw_thread = threading.Thread(target=tag_redraw)
    process = _mp.Process(target=_worker, args=(data, new_data, redraw_event, tiles, state))

    def stop():
        print(">>> stop (1): started")
        state.value = ABORT
        print(">>> stop (2): ABORT")
        new_data.put(None)
        print(">>> stop (2): data")
        redraw_event.set()
        print(">>> stop (3):", redraw_thread)
        redraw_thread.join()
        print(">>> stop (4):", redraw_thread)
        print(">>> stop (5):", process)
        process.join(5)
        print(">>> stop (6):", process)
        process.terminate()
        print(">>> stop (7):", process)

    def update(data):
        #state.value = UPDATE
        new_data.put(data)

    redraw_thread.start()
    process.start()

    return stop, _tile, update

if __name__ == "__main__":
    stop, tile, update = _main()
