# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

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

import bpy
from mathutils import Matrix, Vector, geometry

from . import arnold

from ..nodes import (
    ArnoldNode,
    ArnoldNodeOutput,
    ArnoldNodeWorldOutput,
    ArnoldNodeLightOutput
)

_RN = re.compile("[^-0-9A-Za-z_]")  # regex to cleanup names
_CT = ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT')  # convertible types
_MR = Matrix.Rotation(math.radians(90.0), 4, 'X')


def _CleanNames(prefix, count):
    def fn(name):
        return "%s%d::%s" % (prefix, next(count), _RN.sub("_", name))
    return fn


_AiMatrix = lambda m: arnold.AtMatrix(*numpy.reshape(m.transposed(), -1))

_AiNodeSet = {
    "NodeSocketShader": lambda n, i, v: True,
    "NodeSocketBool": lambda n, i, v: arnold.AiNodeSetBool(n, i, v),
    "NodeSocketInt": lambda n, i, v: arnold.AiNodeSetInt(n, i, v),
    "NodeSocketFloat": lambda n, i, v: arnold.AiNodeSetFlt(n, i, v),
    "NodeSocketColor": lambda n, i, v: arnold.AiNodeSetRGBA(n, i, *v),
    "NodeSocketVector": lambda n, i, v: arnold.AiNodeSetVec(n, i, *v),
    "NodeSocketVectorXYZ": lambda n, i, v: arnold.AiNodeSetPnt(n, i, *v),
    "NodeSocketString": lambda n, i, v: arnold.AiNodeSetStr(n, i, v),
    "ArnoldNodeSocketColor": lambda n, i, v: arnold.AiNodeSetRGB(n, i, *v),
    "ArnoldNodeSocketByte": lambda n, i, v: arnold.AiNodeSetByte(n, i, v),
    "ArnoldNodeSocketProperty": lambda n, i, v: True,
    "STRING": lambda n, i, v: arnold.AiNodeSetStr(n, i, v),
    "BOOL": lambda n, i, v: arnold.AiNodeSetBool(n, i, v),
    "BYTE": lambda n, i, v: arnold.AiNodeSetByte(n, i, v),
    "INT": lambda n, i, v: arnold.AiNodeSetInt(n, i, v),
    "FLOAT": lambda n, i, v: arnold.AiNodeSetFlt(n, i, v),
    "POINT2": lambda n, i, v: arnold.AiNodeSetPnt2(n, i, *v),
    "RGB": lambda n, i, v: arnold.AiNodeSetRGB(n, i, *v),
    "RGBA": lambda n, i, v: arnold.AiNodeSetRGBA(n, i, *v),
    "VECTOR": lambda n, i, v: arnold.AiNodeSetVec(n, i, *v),
    "MATRIX": lambda n, i, v: arnold.AiNodeSetMatrix(n, i, _AiMatrix(v))
}


def _AiNode(node, prefix, nodes):
    """
    Args:
        node (ArnoldNode): node.
        prefix (str): node name prefix.
        nodes (dict): created nodes {Node: AiNode}.
    Returns:
        arnold.AiNode or None
    """
    if not isinstance(node, ArnoldNode):
        return None

    anode = nodes.get(node)
    if anode is None:
        anode = arnold.AiNode(node.ai_name)
        name = "%s&N%d::%s" % (prefix, len(nodes), _RN.sub("_", node.name))
        arnold.AiNodeSetStr(anode, "name", name)
        nodes[node] = anode
        for input in node.inputs:
            if input.is_linked:
                _anode = _AiNode(input.links[0].from_node, prefix, nodes)
                if _anode is not None:
                    arnold.AiNodeLink(_anode, input.identifier, anode)
                    continue
            if not input.hide_value:
                _AiNodeSet[input.bl_idname](anode, input.identifier, input.default_value)
        for p_name, (p_type, p_value) in node.ai_properties.items():
            _AiNodeSet[p_type](anode, p_name, p_value)
    return anode


