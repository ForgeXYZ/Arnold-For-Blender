# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import os
import sys
import ctypes
import numpy
import math

from mathutils import Matrix, Vector
from . import arnold


_AiNodeSet = {
    "NodeSocketFloat": lambda n, i, v: arnold.AiNodeSetFlt(n, i, v),
    "NodeSocketColor": lambda n, i, v: arnold.AiNodeSetRGB(n, i, *v[:3])
}


class Shaders:
    def __init__(self):
        self._shaders = {}
        self._default = None  # default shader, if used
        self._textures = {}

    def get(self, mesh):
        if not mesh.materials:
            return None, None

        idxs = []  # material indices
        shaders = []  # used shaders
        default = -1  # default shader index, if used

        midxs = {}
        for p in mesh.polygons:
            mi = p.material_index
            idx = midxs.get(mi)
            if idx is None:
                mat = mesh.materials[mi]
                if mat:
                    node = self._shaders.get(mat)
                    if node is None:
                        node = self._export(mat)
                        if node is None:
                            node = self.default
                            if default < 0:
                                idx = default = len(shaders)
                            else:
                                idx = default
                        else:
                            idx = len(shaders)
                        self._shaders[mat] = node
                        shaders.append(node)
                    else:
                        try:
                            idx = shaders.index(node)
                        except ValueError:
                            idx = len(shaders)
                            shaders.append(node)
                elif default < 0:
                    idx = default = len(shaders)
                    shaders.append(self.default)
                else:
                    idx = default
                midxs[mi] = idx
            idxs.append(idx)

        return idxs, shaders

    @property
    def default(self):
        node = self._default
        if node is None:
            node = arnold.AiNode('utility')
            arnold.AiNodeSetStr(node, "name", "__default")
            self._default = node
        return node

    def _export(self, mat):
        node = None

        if mat.use_nodes:
            from .. import nodes

            for _node in mat.node_tree.nodes:
                if type(_node) is nodes.ArnoldOutputNode and _node.is_active:
                    input = _node.inputs[0]
                    if input.is_linked:
                        _node = input.links[0].from_node
                        if isinstance(_node, nodes.ArnoldShader):
                            break
                    return None
            else:
                return None
            node = arnold.AiNode(_node.AI_NAME)
            arnold.AiNodeSetStr(node, "name", "%s:%s" % (mat.name, _node.name))
            for input in _node.inputs:
                if input.is_linked:
                    pass
                else:
                    _AiNodeSet[input.bl_idname](node, input.identifier, input.default_value)
            return node

        shader = mat.arnold
        if mat.type == 'SURFACE':
            if shader.type == 'LAMBERT':
                node = arnold.AiNode('lambert')
                arnold.AiNodeSetFlt(node, "Kd", mat.diffuse_intensity)
                arnold.AiNodeSetRGB(node, "Kd_color", *mat.diffuse_color)
                arnold.AiNodeSetRGB(node, "opacity", *shader.opacity)
            elif shader.type == 'STANDARD':
                standard = shader.standard
                node = arnold.AiNode('standard')
                arnold.AiNodeSetFlt(node, "Kd", mat.diffuse_intensity)
                arnold.AiNodeSetRGB(node, "Kd_color", *mat.diffuse_color)
                arnold.AiNodeSetFlt(node, "diffuse_roughness", standard.diffuse_roughness)
                arnold.AiNodeSetFlt(node, "Ks", standard.ks)
                arnold.AiNodeSetRGB(node, "Ks_color", *standard.ks_color)
                arnold.AiNodeSetFlt(node, "specular_roughness", standard.specular_roughness)
                arnold.AiNodeSetFlt(node, "specular_anisotropy", standard.specular_anisotropy)
                arnold.AiNodeSetFlt(node, "specular_rotation", standard.specular_rotation)
            elif shader.type == 'UTILITY':
                utility = shader.utility
                node = arnold.AiNode('utility')
                arnold.AiNodeSetRGB(node, "color", *mat.diffuse_color)
                arnold.AiNodeSetFlt(node, "opacity", utility.opacity)
            else:
                return None
        elif mat.type == 'WIRE':
            wire = shader.wire
            node = arnold.AiNode('wireframe')
            arnold.AiNodeSetStr(node, "edge_type", wire.edge_type)
            arnold.AiNodeSetRGB(node, "line_color", *mat.diffuse_color)
            arnold.AiNodeSetRGB(node, "fill_color", *wire.fill_color)
            arnold.AiNodeSetFlt(node, "line_width", wire.line_width)
            arnold.AiNodeSetBool(node, "raster_space", wire.raster_space)
        else:
            return None
        arnold.AiNodeSetStr(node, "name", mat.name)
        self._images(mat)
        return node

    def _images(self, mat):
        for slot in mat.texture_slots:
            if slot and slot.use:
                tex = slot.texture
                node = arnold.AiNode('image')
                arnold.AiNodeSetStr(node, "name", tex.image.name)
                arnold.AiNodeSetStr(node, "filename", tex.image.filepath_from_user())


