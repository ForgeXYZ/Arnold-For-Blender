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

import arnold

def _export(data, depsgraph, camera, xres, yres, session=None):

    _CONVERTIBLETYPES = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}

    _AiMatrix = lambda m: arnold.AtMatrix(*numpy.reshape(m.transposed(), -1))

    nodes = {} # {Object: AiNode}
    AiNodes = {}  # {Object.data: AiNode}

    #shaders = Shaders(data)

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

            modified = ob.is_modified(bpy.context.scene, 'RENDER')
            if not modified:
                AiNode = AiNodes.get(ob.data)
                if AiNode is not None:
                    node = arnold.AiNode("ginstance")
                    arnold.AiNodeSetStr(node, "name", name)
                    arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(ob.matrix_world))
                    arnold.AiNodeSetBool(node, "inherit_xform", False)
                    arnold.AiNodeSetPtr(node, "node", AiNode)
                    polymesh._export_object_properties(ob, node)
                    arnold.AiMsgDebug(b"    instance (%S)", ob.data.name)
                    continue

            mesh = polymesh._AiPolymesh(ob)
            with mesh:
                if mesh is not None:
                    node = mesh.export()
                    arnold.AiNodeSetStr(node, "name", name)
                    arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(ob.matrix_world))
                    polymesh._export_object_properties(ob, node)
                    if not modified:
                        # cache unmodified shapes for instancing
                        AiNodes[ob.data] = node
                    # cache for duplicators
                    nodes[ob] = node
    if camera:
        camera = cam._AiCamera(camera, session, xres, yres)

    # create a red standard surface shader
    shader1 = arnold.AiNode("standard_surface")
    arnold.AiNodeSetStr(shader1, "name", "myshader1")
    arnold.AiNodeSetRGB(shader1, "base_color", 1.0, 0.02, 0.02)
    arnold.AiNodeSetFlt(shader1, "specular", 0.05)

    # create a point light source
    light = arnold.AiNode("point_light")
    arnold.AiNodeSetStr(light, "name", "mylight")
    # position the light (alternatively use 'matrix')
    arnold.AiNodeSetVec(light, "position", 15.0, 30.0, 15.0)
    arnold.AiNodeSetFlt(light, "intensity", 4500.0) # alternatively, use 'exposure'
    arnold.AiNodeSetFlt(light, "radius", 4.0) # for soft shadows


    render = bpy.context.scene.render
    aspect_x = render.pixel_aspect_x
    aspect_y = render.pixel_aspect_y
    # offsets for border render
    xoff = 0
    yoff = 0

    opts = bpy.context.scene.arnold


    # get the global options node and set some options
    options = arnold.AiUniverseGetOptions()
    color_manager = arnold.AiNode("color_manager_ocio")
    arnold.AiNodeSetPtr(options, "color_manager", color_manager)
    arnold.AiNodeSetInt(options, "xres", xres)
    arnold.AiNodeSetInt(options, "yres", yres)
    arnold.AiNodeSetFlt(options, "aspect_ratio", aspect_y / aspect_x)
    if render.use_border:
        xoff = int(xres * render.border_min_x)
        yoff = int(yres * render.border_min_y)
        arnold.AiNodeSetInt(options, "region_min_x", xoff)
        arnold.AiNodeSetInt(options, "region_min_y", yoff)
        arnold.AiNodeSetInt(options, "region_max_x", int(xres * render.border_max_x) - 1)
        arnold.AiNodeSetInt(options, "region_max_y", int(yres * render.border_max_y) - 1)
    if not opts.lock_sampling_pattern:
        arnold.AiNodeSetInt(options, "AA_seed", bpy.context.scene.frame_current)
    if opts.clamp_sample_values:
        arnold.AiNodeSetFlt(options, "AA_sample_clamp", opts.AA_sample_clamp)
        arnold.AiNodeSetBool(options, "AA_sample_clamp_affects_aovs", opts.AA_sample_clamp_affects_aovs)
    if not opts.auto_threads:
        arnold.AiNodeSetInt(options, "threads", opts.threads)
    arnold.AiNodeSetStr(options, "thread_priority", opts.thread_priority)
    arnold.AiNodeSetStr(options, "pin_threads", opts.pin_threads)
    arnold.AiNodeSetBool(options, "abort_on_error", opts.abort_on_error)
    arnold.AiNodeSetBool(options, "abort_on_license_fail", opts.abort_on_license_fail)
    arnold.AiNodeSetBool(options, "skip_license_check", opts.skip_license_check)
    arnold.AiNodeSetRGB(options, "error_color_bad_texture", *opts.error_color_bad_texture)
    arnold.AiNodeSetRGB(options, "error_color_bad_pixel", *opts.error_color_bad_pixel)
    arnold.AiNodeSetRGB(options, "error_color_bad_shader", *opts.error_color_bad_shader)
    arnold.AiNodeSetInt(options, "bucket_size", opts.bucket_size)
    arnold.AiNodeSetStr(options, "bucket_scanning", opts.bucket_scanning)
    arnold.AiNodeSetBool(options, "ignore_textures", opts.ignore_textures)
    arnold.AiNodeSetBool(options, "ignore_shaders", opts.ignore_shaders)
    arnold.AiNodeSetBool(options, "ignore_atmosphere", opts.ignore_atmosphere)
    arnold.AiNodeSetBool(options, "ignore_lights", opts.ignore_lights)
    arnold.AiNodeSetBool(options, "ignore_shadows", opts.ignore_shadows)
    arnold.AiNodeSetBool(options, "ignore_subdivision", opts.ignore_subdivision)
    arnold.AiNodeSetBool(options, "ignore_displacement", opts.ignore_displacement)
    arnold.AiNodeSetBool(options, "ignore_bump", opts.ignore_bump)
    arnold.AiNodeSetBool(options, "ignore_motion_blur", opts.ignore_motion_blur)
    arnold.AiNodeSetBool(options, "ignore_dof", opts.ignore_dof)
    arnold.AiNodeSetBool(options, "ignore_smoothing", opts.ignore_smoothing)
    arnold.AiNodeSetBool(options, "ignore_sss", opts.ignore_sss)
    arnold.AiNodeSetInt(options, "auto_transparency_depth", opts.auto_transparency_depth)
    arnold.AiNodeSetInt(options, "texture_max_open_files", opts.texture_max_open_files)
    arnold.AiNodeSetFlt(options, "texture_max_memory_MB", opts.texture_max_memory_MB)
    arnold.AiNodeSetStr(options, "texture_searchpath", opts.texture_searchpath)
    arnold.AiNodeSetBool(options, "texture_automip", opts.texture_automip)
    arnold.AiNodeSetInt(options, "texture_autotile", opts.texture_autotile)
    arnold.AiNodeSetBool(options, "texture_accept_untiled", opts.texture_accept_untiled)
    arnold.AiNodeSetBool(options, "texture_accept_unmipped", opts.texture_accept_unmipped)
    arnold.AiNodeSetFlt(options, "low_light_threshold", opts.low_light_threshold)
    arnold.AiNodeSetInt(options, "GI_sss_samples", opts.GI_sss_samples)
    arnold.AiNodeSetBool(options, "sss_use_autobump", opts.sss_use_autobump)
    arnold.AiNodeSetInt(options, "GI_volume_samples", opts.GI_volume_samples)
    arnold.AiNodeSetByte(options, "max_subdivisions", opts.max_subdivisions)
    arnold.AiNodeSetStr(options, "procedural_searchpath", opts.procedural_searchpath)
    arnold.AiNodeSetStr(options, "plugin_searchpath", opts.plugin_searchpath)
    arnold.AiNodeSetInt(options, "GI_diffuse_depth", opts.GI_diffuse_depth)
    arnold.AiNodeSetInt(options, "GI_specular_depth", opts.GI_specular_depth)
    arnold.AiNodeSetInt(options, "GI_transmission_depth", opts.GI_transmission_depth)
    arnold.AiNodeSetInt(options, "GI_volume_depth", opts.GI_volume_depth)
    arnold.AiNodeSetInt(options, "GI_total_depth", opts.GI_total_depth)
    arnold.AiNodeSetInt(options, "GI_diffuse_samples", opts.GI_diffuse_samples)
    arnold.AiNodeSetInt(options, "GI_specular_samples", opts.GI_specular_samples)
    arnold.AiNodeSetInt(options, "GI_transmission_samples", opts.GI_transmission_samples)

    opts = bpy.context.scene.arnold
    arnold.AiMsgSetConsoleFlags(opts.get("console_log_flags", 0))
    arnold.AiMsgSetMaxWarnings(opts.max_warnings)
    arnold.AiMsgDebug(b"ARNOLD: >>>")

    plugins_path = os.path.normpath(os.path.join(os.path.dirname(__file__), os.path.pardir, "bin"))
    arnold.AiLoadPlugins(plugins_path)

    sft = opts.sample_filter_type
    filter = arnold.AiNode(sft)
    arnold.AiNodeSetStr(filter, "name", "__filter")
    if sft == 'blackman_harris_filter':
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_bh_width)
    elif sft == 'sinc_filter':
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_sinc_width)
    elif sft in {'cone_filter',
                 'cook_filter',
                 'disk_filter',
                 'gaussian_filter',
                 'triangle_filter',
                 'contour_filter'}:
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_width)
    elif sft == 'farthest_filter':
        arnold.AiNodeSetStr(filter, "domain", opts.sample_filter_domain)
    elif sft == 'heatmap_filter':
        arnold.AiNodeSetFlt(filter, "minumum", opts.sample_filter_min)
        arnold.AiNodeSetFlt(filter, "maximum", opts.sample_filter_max)
    elif sft == 'variance_filter':
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_width)
        arnold.AiNodeSetBool(filter, "scalar_mode", opts.sample_filter_scalar_mode)
        arnold.AiNodeSetStr(filter, "filter_weights", opts.sample_filter_weights)
    elif sft == 'cryptomatte_filter':
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_width)
        arnold.AiNodeSetInt(filter, "rank", opts.sample_filter_rank)
        arnold.AiNodeSetStr(filter, "filter", opts.cryptomatte_filter)
    elif sft == 'denoise_optix_filter':
        arnold.AiNodeSetFlt(filter, "blend", opts.optix_blend)
    elif sft == 'diff_filter':
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_width)
        arnold.AiNodeSetStr(filter, "filter_weights", opts.sample_filter_weights)
    
    # create an output driver node
    display = arnold.AiNode("driver_display_callback")
    arnold.AiNodeSetStr(display, "name", "__driver")
    outputs_aovs = ( str.encode(opts.aov_pass + "__driver"), )

    outputs = arnold.AiArray(len(outputs_aovs), 1, arnold.AI_TYPE_STRING, *outputs_aovs)
    arnold.AiNodeSetArray(options, "outputs", outputs)

    AA_samples = opts.AA_samples
    if session is not None:
        session["display"] = display
        xoff = 0
        yoff = 0
        session["offset"] = xoff, yoff
        # if opts.progressive_refinement:
        #     isl = opts.initial_sampling_level
        #     session["ipr"] = (isl, AA_samples + 1)
        #     AA_samples = isl
    arnold.AiNodeSetInt(options, "AA_samples", AA_samples)

    arnold.AiMsgDebug(b"ARNOLD DEBUG: <<<")

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