class Shaders:
    def __init__(self, data):
        self._data = data

        self._shaders = {}
        self._default = None  # default shader, if used

        self._Name = _CleanNames("M", itertools.count())

    def get(self, mat):
        if mat:
            node = self._shaders.get(mat)
            if node is None:
                node = self._export(mat)
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
            node = arnold.AiNode('utility')
            arnold.AiNodeSetStr(node, "name", "__default")
            self._default = node
        return node

    def _export(self, mat):
        if mat.use_nodes:
            for n in mat.node_tree.nodes:
                if isinstance(n, ArnoldNodeOutput) and n.is_active:
                    input = n.inputs[0]
                    if input.is_linked:
                        return _AiNode(input.links[0].from_node, self._Name(mat.name), {})
                    break
            return None

        shader = mat.arnold
        if mat.type == 'SURFACE':
            node = arnold.AiNode(shader.type)
            if shader.type == 'lambert':
                arnold.AiNodeSetFlt(node, "Kd", mat.diffuse_intensity)
                arnold.AiNodeSetRGB(node, "Kd_color", *mat.diffuse_color)
                arnold.AiNodeSetRGB(node, "opacity", *shader.lambert.opacity)
            elif shader.type == 'standard':
                standard = shader.standard
                arnold.AiNodeSetFlt(node, "Kd", mat.diffuse_intensity)
                arnold.AiNodeSetRGB(node, "Kd_color", *mat.diffuse_color)
                arnold.AiNodeSetFlt(node, "diffuse_roughness", standard.diffuse_roughness)
                arnold.AiNodeSetFlt(node, "Ks", mat.specular_intensity)
                arnold.AiNodeSetRGB(node, "Ks_color", *mat.specular_color)
                arnold.AiNodeSetFlt(node, "specular_roughness", standard.specular_roughness)
                arnold.AiNodeSetFlt(node, "specular_anisotropy", standard.specular_anisotropy)
                arnold.AiNodeSetFlt(node, "specular_rotation", standard.specular_rotation)
                # TODO: other standard node parmas
            elif shader.type == 'utility':
                utility = shader.utility
                arnold.AiNodeSetStr(node, "color_mode", utility.color_mode)
                arnold.AiNodeSetStr(node, "shade_mode", utility.shade_mode)
                arnold.AiNodeSetStr(node, "overlay_mode", utility.overlay_mode)
                arnold.AiNodeSetRGB(node, "color", *mat.diffuse_color)
                arnold.AiNodeSetFlt(node, "opacity", utility.opacity)
                arnold.AiNodeSetFlt(node, "ao_distance", utility.ao_distance)
            elif shader.type == 'flat':
                arnold.AiNodeSetRGB(node, "color", *mat.diffuse_color)
                arnold.AiNodeSetRGB(node, "opacity", *shader.flat.opacity)
            elif shader.type == 'hair':
                # TODO: implement hair
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
        arnold.AiNodeSetStr(node, "name", self._Name(mat.name))
        return node


def _AiPolymesh(mesh, shaders):
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
    vlist = arnold.AiArrayConvert(nverts, 1, arnold.AI_TYPE_POINT, ctypes.c_void_p(a.ctypes.data))
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
    # TODO: very slow, seems its always a range(0, nloops)
    #a = numpy.array([i for p in polygons for i in p.loop_indices], dtype=numpy.uint32)
    #nidxs = arnold.AiArrayConvert(len(a), 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))
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
    for i, uvt in enumerate(mesh.uv_textures):
        if uvt.active_render:
            uvd = mesh.uv_layers[i].data
            nuvs = len(uvd)
            a = numpy.arange(nuvs, dtype=numpy.uint32)
            uvidxs = arnold.AiArrayConvert(nuvs, 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))
            a = numpy.ndarray(nuvs * 2, dtype=numpy.float32)
            uvd.foreach_get("uv", a)
            uvlist = arnold.AiArrayConvert(nuvs, 1, arnold.AI_TYPE_POINT2, ctypes.c_void_p(a.ctypes.data))
            arnold.AiNodeSetArray(node, "uvidxs", uvidxs)
            arnold.AiNodeSetArray(node, "uvlist", uvlist)
            break

    # materials
    if mesh.materials:
        a = numpy.ndarray(npolygons, dtype=numpy.uint8)
        polygons.foreach_get("material_index", a)
        mm = collections.OrderedDict()
        for i in numpy.unique(a):
            mn = shaders.get(mesh.materials[i])
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
                arnold.AiNodeSetArray(node, "shader", shader)
                arnold.AiNodeSetArray(node, "shidxs", shidxs)
            else:
                arnold.AiNodeSetPtr(node, "shader", t[1][0])

    arnold.AiMsgInfo(b"    node (%f)", ctypes.c_double(time.perf_counter() - pc))
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