def _amatrix(m):
    """
    m: mathutils.Matrix
    returns: pointer to AtArray
    """
    t = (v for r in m.transposed() for v in r)
    matrix = arnold.AiArrayAllocate(1, 1, arnold.AI_TYPE_MATRIX)
    arnold.AiArraySetMtx(matrix, 0, arnold.AtMatrix(*t))
    return matrix


def export(data, scene, camera, xres, yres, session=None, ass_filepath=None):
    shaders = Shaders()

    opts = scene.arnold

    arnold.AiBegin()
    arnold.AiMsgSetConsoleFlags(opts.get("console_log_flags", 0))

    for ob in scene.objects:
        if ob.hide_render:
            continue
        
        if ob.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            mesh = ob.to_mesh(scene, True, 'RENDER', False)
            try:
                mesh.calc_normals_split()
                # No need to call mesh.free_normals_split later, as this mesh is deleted anyway!
                node = arnold.AiNode('polymesh')
                arnold.AiNodeSetStr(node, "name", ob.name)
                arnold.AiNodeSetBool(node, "smoothing", True)
                arnold.AiNodeSetArray(node, "matrix", _amatrix(ob.matrix_world))
                # vertices
                vlist = arnold.AiArrayAllocate(len(mesh.vertices), 1, arnold.AI_TYPE_POINT)
                for i, v in enumerate(mesh.vertices):
                    arnold.AiArraySetPnt(vlist, i, arnold.AtPoint(*v.co))
                arnold.AiNodeSetArray(node, "vlist", vlist)
                # normals
                nlist = arnold.AiArrayAllocate(len(mesh.loops), 1, arnold.AI_TYPE_VECTOR)
                for i, n in enumerate(mesh.loops):
                    arnold.AiArraySetVec(nlist, i, arnold.AtVector(*n.normal))
                arnold.AiNodeSetArray(node, "nlist", nlist)
                # polygons
                count = 0
                nsides = arnold.AiArrayAllocate(len(mesh.polygons), 1, arnold.AI_TYPE_UINT)
                vidxs = arnold.AiArrayAllocate(len(mesh.loops), 1, arnold.AI_TYPE_UINT)
                nidxs = arnold.AiArrayAllocate(len(mesh.loops), 1, arnold.AI_TYPE_UINT)
                for i, p in enumerate(mesh.polygons):
                    arnold.AiArraySetUInt(nsides, i, len(p.loop_indices))
                    for j in p.loop_indices:
                        arnold.AiArraySetUInt(vidxs, count, mesh.loops[j].vertex_index)
                        arnold.AiArraySetUInt(nidxs, count, j)
                        count += 1
                arnold.AiNodeSetArray(node, "nsides", nsides)
                arnold.AiNodeSetArray(node, "vidxs", vidxs)
                arnold.AiNodeSetArray(node, "nidxs", nidxs)
                # uv
                for i, uvt in enumerate(mesh.uv_textures):
                    if uvt.active_render:
                        uvd = mesh.uv_layers[i].data
                        uvidxs = arnold.AiArrayAllocate(len(uvd), 1, arnold.AI_TYPE_UINT)
                        uvlist = arnold.AiArrayAllocate(len(uvd), 1, arnold.AI_TYPE_POINT2)
                        for i, d in enumerate(uvd):
                            arnold.AiArraySetUInt(uvidxs, i, i)
                            arnold.AiArraySetPnt2(uvlist, i, arnold.AtPoint2(*d.uv))
                        arnold.AiNodeSetArray(node, "uvidxs", uvidxs)
                        arnold.AiNodeSetArray(node, "uvlist", uvlist)
                # materials
                idxs, _shaders = shaders.get(mesh)
                if idxs:
                    if len(_shaders) > 1:
                        shidxs = arnold.AiArrayAllocate(len(idxs), 1, arnold.AI_TYPE_BYTE)
                        for i, mi in enumerate(idxs):
                            arnold.AiArraySetByte(shidxs, i, mi)
                        shader = arnold.AiArrayAllocate(len(_shaders), 1, arnold.AI_TYPE_POINTER)
                        for i, sh in enumerate(_shaders):
                            arnold.AiArraySetPtr(shader, i, sh)
                        arnold.AiNodeSetArray(node, "shidxs", shidxs)
                        arnold.AiNodeSetArray(node, "shader", shader)
                    elif _shaders[0]:
                        arnold.AiNodeSetPtr(node, "shader", _shaders[0])
            finally:
                data.meshes.remove(mesh)
        elif ob.type == 'LAMP':
            lamp = ob.data
            light = lamp.arnold
            if lamp.type == 'POINT':
                node = arnold.AiNode("point_light")
                arnold.AiNodeSetFlt(node, "radius", light.point.radius)
            #elif lamp.type == 'HEMI':
            #    node = arnold.AiNode("ambient_light")  # there is no such node in current sdk
            else:
                continue
            arnold.AiNodeSetStr(node, "name", ob.name)
            arnold.AiNodeSetRGB(node, "color", *lamp.color)
            arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
            arnold.AiNodeSetFlt(node, "intensity", light.intensity)
            arnold.AiNodeSetFlt(node, "exposure", light.exposure)
            arnold.AiNodeSetBool(node, "cast_shadows", light.cast_shadows)
            arnold.AiNodeSetBool(node, "cast_volumetric_shadows", light.cast_volumetric_shadows)
            arnold.AiNodeSetFlt(node, "shadow_density", light.shadow_density)
            arnold.AiNodeSetRGB(node, "shadow_color", *light.shadow_color)
            arnold.AiNodeSetInt(node, "samples", light.samples)
            arnold.AiNodeSetBool(node, "normalize", light.normalize)
            arnold.AiNodeSetArray(node, "matrix", _amatrix(ob.matrix_world))

    camera_node = arnold.AiNode("persp_camera")
    arnold.AiNodeSetStr(camera_node, "name", camera.name)
    arnold.AiNodeSetFlt(camera_node, "fov", math.degrees(camera.data.angle))
    arnold.AiNodeSetArray(camera_node, "matrix", _amatrix(camera.matrix_world))

    filter = arnold.AiNode("cook_filter")
    arnold.AiNodeSetStr(filter, "name", "outfilter")
    display = arnold.AiNode("driver_display")
    arnold.AiNodeSetStr(display, "name", "outdriver")
    outputs = arnold.AiArray(1, 1, arnold.AI_TYPE_STRING, b"RGBA RGBA outfilter outdriver")
    if session is not None:
        session['display'] = display

    options = arnold.AiUniverseGetOptions()
    arnold.AiNodeSetInt(options, "xres", xres)
    arnold.AiNodeSetInt(options, "yres", yres)
    arnold.AiNodeSetBool(options, "skip_license_check", opts.skip_license_check)
    arnold.AiNodeSetInt(options, "AA_samples", opts.aa_samples)
    arnold.AiNodeSetInt(options, "AA_seed", opts.aa_seed)
    arnold.AiNodeSetInt(options, "threads", opts.threads)
    arnold.AiNodeSetStr(options, "thread_priority", opts.thread_priority)
    arnold.AiNodeSetPtr(options, "camera", camera_node)
    arnold.AiNodeSetArray(options, "outputs", outputs)

    if ass_filepath:
        # TODO: options
        arnold.AiASSWrite(ass_filepath, arnold.AI_NODE_ALL, False, False)
        arnold.AiEnd()


