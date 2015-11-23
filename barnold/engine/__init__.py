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
import traceback

import bpy
import bgl
from mathutils import Matrix, Vector, geometry

from . import arnold

from ..nodes import (
    ArnoldNode,
    ArnoldNodeOutput,
    ArnoldNodeWorldOutput,
    ArnoldNodeLightOutput
)
from . import bla as _BLA
from . import ipr as _IPR

_IPR = _IPR.ipr()

_RN = re.compile("[^-0-9A-Za-z_]")  # regex to cleanup names
_CT = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}  # convertible types
_MR = Matrix.Rotation(math.radians(90.0), 4, 'X')
_SQRT2 = math.sqrt(2)


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

    arnold.AiMsgDebug(b"    node (%f)", ctypes.c_double(time.perf_counter() - pc))
    return node


def _AiCurvesPS(scene, ob, mod, ps, pss, shaders):
    """Create arnold curves node from a particle system"""
    pc = time.perf_counter()

    ps.set_resolution(scene, ob, 'RENDER')
    try:
        props = pss.arnold.curves
        steps = 2 ** pss.render_step + 1
        curves = _BLA.psys_get_curves(ps, steps, pss.use_parent_particles, props)
        if curves is None:
            return None
        p, r, steps = curves
        points = arnold.AiArrayConvert(len(p), 1, arnold.AI_TYPE_POINT, ctypes.c_void_p(p.ctypes.data))
        radius = arnold.AiArrayConvert(len(r), 1, arnold.AI_TYPE_FLOAT, ctypes.c_void_p(r.ctypes.data))

        arnold.AiMsgDebug(b"    hair [%d] (%f)", ctypes.c_int(len(p)), ctypes.c_double(time.perf_counter() - pc))

        node = arnold.AiNode("curves")
        arnold.AiNodeSetUInt(node, "num_points", steps)
        arnold.AiNodeSetArray(node, "points", points)
        arnold.AiNodeSetArray(node, "radius", radius)
        arnold.AiNodeSetStr(node, "basis", props.basis)
        arnold.AiNodeSetStr(node, "mode", props.mode)
        arnold.AiNodeSetFlt(node, "min_pixel_width", props.min_pixel_width)
        # TODO: own properties (visibility, shadow, ...)
        slots = ob.material_slots
        m = pss.material
        if 0 < m <= len(slots):
            arnold.AiNodeSetPtr(node, "shader", shaders.get(slots[m - 1].material))

        # TODO: work only if particle system emits particles from faces or volume
        if props.uvmap:
            uv_no = ob.data.uv_layers.find(props.uvmap)
            if uv_no >= 0:
                pc = time.perf_counter()

                setFlt = arnold.AiArraySetFlt
                uv_on_emitter = ps.uv_on_emitter

                np = len(ps.particles)
                nch = len(ps.child_particles)
                if nch == 0 or pss.use_parent_particles:
                    tot = np + nch
                    uparam = arnold.AiArrayAllocate(tot, 1, arnold.AI_TYPE_FLOAT)
                    vparam = arnold.AiArrayAllocate(tot, 1, arnold.AI_TYPE_FLOAT)
                    for i, p in enumerate(ps.particles):
                        u, v = uv_on_emitter(mod, p, i, uv_no)
                        setFlt(uparam, i, u)
                        setFlt(vparam, i, v)
                    n = i + 1
                else:
                    uparam = arnold.AiArrayAllocate(nch, 1, arnold.AI_TYPE_FLOAT)
                    vparam = arnold.AiArrayAllocate(nch, 1, arnold.AI_TYPE_FLOAT)
                    n = 0
                if nch > 0:
                    j = np
                    r = nch // np
                    for p in ps.particles:
                        for i in range(r):
                            u, v = uv_on_emitter(mod, p, j, uv_no)
                            setFlt(uparam, n, u)
                            setFlt(vparam, n, v)
                            j += 1
                            n += 1

                arnold.AiMsgDebug(b"    hair uvs (%f)", ctypes.c_double(time.perf_counter() - pc))

                arnold.AiNodeDeclare(node, "uparamcoord", "uniform FLOAT")
                arnold.AiNodeDeclare(node, "vparamcoord", "uniform FLOAT")
                arnold.AiNodeSetArray(node, "uparamcoord", uparam)
                arnold.AiNodeSetArray(node, "vparamcoord", vparam)
    finally:
        ps.set_resolution(scene, ob, 'PREVIEW')
    return node


