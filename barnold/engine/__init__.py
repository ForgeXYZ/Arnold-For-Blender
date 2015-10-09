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

import bpy
from mathutils import Matrix, Vector, geometry
from ..nodes import (
    ArnoldNode,
    ArnoldNodeOutput,
    ArnoldNodeWorldOutput
)
from . import arnold


_M = 1 / 255
_RN = re.compile("[^-0-9A-Za-z_]")


def _CleanNames(prefix, count):
    def fn(name):
        return "%s%d#%s" % (prefix, next(count), _RN.sub("_", name))
    return fn


def _AiMatrix(m):
    """
    m: mathutils.Matrix
    returns: pointer to AtArray
    """
    t = numpy.reshape(m.transposed(), [-1])
    matrix = arnold.AiArrayAllocate(1, 1, arnold.AI_TYPE_MATRIX)
    arnold.AiArraySetMtx(matrix, 0, arnold.AtMatrix(*t))
    return matrix


_AiNodeSet = {
    "NodeSocketShader": lambda n, i, v: True,
    "NodeSocketBool": lambda n, i, v: arnold.AiNodeSetBool(n, i, v),
    "NodeSocketInt": lambda n, i, v: arnold.AiNodeSetInt(n, i, v),
    "NodeSocketFloat": lambda n, i, v: arnold.AiNodeSetFlt(n, i, v),
    "NodeSocketColor": lambda n, i, v: arnold.AiNodeSetRGBA(n, i, *v),
    "NodeSocketVector": lambda n, i, v: arnold.AiNodeSetVec(n, i, *v),
    "NodeSocketString": lambda n, i, v: arnold.AiNodeSetStr(n, i, v),
    "ArnoldNodeSocketColor": lambda n, i, v: arnold.AiNodeSetRGB(n, i, *v),
    "ArnoldNodeSocketByte": lambda n, i, v: arnold.AiNodeSetByte(n, i, v)
}


def _AiNode(node, prefix, nodes):
    """
    Args:
        node (ArnoldNode): node.
        prefix (str): node name prefix.
        nodes (dict): created nodes (Node => AiNode).
    Returns:
        arnold.AiNode or None
    """
    if not isinstance(node, ArnoldNode):
        return None

    anode = nodes.get(node)
    if anode is None:
        # TODO: make node names unique
        name = "%s:%s" % (prefix, _RN.sub("_", node.name))
        anode = arnold.AiNode(node.ai_name)
        arnold.AiNodeSetStr(anode, "name", name)
        for input in node.inputs:
            if input.is_linked:
                _anode = _AiNode(input.links[0].from_node, prefix, nodes)
                if not _anode is None:
                    arnold.AiNodeLink(_anode, input.identifier, anode)
                    continue
            if not input.hide_value:
                _AiNodeSet[input.bl_idname](anode, input.identifier, input.default_value)
        for p_name, (p_type, p_value) in node.ai_properties.items():
            if p_type == 'FILE_PATH':
                arnold.AiNodeSetStr(anode, p_name, bpy.path.abspath(p_value))
            elif p_type == 'STRING':
                arnold.AiNodeSetStr(anode, p_name, p_value)
        nodes[node] = anode
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
        arnold.AiNodeSetStr(node, "name", self._Name(mat.name))
        return node


