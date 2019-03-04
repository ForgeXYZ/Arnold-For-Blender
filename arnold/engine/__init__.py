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

import arnold

def _export(data, depsgraph, camera, xres, yres, session=None):
    arnold.AiBegin()
    arnold.AiMsgSetLogFileName("scene1.log")
    arnold.AiMsgSetConsoleFlags(arnold.AI_LOG_ALL)

    # create a sphere geometric primitive
    sph = arnold.AiNode("sphere")
    arnold.AiNodeSetStr(sph, "name", "mysphere")
    arnold.AiNodeSetVec(sph, "center", 0.0, 4.0, 0.0)
    arnold.AiNodeSetFlt(sph, "radius", 4.0)

    # create a polymesh, with UV coordinates
    # AtNode *mesh = AiNode("polymesh");
    # mesh = AiNode("polymesh")
    # AiNodeSetStr(mesh, "name", "mymesh");
    # AtArray* nsides_array = AiArray(1, 1, AI_TYPE_UINT, 4);
    # AiNodeSetArray(mesh, "nsides", nsides_array);
    # AtArray* vlist_array = AiArray(12, 1, AI_TYPE_FLOAT, -10.f, 0.f, 10.f, 10.f, 0.f, 10.f, -10.f, 0.f, -10.f, 10.f, 0.f, -10.f);
    # AiNodeSetArray(mesh, "vlist", vlist_array);
    # AtArray* vidxs_array = AiArray(4, 1, AI_TYPE_UINT, 0, 1, 3, 2);
    # AiNodeSetArray(mesh, "vidxs", vidxs_array);
    # AtArray* uvlist_array = AiArray(8, 1, AI_TYPE_FLOAT, 0.f, 0.f, 1.f, 0.f, 1.f, 1.f, 0.f, 1.f);
    # AiNodeSetArray(mesh, "uvlist", uvlist_array);
    # AtArray* uvidxs_array = AiArray(4, 1, AI_TYPE_UINT, 0, 1, 2, 3);
    # AiNodeSetArray(mesh, "uvidxs", uvidxs_array);

    # create a red standard surface shader
    shader1 = arnold.AiNode("standard_surface")
    arnold.AiNodeSetStr(shader1, "name", "myshader1")
    arnold.AiNodeSetRGB(shader1, "base_color", 1.0, 0.02, 0.02)
    arnold.AiNodeSetFlt(shader1, "specular", 0.05)

    # create a textured standard surface shader
    shader2 = arnold.AiNode("standard_surface")
    arnold.AiNodeSetStr(shader2, "name", "myshader2")
    arnold.AiNodeSetRGB(shader2, "base_color", 1.0, 0.0, 0.0)

    # create an image shader for texture mapping
    # AtNode *image = AiNode("image");
    # AiNodeSetStr(image, "name", "myimage");
    # AiNodeSetStr(image, "filename", "solidangle_icon.png");
    # AiNodeSetFlt(image, "sscale", 4.f);
    # AiNodeSetFlt(image, "tscale", 4.f);
    # link the output of the image shader to the color input of the surface shader
    # AiNodeLink(image, "base_color", shader2);

    # assign the shaders to the geometric objects
    arnold.AiNodeSetPtr(sph, "shader", shader1)
    # AiNodeSetPtr(mesh, "shader", shader2);

    # create a perspective camera
    camera = arnold.AiNode("persp_camera")
    arnold.AiNodeSetStr(camera, "name", "mycamera")
    # position the camera (alternatively you can set 'matrix')
    arnold.AiNodeSetVec(camera, "position", 0.0, 10.0, 35.0)
    arnold.AiNodeSetVec(camera, "look_at", 0.0, 3.0, 0.0)
    arnold.AiNodeSetFlt(camera, "fov", 45.0)

    # create a point light source
    light = arnold.AiNode("point_light")
    arnold.AiNodeSetStr(light, "name", "mylight")
    # position the light (alternatively use 'matrix')
    arnold.AiNodeSetVec(light, "position", 15.0, 30.0, 15.0)
    arnold.AiNodeSetFlt(light, "intensity", 4500.0) # alternatively, use 'exposure'
    arnold.AiNodeSetFlt(light, "radius", 4.0) # for soft shadows
    # get the global options node and set some options
    options = arnold.AiUniverseGetOptions()
    arnold.AiNodeSetInt(options, "AA_samples", 8)
    arnold.AiNodeSetInt(options, "xres", 480)
    arnold.AiNodeSetInt(options, "yres", 360)
    arnold.AiNodeSetInt(options, "GI_diffuse_depth", 4)
    # set the active camera (optional, since there is only one camera)
    arnold.AiNodeSetPtr(options, "camera", camera)

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

        res = arnold.AiRender(AI_RENDER_MODE_CAMERA)
        if res != AI_SUCCESS:
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

