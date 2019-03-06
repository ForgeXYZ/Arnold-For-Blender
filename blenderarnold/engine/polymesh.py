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


class _AiPolymesh(cl.AbstractContextManager):
    def __init__(self, ob):
        self._object = ob
        self.node = arnold.AiNode("polymesh")

    # @contextmanager
    # def _Mesh(self, ob):
    #     pc = time.perf_counter()
    #     mesh = None
    #     try:
    #         mesh = ob.to_mesh(depsgraph=bpy.context.depsgraph, apply_modifiers=True, calc_undeformed=False)

    #         if mesh:
    #             mesh.calc_normals_split()
    #             arnold.AiMsgDebug(b"    mesh (%f)", ctypes.c_double(time.perf_counter() - pc))

    #         yield mesh
    #     finally:
    #         if mesh:
    #             bpy.data.meshes.remove(mesh, do_unlink=False)
    @contextmanager
    def __enter__(self):
        pc = time.perf_counter()
        mesh = None
        #try:

        self._mesh = self._object.to_mesh(depsgraph=bpy.context.depsgraph, apply_modifiers=True, calc_undeformed=False)

        if mesh:
            mesh.calc_normals_split()
            arnold.AiMsgDebug(b"    mesh (%f)", ctypes.c_double(time.perf_counter() - pc))


        self._meshverts = self._mesh.vertices
        self._meshnverts = len(self._meshverts)

        self._meshloops = self._mesh.loops
        self._meshnloops = len(self._meshloops)

        self._meshpolygons = self._mesh.polygons
        self._meshnpolygons = len(self._meshpolygons)
        
        return mesh
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._mesh:
                bpy.data.meshes.remove(self._mesh, do_unlink=False)

    def export(self):
        verts = self._meshverts
        nverts = self._meshnverts
        loops = self._meshloops
        nloops = self._meshnloops
        polygons = self._meshpolygons
        npolygons = self._meshnpolygons

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
  
        arnold.AiNodeSetBool(self.node, "smoothing", True)
        arnold.AiNodeSetArray(self.node, "vlist", vlist)
        arnold.AiNodeSetArray(self.node, "nlist", nlist)
        arnold.AiNodeSetArray(self.node, "nsides", nsides)
        arnold.AiNodeSetArray(self.node, "vidxs", vidxs)
        arnold.AiNodeSetArray(self.node, "nidxs", nidxs)

        # uv
        for i, uvt in enumerate(self._mesh.uv_layers):
            if uvt.active_render:
                uvd = self._mesh.uv_layers[i].data
                nuvs = len(uvd)
                a = numpy.arange(nuvs, dtype=numpy.uint32)
                uvidxs = arnold.AiArrayConvert(nuvs, 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))
                a = numpy.ndarray(nuvs * 2, dtype=numpy.float32)
                uvd.foreach_get("uv", a)
                uvlist = arnold.AiArrayConvert(nuvs, 1, arnold.AI_TYPE_VECTOR2, ctypes.c_void_p(a.ctypes.data))
                arnold.AiNodeSetArray(self.node, "uvidxs", uvidxs)
                arnold.AiNodeSetArray(self.node, "uvlist", uvlist)
                break

        return self.node

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