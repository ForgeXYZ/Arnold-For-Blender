# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import os
import sys
import ctypes
import itertools
import numpy
import math

import bpy
from mathutils import Matrix, Vector
from ..nodes import ArnoldNode, ArnoldNodeOutput, ArnoldNodeWorldOutput

from . import arnold


_TILE_COLORS = [
    (0, 0, 0),
    (1, 0, 0),
    (0, 1, 0),
    (0, 0, 1),
    (1, 1, 0),
    (0, 1, 1),
    (1, 0, 1),
    (1, 1, 1)
]
_M = 1 / 255


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
        nodes (dict): created nodes (str => AiNode).
    Returns:
        arnold.AiNode or None
    """
    if not isinstance(node, ArnoldNode):
        return None

    name = "%s:%s" % (prefix, node.name)
    name = name.replace(" ", "_")
    anode = nodes.get(name)
    if anode is None:
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
        nodes[name] = anode
    return anode


def _AiNodeTree(prefix, ntree):
    for node in ntree.nodes:
        if isinstance(node, ArnoldNodeOutput) and node.is_active:
            input = node.inputs[0]
            if input.is_linked:
                return _AiNode(input.links[0].from_node, prefix, {})
            break
    return None


class Shaders:
    def __init__(self, data):
        self._data = data

        self._shaders = {}
        self._default = None  # default shader, if used

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
        if mat.use_nodes:
            return _AiNodeTree(mat.name, mat.node_tree)

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
        return node


def export(data, scene, camera, xres, yres, session=None, ass_filepath=None):
    render = scene.render
    opts = scene.arnold

    # enabled scene layers
    layers = [i for i, x in enumerate(scene.layers) if x]
    # offsets for border render
    xoff = 0
    yoff = 0

    shaders = Shaders(data)

    arnold.AiBegin()
    arnold.AiMsgSetConsoleFlags(opts.get("console_log_flags", 0))

    plugins_path = os.path.normpath(os.path.join(os.path.dirname(__file__), os.path.pardir, "bin"))
    arnold.AiLoadPlugins(plugins_path)

    for ob in scene.objects:
        if ob.hide_render:
            continue
        for i in layers:
            if ob.layers[i]:
                break
        else:
            continue
        if ob.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            mesh = ob.to_mesh(scene, True, 'RENDER', False)
            try:
                mesh.calc_normals_split()
                # No need to call mesh.free_normals_split later, as this mesh is deleted anyway!
                node = arnold.AiNode('polymesh')
                arnold.AiNodeSetStr(node, "name", ob.name)
                arnold.AiNodeSetBool(node, "smoothing", True)
                arnold.AiNodeSetArray(node, "matrix", _AiMatrix(ob.matrix_world))
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
                        for i, idx in enumerate(idxs):
                            arnold.AiArraySetByte(shidxs, i, idx)
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
                arnold.AiNodeSetStr(node, "decay_type", light.decay_type)
            #elif lamp.type == 'HEMI':
            #    node = arnold.AiNode("ambient_light")  # there is no such node in current sdk
            elif lamp.type == 'SUN':
                node = arnold.AiNode("distant_light")
            else:
                continue
            arnold.AiNodeSetStr(node, "name", ob.name)
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

    options = arnold.AiUniverseGetOptions()
    arnold.AiNodeSetInt(options, "xres", xres)
    arnold.AiNodeSetInt(options, "yres", yres)
    arnold.AiNodeSetFlt(options, "aspect_ratio", render.pixel_aspect_y / render.pixel_aspect_x)  # TODO: different with blender render if ratio > 1.0
    if render.use_border:
        xoff = int(xres * render.border_min_x)
        yoff = int(yres * render.border_min_y) + 1
        arnold.AiNodeSetInt(options, "region_min_x", xoff)
        arnold.AiNodeSetInt(options, "region_max_x", int(xres * render.border_max_x) - 1)
        arnold.AiNodeSetInt(options, "region_min_y", int(yres * (1.0 - render.border_max_y)))
        arnold.AiNodeSetInt(options, "region_max_y", int(yres * (1.0 - render.border_min_y)) - 1)
    arnold.AiNodeSetBool(options, "skip_license_check", opts.skip_license_check)
    arnold.AiNodeSetInt(options, "AA_samples", opts.AA_samples)
    if not opts.lock_sampling_pattern:
        arnold.AiNodeSetInt(options, "AA_seed", scene.frame_current)
    arnold.AiNodeSetInt(options, "threads", opts.threads)
    arnold.AiNodeSetStr(options, "thread_priority", opts.thread_priority)
    arnold.AiNodeSetInt(options, "bucket_size", opts.bucket_size)
    arnold.AiNodeSetStr(options, "bucket_scanning", opts.bucket_scanning)

    if camera:
        node = arnold.AiNode("persp_camera")
        arnold.AiNodeSetStr(node, "name", camera.name)
        arnold.AiNodeSetFlt(node, "fov", math.degrees(camera.data.angle))
        arnold.AiNodeSetArray(node, "matrix", _AiMatrix(camera.matrix_world))
        arnold.AiNodeSetPtr(options, "camera", node)
    
    world = scene.world
    if world:
        if world.use_nodes:
            for _node in world.node_tree.nodes:
                if isinstance(_node, ArnoldNodeWorldOutput) and _node.is_active:
                    for input in _node.inputs:
                        if input.is_linked:
                            node = _AiNode(input.links[0].from_node, world.name, {})
                            if node:
                                arnold.AiNodeSetPtr(options, input.identifier, node)
                    break
        else:
            # TODO: export worl settings
            pass

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
    outputs = arnold.AiArray(1, 1, arnold.AI_TYPE_STRING, b"RGBA RGBA __outfilter __outdriver")
    arnold.AiNodeSetArray(options, "outputs", outputs)

    if session is not None:
        session["display"] = display
        session["offset"] = xoff, yoff

    if ass_filepath:
        # TODO: options
        arnold.AiNodeSetStr(options, "shader_searchpath", plugins_path)
        arnold.AiASSWrite(ass_filepath, arnold.AI_NODE_ALL, False, False)
        arnold.AiEnd()


def update(engine, data, scene):
    engine._session = {}
    export(
        data,
        scene,
        engine.camera_override,
        engine.resolution_x,
        engine.resolution_y,
        session=engine._session
    )


def render(engine, scene):
    try:
        session = engine._session
        xoff, yoff = session["offset"]

        _tiles = {}
        _colors = itertools.cycle(_TILE_COLORS)
        session["peak"] = 0  # memory peak usage

        def display_callback(x, y, width, height, buffer, data):
            if engine.test_break():
                arnold.AiRenderAbort()
                for (_x , _y), (w, h) in _tiles.items():
                    result = engine.begin_result(_x, _y, w, h)
                    result.layers[0].passes[0].rect = numpy.zeros([w * h, 4])
                    engine.end_result(result)
                return

            x -= xoff
            y = engine.resolution_y - y - height - yoff
            result = engine.begin_result(x, y, width, height)
            if buffer:
                _tiles.pop((x, y))
                t = ctypes.c_byte * (width * height * 4)
                a = t.from_address(ctypes.addressof(buffer.contents))
                rect = numpy.frombuffer(a, numpy.uint8) * _M
                rect = numpy.reshape(rect, [height, width * 4])
                rect = numpy.reshape(numpy.flipud(rect), [-1, 4])
                rect **= 2  # gamma correction
            else:
                _tiles[(x, y)] = (width, height)
                color = next(_colors)
                rect = numpy.ndarray([width * height, 4])
                rect[:] = color + (0.05, )
                color = color + (1.0, )
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
            engine.end_result(result)

            mem = arnold.AiMsgUtilGetUsedMemory() / 1048576  # 1024*1024
            peak = session["peak"] = max(session["peak"], mem)
            engine.update_memory_stats(mem, peak)

        # display callback must be a variable
        cb = arnold.AtDisplayCallBack(display_callback)
        arnold.AiNodeSetPtr(session['display'], "callback", cb)
        arnold.AiRender(arnold.AI_RENDER_MODE_CAMERA)
    except:
        # cancel render on error
        engine.end_result(None, True)
    finally:
        del engine._session
        arnold.AiEnd()