def _AiPointsPS(scene, ob, ps, pss, frame_current, shaders):
    """Create arnold points node from a particle system"""
    pc = time.perf_counter()
    ps.set_resolution(scene, ob, 'RENDER')
    try:
        p = _BLA.psys_get_points(ps, pss, frame_current)
        if p is not None:
            n = len(p)
            if n > 0:
                points = arnold.AiArrayConvert(n, 1, arnold.AI_TYPE_POINT, ctypes.c_void_p(p.ctypes.data))

                arnold.AiMsgDebug(b"    points [%d] (%f)", ctypes.c_int(n), ctypes.c_double(time.perf_counter() - pc))

                node = arnold.AiNode("points")
                arnold.AiNodeSetArray(node, "points", points)
                arnold.AiNodeSetFlt(node, "radius", pss.particle_size)
                props = pss.arnold.points
                arnold.AiNodeSetStr(node, "mode", props.mode)
                if props.mode == 'quad':
                    arnold.AiNodeSetFlt(node, "aspect", props.aspect)
                    arnold.AiNodeSetFlt(node, "rotation", props.rotation)
                arnold.AiNodeSetFlt(node, "min_pixel_width", props.min_pixel_width)
                arnold.AiNodeSetFlt(node, "step_size", props.step_size)
                # TODO: own properties (visibility, shadow, ...)
                slots = ob.material_slots
                m = pss.material
                if 0 < m <= len(slots):
                    arnold.AiNodeSetPtr(node, "shader", shaders.get(slots[m - 1].material))
                return node
    finally:
        ps.set_resolution(scene, ob, 'PREVIEW')
    return None


def _export_object_properties(ob, node):
    props = ob.arnold
    arnold.AiNodeSetByte(node, "visibility", props.visibility)
    arnold.AiNodeSetByte(node, "sidedness", props.sidedness)
    arnold.AiNodeSetBool(node, "receive_shadows", props.receive_shadows)
    arnold.AiNodeSetBool(node, "self_shadows", props.self_shadows)
    arnold.AiNodeSetBool(node, "invert_normals", props.invert_normals)
    arnold.AiNodeSetBool(node, "opaque", props.opaque)
    arnold.AiNodeSetBool(node, "matte", props.matte)
    if props.subdiv_type != 'none':
        arnold.AiNodeSetStr(node, "subdiv_type", props.subdiv_type)
        arnold.AiNodeSetByte(node, "subdiv_iterations", props.subdiv_iterations)
        arnold.AiNodeSetFlt(node, "subdiv_adaptive_error", props.subdiv_adaptive_error)
        arnold.AiNodeSetStr(node, "subdiv_adaptive_metric", props.subdiv_adaptive_metric)
        arnold.AiNodeSetStr(node, "subdiv_adaptive_space", props.subdiv_adaptive_space)
        arnold.AiNodeSetStr(node, "subdiv_uv_smoothing", props.subdiv_uv_smoothing)
        arnold.AiNodeSetBool(node, "subdiv_smooth_derivs", props.subdiv_smooth_derivs)