def _export(data, scene, camera, xres, yres, session=None):
    """
    """

    @contextmanager
    def _Mesh(ob):
        pc = time.perf_counter()
        mesh = ob.to_mesh(scene, True, 'RENDER', False)
        try:
            mesh.calc_normals_split()
            arnold.AiMsgInfo(b"    mesh (%f)", ctypes.c_double(time.perf_counter() - pc))
            yield mesh
        finally:
            data.meshes.remove(mesh)

    _Name = _CleanNames("O", itertools.count())

    # enabled scene layers
    layers = [i for i, j in enumerate(scene.layers) if j]
    in_layers = lambda o: any(o.layers[i] for i in layers)
    # nodes cache
    nodes = {}  # {Object: AiNode}
    inodes = {}  # {Object.data: AiNode}
    lamp_nodes = {}
    mesh_lights = []
    duplicators = []
    duplicator_parent = False

    shaders = Shaders(data)

    opts = scene.arnold
    arnold.AiMsgSetConsoleFlags(opts.get("console_log_flags", 0))
    arnold.AiMsgSetMaxWarnings(opts.max_warnings)

    plugins_path = os.path.normpath(os.path.join(os.path.dirname(__file__), os.path.pardir, "bin"))
    arnold.AiLoadPlugins(plugins_path)

    arnold.AiMsgInfo(b"")
    arnold.AiMsgInfo(b"BARNOLD: >>>")

    ##############################
    ## objects
    for ob in scene.objects:
        arnold.AiMsgInfo(b"[%S] '%S'", ob.type, ob.name)

        if ob.hide_render or not in_layers(ob):
            arnold.AiMsgInfo(b"    skip (hidden)")
            continue

        if duplicator_parent is not False:
            if duplicator_parent == ob.parent:
                duplicator_parent = False
            else:
                arnold.AiMsgInfo(b"    skip (duplicator child)")
                continue

        if ob.is_duplicator:
            duplicators.append(ob)
            if ob.dupli_type in ('VERTS', 'FACES'):
                duplicator_parent = ob.parent
            arnold.AiMsgInfo(b"    skip (duplicator)")
            continue

        if ob.type in _CT:
            modified = ob.is_modified(scene, 'RENDER')
            if not modified:
                inode = inodes.get(ob.data)
                if inode is not None:
                    node = arnold.AiNode("ginstance")
                    arnold.AiNodeSetStr(node, "name", _Name(ob.name))
                    arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(ob.matrix_world))
                    arnold.AiNodeSetBool(node, "inherit_xform", False)
                    arnold.AiNodeSetPtr(node, "node", inode)
                    _export_object_properties(ob, node)
                    arnold.AiMsgInfo(b"    instance (%S)", ob.data.name)
                    continue

            with _Mesh(ob) as mesh:
                node = _AiPolymesh(mesh, shaders)
                arnold.AiNodeSetStr(node, "name", _Name(ob.name))
                arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(ob.matrix_world))
                _export_object_properties(ob, node)
                if not modified:
                    # cache unmodified shapes for instancing
                    inodes[ob.data] = node
                # cache for duplicators
                nodes[ob] = node
        elif ob.type == 'LAMP':
            lamp = ob.data
            light = lamp.arnold
            matrix = ob.matrix_world.copy()
            if lamp.type == 'POINT':
                node = arnold.AiNode("point_light")
                arnold.AiNodeSetFlt(node, "radius", light.radius)
                arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
                arnold.AiMsgInfo(b"    point_light")
            elif lamp.type == 'SUN':
                node = arnold.AiNode("distant_light")
                arnold.AiNodeSetFlt(node, "angle", light.angle)
                arnold.AiMsgInfo(b"    distant_light")
            elif lamp.type == 'SPOT':
                node = arnold.AiNode("spot_light")
                arnold.AiNodeSetFlt(node, "radius", light.radius)
                arnold.AiNodeSetFlt(node, "lens_radius", light.lens_radius)
                arnold.AiNodeSetFlt(node, "cone_angle", math.degrees(lamp.spot_size))
                arnold.AiNodeSetFlt(node, "penumbra_angle", light.penumbra_angle)
                arnold.AiNodeSetFlt(node, "aspect_ratio", light.aspect_ratio)
                arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
                arnold.AiMsgInfo(b"    spot_light")
            elif lamp.type == 'HEMI':
                node = arnold.AiNode("skydome_light")
                arnold.AiNodeSetInt(node, "resolution", light.resolution)
                arnold.AiNodeSetStr(node, "format", light.format)
                arnold.AiMsgInfo(b"    skydome_light")
            elif lamp.type == 'AREA':
                node = arnold.AiNode(light.type)
                if light.type == 'cylinder_light':
                    top = arnold.AiArray(1, 1, arnold.AI_TYPE_POINT, arnold.AtPoint(0, lamp.size_y / 2, 0))
                    arnold.AiNodeSetArray(node, "top", top)
                    bottom = arnold.AiArray(1, 1, arnold.AI_TYPE_POINT, arnold.AtPoint(0, -lamp.size_y / 2, 0))
                    arnold.AiNodeSetArray(node, "bottom", bottom)
                    arnold.AiNodeSetFlt(node, "radius", lamp.size / 2)
                    arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
                elif light.type == 'disk_light':
                    arnold.AiNodeSetFlt(node, "radius", lamp.size / 2)
                    arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
                elif light.type == 'quad_light':
                    x = lamp.size / 2
                    y = lamp.size_y / 2 if lamp.shape == 'RECTANGLE' else x
                    verts = arnold.AiArrayAllocate(4, 1, arnold.AI_TYPE_POINT)
                    arnold.AiArraySetPnt(verts, 0, arnold.AtPoint(-x, -y, 0))
                    arnold.AiArraySetPnt(verts, 1, arnold.AtPoint(-x, y, 0))
                    arnold.AiArraySetPnt(verts, 2, arnold.AtPoint(x, y, 0))
                    arnold.AiArraySetPnt(verts, 3, arnold.AtPoint(x, -y, 0))
                    arnold.AiNodeSetArray(node, "vertices", verts)
                    arnold.AiNodeSetInt(node, "resolution", light.quad_resolution)
                    arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
                elif light.type == 'photometric_light':
                    arnold.AiNodeSetStr(node, "filename", bpy.path.abspath(light.filename))
                    matrix *= _MR
                elif light.type == 'mesh_light':
                    arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
                    if light.mesh:
                        mesh_lights.append((node, light.mesh))
            else:
                arnold.AiMsgInfo(b"    skip (unsupported)")
                continue

            name = _Name(ob.name)
            arnold.AiNodeSetStr(node, "name", name)
            color_node = None
            if lamp.use_nodes:
                filter_nodes = []
                for _node in lamp.node_tree.nodes:
                    if isinstance(_node, ArnoldNodeLightOutput) and _node.is_active:
                        for input in _node.inputs:
                            if input.is_linked:
                                _node = _AiNode(input.links[0].from_node, name, lamp_nodes)
                                if input.identifier == "color":
                                    color_node = _node
                                elif input.bl_idname == "ArnoldNodeSocketFilter":
                                    filter_nodes.append(_node)
                        break
                if filter_nodes:
                    filters = arnold.AiArray(len(filter_nodes), 1, arnold.AI_TYPE_NODE, *filter_nodes)
                    arnold.AiNodeSetArray(node, "filters", filters)
            if color_node is None:
                arnold.AiNodeSetRGB(node, "color", *lamp.color)
            else:
                arnold.AiNodeLink(color_node, "color", node)
            arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(matrix))
            arnold.AiNodeSetFlt(node, "intensity", light.intensity)
            arnold.AiNodeSetFlt(node, "exposure", light.exposure)
            arnold.AiNodeSetBool(node, "cast_shadows", light.cast_shadows)
            arnold.AiNodeSetBool(node, "cast_volumetric_shadows", light.cast_volumetric_shadows)
            arnold.AiNodeSetFlt(node, "shadow_density", light.shadow_density)
            arnold.AiNodeSetRGB(node, "shadow_color", *light.shadow_color)
            arnold.AiNodeSetInt(node, "samples", light.samples)
            arnold.AiNodeSetBool(node, "normalize", light.normalize)
            arnold.AiNodeSetBool(node, "affect_diffuse", light.affect_diffuse)
            arnold.AiNodeSetBool(node, "affect_specular", light.affect_specular)
            arnold.AiNodeSetBool(node, "affect_volumetrics", light.affect_volumetrics)
            arnold.AiNodeSetFlt(node, "diffuse", light.diffuse)
            arnold.AiNodeSetFlt(node, "specular", light.specular)
            arnold.AiNodeSetFlt(node, "sss", light.sss)
            arnold.AiNodeSetFlt(node, "indirect", light.indirect)
            arnold.AiNodeSetInt(node, "max_bounces", light.max_bounces)
            arnold.AiNodeSetInt(node, "volume_samples", light.volume_samples)
            arnold.AiNodeSetFlt(node, "volume", light.volume)
        else:
            arnold.AiMsgInfo(b"    skip (unsupported)")

    ##############################
    ## duplicators
    for duplicator in duplicators:
        i = 0
        pc = time.perf_counter()
        arnold.AiMsgInfo(b"[DUPLI:%S:%S] '%S'", duplicator.type,
                         duplicator.dupli_type, duplicator.name)
        arnold.AiMsgTab(4)
        duplicator.dupli_list_create(scene, 'RENDER')
        try:
            for d in duplicator.dupli_list:
                ob = d.object
                if not ob.hide_render and ob.dupli_type not in ('VERTS', 'FACES') and ob.type in _CT:
                    onode = nodes.get(ob)
                    if onode is None:
                        arnold.AiMsgInfo(b"[%S] '%S'", ob.type, ob.name)
                        with _Mesh(ob) as mesh:
                            node = _AiPolymesh(mesh, shaders)
                            arnold.AiNodeSetStr(node, "name", _Name(ob.name))
                            arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(d.matrix))
                            nodes[ob] = node
                    else:
                        node = arnold.AiNode("ginstance")
                        arnold.AiNodeSetStr(node, "name", _Name(ob.name))
                        arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(d.matrix))
                        arnold.AiNodeSetBool(node, "inherit_xform", False)
                        arnold.AiNodeSetPtr(node, "node", onode)
                        i += 1
                    _export_object_properties(ob, node)
            arnold.AiMsgInfo(b"instances %d (%f)", ctypes.c_int(i),
                             ctypes.c_double(time.perf_counter() - pc))
        finally:
            arnold.AiMsgTab(-4)
            duplicator.dupli_list_clear()

    for light_node, name in mesh_lights:
        ob = scene.objects.get(name)
        if ob is None:
            continue
        node = nodes.get(ob)
        if node is None:
            if ob.type not in _CT:
                continue
            arnold.AiMsgInfo(b"[%S] '%S'", ob.type, ob.name)
            with _Mesh(ob) as mesh:
                node = _AiPolymesh(mesh, shaders)
                arnold.AiNodeSetStr(node, "name", _Name(ob.name))
                arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(ob.matrix_world))
                nodes[ob] = node
        arnold.AiNodeSetPtr(light_node, "mesh", node)

    render = scene.render
    aspect_x = render.pixel_aspect_x
    aspect_y = render.pixel_aspect_y
    # offsets for border render
    xoff = 0
    yoff = 0

    ##############################
    ## options
    options = arnold.AiUniverseGetOptions()
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
        arnold.AiNodeSetInt(options, "AA_seed", scene.frame_current)
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
    arnold.AiNodeSetBool(options, "ignore_direct_lighting", opts.ignore_direct_lighting)
    arnold.AiNodeSetBool(options, "ignore_subdivision", opts.ignore_subdivision)
    arnold.AiNodeSetBool(options, "ignore_displacement", opts.ignore_displacement)
    arnold.AiNodeSetBool(options, "ignore_bump", opts.ignore_bump)
    arnold.AiNodeSetBool(options, "ignore_motion_blur", opts.ignore_motion_blur)
    arnold.AiNodeSetBool(options, "ignore_dof", opts.ignore_dof)
    arnold.AiNodeSetBool(options, "ignore_smoothing", opts.ignore_smoothing)
    arnold.AiNodeSetBool(options, "ignore_sss", opts.ignore_sss)
    arnold.AiNodeSetStr(options, "auto_transparency_mode", opts.auto_transparency_mode)
    arnold.AiNodeSetInt(options, "auto_transparency_depth", opts.auto_transparency_depth)
    arnold.AiNodeSetFlt(options, "auto_transparency_threshold", opts.auto_transparency_threshold)
    arnold.AiNodeSetInt(options, "texture_max_open_files", opts.texture_max_open_files)
    arnold.AiNodeSetFlt(options, "texture_max_memory_MB", opts.texture_max_memory_MB)
    arnold.AiNodeSetStr(options, "texture_searchpath", opts.texture_searchpath)
    arnold.AiNodeSetBool(options, "texture_automip", opts.texture_automip)
    arnold.AiNodeSetInt(options, "texture_autotile", opts.texture_autotile)
    arnold.AiNodeSetBool(options, "texture_accept_untiled", opts.texture_accept_untiled)
    arnold.AiNodeSetBool(options, "texture_accept_unmipped", opts.texture_accept_unmipped)
    arnold.AiNodeSetFlt(options, "texture_glossy_blur", opts.texture_glossy_blur)
    arnold.AiNodeSetFlt(options, "texture_diffuse_blur", opts.texture_diffuse_blur)
    arnold.AiNodeSetFlt(options, "low_light_threshold", opts.low_light_threshold)
    arnold.AiNodeSetInt(options, "sss_bssrdf_samples", opts.sss_bssrdf_samples)
    arnold.AiNodeSetBool(options, "sss_use_autobump", opts.sss_use_autobump)
    arnold.AiNodeSetInt(options, "volume_indirect_samples", opts.volume_indirect_samples)
    arnold.AiNodeSetInt(options, "max_subdivisions", opts.max_subdivisions)
    arnold.AiNodeSetStr(options, "procedural_searchpath", opts.procedural_searchpath)
    arnold.AiNodeSetStr(options, "shader_searchpath", opts.shader_searchpath)
    arnold.AiNodeSetFlt(options, "texture_gamma", opts.texture_gamma)
    arnold.AiNodeSetFlt(options, "light_gamma", opts.light_gamma)
    arnold.AiNodeSetFlt(options, "shader_gamma", opts.shader_gamma)
    arnold.AiNodeSetInt(options, "GI_diffuse_depth", opts.GI_diffuse_depth)
    arnold.AiNodeSetInt(options, "GI_glossy_depth", opts.GI_glossy_depth)
    arnold.AiNodeSetInt(options, "GI_reflection_depth", opts.GI_reflection_depth)
    arnold.AiNodeSetInt(options, "GI_refraction_depth", opts.GI_refraction_depth)
    arnold.AiNodeSetInt(options, "GI_volume_depth", opts.GI_volume_depth)
    arnold.AiNodeSetInt(options, "GI_total_depth", opts.GI_total_depth)
    arnold.AiNodeSetInt(options, "GI_diffuse_samples", opts.GI_diffuse_samples)
    arnold.AiNodeSetInt(options, "GI_glossy_samples", opts.GI_glossy_samples)
    arnold.AiNodeSetInt(options, "GI_refraction_samples", opts.GI_refraction_samples)

    ##############################
    ## camera
    if camera:
        name = "C::" + _RN.sub("_", camera.name)
        mw = camera.matrix_world
        cd = camera.data
        cp = cd.arnold
        node = arnold.AiNode("persp_camera")
        arnold.AiNodeSetStr(node, "name", name)
        arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(mw))
        if cd.sensor_fit == 'VERTICAL':
            sw = cd.sensor_height * xres / yres * aspect_x / aspect_y
        else:
            sw = cd.sensor_width
            if cd.sensor_fit == 'AUTO':
                x = xres * aspect_x
                y = xres * aspect_y
                if x < y:
                    sw *= x / y
        fov = math.degrees(2 * math.atan(sw / (2 * cd.lens)))
        arnold.AiNodeSetFlt(node, "fov", fov)
        if cd.dof_object:
            dof = geometry.distance_point_to_plane(
                mw.to_translation(),
                cd.dof_object.matrix_world.to_translation(),
                mw.col[2][:3]
            )
        else:
           dof = cd.dof_distance
        arnold.AiNodeSetFlt(node, "focus_distance", dof)
        if cp.enable_dof:
            arnold.AiNodeSetFlt(node, "aperture_size", cp.aperture_size)
            arnold.AiNodeSetInt(node, "aperture_blades", cp.aperture_blades)
            arnold.AiNodeSetFlt(node, "aperture_rotation", cp.aperture_rotation)
            arnold.AiNodeSetFlt(node, "aperture_blade_curvature", cp.aperture_blade_curvature)
            arnold.AiNodeSetFlt(node, "aperture_aspect_ratio", cp.aperture_aspect_ratio)
        arnold.AiNodeSetFlt(node, "near_clip", cd.clip_start)
        arnold.AiNodeSetFlt(node, "far_clip", cd.clip_end)
        arnold.AiNodeSetFlt(node, "shutter_start", cp.shutter_start)
        arnold.AiNodeSetFlt(node, "shutter_end", cp.shutter_end)
        arnold.AiNodeSetStr(node, "shutter_type", cp.shutter_type)
        arnold.AiNodeSetStr(node, "rolling_shutter", cp.rolling_shutter)
        arnold.AiNodeSetFlt(node, "rolling_shutter_duration", cp.rolling_shutter_duration)
        # TODO: camera shift
        if session is not None:
            arnold.AiNodeSetPnt2(node, "screen_window_min", -1, 1)
            arnold.AiNodeSetPnt2(node, "screen_window_max", 1, -1)
        arnold.AiNodeSetFlt(node, "exposure", cp.exposure)
        arnold.AiNodeSetPtr(options, "camera", node)
    
    ##############################
    ## world
    world = scene.world
    if world:
        if world.use_nodes:
            for _node in world.node_tree.nodes:
                if isinstance(_node, ArnoldNodeWorldOutput) and _node.is_active:
                    name = "W::" + _RN.sub("_", world.name)
                    for input in _node.inputs:
                        if input.is_linked:
                            node = _AiNode(input.links[0].from_node, name, {})
                            if node:
                                arnold.AiNodeSetPtr(options, input.identifier, node)
                    break
        else:
            # TODO: export world settings
            pass

    ##############################
    ## outputs
    sft = opts.sample_filter_type
    filter = arnold.AiNode(sft)
    arnold.AiNodeSetStr(filter, "name", "__outfilter")
    if sft == 'blackman_harris_filter':
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_bh_width)
    elif sft == 'sinc_filter':
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_sinc_width)
    elif sft in ('cone_filter',
                 'cook_filter',
                 'disk_filter',
                 'gaussian_filter',
                 'triangle_filter'):
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_width)
    elif sft == 'farthest_filter':
        arnold.AiNodeSetStr(filter, "domain", opts.sample_filter_domain)
    elif sft == 'heatmap_filter':
        arnold.AiNodeSetFlt(filter, "minumum", opts.sample_filter_min)
        arnold.AiNodeSetFlt(filter, "maximum", opts.sample_filter_max)
    elif sft == 'variance_filter':
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_width)
        arnold.AiNodeSetBool(filter, "scalar_mode", opts.sample_filter_scalar_mode)

    display = arnold.AiNode("driver_display")
    arnold.AiNodeSetStr(display, "name", "__outdriver")
    arnold.AiNodeSetFlt(display, "gamma", opts.display_gamma)
    arnold.AiNodeSetBool(display, "rgba_packing", False)
    #arnold.AiNodeSetBool(display, "dither", True)

    # TODO: unusable, camera flipped (top to buttom) for tiles hightlighting
    #png = arnold.AiNode("driver_png")
    #arnold.AiNodeSetStr(png, "name", "__png")
    #arnold.AiNodeSetStr(png, "filename", render.frame_path())

    outputs_aovs = (
        b"RGBA RGBA __outfilter __outdriver",
        #b"RGBA RGBA __outfilter __png"
    )
    outputs = arnold.AiArray(len(outputs_aovs), 1, arnold.AI_TYPE_STRING, *outputs_aovs)
    arnold.AiNodeSetArray(options, "outputs", outputs)

    AA_samples = opts.AA_samples
    if session is not None:
        session["display"] = display
        session["offset"] = xoff, yoff
        if opts.progressive_refinement:
            isl = opts.initial_sampling_level
            session["ipr"] = (isl, AA_samples + 1)
            AA_samples = isl
    arnold.AiNodeSetInt(options, "AA_samples", AA_samples)

    arnold.AiMsgInfo(b"BARNOLD: <<<")