def update(self, data, scene):
    self._session = {}
    export(
        data,
        scene,
        self.camera_override,
        self.resolution_x,
        self.resolution_y,
        session=self._session
    )

_TILE_COLORS = [
    [0, 0, 0, 1],
    [1, 0, 0, 1],
    [0, 1, 0, 1],
    [0, 0, 1, 1],
    [1, 1, 0, 1],
    [0, 1, 1, 1],
    [1, 0, 1, 1],
    [1, 1, 1, 1]
]
_M = 1 / 255


def render(self, scene):
    try:
        self._peak = 0
        self._tiles = {}
        self._tile = 0  # color index

        def display_callback(x, y, width, height, buffer, data):
            if self.test_break():
                arnold.AiRenderAbort()
                for (x , y), (w, h) in self._tiles.items():
                    result = self.begin_result(x, self.resolution_y - y - h, w, h)
                    result.layers[0].passes[0].rect = numpy.zeros([w * h, 4])
                    self.end_result(result)
                return

            result = self.begin_result(x, self.resolution_y - y - height, width, height)
            if buffer:
                self._tiles.pop((x, y))
                t = ctypes.c_byte * (width * height * 4)
                a = numpy.frombuffer(t.from_address(ctypes.addressof(buffer.contents)), numpy.uint8)
                rect = numpy.reshape(numpy.flipud(numpy.reshape(a * _M, [height, width * 4])), [-1, 4])
            else:
                self._tiles[(x, y)] = (width, height)
                color = _TILE_COLORS[self._tile]
                if self._tile == 7:
                    self._tile = 0
                else:
                    self._tile += 1
                color[3] = 0.05
                rect = numpy.ndarray([width * height, 4])
                rect[:] = color
                color[3] = 1
                rect[0: 4] = color
                rect[width - 4: width + 1] = color
                _x = width * 2 - 1
                rect[_x: _x + 2] = color
                _x += width
                rect[_x: _x + 2] = color
                rect[_x + width] = color
                _x = width * height
                rect[_x - 4: _x] = color
                _x -= width + 1
                rect[_x: _x + 5] = color
                _x -= width
                rect[_x: _x + 2] = color
                _x -= width
                rect[_x: _x + 2] = color
                rect[_x - width + 1] = color
            result.layers[0].passes[0].rect = rect
            self.end_result(result)

            mem = arnold.AiMsgUtilGetUsedMemory() / 1048576  # 1024*1024
            self._peak = max(self._peak, mem)
            self.update_memory_stats(mem, self._peak)
            #self.update_stats("", "Tile: %dx%d" % (x, y))

        # display callback must be a variable
        cb = arnold.AtDisplayCallBack(display_callback)
        arnold.AiNodeSetPtr(self._session['display'], "callback", cb)
        arnold.AiRender(arnold.AI_RENDER_MODE_CAMERA)
    except:
        # cancel render on error
        self.end_result(None, True)
    finally:
        del self._session
        arnold.AiEnd()
