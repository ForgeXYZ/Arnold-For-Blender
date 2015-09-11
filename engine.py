# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import os
import sys
import ctypes
import numpy
import math

from mathutils import Matrix, Vector


sdk = os.path.join(os.path.dirname(__file__), 'arnold', 'python')
if sdk not in sys.path:
    sys.path.append(sdk)

import arnold

_M = 1 / 255
_P = [ 1, 1, 0, 1]

class Shaders:
    def __init__(self):
        self._shaders = {}
        self._default = None

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
                        idx = len(shaders)
                        node = arnold.AiNode('lambert')
                        arnold.AiNodeSetStr(node, "name", mat.name)
                        arnold.AiNodeSetFlt(node, "Kd", mat.diffuse_intensity)
                        arnold.AiNodeSetRGB(node, "Kd_color", *mat.diffuse_color)
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
                    node = None
                    #node = arnold.AiNode('lambert')
                    #arnold.AiNodeSetStr(node, "name", "__default")
                    #arnold.AiNodeSetFlt(node, "Kd", 0.8)
                    #arnold.AiNodeSetRGB(node, "Kd_color", 0.8, 0.8, 0.8)
                    self._default = node
                    shaders.append(node)
                else:
                    idx = default
                midxs[mi] = idx
            idxs.append(idx)

        return idxs, shaders


def _amatrix(m):
    """
    m: mathutils.Matrix
    returns: pointer to AtArray
    """
    t = (v for r in m.transposed() for v in r)
    matrix = arnold.AiArrayAllocate(1, 1, arnold.AI_TYPE_MATRIX)
    arnold.AiArraySetMtx(matrix, 0, arnold.AtMatrix(*t))
    return matrix


def update(self, data, scene):
    print("-- update --")
    self._session = {}
    shaders = Shaders()

    arnold.AiBegin()
    #arnold.AiMsgSetConsoleFlags(arnold.AI_LOG_ALL)
    
    for ob in scene.objects:
        if ob.hide_render:
            continue
        
        if ob.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            mesh = ob.to_mesh(scene, True, 'RENDER')
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
            if lamp.type == 'POINT':
                node = arnold.AiNode("point_light")
                arnold.AiNodeSetStr(node, "name", ob.name)
                arnold.AiNodeSetRGB(node, "color", *lamp.color)
                arnold.AiNodeSetFlt(node, "intensity", lamp.energy)
                arnold.AiNodeSetArray(node, "matrix", _amatrix(ob.matrix_world))

    ob = self.camera_override
    mw = ob.matrix_world
    camera = arnold.AiNode("persp_camera")
    arnold.AiNodeSetStr(camera, "name", ob.name)
    arnold.AiNodeSetFlt(camera, "fov", math.degrees(ob.data.angle))
    arnold.AiNodeSetArray(camera, "matrix", _amatrix(ob.matrix_world))
        
    filter = arnold.AiNode("gaussian_filter")
    arnold.AiNodeSetStr(filter, "name", "outfilter")
    display = arnold.AiNode("driver_display")
    arnold.AiNodeSetStr(display, "name", "outdriver")
    outputs = arnold.AiArray(1, 1, arnold.AI_TYPE_STRING, b"RGBA RGBA outfilter outdriver")
    self._session['display'] = display

    options = arnold.AiUniverseGetOptions()
    arnold.AiNodeSetBool(options, "skip_license_check", True)
    arnold.AiNodeSetInt(options, "threads", 0)
    arnold.AiNodeSetInt(options, "AA_samples", 10)
    arnold.AiNodeSetInt(options, "xres", self.resolution_x)
    arnold.AiNodeSetInt(options, "yres", self.resolution_y)
    arnold.AiNodeSetPtr(options, "camera", camera)
    arnold.AiNodeSetArray(options, "outputs", outputs)

    #render = self.render
        
    if 0:
        arnold.AiNodeSetBool(options, "preserve_scene_data", True)
        arnold.AiASSWrite(r"D:\Tools\Dev\Src\blender\everything.ass", arnold.AI_NODE_ALL, False, False)


def render(self, scene):
    print("-- render --")
    try:
        self._peak = 0
        self._tiles = {}

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
                rect = numpy.ndarray([width * height, 4])
                rect[:] = [1, 1, 1, 0.05]
                rect[0: 4] = _P
                rect[width - 4: width + 1] = _P
                _x = width * 2 - 1
                rect[_x: _x + 2] = _P
                _x += width
                rect[_x: _x + 2] = _P
                rect[_x + width] = _P
                _x = width * height
                rect[_x - 4: _x] = _P
                _x -= width + 1
                rect[_x: _x + 5] = _P
                _x -= width
                rect[_x: _x + 2] = _P
                _x -= width
                rect[_x: _x + 2] = _P
                rect[_x - width + 1] = _P
            result.layers[0].passes[0].rect = rect
            self.end_result(result)
            
            mem = arnold.AiMsgUtilGetUsedMemory() / 1048576  # 1024*1024
            self._peak = max(self._peak, mem)
            self.update_memory_stats(mem, self._peak)
            #self.update_stats("", "Tile: %dx%d" % (x, y))
    
        # display callback must be a variable
        cb = arnold.AtDisplayCallBack(display_callback)
        arnold.AiNodeSetPtr(self._session['display'], "callback", cb)
        res = arnold.AiRender(arnold.AI_RENDER_MODE_CAMERA)
    finally:
        del self._session
        arnold.AiEnd()