def _AiPolymesh(data, scene, shaders, ob):
    #pc = time.perf_counter()
    print("%s: %s" % (ob.type, ob.name))

    node = None
    mesh = ob.to_mesh(scene, True, 'RENDER', False)
    try:
        #print(" %14.6f: ob.to_mesh()" % (time.perf_counter() - pc))

        mesh.calc_normals_split()
        # No need to call mesh.free_normals_split later, as this mesh is deleted anyway!

        #pc1 = time.perf_counter()
        #print(" %14.6f: mesh.calc_normals_split()" % (pc1 - pc))

        node = arnold.AiNode('polymesh')
        arnold.AiNodeSetBool(node, "smoothing", True)

        verts = mesh.vertices
        nverts = len(verts)
        loops = mesh.loops
        nloops = len(loops)
        polygons = mesh.polygons
        npolygons = len(polygons)

        # vertices
        a = numpy.ndarray([nverts * 3], dtype=numpy.float32)
        verts.foreach_get("co", a)
        vlist = arnold.AiArrayConvert(nverts, 1, arnold.AI_TYPE_POINT, ctypes.c_void_p(a.ctypes.data))
        arnold.AiNodeSetArray(node, "vlist", vlist)

        #pc2 = time.perf_counter()
        #print(" %14.6f: (%10.6f) vertices %s" % (pc2 - pc, pc2 - pc1, nverts))

        # normals
        a = numpy.ndarray([nloops * 3], dtype=numpy.float32)
        loops.foreach_get("normal", a)
        nlist = arnold.AiArrayConvert(nloops, 1, arnold.AI_TYPE_VECTOR, ctypes.c_void_p(a.ctypes.data))
        arnold.AiNodeSetArray(node, "nlist", nlist)

        #pc3 = time.perf_counter()
        #print(" %14.6f: (%10.6f) normals %d" % (pc3 - pc, pc3 - pc2, nloops))

        # polygons
        a = numpy.ndarray([npolygons], dtype=numpy.uint32)
        polygons.foreach_get("loop_total", a)
        nsides = arnold.AiArrayConvert(npolygons, 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))
        arnold.AiNodeSetArray(node, "nsides", nsides)

        a = numpy.ndarray([nloops], dtype=numpy.uint32)
        polygons.foreach_get("vertices", a)
        vidxs = arnold.AiArrayConvert(nloops, 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))
        arnold.AiNodeSetArray(node, "vidxs", vidxs)

        #print(" %14.6f: ..." % (time.perf_counter() - pc))

        # TODO: very slow, seems it always a range(0, nloops)
        #a = numpy.array([i for p in polygons for i in p.loop_indices], dtype=numpy.uint32)
        #nidxs = arnold.AiArrayConvert(len(a), 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))
        a = numpy.arange(nloops, dtype=numpy.uint32)
        nidxs = arnold.AiArrayConvert(nloops, 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))
        arnold.AiNodeSetArray(node, "nidxs", nidxs)

        #pc4 = time.perf_counter()
        #print(" %14.6f: (%10.6f) polygons %d" % (pc4 - pc, pc4 - pc3, npolygons))

        # uv
        for i, uvt in enumerate(mesh.uv_textures):
            if uvt.active_render:
                uvd = mesh.uv_layers[i].data
                nuvs = len(uvd)

                a = numpy.arange(nuvs, dtype=numpy.uint32)
                uvidxs = arnold.AiArrayConvert(nuvs, 1, arnold.AI_TYPE_UINT, ctypes.c_void_p(a.ctypes.data))
                arnold.AiNodeSetArray(node, "uvidxs", uvidxs)

                a = numpy.ndarray([nuvs * 2], dtype=numpy.float32)
                uvd.foreach_get("uv", a)
                uvlist = arnold.AiArrayConvert(nuvs, 1, arnold.AI_TYPE_POINT2, ctypes.c_void_p(a.ctypes.data))
                arnold.AiNodeSetArray(node, "uvlist", uvlist)

                #pc5 = time.perf_counter()
                #print(" %14.6f: (%10.6f) uvs %d" % (pc5 - pc, pc5 - pc4, nuvs))
                break
        #else:
        #    pc5 = time.perf_counter()

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
                    arnold.AiNodeSetArray(node, "shader", shader)

                    shidxs = arnold.AiArrayConvert(len(a), 1, arnold.AI_TYPE_BYTE, ctypes.c_void_p(a.ctypes.data))
                    arnold.AiNodeSetArray(node, "shidxs", shidxs)
                else:
                    arnold.AiNodeSetPtr(node, "shader", t[1][0])

                #pc6 = time.perf_counter()
                #print(" %14.6f: (%10.6f) shaders %d" % (pc6 - pc, pc6 - pc5, nmm))
    finally:
        data.meshes.remove(mesh)
    return node