def _export(data, scene, camera, xres, yres, session=None):
    """
    """

    @contextmanager
    def _Mesh(ob):
        pc = time.perf_counter()
        mesh = ob.to_mesh(scene, True, 'RENDER', False)
        if mesh is not None:
            try:
                mesh.calc_normals_split()
                arnold.AiMsgDebug(b"    mesh (%f)", ctypes.c_double(time.perf_counter() - pc))
                yield mesh
            finally:
                data.meshes.remove(mesh)
        else:
            yield None

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
    arnold.AiMsgDebug(b"BARNOLD: >>>")

    plugins_path = os.path.normpath(os.path.join(os.path.dirname(__file__), os.path.pardir, "bin"))
    arnold.AiLoadPlugins(plugins_path)

    ##############################
    ## objects
    for ob in scene.objects:
        arnold.AiMsgDebug(b"[%S] '%S'", ob.type, ob.name)

        if ob.hide_render or not in_layers(ob):
            arnold.AiMsgDebug(b"    skip (hidden)")
            continue

        if duplicator_parent is not False:
            if duplicator_parent == ob.parent:
                duplicator_parent = False
            else:
                arnold.AiMsgDebug(b"    skip (duplicator child)")
                continue

        if ob.is_duplicator:
            duplicators.append(ob)
            if ob.dupli_type in {'VERTS', 'FACES'}:
                duplicator_parent = ob.parent
            arnold.AiMsgDebug(b"    skip (duplicator)")
            continue

        if ob.type in _CT:
            name = None

            particle_systems = [
                (m, m.particle_system) for m in ob.modifiers
                if m.type == 'PARTICLE_SYSTEM' and m.show_render
            ]
            if particle_systems:
                use_render_emitter = False
                for mod, ps in particle_systems:
                    pss = ps.settings
                    if pss.use_render_emitter:
                        use_render_emitter = True
                    node = None
                    if pss.type == 'HAIR' and pss.render_type == 'PATH':
                        node = _AiCurvesPS(scene, ob, mod, ps, pss, shaders)
                    elif pss.type == 'EMITTER' and pss.render_type in {'HALO', 'LINE', 'PATH'}:
                        node = _AiPointsPS(scene, ob, ps, pss, scene.frame_current, shaders)
                    if node is not None:
                        if name is None:
                            name = _Name(ob.name)
                        arnold.AiNodeSetStr(node, "name", "%s&PS:%s" % (name, _RN.sub("_", ps.name)))
                if not use_render_emitter:
                    continue

            if name is None:
                name = _Name(ob.name)

            modified = ob.is_modified(scene, 'RENDER')
            if not modified:
                inode = inodes.get(ob.data)
                if inode is not None:
                    node = arnold.AiNode("ginstance")
                    arnold.AiNodeSetStr(node, "name", name)
                    arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(ob.matrix_world))
                    arnold.AiNodeSetBool(node, "inherit_xform", False)
                    arnold.AiNodeSetPtr(node, "node", inode)
                    _export_object_properties(ob, node)
                    arnold.AiMsgDebug(b"    instance (%S)", ob.data.name)
                    continue

            with _Mesh(ob) as mesh:
                if mesh is not None:
                    node = _AiPolymesh(mesh, shaders)
                    arnold.AiNodeSetStr(node, "name", name)
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
                arnold.AiMsgDebug(b"    point_light")
            elif lamp.type == 'SUN':
                node = arnold.AiNode("distant_light")
                arnold.AiNodeSetFlt(node, "angle", light.angle)
                arnold.AiMsgDebug(b"    distant_light")
            elif lamp.type == 'SPOT':
                node = arnold.AiNode("spot_light")
                arnold.AiNodeSetFlt(node, "radius", light.radius)
                arnold.AiNodeSetFlt(node, "lens_radius", light.lens_radius)
                arnold.AiNodeSetFlt(node, "cone_angle", math.degrees(lamp.spot_size))
                arnold.AiNodeSetFlt(node, "penumbra_angle", light.penumbra_angle)
                arnold.AiNodeSetFlt(node, "aspect_ratio", light.aspect_ratio)
                arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
                arnold.AiMsgDebug(b"    spot_light")
            elif lamp.type == 'HEMI':
                node = arnold.AiNode("skydome_light")
                arnold.AiNodeSetInt(node, "resolution", light.resolution)
                arnold.AiNodeSetStr(node, "format", light.format)
                arnold.AiMsgDebug(b"    skydome_light")
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
                arnold.AiMsgDebug(b"    skip (unsupported)")
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
            arnold.AiMsgDebug(b"    skip (unsupported)")

    ##############################
    ## duplicators
    for duplicator in duplicators:
        i = 0
        pc = time.perf_counter()
        arnold.AiMsgDebug(b"[DUPLI:%S:%S] '%S'", duplicator.type,
                         duplicator.dupli_type, duplicator.name)
        arnold.AiMsgTab(4)
        duplicator.dupli_list_create(scene, 'RENDER')
        try:
            for d in duplicator.dupli_list:
                ob = d.object
                if not ob.hide_render and ob.dupli_type not in {'VERTS', 'FACES'} and ob.type in _CT:
                    onode = nodes.get(ob)
                    if onode is None:
                        arnold.AiMsgDebug(b"[%S] '%S'", ob.type, ob.name)
                        with _Mesh(ob) as mesh:
                            if mesh is not None:
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
            arnold.AiMsgDebug(b"instances %d (%f)", ctypes.c_int(i),
                             ctypes.c_double(time.perf_counter() - pc))
        finally:
            arnold.AiMsgTab(-4)
            duplicator.dupli_list_clear()

    ##############################
    ## mesh lights
    for light_node, name in mesh_lights:
        ob = scene.objects.get(name)
        if ob is None:
            continue
        node = nodes.get(ob)
        if node is None:
            if ob.type not in _CT:
                continue
            arnold.AiMsgDebug(b"[%S] '%S'", ob.type, ob.name)
            with _Mesh(ob) as mesh:
                if mesh is not None:
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
    arnold.AiNodeSetInt(options, "GI_sss_samples", opts.GI_sss_samples)
    arnold.AiNodeSetBool(options, "sss_use_autobump", opts.sss_use_autobump)
    arnold.AiNodeSetInt(options, "GI_volume_samples", opts.GI_volume_samples)
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
        cdata = camera.data
        cp = cdata.arnold
        node = arnold.AiNode("persp_camera")
        arnold.AiNodeSetStr(node, "name", name)
        arnold.AiNodeSetMatrix(node, "matrix", _AiMatrix(mw))
        if cdata.sensor_fit == 'VERTICAL':
            sw = cdata.sensor_height * xres / yres * aspect_x / aspect_y
        else:
            sw = cdata.sensor_width
            if cdata.sensor_fit == 'AUTO':
                x = xres * aspect_x
                y = xres * aspect_y
                if x < y:
                    sw *= x / y
        fov = math.degrees(2 * math.atan(sw / (2 * cdata.lens)))
        arnold.AiNodeSetFlt(node, "fov", fov)
        if cdata.dof_object:
            dof = geometry.distance_point_to_plane(
                mw.to_translation(),
                cdata.dof_object.matrix_world.to_translation(),
                mw.col[2][:3]
            )
        else:
           dof = cdata.dof_distance
        arnold.AiNodeSetFlt(node, "focus_distance", dof)
        if cp.enable_dof:
            arnold.AiNodeSetFlt(node, "aperture_size", cp.aperture_size)
            arnold.AiNodeSetInt(node, "aperture_blades", cp.aperture_blades)
            arnold.AiNodeSetFlt(node, "aperture_rotation", cp.aperture_rotation)
            arnold.AiNodeSetFlt(node, "aperture_blade_curvature", cp.aperture_blade_curvature)
            arnold.AiNodeSetFlt(node, "aperture_aspect_ratio", cp.aperture_aspect_ratio)
        arnold.AiNodeSetFlt(node, "near_clip", cdata.clip_start)
        arnold.AiNodeSetFlt(node, "far_clip", cdata.clip_end)
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
    arnold.AiNodeSetStr(filter, "name", "__filter")
    if sft == 'blackman_harris_filter':
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_bh_width)
    elif sft == 'sinc_filter':
        arnold.AiNodeSetFlt(filter, "width", opts.sample_filter_sinc_width)
    elif sft in {'cone_filter',
                 'cook_filter',
                 'disk_filter',
                 'gaussian_filter',
                 'triangle_filter'}:
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
    arnold.AiNodeSetStr(display, "name", "__driver")
    arnold.AiNodeSetFlt(display, "gamma", opts.display_gamma)
    arnold.AiNodeSetBool(display, "rgba_packing", False)

    # TODO: unusable, camera flipped (top to buttom) for tiles hightlighting
    #png = arnold.AiNode("driver_png")
    #arnold.AiNodeSetStr(png, "name", "__png")
    #arnold.AiNodeSetStr(png, "filename", render.frame_path())

    outputs_aovs = (
        b"RGBA RGBA __filter __driver",
        #b"RGBA RGBA __filter __png"
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

    arnold.AiMsgDebug(b"BARNOLD: <<<")


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
                    result = _htiles.pop((_x, _y), None)
                    if result is None:
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


def view_update(engine, context):
    print(">>> view_update [%f]:" % time.clock(), engine)
    try:
        ipr = getattr(engine, "_ipr", None)
        if ipr is None:
            blend_data = context.blend_data
            scene = context.scene
            region = context.region
            v3d = context.space_data
            rv3d = context.region_data

            nodes = []
            _nodes = {}

            @contextmanager
            def _to_mesh(ob):
                pc = time.perf_counter()
                mesh = ob.to_mesh(scene, True, 'PREVIEW', False)
                if mesh is not None:
                    try:
                        mesh.calc_normals_split()
                        print("    to_mesh (%f)" % (time.perf_counter() - pc))
                        yield mesh
                    finally:
                        # it force call view_update
                        blend_data.meshes.remove(mesh)
                else:
                    yield None

            def _AiNode(node, prefix):
                anode = _nodes.get(node)
                if anode is None and isinstance(node, ArnoldNode):
                    params = {'name': ('STRING', "%s&N::%s" % (prefix, node.name))}
                    for input in node.inputs:
                        if input.is_linked:
                            _anode = _AiNode(input.links[0].from_node, prefix)
                            if _anode is not None:
                                params[input.identifier] = ('LINK', _anode)
                                continue
                        if not input.hide_value:
                            v = input.default_value
                            if input.bl_idname in {'NodeSocketColor',
                                                   'NodeSocketVector',
                                                   'NodeSocketVectorXYZ',
                                                   'ArnoldNodeSocketColor'}:
                                v = v[:]
                            params[input.identifier] = (input.bl_idname, v)
                    for n, (t, v) in node.ai_properties.items():
                        if t in {'RGB', 'RGBA', 'VECTOR'}:
                            v = v[:]
                        params[n] = (t, v)
                    anode = (node.ai_name, params)
                    _nodes[node] = anode
                    nodes.append(anode)
                return anode

            for ob in scene.objects:
                if ob.is_visible(scene) and ob.type in _CT:
                    with _to_mesh(ob) as mesh:
                        if mesh is not None:
                            verts = mesh.vertices
                            polygons = mesh.polygons
                            loops = mesh.loops
                            vlist = numpy.ndarray(len(verts) * 3, dtype=numpy.float32)
                            verts.foreach_get("co", vlist)
                            nsides = numpy.ndarray(len(polygons), dtype=numpy.uint32)
                            polygons.foreach_get("loop_total", nsides)
                            vidxs = numpy.ndarray(len(loops), dtype=numpy.uint32)
                            polygons.foreach_get("vertices", vidxs)
                            nodes.append(('polymesh', {
                                'name': ('STRING', "O::" + ob.name),
                                'matrix': ('MATRIX', numpy.reshape(ob.matrix_world.transposed(), -1)),
                                'vlist': ('ARRAY', (arnold.AI_TYPE_POINT, vlist)),
                                'nsides': ('ARRAY', (arnold.AI_TYPE_UINT, nsides)),
                                'vidxs': ('ARRAY', (arnold.AI_TYPE_UINT, vidxs)),
                                #'smoothing': ('BOOL', True),
                            }))

            #####################################
            ## camera
            view_matrix = rv3d.view_matrix.copy()
            _camera = {
                'name': ('STRING', '__camera'),
                'matrix': ('MATRIX', numpy.reshape(view_matrix.inverted().transposed(), -1)),
            }
            view_perspective = rv3d.view_perspective
            if view_perspective == 'CAMERA':
                camera_data = _view_update_camera(region.width / region.height, v3d, rv3d, _camera)
            elif view_perspective == 'PERSP':
                camera_data = _view_update_persp(v3d, _camera)
            else:  # view_perspective == 'PERSP'
                pass
            camera = ('persp_camera', _camera)
            nodes.append(camera)

            #####################################
            ## options
            opts = scene.arnold
            options = {
                'camera': ('NODE', camera),
                'thread_priority': ('STRING', opts.thread_priority),
                'pin_threads': ('STRING', opts.pin_threads),
                'abort_on_error': ('BOOL', opts.abort_on_error),
                'abort_on_license_fail': ('BOOL', opts.abort_on_license_fail),
                'skip_license_check': ('BOOL', opts.skip_license_check),
                'error_color_bad_texture': ('RGB', opts.error_color_bad_texture[:]),
                'error_color_bad_pixel': ('RGB', opts.error_color_bad_pixel[:]),
                'error_color_bad_shader': ('RGB', opts.error_color_bad_shader[:]),
                'bucket_size': ('INT', opts.ipr_bucket_size),
                'bucket_scanning': ('STRING', opts.bucket_scanning),
                'ignore_textures': ('BOOL', opts.ignore_textures),
                'ignore_shaders': ('BOOL', opts.ignore_shaders),
                'ignore_atmosphere': ('BOOL', opts.ignore_atmosphere),
                'ignore_lights': ('BOOL', opts.ignore_lights),
                'ignore_shadows': ('BOOL', opts.ignore_shadows),
                'ignore_direct_lighting': ('BOOL', opts.ignore_direct_lighting),
                'ignore_subdivision': ('BOOL', opts.ignore_subdivision),
                'ignore_displacement': ('BOOL', opts.ignore_displacement),
                'ignore_bump': ('BOOL', opts.ignore_bump),
                'ignore_motion_blur': ('BOOL', opts.ignore_motion_blur),
                'ignore_dof': ('BOOL', opts.ignore_dof),
                'ignore_smoothing': ('BOOL', opts.ignore_smoothing),
                'ignore_sss': ('BOOL', opts.ignore_sss),
                'auto_transparency_mode': ('STRING', opts.auto_transparency_mode),
                'auto_transparency_depth': ('INT', opts.auto_transparency_depth),
                'auto_transparency_threshold': ('FLOAT', opts.auto_transparency_threshold),
                'texture_max_open_files': ('INT', opts.texture_max_open_files),
                'texture_max_memory_MB': ('FLOAT', opts.texture_max_memory_MB),
                'texture_searchpath': ('STRING', opts.texture_searchpath),
                'texture_automip': ('BOOL', opts.texture_automip),
                'texture_autotile': ('INT', opts.texture_autotile),
                'texture_accept_untiled': ('BOOL', opts.texture_accept_untiled),
                'texture_accept_unmipped': ('BOOL', opts.texture_accept_unmipped),
                'texture_glossy_blur': ('FLOAT', opts.texture_glossy_blur),
                'texture_diffuse_blur': ('FLOAT', opts.texture_diffuse_blur),
                'low_light_threshold': ('FLOAT', opts.low_light_threshold),
                'GI_sss_samples': ('INT', opts.GI_sss_samples),
                'sss_use_autobump': ('BOOL', opts.sss_use_autobump),
                'GI_volume_samples': ('INT', opts.GI_volume_samples),
                'max_subdivisions': ('INT', opts.max_subdivisions),
                'procedural_searchpath': ('STRING', opts.procedural_searchpath),
                'shader_searchpath': ('STRING', opts.shader_searchpath),
                'texture_gamma': ('FLOAT', opts.texture_gamma),
                'light_gamma': ('FLOAT', opts.light_gamma),
                'shader_gamma': ('FLOAT', opts.shader_gamma),
                'GI_diffuse_depth': ('INT', opts.GI_diffuse_depth),
                'GI_glossy_depth': ('INT', opts.GI_glossy_depth),
                'GI_reflection_depth': ('INT', opts.GI_reflection_depth),
                'GI_refraction_depth': ('INT', opts.GI_refraction_depth),
                'GI_volume_depth': ('INT', opts.GI_volume_depth),
                'GI_total_depth': ('INT', opts.GI_total_depth),
                'GI_diffuse_samples': ('INT', opts.GI_diffuse_samples),
                'GI_glossy_samples': ('INT', opts.GI_glossy_samples),
                'GI_refraction_samples': ('INT', opts.GI_refraction_samples),
            }

            #####################################
            ## world
            world = scene.world
            if world and world.use_nodes:
                for _node in world.node_tree.nodes:
                    if isinstance(_node, ArnoldNodeWorldOutput) and _node.is_active:
                        for input in _node.inputs:
                            if input.is_linked:
                                node = _AiNode(input.links[0].from_node, "W::" + world.name)
                                if node:
                                    options[input.identifier] = ('NODE', node)

            #from pprint import pprint as pp
            #pp(options)
            #pp(nodes)

            ipr = _IPR(engine, {
                'options': options,
                'nodes': nodes,
                'sl': (opts.initial_sampling_level, opts.AA_samples)
            }, region.width, region.height)

            ipr.view_perspective = view_perspective
            ipr.view_matrix = view_matrix
            ipr.camera_data = camera_data

            engine._ipr = ipr
    except:
        print("~" * 30)
        traceback.print_exc()
        print("~" * 30)


def view_draw(engine, context):
    #print(">>> view_draw [%f]:" % time.clock(), engine)
    try:
        region = context.region
        v3d = context.space_data
        rv3d = context.region_data

        data = {}
        _camera = {}
        ipr = engine._ipr
        width = region.width
        height = region.height

        view_matrix = rv3d.view_matrix
        if view_matrix != ipr.view_matrix:
            ipr.view_matrix = view_matrix.copy()
            _camera['matrix'] = ('MATRIX', numpy.reshape(view_matrix.inverted().transposed(), -1))

        view_perspective = rv3d.view_perspective
        if view_perspective != ipr.view_perspective:
            ipr.view_perspective = view_perspective
            if view_perspective == 'CAMERA':
                ipr.camera_data = _view_update_camera(region.width / region.height, v3d, rv3d, _camera)
            elif view_perspective == 'PERSP':
                ipr.camera_data = _view_update_persp(v3d, _camera)
            else:
                # TODO: orpho
                return
        elif view_perspective == 'CAMERA':
            cdata = v3d.camera.data
            fit = cdata.sensor_fit
            sensor = cdata.sensor_height if fit == 'VERTICAL' else cdata.sensor_width
            offset_x, offset_y = rv3d.view_camera_offset
            camera_data = (rv3d.view_camera_zoom, fit, sensor, cdata.lens,
                           offset_x, offset_y, cdata.shift_x, cdata.shift_y)
            if camera_data != ipr.camera_data:
                ipr.camera_data = _view_update_camera(region.width / region.height, v3d, rv3d, _camera)
        elif view_perspective == 'PERSP':
            lens = v3d.lens
            if lens != ipr.camera_data[0]:
                _camera['fov'] = ('FLOAT', math.degrees(2 * math.atan(64.0 / (2 * lens))))
                ipr.camera_data = (lens, )
        else:
            # TODO: orpho
            return

        if _camera:
            data.setdefault('nodes', {})['__camera'] = _camera

        (width, height), rect = ipr.update(width, height, data)

        v = bgl.Buffer(bgl.GL_FLOAT, 4)
        bgl.glGetFloatv(bgl.GL_VIEWPORT, v)
        vw = v[2]
        vh = v[3]
        bgl.glRasterPos2f(0, vh - 1.0)
        bgl.glPixelZoom(vw / width, -vh / height)
        bgl.glDrawPixels(width, height, bgl.GL_RGBA, bgl.GL_FLOAT,
                         bgl.Buffer(bgl.GL_FLOAT, len(rect), rect))
        bgl.glPixelZoom(1.0, 1.0)
        bgl.glRasterPos2f(0, 0)
    except:
        print("~" * 30)
        traceback.print_exc()
        print("~" * 30)


def free(engine):
    print(">>> free: [%f]:" % time.clock(), engine)
    if hasattr(engine, "_ipr"):
        engine._ipr.stop()
        del engine._ipr


def _view_update_camera(aspect, v3d, rv3d, camera):
    zoom = rv3d.view_camera_zoom
    z = ((_SQRT2 + zoom / 50) ** 2) / 4

    cdata = v3d.camera.data
    fit = cdata.sensor_fit
    if fit == 'VERTICAL':
        sensor = cdata.sensor_height
        _sensor = (16 * sensor / 9) / z  # sensor / (18 / 32)
        z *= 9 / 16  # 18 / 32
    else:
        sensor = cdata.sensor_width
        _sensor = sensor / z
    lens = cdata.lens
    camera['fov'] = ('FLOAT', math.degrees(2 * math.atan(_sensor / (2 * lens))))

    offset_x, offset_y = rv3d.view_camera_offset
    shift_x = cdata.shift_x
    shift_y = cdata.shift_y
    shx = 2 * z * (2 * offset_x + shift_x)
    shy = 2 * z * (2 * offset_y + shift_y * aspect)
    camera['screen_window_min'] = ('POINT2', (-1 + shx, -1 + shy))
    camera['screen_window_max'] = ('POINT2', (1 + shx, 1 + shy))

    return (zoom, fit, sensor, lens, offset_x, offset_y, shift_x, shift_y)


def _view_update_persp(v3d, camera):
    lens = v3d.lens
    camera['fov'] = ('FLOAT', math.degrees(2 * math.atan(64.0 / (2 * lens))))
    camera['screen_window_min'] = ('POINT2', (-1, -1))
    camera['screen_window_max'] = ('POINT2', (1, 1))
    return (lens, )
