# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import sys

ABORT = 1
UPDATE = 2


def ipr():
    import weakref
    from types import ModuleType

    code = __spec__.loader.get_code(__name__)

    def _exec(engine, data):
        _main = sys.modules["__main__"]
        try:
            mod = ModuleType("__main__")
            mod.__file__ = __file__

            mod.engine = weakref.ref(engine)
            mod.data = data

            sys.modules["__main__"] = mod
            exec(code, mod.__dict__)
        finally:
            sys.modules["__main__"] = _main
        return mod

    return _exec


def _worker(data, new_data, redraw_event, tiles, state):
    print("+++ _worker: started")

    import os
    import numpy
    import ctypes

    dir = os.path.dirname(__file__)
    if dir not in sys.path:
        sys.path.append(dir)

    import arnold

    nodes = {}
    links = []

    def _AiNodeSetArray(node, param, value):
        t, a = value
        _len = len(a)
        if t == arnold.AI_TYPE_POINT:
            _len //= 3
        elif t == arnold.AI_TYPE_UINT:
            pass
        _a = arnold.AiArrayConvert(_len, 1, t, ctypes.c_void_p(a.ctypes.data))
        arnold.AiNodeSetArray(node, param, _a)

    _AiNodeSet = {
        'NodeSocketShader': lambda n, i, v: True,
        'NodeSocketBool': lambda n, i, v: arnold.AiNodeSetBool(n, i, v),
        'NodeSocketInt': lambda n, i, v: arnold.AiNodeSetInt(n, i, v),
        'NodeSocketFloat': lambda n, i, v: arnold.AiNodeSetFlt(n, i, v),
        'NodeSocketColor': lambda n, i, v: arnold.AiNodeSetRGBA(n, i, *v),
        'NodeSocketVector': lambda n, i, v: arnold.AiNodeSetVec(n, i, *v),
        'NodeSocketVectorXYZ': lambda n, i, v: arnold.AiNodeSetPnt(n, i, *v),
        'NodeSocketString': lambda n, i, v: arnold.AiNodeSetStr(n, i, v),
        'ArnoldNodeSocketColor': lambda n, i, v: arnold.AiNodeSetRGB(n, i, *v),
        'ArnoldNodeSocketByte': lambda n, i, v: arnold.AiNodeSetByte(n, i, v),
        'ArnoldNodeSocketProperty': lambda n, i, v: True,
        'BOOL': lambda n, p, v: arnold.AiNodeSetBool(n, p, v),
        'BYTE': lambda n, p, v: arnold.AiNodeSetByte(n, p, v),
        'INT': lambda n, p, v: arnold.AiNodeSetInt(n, p, v),
        'FLOAT': lambda n, p, v: arnold.AiNodeSetFlt(n, p, v),
        'POINT2': lambda n, p, v: arnold.AiNodeSetPnt2(n, p, *v),
        'RGB': lambda n, p, v: arnold.AiNodeSetRGB(n, p, *v),
        'RGBA': lambda n, p, v: arnold.AiNodeSetRGBA(n, p, *v),
        'VECTOR': lambda n, p, v: arnold.AiNodeSetVec(n, p, *v),
        'STRING': lambda n, p, v: arnold.AiNodeSetStr(n, p, v),
        'NODE': lambda n, p, v: arnold.AiNodeSetPtr(n, p, nodes[v]),
        'MATRIX': lambda n, p, v: arnold.AiNodeSetMatrix(n, p, arnold.AtMatrix(*v)),
        'ARRAY': _AiNodeSetArray,
        'LINK': lambda n, p, v: links.append((n, p, v)),
    }

    arnold.AiBegin()
    try:
        #arnold.AiMsgSetConsoleFlags(arnold.AI_LOG_ALL)
        #arnold.AiMsgSetConsoleFlags(0x000E)

        #from pprint import pprint as pp
        #pp(data)

        for ntype, params in data['nodes']:
            node = arnold.AiNode(ntype)
            for n, (t, v) in params.items():
                _AiNodeSet[t](node, n, v)
            nodes[params['name'][1]] = node

        options = arnold.AiUniverseGetOptions()
        for n, (t, v) in data['options'].items():
            _AiNodeSet[t](options, n, v)

        for n, p, v in links:
            arnold.AiNodeLink(nodes[v], p, n)

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

        _width = data['options']['xres'][1]
        _height = data['options']['yres'][1]
        _tiles = numpy.asarray(tiles).reshape([_height, _width, 4])

        def _callback(x, y, width, height, buffer, data):
            #print("+++ _callback:", x, y, width, height, ctypes.cast(buffer, ctypes.c_void_p))
            if buffer:
                try:
                    if not state.value and new_data.empty():
                        _buffer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_float))
                        tile = numpy.ctypeslib.as_array(_buffer, shape=(height, width, 4))
                        _tiles[y : y + height, x : x + width] = tile
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
            for sl in range(-3, 1):
                arnold.AiNodeSetInt(options, "AA_samples", sl)
                res = arnold.AiRender(arnold.AI_RENDER_MODE_CAMERA)
                if res != arnold.AI_SUCCESS:
                    break

            while True:
                try:
                    _data = new_data.get(timeout=1)
                    #print(">>> worker: data")
                    if new_data.empty():
                        if _data is not None:
                            for name, params in _data['nodes'].items():
                                node = arnold.AiNodeLookUpByName(name)
                                for n, (t, v) in params.items():
                                    _AiNodeSet[t](node, n, v)
                        break
                except:
                    #print("+++ worker: data empty")
                    pass
    finally:
        arnold.AiEnd()
    print("+++ _worker: finished")


def _main():
    import threading
    import multiprocessing as _mp

    import bpy
    _mp.set_executable(bpy.app.binary_path_python)

    width = data['options']['xres'][1]
    height = data['options']['yres'][1]

    state = _mp.Value('i', 0)
    redraw_event = _mp.Event()
    tiles = _mp.sharedctypes.RawArray('f', width * height * 4)
    new_data = _mp.Queue()

    def tag_redraw():
        while redraw_event.wait() and state.value != ABORT:
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
        new_data.close()
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

    return stop, tiles, update


if __name__ == "__main__":
    stop, tiles, update = _main()
    del data
