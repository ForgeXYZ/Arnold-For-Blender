import ctypes
import itertools
import collections
import numpy
import math
import time
import re
from contextlib import contextmanager
import traceback
import contextlib as cl

import bpy
import bgl
from mathutils import Matrix, Vector, geometry

import arnold


class _AiCamera():
    def __init__(self, camera, session, xres, yres):
        _RN = re.compile("[^-0-9A-Za-z_]") 
        self._name = "C::" + _RN.sub("_", camera.name)
        self._mw = camera.matrix_world
        self._cdata = camera.data
        self._cp = self._cdata.arnold
        #print(camera.location.x)
        self._camera_type = self._cp.camera_type

        self._session = session

        self._xres = xres
        self._yres = yres

        #self._bpy_camera = camera
        self.node = arnold.AiNode(self._camera_type)

    def export(self):
        _AiMatrix = lambda m: arnold.AtMatrix(*numpy.reshape(m.transposed(), -1))

        arnold.AiNodeSetStr(self.node, "name", self._name)
        arnold.AiNodeSetMatrix(self.node, "matrix", _AiMatrix(self._mw))

        render = bpy.context.scene.render
        aspect_x = render.pixel_aspect_x
        aspect_y = render.pixel_aspect_y

        if self._cdata.sensor_fit == 'VERTICAL':
            sw = self._cdata.sensor_height * self._xres / self._yres * aspect_x / aspect_y
        else:
            sw = self._cdata.sensor_width
            if self._cdata.sensor_fit == 'AUTO':
                x = self._xres * aspect_x
                y = self._xres * aspect_y
                if x < y:
                    sw *= x / y
        fov = math.degrees(2 * math.atan(sw / (2 * self._cdata.lens)))
        arnold.AiNodeSetFlt(self.node, "fov", fov)
        if self._cdata.dof_object:
            dof = geometry.distance_point_to_plane(
                self._mw.to_translation(),
                self._cdata.dof_object.matrix_world.to_translation(),
                self._mw.col[2][:3]
            )
        else:
           dof = self._cdata.dof_distance
        arnold.AiNodeSetFlt(self.node, "focus_distance", dof)
        if self._cp.enable_dof:
            arnold.AiNodeSetFlt(self.node, "aperture_size", self._cp.aperture_size)
            arnold.AiNodeSetInt(self.node, "aperture_blades", self._cp.aperture_blades)
            arnold.AiNodeSetFlt(self.node, "aperture_rotation", self._cp.aperture_rotation)
            arnold.AiNodeSetFlt(self.node, "aperture_blade_curvature", self._cp.aperture_blade_curvature)
            arnold.AiNodeSetFlt(self.node, "aperture_aspect_ratio", self._cp.aperture_aspect_ratio)
        arnold.AiNodeSetFlt(self.node, "near_clip", self._cdata.clip_start)
        arnold.AiNodeSetFlt(self.node, "far_clip", self._cdata.clip_end)
        arnold.AiNodeSetFlt(self.node, "shutter_start", self._cp.shutter_start)
        arnold.AiNodeSetFlt(self.node, "shutter_end", self._cp.shutter_end)
        arnold.AiNodeSetStr(self.node, "shutter_type", self._cp.shutter_type)
        arnold.AiNodeSetStr(self.node, "rolling_shutter", self._cp.rolling_shutter)
        arnold.AiNodeSetFlt(self.node, "rolling_shutter_duration", self._cp.rolling_shutter_duration)
        # TODO: camera shift
        if self._session is not None:
            arnold.AiNodeSetVec2(self.node, "screen_window_min", -1, -1)
            arnold.AiNodeSetVec2(self.node, "screen_window_max", 1, 1)
        arnold.AiNodeSetFlt(self.node, "exposure", self._cp.exposure)
        options = arnold.AiUniverseGetOptions()
        arnold.AiNodeSetPtr(options, "camera", self.node)