def _export(data, scene, camera, xres, yres, session=None):
    render = scene.render
    opts = scene.arnold

    # enabled scene layers
    layers = [i for i, j in enumerate(scene.layers) if j]
    in_layers = lambda o: any(o.layers[i] for i in layers)
    # nodes cache
    nodes = {}  # {Object: AiNode}
    inodes = {}  # {Object.data: AiNode}
    duplicators = []

    _Name = _CleanNames("O", itertools.count())

    shaders = Shaders(data)

    arnold.AiMsgSetConsoleFlags(opts.get("console_log_flags", 0))
    arnold.AiMsgSetMaxWarnings(opts.max_warnings)

    plugins_path = os.path.normpath(os.path.join(os.path.dirname(__file__), os.path.pardir, "bin"))
    arnold.AiLoadPlugins(plugins_path)

    ##############################
    ## objects
    for ob in scene.objects:
        if ob.hide_render or not in_layers(ob):
            continue

        if ob.is_duplicator:
            duplicators.append(ob)
            continue

        if ob.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            modified = ob.is_modified(scene, 'RENDER')
            if not modified:
                inode = inodes.get(ob.data)
                if not inode is None:
                    node = arnold.AiNode("ginstance")
                    arnold.AiNodeSetStr(node, "name", _Name(ob.name))
                    arnold.AiNodeSetArray(node, "matrix", _AiMatrix(ob.matrix_world))
                    arnold.AiNodeSetBool(node, "inherit_xform", False)
                    arnold.AiNodeSetPtr(node, "node", inode)
                    continue

            node = _AiPolymesh(data, scene, shaders, ob)
            arnold.AiNodeSetStr(node, "name", _Name(ob.name))
            arnold.AiNodeSetArray(node, "matrix", _AiMatrix(ob.matrix_world))

            if not modified:
                # cache unmodified shapes for instancing
                inodes[ob.data] = node
            # cache for duplicators
            nodes[ob] = node
        elif ob.type == 'LAMP':
            lamp = ob.data
            light = lamp.arnold
            if lamp.type == 'POINT':
                node = arnold.AiNode("point_light")
                arnold.AiNodeSetFlt(node, "radius", light.point.radius)
                arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
            #elif lamp.type == 'HEMI':
            #    node = arnold.AiNode("ambient_light")  # there is no such node in current sdk
            elif lamp.type == 'SUN':
                node = arnold.AiNode("distant_light")
            else:
                continue
            arnold.AiNodeSetStr(node, "name", _Name(ob.name))
            arnold.AiNodeSetRGB(node, "color", *lamp.color)
            arnold.AiNodeSetFlt(node, "intensity", light.intensity)
            arnold.AiNodeSetFlt(node, "exposure", light.exposure)
            arnold.AiNodeSetBool(node, "cast_shadows", light.cast_shadows)
            arnold.AiNodeSetBool(node, "cast_volumetric_shadows", light.cast_volumetric_shadows)
            arnold.AiNodeSetFlt(node, "shadow_density", light.shadow_density)
            arnold.AiNodeSetRGB(node, "shadow_color", *light.shadow_color)
            arnold.AiNodeSetInt(node, "samples", light.samples)
            arnold.AiNodeSetBool(node, "normalize", light.normalize)
            arnold.AiNodeSetArray(node, "matrix", _AiMatrix(ob.matrix_world))

    ##############################
    ## duplicators
    for d in duplicators:
        if d.dupli_type == 'GROUP':
            d.dupli_list_create(scene, 'RENDER')
            try:
                for dlo in d.dupli_list:
                    ob = dlo.object
                    onode = nodes.get(ob)
                    if onode is None:
                        # TODO: check object type, must be convertable to mesh
                        onode = _AiPolymesh(data, scene, shaders, ob)
                        arnold.AiNodeSetStr(onode, "name", _Name(ob.name))
                        arnold.AiNodeSetArray(onode, "matrix", _AiMatrix(dlo.matrix))
                        nodes[ob] = onode
                        continue
                    node = arnold.AiNode("ginstance")
                    arnold.AiNodeSetStr(node, "name", _Name(ob.name))
                    arnold.AiNodeSetArray(node, "matrix", _AiMatrix(dlo.matrix))
                    arnold.AiNodeSetBool(node, "inherit_xform", False)
                    arnold.AiNodeSetPtr(node, "node", onode)
            finally:
                d.dupli_list_clear()

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
        mw = camera.matrix_world
        node = arnold.AiNode("persp_camera")
        arnold.AiNodeSetStr(node, "name", camera.name)
        arnold.AiNodeSetArray(node, "matrix", _AiMatrix(mw))
        cd = camera.data
        cp = cd.arnold
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
        if not session is None:
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
                    _n = "W#" + _RN.sub("_", world.name)
                    for input in _node.inputs:
                        if input.is_linked:
                            node = _AiNode(input.links[0].from_node, _n, {})
                            if node:
                                arnold.AiNodeSetPtr(options, input.identifier, node)
                    break
        else:
            # TODO: export world settings
            pass

    ##############################
    ## outputs
    sft = opts.sample_filter_type
    filter = arnold.AiNode(opts.sample_filter_type)
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
            if engine.test_break():
                arnold.AiRenderAbort()
                while _htiles:
                    (x, y), result = _htiles.popitem()
                    engine.end_result(result, True)
            else:
                x -= xoff
                y -= yoff
                if buffer:
                    result = _htiles.pop((x, y))
                    if not result is None:
                        result = engine.begin_result(x, y, width, height)
                    _buffer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_float))
                    rect = numpy.ctypeslib.as_array(_buffer, shape=(width * height, 4))
                    rect **= 2.2  # gamma correction
                    result.layers[0].passes[0].rect = rect
                    engine.end_result(result)
                else:
                    result = engine.begin_result(x, y, width, height)
                    # TODO: sometimes highlighted tiles become empty
                    #engine.update_result(result)
                    _htiles[(x, y)] = result
            mem = arnold.AiMsgUtilGetUsedMemory() / 1048576  # 1024*1024
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
                    engine.update_stats("", "SL: %d" % sl)
        if res != arnold.AI_SUCCESS:
            engine.error_set("Render status: %d" % res)
    except:
        # cancel render on error
        engine.end_result(None, True)
    finally:
        del engine._session
        arnold.AiEnd()