def export_ass(data, scene, camera, xres, yres, filepath, open_procs, binary):
    arnold.AiBegin()
    try:
        _export(data, scene, camera, xres, yres)
        arnold.AiASSWrite(filepath, arnold.AI_NODE_ALL, open_procs, binary)
    finally:
        arnold.AiEnd()


def update(engine, data, scene):
    engine.use_highlight_tiles = True
    engine._session = {}
    arnold.AiBegin()
    _export(data, scene,
            engine.camera_override,
            engine.resolution_x,
            engine.resolution_y,
            session=engine._session)


def render(engine, scene):
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
                    result = _htiles.pop((_x, _y))
                    if result is not None:
                        result = engine.begin_result(_x, _y, width, height)
                    _buffer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_float))
                    rect = numpy.ctypeslib.as_array(_buffer, shape=(width * height, 4))
                    # TODO: gamma correction. need??? kick is darker
                    # set 1/2.2 the driver_display node by default
                    #rect **= 2.2
                    result.layers[0].passes[0].rect = rect
                    engine.end_result(result)
                finally:
                    arnold.AiFree(buffer)
            else:
                result = engine.begin_result(_x, _y, width, height)
                # TODO: sometimes highlighted tiles become empty
                #engine.update_result(result)
                _htiles[(_x, _y)] = result

            if engine.test_break():
                arnold.AiRenderAbort()
                while _htiles:
                    (_x, _y), result = _htiles.popitem()
                    engine.end_result(result, True)

            mem = session["mem"] = arnold.AiMsgUtilGetUsedMemory() / 1048576  # 1024*1024
            peak = session["peak"] = max(session["peak"], mem)
            engine.update_memory_stats(mem, peak)

        # display callback must be a variable
        cb = arnold.AtDisplayCallBack(display_callback)
        arnold.AiNodeSetPtr(session['display'], "callback", cb)

        res = arnold.AiRender(arnold.AI_RENDER_MODE_CAMERA)
        if res == arnold.AI_SUCCESS:
            ipr = session.get("ipr")
            if ipr:
                options = arnold.AiUniverseGetOptions()
                for sl in range(*ipr):
                    arnold.AiNodeSetInt(options, "AA_samples", sl)
                    res = arnold.AiRender(arnold.AI_RENDER_MODE_CAMERA)
                    if res != arnold.AI_SUCCESS:
                        break
                    engine.update_stats("", "Mem: %.2fMb, SL: %d" % (session.get("mem", "NA"), sl))
        if res != arnold.AI_SUCCESS:
            engine.error_set("Render status: %d" % res)
    except:
        # cancel render on error
        engine.end_result(None, True)
    finally:
        del engine._session
        arnold.AiEnd()
