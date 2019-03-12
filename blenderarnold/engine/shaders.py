#import MaterialX

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

class _AiShaders:

    def __init__(self, data):
        self._data = data

        self._shaders = {}
        self._default = arnold.AiNode('lambert')  # default shader, if used

        self._Name = _CleanNames("M", itertools.count())

        self._AiNodeSet = {
            "NodeSocketShader": lambda n, i, v: True,
            "NodeSocketBool": lambda n, i, v: arnold.AiNodeSetBool(n, i, v),
            "NodeSocketInt": lambda n, i, v: arnold.AiNodeSetInt(n, i, v),
            "NodeSocketFloat": lambda n, i, v: arnold.AiNodeSetFlt(n, i, v),
            "NodeSocketColor": lambda n, i, v: arnold.AiNodeSetRGBA(n, i, *v),
            "NodeSocketVector": lambda n, i, v: arnold.AiNodeSetVec(n, i, *v),
            "NodeSocketVectorXYZ": lambda n, i, v: arnold.AiNodeSetVec(n, i, *v),
            "NodeSocketString": lambda n, i, v: arnold.AiNodeSetStr(n, i, v),
            "ArnoldNodeSocketColor": lambda n, i, v: arnold.AiNodeSetRGB(n, i, *v),
            "ArnoldNodeSocketByte": lambda n, i, v: arnold.AiNodeSetByte(n, i, v),
            "ArnoldNodeSocketProperty": lambda n, i, v: True,
            "STRING": lambda n, i, v: arnold.AiNodeSetStr(n, i, v),
            #'ARRAY': _AiNodeSetArray,
            "BOOL": lambda n, i, v: arnold.AiNodeSetBool(n, i, v),
            "BYTE": lambda n, i, v: arnold.AiNodeSetByte(n, i, v),
            "INT": lambda n, i, v: arnold.AiNodeSetInt(n, i, v),
            "FLOAT": lambda n, i, v: arnold.AiNodeSetFlt(n, i , v),
            "VECTOR2": lambda n, i, v: arnold.AiNodeSetVec2(n, i, *v),
            "RGB": lambda n, i, v: arnold.AiNodeSetRGB(n, i, *v),
            "RGBA": lambda n, i, v: arnold.AiNodeSetRGBA(n, i, *v),
            "VECTOR": lambda n, i, v: arnold.AiNodeSetVec(n, i, *v),
            "MATRIX": lambda n, i, v: arnold.AiNodeSetMatrix(n, i, _AiMatrix(v))
        }

    def get(self, mat):
        if mat:
            node = self._shaders.get(mat)
            if node is None:
                # node = self._export(mat)
                if node is None:
                    node = self.default
                self._shaders[mat] = node
        else:
            node = self.default
        return node

    @property
    def default(self):
        node = self._default
        if node is None:
            node = arnold.AiNode('lambert')
            arnold.AiNodeSetStr(node, "name", "__default")
            self._default = node
        return node
    
    def _AiNode(self, node, prefix, nodes):
        """
        Args:
            node (ArnoldNode): node.
            prefix (str): node name prefix.
            nodes (dict): created nodes {Node: AiNode}.
        Returns:
            arnold.AiNode or None
        """
        # if not isinstance(node, nt.ArnoldNode):
        #     return None

        anode = nodes.get(node)
        if anode is None:
            anode = arnold.AiNode(node.ai_name)
            _RN = re.compile("[^-0-9A-Za-z_]")  # regex to cleanup names
            name = "%s&N%d::%s" % (prefix, len(nodes), _RN.sub("_", node.name))
            arnold.AiNodeSetStr(anode, "name", name)
            nodes[node] = anode
            for input in node.inputs:
                if input.is_linked:
                    _anode = self._AiNode(input.links[0].from_node, prefix, nodes)
                    if _anode is not None:
                        arnold.AiNodeLink(_anode, input.identifier, anode)
                        continue
                if not input.hide_value:
                    self._AiNodeSet[input.bl_idname](anode, input.identifier, input.default_value)
            for p_name, (p_type, p_value) in node.ai_properties.items():
                self._AiNodeSet[p_type](anode, p_name, p_value)
        return anode
    
    def export(self, mesh, node):
        # materials
        if mesh.materials:
            _Name = _CleanNames("M", itertools.count())
            #if mesh.materials[0].use_nodes:
                #for _node in mesh.materials[0].node_tree.nodes:
                    # if isinstance(_node, nt.ArnoldNodeOutput) and _node.is_active:
                    #     for input in _node.inputs:
                    #         if input.is_linked:
                    #             # Displacement Mapping (Arnold needs map to be a pointer to the array of nodes pointing to displacement)
                    #             if input.identifier == "disp_map":
                    #                 dispnodes = []
                    #                 # _AiNode() converts blender node to arnold node
                    #                 dispnodes.append(_AiNode(input.links[0].from_node, _Name(mesh.materials[0].name), {}))
                    #                 nmaps = len(dispnodes)
                    #                 # Calculate the number of nodes linked to displacement and initialize a numpy array
                    #                 a = numpy.ndarray(nmaps, dtype=numpy.uint8)
                    #                 mm = collections.OrderedDict()
                    #                 # Set up the arnold parameters as NODE INDEX 
                    #                 for i in numpy.unique(a):
                    #                     mn = _AiNode(input.links[0].from_node, _Name(mesh.materials[0].name), {})
                    #                     mi = mm.setdefault(id(mn), (mn, []))[1]
                    #                     mi.append(i)
                    #                 for i, (mn, mi) in enumerate(mm.values()):
                    #                     a[numpy.in1d(a, numpy.setdiff1d(mi, i))] = i
                    #                 if mm:
                    #                     nmm = len(mm)
                    #                     t = mm.popitem(False)
                    #                     if t:
                    #                         # Point to the array of nodes
                    #                         AiDisplace = arnold.AiArrayAllocate(nmm, 1, arnold.AI_TYPE_POINTER)
                    #                         arnold.AiArraySetPtr(AiDisplace, 0, t[1][0])
                    #                         i = 1
                    #                         while mm:
                    #                             arnold.AiArraySetPtr(AiDisplace, 0, mm.popitem(False)[1][0])
                    #                             i += 1
                    #                         # Link Displacement Map to corresponding image node
                    #                         arnold.AiNodeSetArray(node, "disp_map", AiDisplace)
                                            
            # Calculate shaders per face assignment
            polygons = mesh.polygons
            npolygons = len(polygons)

            a = numpy.ndarray(npolygons, dtype=numpy.uint8)
            polygons.foreach_get("material_index", a)
            mm = collections.OrderedDict()
            for i in numpy.unique(a):
                mn = self.get(mesh.materials[i])
                mi = mm.setdefault(id(mn), (mn, []))[1]
                mi.append(i)
            for i, (mn, mi) in enumerate(mm.values()):
                a[numpy.in1d(a, numpy.setdiff1d(mi, i))] = i
            if mm:
                nmm = len(mm)
                t = mm.popitem(False)
                if mm:
                    shader = arnold.AiArrayAllocate(nmm, 1, arnold.AI_TYPE_POINTER)
                    arnold.AiArraySetPtr(shader, 0, t[1][0])
                    i = 1
                    while mm:
                        arnold.AiArraySetPtr(shader, i, mm.popitem(False)[1][0])
                        i += 1
                    shidxs = arnold.AiArrayConvert(len(a), 1, arnold.AI_TYPE_BYTE, ctypes.c_void_p(a.ctypes.data))
                    #disp_map = arnold.AiArrayConvert(len(a), 1, arnold.AI_TYPE_BYTE, ctypes.c_void_p(a.ctypes.data))
                    arnold.AiNodeSetArray(node, "shader", shader)
                    arnold.AiNodeSetArray(node, "shidxs", shidxs)
                    #arnold.AiNodeSetArray(node, "disp_map", disp_map)
                else:
                    arnold.AiNodeSetPtr(node, "shader", t[1][0])

def _CleanNames(prefix, count):
        _RN = re.compile("[^-0-9A-Za-z_]")  # regex to cleanup names
        def fn(name):
            return "%s%d::%s" % (prefix, next(count), _RN.sub("_", name))
        return fn
    