import os
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


class _AiOptions():
    def __init__(self, session, xres, yres):
        # Get the global options node
        self._options = arnold.AiUniverseGetOptions()

        self._session = session

        self._xres = xres
        self._yres = yres

    def export(self):
        render = bpy.context.scene.render
        # offsets for border render
        xoff = 0
        yoff = 0
        opts = bpy.context.scene.arnold

        #...and set some options
        color_manager = arnold.AiNode("color_manager_ocio")
        arnold.AiNodeSetPtr(self._options, "color_manager", color_manager)
        arnold.AiNodeSetInt(self._options, "xres", self._xres)
        arnold.AiNodeSetInt(self._options, "yres", self._yres)

        if render.use_border:
            xoff = int(self._xres * render.border_min_x)
            yoff = int(self._yres * render.border_min_y)
            arnold.AiNodeSetInt(self._options, "region_min_x", xoff)
            arnold.AiNodeSetInt(self._options, "region_min_y", yoff)
            arnold.AiNodeSetInt(self._options, "region_max_x", int(self._xres * render.border_max_x) - 1)
            arnold.AiNodeSetInt(self._options, "region_max_y", int(self._yres * render.border_max_y) - 1)
        if not opts.lock_sampling_pattern:
            arnold.AiNodeSetInt(self._options, "AA_seed", bpy.context.scene.frame_current)
        if opts.clamp_sample_values:
            arnold.AiNodeSetFlt(self._options, "AA_sample_clamp", opts.AA_sample_clamp)
            arnold.AiNodeSetBool(self._options, "AA_sample_clamp_affects_aovs", opts.AA_sample_clamp_affects_aovs)
        if not opts.auto_threads:
            arnold.AiNodeSetInt(self._options, "threads", opts.threads)
        arnold.AiNodeSetStr(self._options, "thread_priority", opts.thread_priority)
        arnold.AiNodeSetStr(self._options, "pin_threads", opts.pin_threads)
        arnold.AiNodeSetBool(self._options, "abort_on_error", opts.abort_on_error)
        arnold.AiNodeSetBool(self._options, "abort_on_license_fail", opts.abort_on_license_fail)
        arnold.AiNodeSetBool(self._options, "skip_license_check", opts.skip_license_check)
        arnold.AiNodeSetRGB(self._options, "error_color_bad_texture", *opts.error_color_bad_texture)
        arnold.AiNodeSetRGB(self._options, "error_color_bad_pixel", *opts.error_color_bad_pixel)
        arnold.AiNodeSetRGB(self._options, "error_color_bad_shader", *opts.error_color_bad_shader)
        arnold.AiNodeSetInt(self._options, "bucket_size", opts.bucket_size)
        arnold.AiNodeSetStr(self._options, "bucket_scanning", opts.bucket_scanning)
        arnold.AiNodeSetBool(self._options, "ignore_textures", opts.ignore_textures)
        arnold.AiNodeSetBool(self._options, "ignore_shaders", opts.ignore_shaders)
        arnold.AiNodeSetBool(self._options, "ignore_atmosphere", opts.ignore_atmosphere)
        arnold.AiNodeSetBool(self._options, "ignore_lights", opts.ignore_lights)
        arnold.AiNodeSetBool(self._options, "ignore_shadows", opts.ignore_shadows)
        arnold.AiNodeSetBool(self._options, "ignore_subdivision", opts.ignore_subdivision)
        arnold.AiNodeSetBool(self._options, "ignore_displacement", opts.ignore_displacement)
        arnold.AiNodeSetBool(self._options, "ignore_bump", opts.ignore_bump)
        arnold.AiNodeSetBool(self._options, "ignore_motion_blur", opts.ignore_motion_blur)
        arnold.AiNodeSetBool(self._options, "ignore_dof", opts.ignore_dof)
        arnold.AiNodeSetBool(self._options, "ignore_smoothing", opts.ignore_smoothing)
        arnold.AiNodeSetBool(self._options, "ignore_sss", opts.ignore_sss)
        arnold.AiNodeSetInt(self._options, "auto_transparency_depth", opts.auto_transparency_depth)
        arnold.AiNodeSetInt(self._options, "texture_max_open_files", opts.texture_max_open_files)
        arnold.AiNodeSetFlt(self._options, "texture_max_memory_MB", opts.texture_max_memory_MB)
        arnold.AiNodeSetStr(self._options, "texture_searchpath", opts.texture_searchpath)
        arnold.AiNodeSetBool(self._options, "texture_automip", opts.texture_automip)
        arnold.AiNodeSetInt(self._options, "texture_autotile", opts.texture_autotile)
        arnold.AiNodeSetBool(self._options, "texture_accept_untiled", opts.texture_accept_untiled)
        arnold.AiNodeSetBool(self._options, "texture_accept_unmipped", opts.texture_accept_unmipped)
        arnold.AiNodeSetFlt(self._options, "low_light_threshold", opts.low_light_threshold)
        arnold.AiNodeSetInt(self._options, "GI_sss_samples", opts.GI_sss_samples)
        arnold.AiNodeSetBool(self._options, "sss_use_autobump", opts.sss_use_autobump)
        arnold.AiNodeSetInt(self._options, "GI_volume_samples", opts.GI_volume_samples)
        arnold.AiNodeSetByte(self._options, "max_subdivisions", opts.max_subdivisions)
        arnold.AiNodeSetStr(self._options, "procedural_searchpath", opts.procedural_searchpath)
        arnold.AiNodeSetStr(self._options, "plugin_searchpath", opts.plugin_searchpath)
        arnold.AiNodeSetInt(self._options, "GI_diffuse_depth", opts.GI_diffuse_depth)
        arnold.AiNodeSetInt(self._options, "GI_specular_depth", opts.GI_specular_depth)
        arnold.AiNodeSetInt(self._options, "GI_transmission_depth", opts.GI_transmission_depth)
        arnold.AiNodeSetInt(self._options, "GI_volume_depth", opts.GI_volume_depth)
        arnold.AiNodeSetInt(self._options, "GI_total_depth", opts.GI_total_depth)
        arnold.AiNodeSetInt(self._options, "GI_diffuse_samples", opts.GI_diffuse_samples)
        arnold.AiNodeSetInt(self._options, "GI_specular_samples", opts.GI_specular_samples)
        arnold.AiNodeSetInt(self._options, "GI_transmission_samples", opts.GI_transmission_samples)

        # create an output driver node
        display = arnold.AiNode("driver_display_callback")
        arnold.AiNodeSetStr(display, "name", "__driver")
        outputs_aovs = ( str.encode(opts.aov_pass + "__driver"), )

        outputs = arnold.AiArray(len(outputs_aovs), 1, arnold.AI_TYPE_STRING, *outputs_aovs)
        arnold.AiNodeSetArray(self._options, "outputs", outputs)

        AA_samples = opts.AA_samples
        if self._session is not None:
            self._session["display"] = display
            self._session["offset"] = xoff, yoff
            if opts.progressive_refinement:
                isl = opts.initial_sampling_level
                self._session["ipr"] = (isl, AA_samples + 1)
                AA_samples = isl
        arnold.AiNodeSetInt(self._options, "AA_samples", AA_samples)

        opts = bpy.context.scene.arnold
        arnold.AiMsgSetConsoleFlags(opts.get("console_log_flags", 0))
        arnold.AiMsgSetMaxWarnings(opts.max_warnings)
        arnold.AiMsgDebug(b"ARNOLD: >>>")

        plugins_path = os.path.normpath(os.path.join(os.path.dirname(__file__), os.path.pardir, "bin"))
        arnold.AiLoadPlugins(plugins_path)
