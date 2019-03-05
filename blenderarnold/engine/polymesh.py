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

def _AiPolymesh(mesh):
    pc = time.perf_counter()

    verts = mesh.vertices
    nverts = len(verts)
    loops = mesh.loops
    nloops = len(loops)
    polygons = mesh.polygons
    npolygons = len(polygons)

    # vertices
    a = numpy.ndarray(nverts * 3, dtype=numpy.float32)
    verts.foreach_get("co", a)
    vlist = arnold.AiArrayConvert(nverts, 1, arnold.AI_TYPE_VECTOR, ctypes.c_void_p(a.ctypes.data))
    # normals
    a = numpy.ndarray(nloops * 3, dtype=numpy.float32)
    loops.foreach_get("normal", a)
    nlist = arnold.AiArrayConvert(nloops, 1, arnold.AI_TYPE_VECTOR, ctypes.c_void_p(a.ctypes.data))
    # polygons
    a = numpy.ndarray(npolygons, dtype=numpy.uint32)
    polygons.foreach_get("loop_total", a)
    nsides = arnold.AiArrayConvert(npolygons, 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))
    a = numpy.ndarray(nloops, dtype=numpy.uint32)
    polygons.foreach_get("vertices", a)
    vidxs = arnold.AiArrayConvert(nloops, 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))
    a = numpy.arange(nloops, dtype=numpy.uint32)
    nidxs = arnold.AiArrayConvert(nloops, 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))

    node = arnold.AiNode('polymesh')
    arnold.AiNodeSetBool(node, "smoothing", True)
    arnold.AiNodeSetArray(node, "vlist", vlist)
    arnold.AiNodeSetArray(node, "nlist", nlist)
    arnold.AiNodeSetArray(node, "nsides", nsides)
    arnold.AiNodeSetArray(node, "vidxs", vidxs)
    arnold.AiNodeSetArray(node, "nidxs", nidxs)

    # uv
    for i, uvt in enumerate(mesh.uv_layers):
        if uvt.active_render:
            uvd = mesh.uv_layers[i].data
            nuvs = len(uvd)
            a = numpy.arange(nuvs, dtype=numpy.uint32)
            uvidxs = arnold.AiArrayConvert(nuvs, 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))
            a = numpy.ndarray(nuvs * 2, dtype=numpy.float32)
            uvd.foreach_get("uv", a)
            uvlist = arnold.AiArrayConvert(nuvs, 1, arnold.AI_TYPE_VECTOR2, ctypes.c_void_p(a.ctypes.data))
            arnold.AiNodeSetArray(node, "uvidxs", uvidxs)
            arnold.AiNodeSetArray(node, "uvlist", uvlist)
            break
            
    return node

def _export_object_properties(ob, node):
    props = ob.arnold
    arnold.AiNodeSetByte(node, "visibility", props.visibility)
    arnold.AiNodeSetByte(node, "sidedness", props.sidedness)
    arnold.AiNodeSetBool(node, "receive_shadows", props.receive_shadows)
    arnold.AiNodeSetBool(node, "self_shadows", props.self_shadows)
    arnold.AiNodeSetBool(node, "invert_normals", props.invert_normals)
    arnold.AiNodeSetBool(node, "opaque", props.opaque)
    arnold.AiNodeSetBool(node, "matte", props.matte)
    #arnold.AiNodeSetArray(node, "disp_map", props.disp_map)
    arnold.AiNodeSetFlt(node, "disp_height", props.disp_height)
    if props.subdiv_type != 'none':
        arnold.AiNodeSetStr(node, "subdiv_type", props.subdiv_type)
        arnold.AiNodeSetByte(node, "subdiv_iterations", props.subdiv_iterations)
        arnold.AiNodeSetFlt(node, "subdiv_adaptive_error", props.subdiv_adaptive_error)
        arnold.AiNodeSetStr(node, "subdiv_adaptive_metric", props.subdiv_adaptive_metric)
        arnold.AiNodeSetStr(node, "subdiv_adaptive_space", props.subdiv_adaptive_space)
        arnold.AiNodeSetStr(node, "subdiv_uv_smoothing", props.subdiv_uv_smoothing)
        arnold.AiNodeSetBool(node, "subdiv_smooth_derivs", props.subdiv_smooth_derivs)