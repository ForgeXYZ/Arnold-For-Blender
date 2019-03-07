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


class _AiLights():
    def __init__(self, light):
        self._bpy_light = light

        self._lamp = light.data
        self._light = self._lamp.arnold
        self._matrix = light.matrix_world.copy()

    def export(self):
        if self._lamp.type == 'POINT':
                node = arnold.AiNode("point_light")
                arnold.AiNodeSetFlt(node, "radius", self._light.radius)
                arnold.AiNodeSetStr(node, "decay_type", self._light.decay_type)
                arnold.AiMsgDebug(b"    point_light")
        elif self._lamp.type == 'SUN':
            node = arnold.AiNode("distant_light")
            arnold.AiNodeSetFlt(node, "angle", self._light.angle)
            arnold.AiMsgDebug(b"    distant_light")
        elif self._lamp.type == 'SPOT':
            node = arnold.AiNode("spot_light")
            arnold.AiNodeSetFlt(node, "radius", self._light.radius)
            arnold.AiNodeSetFlt(node, "lens_radius", self._light.lens_radius)
            arnold.AiNodeSetFlt(node, "cone_angle", math.degrees(self._lamp.spot_size))
            arnold.AiNodeSetFlt(node, "penumbra_angle", self._light.penumbra_angle)
            arnold.AiNodeSetFlt(node, "aspect_ratio", self._light.aspect_ratio)
            arnold.AiNodeSetStr(node, "decay_type", self._light.decay_type)
            arnold.AiMsgDebug(b"    spot_light")
        elif self._lamp.type == 'HEMI':
            node = arnold.AiNode("skydome_light")
            arnold.AiNodeSetInt(node, "resolution", self._light.resolution)
            arnold.AiNodeSetStr(node, "format", self._light.format)
            arnold.AiMsgDebug(b"    skydome_light")
        elif self._lamp.type == 'AREA':
            node = arnold.AiNode(self._light.type)
            if self._light.type == 'cylinder_light':
                top = arnold.AiArray(1, 1, arnold.AI_TYPE_VECTOR, arnold.AtVector(0, self._lamp.size_y / 2, 0))
                arnold.AiNodeSetArray(node, "top", top)
                bottom = arnold.AiArray(1, 1, arnold.AI_TYPE_VECTOR, arnold.AtVector(0, -self._lamp.size_y / 2, 0))
                arnold.AiNodeSetArray(node, "bottom", bottom)
                arnold.AiNodeSetFlt(node, "radius", self._lamp.size / 2)
                arnold.AiNodeSetStr(node, "decay_type", self._light.decay_type)
            elif self._light.type == 'disk_light':
                arnold.AiNodeSetFlt(node, "radius", self._lamp.size / 2)
                #arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
            elif self._light.type == 'quad_light':
                x = self._lamp.size / 2
                y = self._lamp.size_y / 2 if self._lamp.shape == 'RECTANGLE' else x
                verts = arnold.AiArrayAllocate(4, 1, arnold.AI_TYPE_VECTOR)
                arnold.AiArraySetVec(verts, 0, arnold.AtVector(-x, -y, 0))
                arnold.AiArraySetVec(verts, 1, arnold.AtVector(-x, y, 0))
                arnold.AiArraySetVec(verts, 2, arnold.AtVector(x, y, 0))
                arnold.AiArraySetVec(verts, 3, arnold.AtVector(x, -y, 0))
                arnold.AiNodeSetArray(node, "vertices", verts)
                arnold.AiNodeSetInt(node, "resolution", self._light.quad_resolution)
                #arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
            elif self._light.type == 'photometric_light':
                arnold.AiNodeSetStr(node, "filename", bpy.path.abspath(self._light.filename))
                _MR = Matrix.Rotation(math.radians(90.0), 4, 'X')
                matrix = matrix @ _MR
            elif self._light.type == 'mesh_light':
                arnold.AiNodeSetStr(node, "decay_type", self._light.decay_type)
                if self._light.mesh:
                    mesh_lights = []
                    mesh_lights.append((node, self._light.mesh))
        else:
            arnold.AiMsgDebug(b"    skip (unsupported)")

        _RN = re.compile("[^-0-9A-Za-z_]")

        def _CleanNames(prefix, count):
            def fn(name):
                return "%s%d::%s" % (prefix, next(count), _RN.sub("_", name))
            return fn

        _Name = _CleanNames("O", itertools.count())
        name = _Name(self._bpy_light.name)
        arnold.AiNodeSetStr(node, "name", name)

        _AiMatrix = lambda m: arnold.AtMatrix(*numpy.reshape(m.transposed(), -1))

        color_node = None

        # TODO: Lamp Nodes
        # if lamp.use_nodes:
        #     filter_nodes = []
        #     for _node in lamp.node_tree.nodes:
        #         if isinstance(_node, nt.ArnoldNodeLightOutput) and _node.is_active:
        #             for input in _node.inputs:
        #                 if input.is_linked:
        #                     _node = _AiNode(input.links[0].from_node, name, lamp_nodes)
        #                     if input.identifier == "color":
        #                         color_node = _node
        #                     elif input.bl_idname == "ArnoldNodeSocketFilter":
        #                         filter_nodes.append(_node)
        #             break
        #     if filter_nodes:
        #         filters = arnold.AiArray(len(filter_nodes), 1, arnold.AI_TYPE_NODE, *filter_nodes)
        #         arnold.AiNodeSetArray(node, "filters", filters)

        if color_node is None:
            arnold.AiNodeSetRGB(node, "color", *self._lamp.color)
        else:
            arnold.AiNodeLink(color_node, "color", node)
        arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(self._matrix))
        arnold.AiNodeSetFlt(node, "intensity", self._light.intensity)
        arnold.AiNodeSetFlt(node, "exposure", self._light.exposure)
        arnold.AiNodeSetBool(node, "cast_shadows", self._light.cast_shadows)
        arnold.AiNodeSetBool(node, "cast_volumetric_shadows", self._light.cast_volumetric_shadows)
        arnold.AiNodeSetFlt(node, "shadow_density", self._light.shadow_density)
        arnold.AiNodeSetRGB(node, "shadow_color", *self._light.shadow_color)
        arnold.AiNodeSetInt(node, "samples", self._light.samples)
        arnold.AiNodeSetBool(node, "normalize", self._light.normalize)
        #arnold.AiNodeSetBool(node, "affect_diffuse", light.affect_diffuse)
        # arnold.AiNodeSetBool(node, "affect_specular", light.affect_specular)
        # arnold.AiNodeSetBool(node, "affect_volumetrics", light.affect_volumetrics)
        arnold.AiNodeSetFlt(node, "diffuse", self._light.diffuse)
        arnold.AiNodeSetFlt(node, "specular", self._light.specular)
        arnold.AiNodeSetFlt(node, "sss", self._light.sss)
        arnold.AiNodeSetFlt(node, "indirect", self._light.indirect)
        arnold.AiNodeSetInt(node, "max_bounces", self._light.max_bounces)
        arnold.AiNodeSetInt(node, "volume_samples", self._light.volume_samples)
        arnold.AiNodeSetFlt(node, "volume", self._light.volume)