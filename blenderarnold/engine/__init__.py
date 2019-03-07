# -*- coding: utf-8 -*-

__authors__ = "Tyler Furby, Jared Webber"

import os
import sys
import ctypes
import itertools
import collections
import numpy
import math
import time
import re
from contextlib import contextmanager
import traceback

import bpy
import bgl
from mathutils import Matrix, Vector, geometry

from . import polymesh as polymesh
from . import camera as cam
from . import lights as light
from . import options as options
from . import filters as filters

import arnold

def _export(data, depsgraph, camera, xres, yres, session=None):

    _CONVERTIBLETYPES = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}

    def _CleanNames(prefix, count):
        _RN = re.compile("[^-0-9A-Za-z_]")  # regex to cleanup names
        def fn(name):
            return "%s%d::%s" % (prefix, next(count), _RN.sub("_", name))
        return fn

    _Name = _CleanNames("O", itertools.count())
    
    for ob in bpy.data.objects:
        if ob.type in _CONVERTIBLETYPES:
            name = None

            if name is None:
                name = _Name(ob.name)

            mesh = polymesh._AiPolymesh(ob)
            with mesh:
                if mesh is not None:
                    mesh.export(name)

        elif ob.type == 'LIGHT':
            AiLight = light._AiLights(ob)
            AiLight.export()

    AiOptions = options._AiOptions(session, xres, yres)
    AiOptions.export()
    
    if camera:
        AiCamera = cam._AiCamera(camera, session, xres, yres)
        AiCamera.export()

    AiFilters = filters._AiFilters()
    AiFilters.export()
    

def update(engine, data, depsgraph):
    print("Arnold Engine Updating...")
    engine.use_highlight_tiles = True
    engine._session = {}
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    arnold.AiBegin()
    _export(data, depsgraph,
            engine.camera_override,
            engine.resolution_x,
            engine.resolution_y,
            session=engine._session)

def render(engine, depsgraph):
    try:
        session = engine._session
        xoff, yoff = session["offset"]

        _htiles = {}  # highlighted tiles
        session["peak"] = 0  # memory peak usage
        
        def display_callback(x, y, width, height, buffer, data):
            _x = x - xoff
            _y = y - yoff
            if buffer:
                try:
                    result = _htiles.pop((_x, _y), None)
                    if result is None:
                        result = engine.begin_result(_x, _y, width, height)
                    _buffer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_float))
                    rect = numpy.ctypeslib.as_array(_buffer, shape=(width * height, 4))
                    result.layers[0].passes[0].rect = rect
                    engine.end_result(result)

                    # HACK: Update Render Progress
                    display_callback.counter += 0.0020
                    engine.update_progress(display_callback.counter)
                
                finally:
                    arnold.AiFree(buffer)
            else:
                result = engine.begin_result(_x, engine.resolution_y - _y - height, width, height)
                _htiles[(_x, _y)] = result

            if engine.test_break():
                arnold.AiRenderAbort()
                while _htiles:
                    (_x, _y), result = _htiles.popitem()
                    engine.end_result(result, cancel=True)

            mem = session["mem"] = arnold.AiMsgUtilGetUsedMemory() / 1048576  # 1024*1024
            peak = session["peak"] = max(session["peak"], mem)
            engine.update_memory_stats(memory_used=mem, memory_peak=peak)

        # display callback must be a variable
        cb = arnold.AtDisplayCallBack(display_callback)
        arnold.AiNodeSetPtr(session["display"], "callback", cb)

        # HACK: Update Render Progress
        display_callback.counter = 0

        res = arnold.AiRender(arnold.AI_RENDER_MODE_CAMERA)
        if res != arnold.AI_SUCCESS:
            ipr = session.get("ipr")
            if ipr:
                options = arnold.AiUniverseGetOptions()
                for sl in range(*ipr):
                    arnold.AiNodeSetInt(options, "AA_samples", sl)
                    res = arnold.AiRender(arnold.AI_RENDER_MODE_CAMERA)
                    if res == arnold.AI_SUCCESS:
                        break
                    engine.update_stats("", "Mem: %.2fMb, SL: %d" % (session.get("mem", "NA"), sl))
        if res != arnold.AI_SUCCESS:
            engine.error_set("Render status: %d" % res)
    
    except:
        # cancel render on error
        engine.end_result(None, cancel=True)
    finally:
        del engine._session
        arnold.AiEnd()

