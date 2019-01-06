# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import collections

import bpy
from bpy.app.handlers import persistent


import _cycles
import xml.etree.ElementTree as ET

import tempfile
import nodeitems_utils
import shutil

from bpy.types import NodeTree, NodeSocket, Node, ColorRamp, PropertyGroup
from bpy.props import *
from nodeitems_utils import NodeCategory, NodeItem

from mathutils import Matrix, Euler, Color
from bl_ui.space_node import NODE_HT_header, NODE_MT_editor_menus
import nodeitems_utils

from . icons.icons import load_icons
from . import ArnoldRenderEngine
from . import props

from .cycles_convert import convert_cycles_node
import barnold.ui as ui


_WRAP_ITEMS = [
    ('periodic', "Periodic", "Periodic"),
    ('black', "Black", "Black"),
    ('clamp', "Clamp", "Clamp"),
    ('mirror', "Mirror", "Mirror"),
    ('file', "File", "File")
]


def _draw_property(layout, data, identifier, links):
    state = links.get(identifier, None)
    row = layout.row(align=True)
    sub = row.row(align=True)
    if state is True:
        icon = 'PROP_ON'
        sub.enabled = False
    elif state is False:
        icon = 'PROP_CON'
    else:
        icon = 'PROP_OFF'
    sub.prop(data, identifier)
    op = row.operator("barnold.node_socket_add", text="", icon=icon)
    op.identifier = identifier

def find_node(material, nodetype):
    if material and material.node_tree:
        ntree = material.node_tree

        active_output_node = None
        for node in ntree.nodes:
            if getattr(node, "bl_idname", None) == nodetype:
                if getattr(node, "is_active_output", True):
                    return node
                if not active_output_node:
                    active_output_node = node
        return active_output_node

    return None

def is_arnold_nodetree(material):
    return find_node(material, 'ArnoldNodeOutput')

def set_ouput_node_location(nt, output_node, cycles_output):
    output_node.location = cycles_output.location
    output_node.location[1] -= 500

def offset_node_location(arnold_parent, arnold_node, cycles_node):
    linked_socket = next((sock for sock in cycles_node.outputs if sock.is_linked),
                         None)
    arnold_node.location = arnold_parent.location
    if linked_socket:
        arnold_node.location += (cycles_node.location -
                               linked_socket.links[0].to_node.location)

def create_arnold_surface(nt, parent_node, input_index, node_type="ArnoldNodeStandardSurface"):
    layer = nt.nodes.new(node_type)
    nt.links.new(layer.outputs[0], parent_node.inputs[input_index])
    #setattr(layer, 'enableDiffuse', False)

    layer.location = parent_node.location
    layer.diffuseGain = 0
    layer.location[0] -= 300
    return layer

combine_nodes = ['ShaderNodeAddShader', 'ShaderNodeMixShader']

def convert_cycles_bsdf(nt, arnold_parent, node, input_index):

    # if mix or add pass both to parent
    if node.bl_idname in combine_nodes:
        i = 0 if node.bl_idname == 'ShaderNodeAddShader' else 1

        node1 = node.inputs[
            0 + i].links[0].from_node if node.inputs[0 + i].is_linked else None
        node2 = node.inputs[
            1 + i].links[0].from_node if node.inputs[1 + i].is_linked else None

        if not node1 and not node2:
            return
        elif not node1:
            convert_cycles_bsdf(nt, arnold_parent, node2, input_index)
        elif not node2:
            convert_cycles_bsdf(nt, arnold_parent, node1, input_index)

        # if ones a combiner or they're of the same type and not glossy we need
        # to make a mixer
        elif node.bl_idname == 'ShaderNodeMixShader' or node1.bl_idname in combine_nodes \
                or node2.bl_idname in combine_nodes or \
                node1.bl_idname == 'ShaderNodeGroup' or node2.bl_idname == 'ShaderNodeGroup' \
                or (bsdf_map[node1.bl_idname][0] == bsdf_map[node2.bl_idname][0]):
            mixer = nt.nodes.new('ArnoldNodeMixRGB')
            # if parent is output make a arnold standard surface first
            nt.links.new(mixer.outputs["ArnoldNodeOutput"],
                         arnold_parent.inputs[input_index])
            offset_node_location(arnold_parent, mixer, node)

            # set the layer masks
            if node.bl_idname == 'ShaderNodeAddShader':
                mixer.layer1Mask = .5
            else:
                convert_cycles_input(
                    nt, node.inputs['Fac'], mixer, 'layer1Mask')

            # make a new node for each
            convert_cycles_bsdf(nt, mixer, node1, 0)
            convert_cycles_bsdf(nt, mixer, node2, 1)

        # this is a heterogenous mix of add
        # else:
        #     if arnold_parent.plugin_name == 'ArnoldLayerMixer':
        #         old_parent = arnold_parent
        #         arnold_parent = create_arnold_surface(nt, arnold_parent, input_index,
        #                                           'ArnoldLayerPattern')
        #         offset_node_location(old_parent, arnold_parent, node)
        #     convert_cycles_bsdf(nt, arnold_parent, node1, 0)
        #     convert_cycles_bsdf(nt, arnold_parent, node2, 1)

    # otherwise set lobe on parent
    # elif 'Bsdf' in node.bl_idname or node.bl_idname == 'ShaderNodeSubsurfaceScattering':
    #     if arnold_parent.plugin_name == 'ArnoldLayerMixer':
    #         old_parent = arnold_parent
    #         arnold_parent = create_arnold_surface(nt, arnold_parent, input_index,
    #                                           'ArnoldLayerMixer')
    #         offset_node_location(old_parent, arnold_parent, node)
    #
    #     node_type = node.bl_idname
    #     bsdf_map[node_type][1](nt, node, arnold_parent)
    # # if we find an emission node, naively make it a meshlight
    # # note this will only make the last emission node the light
    elif node.bl_idname == 'ShaderNodeEmission':
        output = next((n for n in nt.nodes if hasattr(n, 'rendearnold_node_type') and
                       n.rendearnold_node_type == 'output'),
                      None)
        meshlight = nt.nodes.new("meshlight")
        nt.links.new(meshlight.outputs[0], output.inputs["Light"])
        meshlight.location = output.location
        meshlight.location[0] -= 300
        convert_cycles_input(
            nt, node.inputs['Strength'], meshlight, "intensity")
        if node.inputs['Color'].is_linked:
            convert_cycles_input(
                nt, node.inputs['Color'], meshlight, "textureColor")
        else:
            setattr(meshlight, 'lightColor', node.inputs[
                    'Color'].default_value[:3])

    else:
        arnold_node = convert_cycles_node(nt, node)
        nt.links.new(arnold_node.outputs[0], arnold_parent.inputs[input_index])

def convert_cycles_displacement(nt, surface_node, displace_socket):
    # for now just do bump
    if displace_socket.is_linked:
        bump = nt.nodes.new("ArnoldNodeBump2D")
        nt.links.new(bump.outputs[0], surface_node.inputs['bumpNormal'])
        bump.location = surface_node.location
        bump.location[0] -= 200
        bump.location[1] -= 100

        convert_cycles_input(nt, displace_socket, bump, "inputBump")

def convert_cycles_nodetree(id, output_node, reporter):
    # find base node
    from . import cycles_convert
    cycles_convert.converted_nodes = {}
    nt = id.node_tree
    reporter({'INFO'}, 'Converting material ' + id.name + ' to Arnold')
    cycles_output_node = find_node(id, 'ShaderNodeOutputMaterial')
    if not cycles_output_node:
        reporter({'WARNING'}, 'No Cycles output found ' + id.name)
        return False

    # if no bsdf return false
    if not cycles_output_node.inputs[0].is_linked:
        reporter({'WARNING'}, 'No Cycles bsdf found ' + id.name)
        return False

    # set the output node location
    set_ouput_node_location(nt, output_node, cycles_output_node)

    # walk tree
    cycles_convert.report = reporter
    begin_cycles_node = cycles_output_node.inputs[0].links[0].from_node
    # if this is an emission use Arnold Mesh Light
    if begin_cycles_node.bl_idname == "ShaderNodeEmission":
        meshlight = nt.nodes.new("mesh_light")
        nt.links.new(meshlight.outputs[0], output_node.inputs["Light"])
        offset_node_location(output_node, meshlight, begin_cycles_node)
        convert_cycles_input(nt, begin_cycles_node.inputs[
                             'Strength'], meshlight, "intensity")
        if begin_cycles_node.inputs['Color'].is_linked:
            convert_cycles_input(nt, begin_cycles_node.inputs[
                                 'Color'], meshlight, "textureColor")
        else:
            setattr(meshlight, 'lightColor', begin_cycles_node.inputs[
                    'Color'].default_value[:3])
        bxdf = nt.nodes.new('ArnoldNode')
        nt.links.new(bxdf.outputs[0], output_node.inputs["Surface"])
    else:
        base_surface = create_arnold_surface(nt, output_node, 0)
        offset_node_location(output_node, base_surface, begin_cycles_node)
        convert_cycles_bsdf(nt, base_surface, begin_cycles_node, 0)
        convert_cycles_displacement(
            nt, base_surface, cycles_output_node.inputs[2])
    return True


@ArnoldRenderEngine.register_class
class ArnoldWorldNodeTree(NodeTree):
    bl_idname = 'ARNOLD_WORLD_NODETREE'
    bl_label = "Arnold World"
    bl_icon = 'WORLD'

    _draw_header = None

    @classmethod
    def poll(cls, context):
        return ArnoldRenderEngine.is_active(context)

    @classmethod
    def get_from_context(cls, context):
        scene = context.scene
        if scene:
            world = scene.world
            if world:
                return (world.node_tree, world, world)
        return (None, None, None)

    @classmethod
    def register(cls):
        # HACK: show own header ui for node editor for world nodes
        if cls._draw_header is None:
            def draw(self, context):
                if ArnoldRenderEngine.is_active(context):
                    snode = context.space_data
                    if snode.tree_type == 'ARNOLD_WORLD_NODETREE':
                        ###################################
                        # copy from space_node.py:36
                        layout = self.layout

                        scene = context.scene
                        snode_id = snode.id
                        toolsettings = context.tool_settings

                        row = layout.row(align=True)
                        row.template_header()

                        NODE_MT_editor_menus.draw_collapsible(context, layout)

                        layout.prop(snode, "tree_type", text="", expand=True)
                        # end copy
                        ###################################

                        ###################################
                        # copy from space_node.py:72
                        row = layout.row()
                        row.enabled = not snode.pin
                        row.template_ID(scene, "world", new="world.new")
                        if snode_id:
                            row.prop(snode_id, "use_nodes")
                        # end copy
                        ###################################

                        ###################################
                        # copy from space_node.py:113
                        layout.prop(snode, "pin", text="")
                        layout.operator("node.tree_path_parent", text="", icon='FILE_PARENT')

                        layout.separator()

                        # Auto-offset nodes (called "insert_offset" in code)
                        layout.prop(snode, "use_insert_offset", text="")

                        # Snap
                        row = layout.row(align=True)
                        row.prop(toolsettings, "use_snap", text="")
                        row.prop(toolsettings, "snap_node_element", icon_only=True)
                        if toolsettings.snap_node_element != 'GRID':
                            row.prop(toolsettings, "snap_target", text="")

                        row = layout.row(align=True)
                        row.operator("node.clipboard_copy", text="", icon='COPYDOWN')
                        row.operator("node.clipboard_paste", text="", icon='PASTEDOWN')

                        layout.template_running_jobs()
                        # end copy
                        ###################################
                        return
                cls._draw_header(self, context)

            cls._draw_header = NODE_HT_header.draw
            NODE_HT_header.draw = draw

    @classmethod
    def unregister_draw_cb(cls):
        if cls._draw_header is not None:
            NODE_HT_header.draw = cls._draw_header
            cls._draw_header = None


@ArnoldRenderEngine.register_class
class ArnoldNodeSocketProperty(NodeSocket):
    # stub
    default_value: FloatProperty()

    path: StringProperty()
    attr: StringProperty()
    is_color: BoolProperty()
    color: FloatVectorProperty(size=4)

    def draw(self, context, layout, node, text):
        data = node
        if self.path:
            data = node.path_resolve(self.path)
        if self.is_output or self.is_linked:
            layout.label(text=text)
        elif self.is_color:
            row = layout.row()
            row.alignment = 'LEFT'
            row.prop(data, self.attr, text="")
            row.label(text=text)
        else:
            layout.prop(data, self.attr, text=text)

    def draw_color(self, context, node):
        return self.color


@ArnoldRenderEngine.register_class
class ArnoldNodeSocketColor(NodeSocket):
    bl_label = "Color"

    default_value: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        default=(1, 1, 1),
        min=0, max=1
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            row = layout.row()
            row.alignment = 'LEFT'
            row.prop(self, "default_value", text="")
            row.label(text=text)

    def draw_color(self, context, node):
        # <blender_sources>/source/blender/editors/space_node/drawnode.c:3010 (SOCK_RGBA)
        return (0.78, 0.78, 0.16, 1.0)


@ArnoldRenderEngine.register_class
class ArnoldNodeSocketByte(NodeSocket):
    bl_label = "Value"

    default_value: IntProperty(
        name="Value",
        subtype='UNSIGNED',
        min=0, max=255
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "default_value", text=text)

    def draw_color(self, context, node):
        # <blender_sources>/source/blender/editors/space_node/drawnode.c:3010 (SOCK_INT)
        return (0.6, 0.52, 0.15, 1.0)


@ArnoldRenderEngine.register_class
class ArnoldNodeSocketFilter(NodeSocket):
    bl_label = "Filter"

    default_value: StringProperty(
        name="Filter"
    )

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        # <blender_sources>/source/blender/editors/space_node/drawnode.c:3010 (SOCK_INT)
        return (0.6, 0.52, 0.15, 1.0)


class ArnoldNode(Node):
    @property
    def ai_properties(self):
        return {}


class _NodeOutput:
    bl_label = "Output"

    def _get_active(self):
        return not self.mute

    def _set_active(self, value=True):
        for node in self.id_data.nodes:
            if isinstance(node, _NodeOutput):
                node.mute = (self != node)

    is_active: BoolProperty(
        name="Active",
        description="Active Output",
        get=_get_active,
        set=_set_active
    )

    def init(self, context):
        self._set_active()

    def copy(self, node):
        self._set_active()

    def draw_buttons(self, context, layout):
        layout.prop(self, "is_active", icon='RADIOBUT_ON' if self.is_active else 'RADIOBUT_OFF')


@ArnoldRenderEngine.register_class
class ArnoldNodeOutput(_NodeOutput, Node):
    bl_icon = 'MATERIAL'

    # disp_map: StringProperty(
    #     name="Displacement",
    #     subtype='FILE_PATH'
    # )

    def init(self, context):
        super().init(context)
        self.inputs.new(type="NodeSocketShader", name="Surface", identifier="surface")
        self.inputs.new(type="NodeSocketShader", name="Volume", identifier="volume")
        self.inputs.new(type="NodeSocketShader", name="Displacement", identifier="disp_map")

    
    # @property
    # def ai_properties(self):
    #     return {
    #         "disp_map": ('FLOAT', self.disp_map)
    #     }


@ArnoldRenderEngine.register_class
class ArnoldNodeWorldOutput(_NodeOutput, Node):
    bl_icon = 'WORLD'

    def init(self, context):
        super().init(context)
        self.inputs.new(type="NodeSocketShader", name="Background", identifier="background")
        self.inputs.new(type="NodeSocketShader", name="Atmosphere", identifier="atmosphere")


@ArnoldRenderEngine.register_class
class ArnoldNodeLightOutput(_NodeOutput, Node):
    bl_icon = 'LIGHT'

    active_filter_index: IntProperty(
        default=1
    )

    def init(self, context):
        super().init(context)
        self.inputs.new(type="NodeSocketShader", name="Color", identifier="color")
        self.inputs.new(type="ArnoldNodeSocketFilter", name="Filter", identifier="filter")

    def draw_buttons_ext(self, context, layout):
        row = layout.row()
        col = row.column()
        col.template_list("ARNOLD_UL_light_filters", "", self, "inputs", self, "active_filter_index", rows=2)
        col = row.column(align=True)
        col.operator("barnold.light_filter_add", text="", icon="ADD")
        col.operator("barnold.light_filter_remove", text="", icon="REMOVE")


@ArnoldRenderEngine.register_class
class ArnoldNodeLambert(ArnoldNode):
    bl_label = "Lambert"
    bl_icon = 'MATERIAL'

    ai_name = "lambert"

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Diffuse", identifier="Kd_color")
        self.inputs.new(type="NodeSocketFloat", name="Weight", identifier="Kd").default_value = 0.7
        self.inputs.new(type="ArnoldNodeSocketColor", name="Opacity", identifier="opacity")

@ArnoldRenderEngine.register_class
class ArnoldNodeColorCorrect(ArnoldNode):
    bl_label = "Color Correct"
    bl_icon = 'MATERIAL'
    bl_width_default=200

    ai_name = "color_correct"

    mask: FloatProperty(
        name="Mask",
        subtype='FACTOR',
        min=0, max=1,
        default=1
    )

    gamma: FloatProperty(
        name="Gamma",
        subtype='FACTOR',
        min=0, max=5,
        default=1
    )

    hue_shift: FloatProperty(
        name="Hue Shift",
        subtype='FACTOR',
        min=0, max=1,
        default=0
    )

    saturation: FloatProperty(
        name="Saturation",
        subtype='FACTOR',
        min=0, max=5,
        default=1
    )

    contrast: FloatProperty(
        name="Contrast",
        subtype='FACTOR',
        min=0, max=1,
        default=1
    )

    contrast_pivot: FloatProperty(
        name="Contrast Pivot",
        subtype='FACTOR',
        min=0, max=1,
        default=0.180
    )

    exposure: FloatProperty(
        name="Exposure",
        subtype='FACTOR',
        min=0, max=1,
        default=0
    )

    multiply: FloatVectorProperty(
        name="Multiply",
         subtype='COLOR',
         min=0, max=1,
         default=(1, 1, 1)
    )

    add: FloatVectorProperty(
        name="Add",
         subtype='COLOR',
         min=0, max=1,
         default=(0, 0, 0)
    )
    invert: BoolProperty(
        name="Invert",
        default=False
    )

    is_luminance: BoolProperty(
        name="Is Luminance",
        default=False
    )

    multiply_alpha: FloatProperty(
        name="Multiply",
        subtype='FACTOR',
        min=0, max=1,
        default=1.0
    )

    add_alpha: FloatProperty(
        name="Add",
        subtype='FACTOR',
        min=0, max=1,
        default=0.0
    )

    invert_alpha: BoolProperty(
        name="Invert",
        default=False
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Shader", identifier="input").default_value=(0,0,0)
        self.inputs.new(type="NodeSocketFloat", name="Mask", identifier="mask").default_value = 1.0

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.label(text="Color Correction")
        flow = col.column_flow(align=True)
        flow.prop(self, "gamma")
        flow.prop(self, "hue_shift")
        flow.prop(self, "saturation")
        flow.prop(self, "contrast")
        flow.prop(self, "contrast_pivot")
        flow.prop(self, "exposure")
        flow.prop(self, "multiply")
        flow.prop(self, "add")
        flow.prop(self, "invert")
        col.label(text="")
        col = layout.column()
        col.label(text="Alpha")
        flow = col.column_flow(align=True)
        flow.prop(self, "is_luminance")
        flow.prop(self, "multiply_alpha")
        flow.prop(self, "add_alpha")
        flow.prop(self, "invert_alpha")
        col.label(text="")
    
    @property
    def ai_properties(self):
        return {
            "gamma": ('FLOAT', self.gamma),
            "hue_shift": ('FLOAT', self.hue_shift),
            "saturation": ('FLOAT', self.saturation),
            "contrast": ('FLOAT', self.contrast),
            "contrast_pivot": ('BOOL', self.contrast_pivot),
            "exposure": ('FLOAT', self.exposure),
            "multiply": ('RGB', self.multiply),
            "add": ('RGB', self.add),
            "invert": ('BOOL', self.invert),
            "is_luminance": ('FLOAT', self.is_luminance),
            "multiply_alpha": ('FLOAT', self.multiply_alpha),
            "add_alpha": ('FLOAT', self.add_alpha),
            "invert_alpha": ('BOOL', self.invert_alpha),
        }



@ArnoldRenderEngine.register_class
class ArnoldNodeStandardVolume(ArnoldNode):
    bl_label="Standard Volume"
    bl_icon= "MATERIAL"
    color = (1,1,1)
    bl_width_default=200

    ai_name="standard_volume"

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.inputs.new(type="NodeSocketFloat", name="Density", identifier="density").default_value = 1.0
        self.inputs.new(type="NodeSocketFloat", name="Scatter", identifier="scatter").default_value = 1.0
        self.inputs.new(type="ArnoldNodeSocketColor", name="Scatter Color", identifier="scatter_color").default_value = (0.5, 0.5, 0.5)
        self.inputs.new(type="ArnoldNodeSocketColor", name="Transparent", identifier="transparent").default_value = (0.368, 0.368, 0.368)
        self.inputs.new(type="NodeSocketFloat", name="Transparent Depth", identifier="transparent_depth").default_value = 1.0
        self.inputs.new(type="NodeSocketFloat", name="Emission", identifier="emission").default_value = 1.0
        self.inputs.new(type="ArnoldNodeSocketColor", name="Emission Color", identifier="emission_color")
        self.inputs.new(type="NodeSocketFloat", name="Temperature", identifier="temperature").default_value=1.0
        self.inputs.new(type="NodeSocketFloat", name="Blackbody Kelvin", identifier="blackbody_kelvin").default_value=5000.000
        self.inputs.new(type="NodeSocketFloat", name="Blackbody Intensity", identifier="blackbody_intensity").default_value=1.0

@ArnoldRenderEngine.register_class
class ArnoldNodeStandardSurface(ArnoldNode):
    bl_label = "Standard Surface"
    bl_icon = 'MATERIAL'
    bl_width_default = 200

    ai_name = "standard_surface"

    sockets = collections.OrderedDict([
        # Base
        ("base_color"               , ('RGB',   "Base Color",        "ext_properties")),
        ("base"                     , ('FLOAT', "Base",              "ext_properties")),
        ("diffuse_roughness"        , ('FLOAT', "Diffuse Roughness", "ext_properties")),
        ("metalness"                , ('FLOAT', "Diffuse Metalness", "ext_properties")),
        # Specular
        ("specular_color"           , ('RGB',   "Specular Color", "ext_properties")),
        ("specular"                 , ('FLOAT', "Specular Scale", "ext_properties")),
        ("specular_roughness"       , ('FLOAT', "Specular Roughness", "ext_properties")),
        ("specular_ior"             , ('FLOAT', "Specular IOR", "ext_properties")),
        ("specular_anisotropy"      , ('FLOAT', "Specular Anisotropy", "ext_properties")),
        ("specular_rotation"        , ('FLOAT', "Specular Rotation", "ext_properties")),
        # Transmission
        ("transmission_color"                 , ('RGB', "Transmission Color", "ext_properties")),
        ("transmission"                       , ('FLOAT', "Transmission", "ext_properties")),
        ("transmission_depth"       , ('FLOAT', "Transmission Depth", "ext_properties")),
        ("transmission_scatter"       , ('RGB', "Transmission Scatter", "ext_properties")),
        ("transmission_scatter_anisotropy", ('FLOAT', "Transmission Anisotropy", "ext_properties")),
        ("transmission_extra_roughness", ('FLOAT', "Transmission Extra Roughness", "ext_properties")),
        ("transmission_dispersion"          , ('FLOAT', "Transmission Abbe", "ext_properties")),
        ("transmit_aovs"                    , ('BOOL',  "Transmit AOVs",     "ext_properties")),
        # Coat
        ("coat"                , ('FLOAT', "Coat", "ext_properties")),
        ("coat_color"          , ('RGB', "Coat Color", "ext_properties")),
        ("coat_roughness"     , ('FLOAT', "Coat Roughness", "ext_properties")),
        ("coat_ior"            , ('FLOAT', "Coat IOR", "ext_properties")),
        ("coat_normal"         ,('VECTOR', "Coat Normal", "ext_properties")),
        # Thin Film
        ("thin_film_thickness" ,('FLOAT', "Thin Film Thickness", "ext_properties")),
        ("thin_film_ior",       ('FLOAT',"Thin Film IOR",        "ext_properties")),
        # Geometry
        ("opacity"                  , ('RGB', "Opacity",     "ext_properties")),
        ("thin_walled"              , ('BOOL',  "Thin Walled", "ext_properties")),
        # Subsurface
        ("subsurface"               , ('FLOAT', "Subsurface", "ext_properties")),
        ("subsurface_color"         , ('RGB', "Subsurface Color", "ext_properties")),
        ("subsurface_radius"        , ('RGB', "Subsurface Radius", "ext_properties")),
        ("subsurface_scale"         , ('FLOAT', "Subsurface Scale", "ext_properties")),
        ("subsurface_anisotropy"    , ('FLOAT', "Subsurface Anisotropy", "ext_properties")),
        ("subsurface_type"          , ('STRING',"Subsurface Type",       "ext_properties")),
        # Emission
        ("emission_color"           , ('RGB', "Emission Color", "ext_properties")),
        ("emission"                 , ('FLOAT', "Emission", "ext_properties")),
        # Normal
        ("normal"                 , ('VECTOR', "Normal", "ext_properties"))
    ])

    # base: FloatProperty(
    #     name="Scale",
    #     subtype='FACTOR',
    #     min=0, max=1,
    #     default=0.7
    # )
    # base_color: FloatVectorProperty(
    #     name="Color",
    #     subtype='COLOR',
    #     min=0, max=1,
    #     default=(1, 1, 1)
    # )
    # specular: FloatProperty(
    #     name="Scale",
    #     subtype='FACTOR',
    #     min=0, max=1
    # )
    # specular_color: FloatVectorProperty(
    #     name="Color",
    #     subtype='COLOR',
    #     min=0, max=1,
    #     default=(1, 1, 1)
    # )
    # emission_color: FloatVectorProperty(
    #     name="Color",
    #     subtype='COLOR',
    #     min=0, max=1,
    #     default=(1,1,1)
    # )
    ext_properties: PointerProperty(
        type=props.ArnoldShaderStandardSurface
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.create_socket(identifier="base")
        self.create_socket(identifier="base_color")
        self.create_socket(identifier="diffuse_roughness")
        self.create_socket(identifier="specular")
        self.create_socket(identifier="specular_color")
        self.create_socket(identifier="specular_roughness")
        self.create_socket(identifier="transmission")
        self.create_socket(identifier="transmission_color")
        self.create_socket(identifier="transmission_depth")
        self.create_socket(identifier="transmission_scatter")
        self.create_socket(identifier="transmission_extra_roughness")
        self.create_socket(identifier="subsurface")
        self.create_socket(identifier="subsurface_color")
        self.create_socket(identifier="subsurface_radius")
        self.create_socket(identifier="coat")
        self.create_socket(identifier="coat_color")
        self.create_socket(identifier="coat_roughness")
        self.create_socket(identifier="emission")
        self.create_socket(identifier="emission_color")
        self.create_socket(identifier="opacity")
        self.create_socket(identifier="normal")

    # def init(self, context):
    #     self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
    #     self.inputs.new(type="NodeSocketFloat", name="Base", identifier="base").default_value = 0.8
    #     self.inputs.new(type="ArnoldNodeSocketColor", name="Base Color", identifier=ext_properties)
    #     self.inputs.new(type="NodeSocketFloat", name="Diffuse Roughness", identifier="diffuse_roughness")
    #     self.inputs.new(type="NodeSocketFloat", name="Specular", identifier="specular").default_value=1.0
    #     self.inputs.new(type="ArnoldNodeSocketColor", name="Specular Color", identifier="specular_color")
    #     self.inputs.new(type="NodeSocketFloat", name="Specular Roughness", identifier="specular_roughness").default_value=.1
    #     self.inputs.new(type="NodeSocketFloat", name="Transmission", identifier="transmission")
    #     self.inputs.new(type="ArnoldNodeSocketColor", name="Transmission Color", identifier="transmission_color")
    #     self.inputs.new(type="NodeSocketFloat", name="Transmission Depth", identifier="transmission_depth")
    #     self.inputs.new(type="ArnoldNodeSocketColor", name="Transmission Scatter", identifier="transmission_scatter").default_value=(0,0,0)
    #     self.inputs.new(type="NodeSocketFloat", name="Transmission Extra Roughness", identifier="transmission_extra_roughness")
    #     self.inputs.new(type="NodeSocketFloat", name="Subsurface", identifier="subsurface")
    #     self.inputs.new(type="ArnoldNodeSocketColor", name="Subsurface Color", identifier="subsurface_color")
    #     self.inputs.new(type="ArnoldNodeSocketColor", name="Subsurface Radius", identifier="subsurface_radius")
    #     self.inputs.new(type="NodeSocketFloat", name="Coat", identifier="coat")
    #     self.inputs.new(type="ArnoldNodeSocketColor", name="Coat Color", identifier="coat_color")
    #     self.inputs.new(type="NodeSocketFloat", name="Coat Roughness", identifier="coat_roughness").default_value=.1
    #     self.inputs.new(type="NodeSocketFloat", name="Sheen Weight", identifier="sheen").default_value = 0
    #     self.inputs.new(type="ArnoldNodeSocketColor", name="Sheen Color", identifier="sheen_color").default_value=(1,1,1)
    #     self.inputs.new(type="NodeSocketFloat", name="Sheen Roughness", identifier="sheen_roughness").default_value=0.3
    #     self.inputs.new(type="NodeSocketFloat", name="Emission", identifier="emission")
    #     self.inputs.new(type="ArnoldNodeSocketColor", name="Emission Color", identifier="emission_color")
    #     self.inputs.new(type="NodeSocketFloat", name="Opacity", identifier="opacity")
    #     self.inputs.new(type="NodeSocketVectorXYZ", name="Normal Camera", identifier="normal")
     # def init(self, context):
    #     self.outputs.new("NodeSocketShader", "RGB", "output")
    #     self.inputs.new("ArnoldNodeSocketColor", "Diffuse", "base_color")
    #     self.inputs.new("NodeSocketFloat", "Weight", "base").default_value = 0.7
    #     self.inputs.new("ArnoldNodeSocketColor", "Opacity", "opacity")

    def draw_buttons_ext(self, context, layout):
        inputs = self.inputs
        properties = self.ext_properties

        links = {i.identifier: i.is_linked for i in inputs}

        # Diffuse
        sublayout = ui._subpanel(layout, "Diffuse", properties.ui_diffuse,
                              "ext_properties", "ui_diffuse", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "base", links)
            _draw_property(col, properties, "base_color", links)
            _draw_property(col, properties, "diffuse_roughness", links)
            _draw_property(col, properties, "metalness", links)

        # Specular
        sublayout = ui._subpanel(layout, "Specular", properties.ui_specular,
                              "ext_properties", "ui_specular", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "specular", links)
            _draw_property(col, properties, "specular_color", links)
            _draw_property(col, properties, "specular_roughness", links)
            _draw_property(col, properties, "specular_ior", links)
            _draw_property(col, properties, "specular_anisotropy", links)
            _draw_property(col, properties, "specular_rotation", links)

        # Transmission
        sublayout = ui._subpanel(layout, "Transmission", properties.ui_refraction,
                              "ext_properties", "ui_refraction", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "transmission", links)
            _draw_property(col, properties, "transmission_color", links)
            _draw_property(col, properties, "transmission_depth", links)
            _draw_property(col, properties, "transmission_scatter", links)
            _draw_property(col, properties, "transmission_scatter_anisotropy", links)
            _draw_property(col, properties, "transmission_dispersion", links)
            _draw_property(col, properties, "transmission_extra_roughness", links)
            _draw_property(col, properties, "transmit_aovs", links)

        # Subsurface
        sublayout = ui._subpanel(layout, "Subsurface", properties.ui_sss,
                              "ext_properties", "ui_sss", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "subsurface", links)
            _draw_property(col, properties, "subsurface_color", links)
            _draw_property(col, properties, "subsurface_radius", links)
            _draw_property(col, properties, "subsurface_scale", links)
            _draw_property(col, properties, "subsurface_type", links)
            _draw_property(col, properties, "subsurface_anisotropy", links)

        # Coat
        sublayout = ui._subpanel(layout, "Coat", properties.ui_coat,
                              "ext_properties", "ui_coat", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "coat", links)
            _draw_property(col, properties, "coat_color", links)
            _draw_property(col, properties, "coat_roughness", links)
            _draw_property(col, properties, "coat_ior", links)
            _draw_property(col, properties, "coat_normal", links)


        # Emission
        sublayout = ui._subpanel(layout, "Emission", properties.ui_emission,
                              "ext_properties", "ui_emission", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "emission", links)
            _draw_property(col, properties, "emission_color", links)

        # Thin Film
        sublayout = ui._subpanel(layout, "Thin Film", properties.ui_thinfilm,
                              "ext_properties", "ui_thinfilm", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "thin_film_thickness", links)
            _draw_property(col, properties, "thin_film_ior", links)

        # Geometry
        sublayout = ui._subpanel(layout, "Geometry", properties.ui_geometry,
                              "ext_properties", "ui_geometry", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "opacity", links)
            _draw_property(col, properties, "thin_walled", links)

        # Advanced
        sublayout = ui._subpanel(layout, "Advanced", properties.ui_caustics,
                              "ext_properties", "ui_advanced", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "caustics", links)
            _draw_property(col, properties, "internal_reflections", links)
            _draw_property(col, properties, "exit_to_background", links)
            _draw_property(col, properties, "indirect_diffuse", links)
            _draw_property(col, properties, "indirect_specular", links)
            _draw_property(col, properties, "normal", links)


    def _find_index(self, identifier):
        ret = 0
        socks = iter(self.sockets)
        for i in self.inputs:
            for s in socks:
                if s == identifier:
                    return ret
                if s == i.identifier:
                    ret += 1
                    break
            else:
                break
        return ret

    def create_socket(self, identifier):
        from_index = len(self.inputs)
        to_index = self._find_index(identifier)
        type, name, path = self.sockets[identifier]
        sock = self.inputs.new(type="ArnoldNodeSocketProperty", name=name, identifier=identifier)
        sock.path = path
        sock.attr = identifier
        if type in ('RGB', 'RGBA'):
            sock.is_color = True
            sock.color = (0.78, 0.78, 0.16, 1 if type == 'RGB' else 0.5)
        elif type == 'FLOAT':
            sock.color = (0.63, 0.63, 0.63, 1.0)
        if to_index < from_index:
            self.inputs.move(from_index, to_index)

    @property
    def ai_properties(self):
        links = [i.identifier for i in self.inputs if i.is_linked]
        props = self.ext_properties
        ret = {
            'exit_to_background': ('BOOL', props.exit_to_background),
            'caustics': ('BOOL', props.caustics),
            'internal_reflections': ('BOOL', props.internal_reflections),
        }
        for i, (t, n, p) in self.sockets.items():
            if i not in links:
                ret[i] = (t, self.path_resolve(p + "." + i if p else i))
        return ret


@ArnoldRenderEngine.register_class
class ArnoldNodeCarPaint(ArnoldNode):
    bl_label = "Car Paint"
    bl_icon = 'MATERIAL'
    bl_width_default = 200

    ai_name = 'car_paint'

    sockets = collections.OrderedDict([
        # Base
        ("base_color"               , ('RGB',   "Base Color",      "ext_properties")),
        ("base"                     , ('FLOAT', "Base",            "ext_properties")),
        ("base_roughness"           , ('FLOAT', "Base Roughness",  "ext_properties")),

        # Specular
        ("specular_color"           , ('RGB',    "Specular Color",         "ext_properties")),
        ("specular"                 , ('FLOAT',  "Specular Scale",         "ext_properties")),
        ("specular_flip_flop"       , ('RGB',    "Specular Flip Flop",     "ext_properties")),
        ("specular_light_facing"    , ('RGB',    "Specular Light Facing",  "ext_properties")),
        ("specular_falloff"         , ('FLOAT',  "Specular Falloff",       "ext_properties")),
        ("specular_roughness"       , ('FLOAT',  "Specular Roughness",     "ext_properties")),
        ("specular_IOR"             , ('FLOAT',  "Specular IOR",           "ext_properties")),

        # Flakes
        ("transmission_color"       , ('RGB',    "Transmission Color",     "ext_properties")),
        ("flake_color"              , ('RGB',    "Flake Color",            "ext_properties")),
        ("flake_flip_flop"          , ('RGB',    "Flake Flip Flop",        "ext_properties")),
        ("flake_light_facing"       , ('RGB',    "Flake Light Facing",     "ext_properties")),
        ("flake_falloff"            , ('FLOAT',  "Flake Falloff",          "ext_properties")),
        ("flake_roughness"          , ('FLOAT',  "Flake Roughness",        "ext_properties")),
        ("flake_IOR"                , ('FLOAT',  "Flake IOR",              "ext_properties")),
        ("flake_scale"              , ('FLOAT',  "Flake Scale",            "ext_properties")),
        ("flake_density"            , ('FLOAT',  "Flake Density",          "ext_properties")),
        ("flake_layers"             , ('INT',    "Flake Layers",           "ext_properties")),
        ("flake_normal_randomize"   , ('FLOAT',  "Flake Normal Randomize", "ext_properties")),
        ("flake_coord_space"        , ('STRING', "Flake Coordinate Space", "ext_properties")),
        ("pref_name"                , ('STRING', "Pref Name",              "ext_properties")),

        # Coat
        ("coat"                     , ('FLOAT',  "Coat",                   "ext_properties")),
        ("coat_color"               , ('RGB',    "Coat Color",             "ext_properties")),
        ("coat_roughness"           , ('FLOAT',  "Coat Roughness",         "ext_properties")),
        ("coat_IOR"                 , ('FLOAT',  "Coat IOR",               "ext_properties")),
        ("coat_normal"              , ('VECTOR', "Coat Normal",            "ext_properties")),
    ])

    ext_properties: PointerProperty(
        type=props.ArnoldShaderCarPaint
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.create_socket(identifier="base")
        self.create_socket(identifier="base_color")
        self.create_socket(identifier="base_roughness")
        self.create_socket(identifier="specular")
        self.create_socket(identifier="specular_color")
        self.create_socket(identifier="specular_flip_flop")
        self.create_socket(identifier="specular_light_facing")
        self.create_socket(identifier="specular_falloff")
        self.create_socket(identifier="specular_roughness")
        self.create_socket(identifier="specular_IOR")
        self.create_socket(identifier="transmission_color")
        self.create_socket(identifier="flake_color")
        self.create_socket(identifier="flake_flip_flop")
        self.create_socket(identifier="flake_light_facing")
        self.create_socket(identifier="flake_falloff")
        self.create_socket(identifier="flake_roughness")
        self.create_socket(identifier="flake_IOR")
        self.create_socket(identifier="flake_scale")
        self.create_socket(identifier="flake_density")
        self.create_socket(identifier="flake_layers")
        self.create_socket(identifier="flake_normal_randomize")
        self.create_socket(identifier="flake_coord_space")
        self.create_socket(identifier="pref_name")
        self.create_socket(identifier="coat")
        self.create_socket(identifier="coat_color")
        self.create_socket(identifier="coat_roughness")
        self.create_socket(identifier="coat_IOR")
        self.create_socket(identifier="coat_normal")

    def draw_buttons_ext(self, context, layout):
        inputs = self.inputs
        properties = self.ext_properties

        links = {i.identifier: i.is_linked for i in inputs}

        # Base
        sublayout = ui._subpanel(layout, "Base", properties.ui_base,
                              "ext_properties", "ui_base", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "base", links)
            _draw_property(col, properties, "base_color", links)
            _draw_property(col, properties, "base_roughness", links)

        # Specular
        sublayout = ui._subpanel(layout, "Specular", properties.ui_specular,
                              "ext_properties", "ui_specular", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "specular", links)
            _draw_property(col, properties, "specular_color", links)
            _draw_property(col, properties, "specular_roughness", links)
            _draw_property(col, properties, "specular_flip_flop", links)
            _draw_property(col, properties, "specular_light_facing", links)
            _draw_property(col, properties, "specular_falloff", links)
            _draw_property(col, properties, "specular_IOR", links)

        # Flake
        sublayout = ui._subpanel(layout, "Flake", properties.ui_flake,
                              "ext_properties", "ui_flake", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "transmission_color", links)
            _draw_property(col, properties, "flake_color", links)
            _draw_property(col, properties, "flake_flip_flop", links)
            _draw_property(col, properties, "flake_light_facing", links)
            _draw_property(col, properties, "flake_falloff", links)
            _draw_property(col, properties, "flake_roughness", links)
            _draw_property(col, properties, "flake_IOR", links)
            _draw_property(col, properties, "flake_scale", links)
            _draw_property(col, properties, "flake_density", links)
            _draw_property(col, properties, "flake_layers", links)
            _draw_property(col, properties, "flake_normal_randomize", links)
            _draw_property(col, properties, "flake_coord_space", links)
            _draw_property(col, properties, "pref_name", links)

        # Coat
        sublayout = ui._subpanel(layout, "Coat", properties.ui_coat,
                              "ext_properties", "ui_coat", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "coat", links)
            _draw_property(col, properties, "coat_color", links)
            _draw_property(col, properties, "coat_roughness", links)
            _draw_property(col, properties, "coat_IOR", links)
            _draw_property(col, properties, "coat_normal", links)

    def _find_index(self, identifier):
        ret = 0
        socks = iter(self.sockets)
        for i in self.inputs:
            for s in socks:
                if s == identifier:
                    return ret
                if s == i.identifier:
                    ret += 1
                    break
            else:
                break
        return ret

    def create_socket(self, identifier):
        from_index = len(self.inputs)
        to_index = self._find_index(identifier)
        type, name, path = self.sockets[identifier]
        sock = self.inputs.new(type="ArnoldNodeSocketProperty", name=name, identifier=identifier)
        sock.path = path
        sock.attr = identifier
        if type in ('RGB', 'RGBA'):
            sock.is_color = True
            sock.color = (0.78, 0.78, 0.16, 1 if type == 'RGB' else 0.5)
        elif type == 'FLOAT':
            sock.color = (0.63, 0.63, 0.63, 1.0)
        if to_index < from_index:
            self.inputs.move(from_index, to_index)

    @property
    def ai_properties(self):
        links = [i.identifier for i in self.inputs if i.is_linked]
        props = self.ext_properties
        ret = {
            # 'exit_to_background': ('BOOL', props.exit_to_background),
            # 'caustics': ('BOOL', props.caustics),
            # 'internal_reflections': ('BOOL', props.internal_reflections),
        }
        for i, (t, n, p) in self.sockets.items():
            if i not in links:
                ret[i] = (t, self.path_resolve(p + "." + i if p else i))
        return ret


@ArnoldRenderEngine.register_class
class ArnoldNodeToon(ArnoldNode):
    bl_label = "Toon"
    bl_icon = 'MATERIAL'
    bl_width_default = 200

    ai_name = "toon"

    sockets = collections.OrderedDict([
        # Base
        ("base_color"               , ('RGB',   "Base Color",   "ext_properties")),
        ("base"                     , ('FLOAT', "Base",         "ext_properties")),
        ("base_tonemap"             , ('RGB',   "Base Tonemap", "ext_properties")),

        # Edge
        ("mask_color"               , ('RGB', "Mask Color", "ext_properties")),
        ("edge_color"               , ('RGB', "Edge Color", "ext_properties")),
        ("edge_tonemap"             , ('RGB', "Edge Tonemap", "ext_properties")),
        ("edge_opacity"             , ('FLOAT', "Edge Opacity", "ext_properties")),
        ("edge_width_scale"         , ('FLOAT', "Edge Width Scale", "ext_properties")),


        # Silhouette
        ("silhouette_color"        , ('RGB', "Silhouette Color", "ext_properties")),
        ("silhouette_tonemap"      , ('RGB', "Silhouette Tonemap", "ext_properties")),
        ("silhouette_opacity"      , ('FLOAT', "Silhouette Opacity", "ext_properties")),
        ("silhouette_width_scale"  , ('FLOAT', "Silhouette Width Scale", "ext_properties")),
        #("priority"                , ('INT', "Priority", "ext_properties")),
        ("enable_silhouette"       , ('BOOL', "Enable Silhouette", "ext_properties")),
        ("ignore_throughput"       , ('BOOL', "Ignore Throughput", "ext_properties")),
        ("enable"                  , ('BOOL', "Enable", "ext_properties")),
        ("id_difference"           , ('BOOL', "ID Difference", "ext_properties")),
        ("shader_difference"       , ('BOOL', "Shader Difference", "ext_properties")),
        ("uv_threshold"            , ('FLOAT', "UV Threshold", "ext_properties")),
        ("angle_threshold"         , ('FLOAT', "Angle Threshold", "ext_properties")),
        ("normal_type"             , ('STRING', "Normal Type", "ext_properties")),

        # Specular
        ("specular_color"           , ('RGB',   "Specular Color", "ext_properties")),
        ("specular"                 , ('FLOAT', "Specular Scale", "ext_properties")),
        ("specular_roughness"       , ('FLOAT', "Specular Roughness", "ext_properties")),
        ("specular_tonemap"         , ('RGB',   "Specular Tonemap", "ext_properties")),
        ("specular_anisotropy"      , ('FLOAT', "Specular Anisotropy", "ext_properties")),
        ("specular_rotation"        , ('FLOAT', "Specular Rotation", "ext_properties")),
        ("lights"                   , ('STRING',"Lights", "ext_properties")),
        ("highlight_color"          , ('RGB',   "Highlight Color", "ext_properties")),
        ("highlight_size"           , ('FLOAT', "Highlight Size", "ext_properties")),
        ("aov_highlight"            , ('STRING', "AOV Highlight", "ext_properties")),
        ("rim_light"                , ('STRING', "Rim Light", "ext_properties")),
        ("rim_light_color"          , ('RGB', "Rim Light Color", "ext_properties")),
        ("rim_light_width"          , ('FLOAT', "Rim Light Width", "ext_properties")),
        ("aov_rim_light"            , ('STRING', "AOV Rim Light", "ext_properties")),

        # Transmission
        ("transmission_color"       , ('RGB', "Transmission Color", "ext_properties")),
        ("transmission"             , ('FLOAT', "Transmission", "ext_properties")),
        ("transmission_roughness"   , ('FLOAT', "Transmission Roughness", "ext_properties")),
        ("transmission_anisotropy"  , ('FLOAT', "Transmission Anisotropy", "ext_properties")),
        ("transmission_rotation"    , ('FLOAT', "Transmission Rotation", "ext_properties")),

        # Emission
        ("emission_color"           , ('RGB', "Emission Color", "ext_properties")),
        ("emission"                 , ('FLOAT', "Emission", "ext_properties")),

        # Advanced
        ("IOR"                      ,('FLOAT', "IOR", "ext_properties")),
        ("normal"                   ,('VECTOR', "Normal", "ext_properties")),
        ("tangent"                  ,('VECTOR', "Tangent", "ext_properties")),
        ("indirect_diffuse"         ,('FLOAT', "Indirect Diffuse", "ext_properties")),
        ("indirect_specular"        ,('FLOAT', "Indirect Specular", "ext_properties")),
        ("bump_mode"                ,('STRING', "Bump Mode", "ext_properties")),
        ("energy_conserving"        ,('BOOL', "Energy Conserving", "ext_properties")),
        ("user_id"                  ,('BOOL', "User ID", "ext_properties")),

        # Sheen
        ("sheen"                    ,('FLOAT', "Sheen Scale",     "ext_properties")),
        ("sheen_color"              ,('RGB',   "Sheen Color",     "ext_properties")),
        ("sheen_roughness"          ,('FLOAT', "Sheen Roughness", "ext_properties"))

    ])

    ext_properties: PointerProperty(
        type=props.ArnoldShaderToon
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.create_socket(identifier="base")
        self.create_socket(identifier="base_color")
        self.create_socket(identifier="base_tonemap")
        self.create_socket(identifier="specular")
        self.create_socket(identifier="specular_color")
        self.create_socket(identifier="specular_roughness")
        self.create_socket(identifier="specular_tonemap")
        self.create_socket(identifier="specular_anisotropy")
        self.create_socket(identifier="specular_rotation")
        self.create_socket(identifier="transmission_color")
        self.create_socket(identifier="transmission_anisotropy")
        self.create_socket(identifier="transmission_rotation")
        self.create_socket(identifier="transmission_roughness")
        self.create_socket(identifier="transmission")
        self.create_socket(identifier="mask_color")
        self.create_socket(identifier="edge_color")
        self.create_socket(identifier="edge_tonemap")
        self.create_socket(identifier="edge_opacity")
        self.create_socket(identifier="edge_width_scale")
        self.create_socket(identifier="silhouette_color")
        self.create_socket(identifier="silhouette_tonemap")
        self.create_socket(identifier="silhouette_opacity")
        self.create_socket(identifier="silhouette_width_scale")
        self.create_socket(identifier="priority")
        self.create_socket(identifier="enable_silhouette")
        self.create_socket(identifier="angle_threshold")
        #self.create_socket(identifier="normal_type")
        self.create_socket(identifier="highlight_color")
        self.create_socket(identifier="highlight_size")
        self.create_socket(identifier="rim_light_width")
        self.create_socket(identifier="rim_light_color")
        self.create_socket(identifier="IOR")
        self.create_socket(identifier="normal")
        self.create_socket(identifier="tangent")
        self.create_socket(identifier="sheen")
        self.create_socket(identifier="sheen_color")
        self.create_socket(identifier="sheen_roughness")
        self.create_socket(identifier="emission")
        self.create_socket(identifier="emission_color")

    def draw_buttons_ext(self, context, layout):
        inputs = self.inputs
        properties = self.ext_properties

        links = {i.identifier: i.is_linked for i in inputs}

        # Base
        sublayout = ui._subpanel(layout, "Base", properties.ui_base,
                              "ext_properties", "ui_base", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "base", links)
            _draw_property(col, properties, "base_color", links)
            _draw_property(col, properties, "base_tonemap", links)

        # Specular
        sublayout = ui._subpanel(layout, "Specular", properties.ui_specular,
                              "ext_properties", "ui_specular", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "specular", links)
            _draw_property(col, properties, "specular_color", links)
            _draw_property(col, properties, "specular_roughness", links)
            _draw_property(col, properties, "specular_tonemap", links)
            _draw_property(col, properties, "specular_anisotropy", links)
            _draw_property(col, properties, "specular_rotation", links)
            _draw_property(col, properties, "lights", links)
            _draw_property(col, properties, "highlight_color", links)
            _draw_property(col, properties, "highlight_size", links)
            _draw_property(col, properties, "aov_highlight", links)
            _draw_property(col, properties, "rim_light", links)
            _draw_property(col, properties, "rim_light_color", links)
            _draw_property(col, properties, "rim_light_width", links)
            _draw_property(col, properties, "aov_rim_light", links)


        # Transmission
        sublayout = ui._subpanel(layout, "Transmission", properties.ui_transmission,
                              "ext_properties", "ui_transmission", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "transmission", links)
            _draw_property(col, properties, "transmission_color", links)
            _draw_property(col, properties, "transmission_roughness", links)
            _draw_property(col, properties, "transmission_anisotropy", links)
            _draw_property(col, properties, "transmission_rotation", links)

        # Edge
        sublayout = ui._subpanel(layout, "Edge", properties.ui_edge,
                              "ext_properties", "ui_edge", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "mask_color", links)
            _draw_property(col, properties, "edge_color", links)
            _draw_property(col, properties, "edge_tonemap", links)
            _draw_property(col, properties, "edge_opacity", links)
            _draw_property(col, properties, "edge_width_scale", links)

        # Silhouette
        sublayout = ui._subpanel(layout, "Silhouette", properties.ui_silhouette,
                              "ext_properties", "ui_silhouette", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "silhouette_color", links)
            _draw_property(col, properties, "silhouette_tonemap", links)
            _draw_property(col, properties, "silhouette_opacity", links)
            _draw_property(col, properties, "silhouette_width_scale", links)
            _draw_property(col, properties, "priority", links)
            _draw_property(col, properties, "enable_silhouette", links)
            _draw_property(col, properties, "ignore_throughput", links)
            _draw_property(col, properties, "enable", links)
            _draw_property(col, properties, "id_difference", links)
            _draw_property(col, properties, "shader_difference", links)
            _draw_property(col, properties, "uv_threshold", links)
            _draw_property(col, properties, "angle_threshold", links)
            _draw_property(col, properties, "normal_type", links)


        # Emission
        sublayout = ui._subpanel(layout, "Emission", properties.ui_emission,
                              "ext_properties", "ui_emission", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "emission", links)
            _draw_property(col, properties, "emission_color", links)

        # Sheen
        sublayout = ui._subpanel(layout, "Sheen", properties.ui_sheen,
                              "ext_properties", "ui_sheen", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "sheen", links)
            _draw_property(col, properties, "sheen_color", links)
            _draw_property(col, properties, "sheen_roughness", links)

        # Advanced
        sublayout = ui._subpanel(layout, "Advanced", properties.ui_advanced,
                              "ext_properties", "ui_advanced", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "IOR", links)
            _draw_property(col, properties, "normal", links)
            _draw_property(col, properties, "tangent", links)
            _draw_property(col, properties, "indirect_diffuse", links)
            _draw_property(col, properties, "indirect_specular", links)
            _draw_property(col, properties, "bump_mode", links)
            _draw_property(col, properties, "energy_conserving", links)
            _draw_property(col, properties, "user_id", links)


    def _find_index(self, identifier):
        ret = 0
        socks = iter(self.sockets)
        for i in self.inputs:
            for s in socks:
                if s == identifier:
                    return ret
                if s == i.identifier:
                    ret += 1
                    break
            else:
                break
        return ret

    def create_socket(self, identifier):
        from_index = len(self.inputs)
        to_index = self._find_index(identifier)
        type, name, path = self.sockets[identifier]
        sock = self.inputs.new(type="ArnoldNodeSocketProperty", name=name, identifier=identifier)
        sock.path = path
        sock.attr = identifier
        if type in ('RGB', 'RGBA'):
            sock.is_color = True
            sock.color = (0.78, 0.78, 0.16, 1 if type == 'RGB' else 0.5)
        elif type == 'FLOAT':
            sock.color = (0.63, 0.63, 0.63, 1.0)
        if to_index < from_index:
            self.inputs.move(from_index, to_index)

    @property
    def ai_properties(self):
        links = [i.identifier for i in self.inputs if i.is_linked]
        props = self.ext_properties
        ret = {
            # 'exit_to_background': ('BOOL', props.exit_to_background),
            # 'caustics': ('BOOL', props.caustics),
            # 'internal_reflections': ('BOOL', props.internal_reflections),
        }
        for i, (t, n, p) in self.sockets.items():
            if i not in links:
                ret[i] = (t, self.path_resolve(p + "." + i if p else i))
        return ret

@ArnoldRenderEngine.register_class
class ArnoldNodeUtility(ArnoldNode):
    bl_label = "Utility"
    bl_icon = 'MATERIAL'

    ai_name = "utility"

    color_mode: EnumProperty(
        name="Color Mode",
        items=[
            ('color', "Color", "Single color output"),
            ('ng', "Geometric Normal", "Shader normals in world space."),
            ('ns', "Un-bumped Normal", "Smooth un-bumped normals in screen space."),
            ('n', "Normal", "Geometry normals in world space."),
            ('bary', "Barycentric Coords", "Barycentry coordinates (bu corresponds to red and bv to green) of the primitive."),
            ('uv', "UV Coords", "UV coordinates (u corresponds to red and v to green) of the primitive."),
            ('u', "U Coords", "U coordinate mapped to the red, green and blue channels."),
            ('v', "V Coords", "V coordinate mapped to the red, green and blue channels."),
            ('dpdu', "U Surface Derivative (dPdu)", "Surface derivative with respect to u coordinate."),
            ('dpdv', "V Surface Derivative (dPdv)", "Surface derivative with respect to v coordinate."),
            ('p', "Shading Point", "Shading point, relative to the Bounding Box."),
            ('prims', "Primitive ID", "Each primitive ID is represented as a different color."),
            ('uniformid', "Uniform ID", "Allows you to color by patch instad of by polygon and by curve instead of curve segments."),
            ('wire', "Triangle Wireframe", "Renders a triangulated wireframe of the mesh."),
            ('polywire', "Polygon Wireframe", "Renders a plygon wireframe of the mesh."),
            ('obj', "Object", "Object mode uses the name of the shapes to compute the color."),
            ('edgelength', "Edge Length", "Shows the edge length of the primitive as a heatmap."),
            ('floatgrid', "Floatgrid", "A color is mapped around a Hash function based on the Shading Point."),
            ('reflectline', "Reflection Lines", "Use to diagnose the contour lines of a mesh."),
            ('bad_uvs', "Bad UVs", "Returns magenta in the UV of the privitive that are degenerated."),
            ('nlights', "Number of lights", "Shows the relative number of lights considered at the shading point."),
            ('id', "Object ID", "Id mode uses the ID parameter shapes have in order to compute the color."),
            ('bumpdiff', "Bump Difference", "This mode shows how far the bump and autobump normals vary from the base smooth-shaded normals as a heatmap."),
            ('pixelerror', "Subdivision Pixel Error", "Shows as a heatmap mode, the edge lenth of the privitive based on how well the polygon matches the subdiv_pixel_error.")
        ],
        default='color'
    )
    shade_mode: EnumProperty(
        name="Shade Mode",
        items=[
            ('ndoteye', "Ndoteye", "Uses a dot product between the Normal and the Eye vector."),
            ('lambert', "Lambert", "Uses a Lambertian shading model."),
            ('flat', "Flat", "Renders the model as a pure, solid flatly lit and shaded color."),
            ('ambocc', "Ambocc", "Renders the model usgin an ambient occlusion technique."),
            ('plastic', "Plastic", "Has both diffuse (0.7) and specular (0.1) components.")
        ],
        default='ndoteye'
    )
    overlay_mode: EnumProperty(
        name="Overlay Mode",
        items=[
            ('none', "None", "None"),
            ('wire', "Wire", "Wire"),
            ('polywire', "Polywire", "Polywire")
        ],
        default='none'
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Color", identifier="color")
        self.inputs.new(type="NodeSocketFloat", name="Opacity", identifier="opacity").default_value = 1
        self.inputs.new(type="NodeSocketFloat", name="AO Distance", identifier="ao_distance").default_value = 100

    def draw_buttons(self, context, layout):
        layout.prop(self, "color_mode", text="")
        layout.prop(self, "shade_mode", text="")
        layout.prop(self, "overlay_mode", text="")

    @property
    def ai_properties(self):
        return {
            "color_mode": ('STRING', self.color_mode),
            "shade_mode": ('STRING', self.shade_mode),
            "overlay_mode": ('STRING', self.overlay_mode)
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeFlat(ArnoldNode):
    bl_label = "Flat"
    bl_icon = 'MATERIAL'

    ai_name = "flat"

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Color", identifier="color")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Opacity", identifier="opacity")




def translate_cycles_node(ri, node, mat_name):
    if node.bl_idname == 'ShaderNodeGroup':
        translate_node_group(ri, node, mat_name)
        return

    if node.bl_idname not in cycles_node_map.keys():
        print('No translation for node of type %s named %s' %
              (node.bl_idname, node.name))
        return

    mapping = cycles_node_map[node.bl_idname]
    params = {}
    for in_name, input in node.inputs.items():
        param_name = "%s %s" % (get_socket_type(
            node, input), get_socket_name(node, input))
        if input.is_linked:
            param_name = 'reference ' + param_name
            link = input.links[0]
            param_val = get_output_param_str(
                link.from_node, mat_name, link.from_socket, input)

        else:
            param_val = rib(input.default_value,
                            type_hint=get_socket_type(node, input))
            # skip if this is a vector set to 0 0 0
            if input.type == 'VECTOR' and param_val == [0.0, 0.0, 0.0]:
                continue

        params[param_name] = param_val

    ramp_size = 256
    if node.bl_idname == 'ShaderNodeValToRGB':
        colors = []
        alphas = []

        for i in range(ramp_size):
            c = node.color_ramp.evaluate(float(i) / (ramp_size - 1.0))
            colors.extend(c[:3])
            alphas.append(c[3])
        params['color[%d] ramp_color' % ramp_size] = colors
        params['float[%d] ramp_alpha' % ramp_size] = alphas
    elif node.bl_idname == 'ShaderNodeVectorCurve':
        colors = []
        node.mapping.initialize()
        r = node.mapping.curves[0]
        g = node.mapping.curves[1]
        b = node.mapping.curves[2]

        for i in range(ramp_size):
            v = float(i) / (ramp_size - 1.0)
            colors.extend([r.evaluate(v), g.evaluate(v), b.evaluate(v)])

        params['color[%d] ramp' % ramp_size] = colors

    elif node.bl_idname == 'ShaderNodeRGBCurve':
        colors = []
        node.mapping.initialize()
        c = node.mapping.curves[0]
        r = node.mapping.curves[1]
        g = node.mapping.curves[2]
        b = node.mapping.curves[3]

        for i in range(ramp_size):
            v = float(i) / (ramp_size - 1.0)
            c_val = c.evaluate(v)
            colors.extend([r.evaluate(v) * c_val, g.evaluate(v)
                           * c_val, b.evaluate(v) * c_val])

        params['color[%d] ramp' % ramp_size] = colors

    #print('doing %s %s' % (node.bl_idname, node.name))
    # print(params)
    ri.Pattern(mapping, get_node_name(node, mat_name), params)




cycles_node_map = {
    'ShaderNodeAttribute': 'node_attribute',
    'ShaderNodeBlackbody': 'node_checker_blackbody',
    'ShaderNodeTexBrick': 'node_brick_texture',
    'ShaderNodeBrightContrast': 'node_brightness',
    'ShaderNodeTexChecker': 'node_checker_texture',
    'ShaderNodeBump': 'node_bump',
    'ShaderNodeCameraData': 'node_camera',
    'ShaderNodeTexChecker': 'node_checker_texture',
    'ShaderNodeCombineHSV': 'node_combine_hsv',
    'ShaderNodeCombineRGB': 'node_combine_rgb',
    'ShaderNodeCombineXYZ': 'node_combine_xyz',
    'ShaderNodeTexEnvironment': 'node_environment_texture',
    'ShaderNodeFresnel': 'node_fresnel',
    'ShaderNodeGamma': 'node_gamma',
    'ShaderNodeNewGeometry': 'node_geometry',
    'ShaderNodeTexGradient': 'node_gradient_texture',
    'ShaderNodeHairInfo': 'node_hair_info',
    'ShaderNodeInvert': 'node_invert',
    'ShaderNodeHueSaturation': 'node_hsv',
    'ShaderNodeTexImage': 'node_image_texture',
    'ShaderNodeHueSaturation': 'node_hsv',
    'ShaderNodeLayerWeight': 'node_layer_weight',
    'ShaderNodeLightFalloff': 'node_light_falloff',
    'ShaderNodeLightPath': 'node_light_path',
    'ShaderNodeTexMagic': 'node_magic_texture',
    'ShaderNodeMapping': 'node_mapping',
    'ShaderNodeMath': 'node_math',
    'ShaderNodeMixRGB': 'node_mix',
    'ShaderNodeTexMusgrave': 'node_musgrave_texture',
    'ShaderNodeTexNoise': 'node_noise_texture',
    'ShaderNodeNormal': 'node_normal',
    'ShaderNodeNormalMap': 'node_normal_map',
    'ShaderNodeObjectInfo': 'node_object_info',
    'ShaderNodeParticleInfo': 'node_particle_info',
    'ShaderNodeRGBCurve': 'node_rgb_curves',
    'ShaderNodeValToRGB': 'node_rgb_ramp',
    'ShaderNodeSeparateHSV': 'node_separate_hsv',
    'ShaderNodeSeparateRGB': 'node_separate_rgb',
    'ShaderNodeSeparateXYZ': 'node_separate_xyz',
    'ShaderNodeTexSky': 'node_sky_texture',
    'ShaderNodeTangent': 'node_tangent',
    'ShaderNodeTexCoord': 'node_texture_coordinate',
    'ShaderNodeUVMap': 'node_uv_map',
    'ShaderNodeValue': 'node_value',
    'ShaderNodeVectorCurves': 'node_vector_curves',
    'ShaderNodeVectorMath': 'node_vector_math',
    'ShaderNodeVectorTransform': 'node_vector_transform',
    'ShaderNodeTexVoronoi': 'node_voronoi_texture',
    'ShaderNodeTexWave': 'node_wave_texture',
    'ShaderNodeWavelength': 'node_wavelength',
    'ShaderNodeWireframe': 'node_wireframe',
}



@ArnoldRenderEngine.register_class
class ArnoldNodeShadowMatte(ArnoldNode):
    bl_label = "Shadow Matte"
    bl_icon = 'MATERIAL'

    ai_name="shadow_matte"

    ui_background: BoolProperty(
        name="Background",
        default=True
    )

    ui_shadow: BoolProperty(
        name="Background",
        default=True
    )

    ui_diffuse: BoolProperty(
        name="Background",
        default=True
    )

    ui_specular: BoolProperty(
        name="Background",
        default=True
    )

    ui_light: BoolProperty(
        name="Background",
        default=True
    )

    ui_aov: BoolProperty(
        name="Background",
        default=True
    )

    background: EnumProperty(
        name="Background",
        items=[
            ('scene_background', "Scene Background", "Scene Background"),
            ('background_color', "Background Color", "Background Color")
        ],
        default='scene_background'
    )

    background_color: FloatVectorProperty(
        name="Background Color",
        size=3,
        min=0, max=1,
        subtype='COLOR',
        default=(1, 1, 1)
    ) 

    shadow_color: FloatVectorProperty(
        name="Shadow Color",
        size=3,
        min=0, max=1,
        subtype='COLOR',
        default=(0, 0, 0)
    )

    shadow_opacity: FloatProperty(
        name="Shadow Opacity",
        subtype='FACTOR',
        default=1
    )

    backlighting: FloatProperty(
        name="Shadow Opacity",
        subtype='FACTOR',
        default=0
    )

    alpha_mask: BoolProperty(
        name="Alpha Mask",
        default=True
    )

    diffuse_color: FloatVectorProperty(
        name="Diffuse Color",
        size=3,
        min=0, max=1,
        subtype='COLOR',
        default=(1, 1, 1)
    )

    diffuse_intensity: FloatProperty(
        name="Diffuse Intensity",
        subtype='FACTOR',
        default=0.7
    )

    use_background: BoolProperty(
        name="Use Background",
        default=True
    )
    
    indirect_diffuse_enable: BoolProperty(
        name="Indirect Diffuse",
        default=False
    )

    indirect_specular_enable: BoolProperty(
        name="Indirect Specular",
        default=False
    )

    specular_color: FloatVectorProperty(
        name="Specular Color",
        size=3,
        min=0, max=1,
        subtype='COLOR',
        default=(1, 1, 1)
    )

    specular_intensity: FloatProperty(
        name="Specular Intensity",
        subtype='FACTOR',
        default=1.0
    )

    specular_roughness: FloatProperty(
        name="Specular Roughness",
        subtype='FACTOR',
        default=0.1
    )

    specular_IOR: FloatProperty(
        name="Specular IOR",
        subtype='FACTOR',
        default=1.52
    )

    light_group: StringProperty(
        name="Light Group",
        default=""
    )

    shadow_aov: StringProperty(
        name="Shadow AOV",
        default="shadow"
    )

    shadow_diff: StringProperty(
        name="Shadow Diff",
        default="shadow_diff"
    )

    shadow_mask: StringProperty(
        name="Shadow Mask",
        default="shadow_mask"
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        
    def draw_buttons(self, context, layout):
        col = layout.column()
        sublayout = ui._nodesubpanel(layout, "Background", self.ui_background, "ui_background", "node")
        if sublayout:
            col = sublayout.column()
            col.prop(self, "background", text="Background")
            col.prop(self, "background_color", text="Background Color")
        sublayout = ui._nodesubpanel(layout, "Shadows", self.ui_shadow, "ui_shadow", "node")
        if sublayout:
            col = sublayout.column()
            col.prop(self, "shadow_color", text="Shadow Color")
            col.prop(self, "shadow_opacity", text="Shadow Opacity")
            col.prop(self, "backlighting", text="Backlighting")
            col.prop(self, "alpha_mask", text="Alpha Mask")
        sublayout = ui._nodesubpanel(layout, "Diffuse", self.ui_diffuse, "ui_diffuse", "node")
        if sublayout:
            col = sublayout.column()
            col.prop(self, "diffuse_color", text="Color")
            col.prop(self, "diffuse_intensity", text="Intensity")
            col.prop(self, "use_background", text="Use Background")
            col.prop(self, "indirect_diffuse_enable", text="Indirect Diffuse")
        sublayout = ui._nodesubpanel(layout, "Specular", self.ui_specular, "ui_specular", "node")
        if sublayout:
            col = sublayout.column()
            col.prop(self, "indirect_specular_enable", text="Indirect Specular")
            col.prop(self, "specular_color", text="Color")
            col.prop(self, "specular_intensity", text="Intensity")
            col.prop(self, "specular_roughness", text="Roughness")
            col.prop(self, "specular_IOR", text="IOR")
        sublayout = ui._nodesubpanel(layout, "Lights", self.ui_light, "ui_light", "node")
        if sublayout:
            col = sublayout.column()
            col.prop(self, "light_group", text="Light Group")
        sublayout = ui._nodesubpanel(layout, "AOVs", self.ui_aov, "ui_aov", "node")
        if sublayout:
            col = sublayout.column()
            col.prop(self, "shadow_aov", text="Shadow")
            col.prop(self, "shadow_diff", text="Shadow Diff")
            col.prop(self, "shadow_mask", text="Shadow Mask")

    @property
    def ai_properties(self):
        return {
            "background": ('STRING', self.background),
            "background_color": ('RGB', self.background_color),
            "shadow_color": ('RGB', self.shadow_color),
            "shadow_opacity": ('FLOAT', self.shadow_opacity),
            "backlighting": ('FLOAT', self.backlighting),
            "alpha_mask": ('BOOL', self.alpha_mask),
            "diffuse_color": ('RGB', self.diffuse_color),
            "diffuse_intensity": ('FLOAT', self.diffuse_intensity),
            "use_background": ('BOOL', self.use_background),
            "indirect_diffuse_enable": ('BOOL', self.indirect_diffuse_enable),
            "indirect_specular_enable": ('BOOL', self.indirect_specular_enable),
            "specular_color": ('RGB', self.specular_color),
            "specular_intensity": ('FLOAT', self.specular_intensity),
            "specular_roughness": ('FLOAT', self.specular_roughness),
            "specular_IOR": ('FLOAT', self.specular_IOR),
            "light_group": ('STRING', self.light_group),
            "shadow_aov": ('STRING', self.shadow_aov),
            "shadow_diff": ('STRING', self.shadow_diff),
            "shadow_mask": ('STRING', self.shadow_mask)
        }

@ArnoldRenderEngine.register_class
class ColorRampItem(PropertyGroup):
    offset: FloatProperty(name="Offset", default=0.0, min=0, max=1)
    value: FloatVectorProperty(name="", min=0, soft_max=1, subtype="COLOR")
    # For internal use
    index: IntProperty()
    node_name: StringProperty()

    def update_add_keyframe(self, context):
        data_path = 'nodes["%s"].ramp_items[%d]' % (self.node_name, self.index)
        self.id_data.keyframe_insert(data_path=data_path + ".offset")
        self.id_data.keyframe_insert(data_path=data_path + ".value")
        self["add_keyframe"] = False

    def update_remove_keyframe(self, context):
        data_path = 'nodes["%s"].ramp_items[%d]' % (self.node_name, self.index)
        self.id_data.keyframe_delete(data_path=data_path + ".offset")
        self.id_data.keyframe_delete(data_path=data_path + ".value")
        self["remove_keyframe"] = False

    # This is a bit of a hack, we use BoolProperties as buttons
    add_keyframe: BoolProperty(name="", description="Add a keyframe on the current frame",
                                default=False, update=update_add_keyframe)
    remove_keyframe: BoolProperty(name="", description="Remove the keyframe on the current frame",
                                   default=False, update=update_remove_keyframe)

@ArnoldRenderEngine.register_class
class ArnoldNodeRamp(ArnoldNode, bpy.types.Node):

    bl_label = "Ramp RGB"
    bl_icon = 'PREFERENCES'

    ai_name="ramp_rgb"
    bl_width_default = 250

    interpolation_items = [
        ("constant", "Constant", "Constant interpolation between values, smooth transition", 0),
        ("linear", "Linear", "Linear interpolation between values, smooth transition", 1),
        ("catmull-rom", "Catmull", "No interpolation between values, sharp transition", 2),
        ("monotone-cubic", "Cubic", "Cubic interpolation between values, smooth transition", 3),
    ]
    interpolation: EnumProperty(name="Mode", description="Interpolation type of band values",
                                 items=interpolation_items, default="constant")

    def update_add(self, context):
        if len(self.ramp_items) == 1:
            new_offset = 1
            new_value = (1, 1, 1)
        else:
            max_item = None

            for item in self.ramp_items:
                if max_item is None or item.offset > max_item.offset:
                    max_item = item

            new_offset = max_item.offset
            new_value = max_item.value

        new_item = self.ramp_items.add()
        new_item.offset = new_offset
        new_item.value = new_value
        new_item.index = len(self.ramp_items) - 1
        new_item.node_name = self.name

        self["add_item"] = False

    def update_remove(self, context):
        if len(self.ramp_items) > 2:
            self.ramp_items.remove(len(self.ramp_items) - 1)
        self["remove_item"] = False


    # This is a bit of a hack, we use BoolProperties as buttons
    add_item: BoolProperty(name="Add", description="Add an offset",
                            default=False, update=update_add)
    remove_item: BoolProperty(name="Remove", description="Remove last offset",
                               default=False, update=update_remove)
    ramp_items: CollectionProperty(type=ColorRampItem)
    
    def init(self, context):

        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")

        # Add inital items
        item_0 = self.ramp_items.add()
        item_0.offset = 0
        item_0.value = (0.0, 0.0, 0.0)
        item_0.index = 0
        item_0.node_name = self.name

        item_1 = self.ramp_items.add()
        item_1.offset = 1
        item_1.value = (1.0, 1.0, 1.0)
        item_1.index = 1
        item_1.node_name = self.name

    def copy(self, orig_node):
        for item in self.ramp_items:
            # We have to update the parent node's name by hand because it's a StringProperty
            item.node_name = self.name
        
    def draw_buttons(self, context, layout):
        layout.prop(self, "interpolation", expand=True)

        row = layout.row(align=True)
        row.prop(self, "add_item", icon="ADD")

        subrow = row.row(align=True)
        subrow.enabled = len(self.ramp_items) > 2
        subrow.prop(self, "remove_item", icon="REMOVE")

        for index, item in enumerate(self.ramp_items):
            row = layout.row(align=True)

            split = row.split(align=True, factor=0.55)
            split.prop(item, "offset", slider=True)
            split.prop(item, "value")

            node_tree = self.id_data
            anim_data = node_tree.animation_data
            # Keyframes are attached to fcurves, which are attached to the parent node tree
            if anim_data and anim_data.action:
                data_path = 'nodes["%s"].ramp_items[%d].offset' % (self.name, index)
                fcurves = (fcurve for fcurve in anim_data.action.fcurves if fcurve.data_path == data_path)

                fcurve_on_current_frame = False

                for fcurve in fcurves:
                    for keyframe_point in fcurve.keyframe_points:
                        frame = keyframe_point.co[0]
                        if frame == context.scene.frame_current:
                            fcurve_on_current_frame = True
                            break
            else:
                fcurve_on_current_frame = False

            if fcurve_on_current_frame:
                sub = row.row(align=True)
                # Highlight in red to show that a keyframe exists
                sub.alert = True
                sub.prop(item, "remove_keyframe", toggle=True, icon="KEY_DEHLT")
            else:
                row.prop(item, "add_keyframe", toggle=True, icon="KEY_HLT")

    @property
    def ai_properties(self):
        #scale = self.geometry_matrix_scale

        definitions = {
            "type": "u",
            "interpolation": self.interpolation,
            #"amount": self.inputs["Amount"].export(exporter, props),
        }

        offsets = []
        colors = []

        for index, item in enumerate(self.ramp_items):            
            definitions["offset%d" % index] = item.offset
            offsets.append(definitions["offset%d" % index])
            definitions["value%d" % index] = list(item.value)
            colors.append(definitions["value%d" % index])

        
        if self.interpolation == "constant":
            interpolations = [0]
        elif self.interpolation == "linear":
            interpolations = [1]
        elif self.interpolation == "catmull-rom":
            interpolations = [2]
        else:
            interpolations = [3]

        for i in range(len(offsets) - 1):
            interpolations.append(interpolations[0])

        # position = 1.0
        # color = (0,0,0)
        #interpolation = self.interpolation_items
        # matrix.rotate(Euler(self.geometry_matrix_rotation))
        # matrix = matrix.to_4x4()
        # matrix.translation = (self.geometry_matrix_translation)
        return {
            "type": ('STRING', definitions.get("type")),
            "interpolation": ('ARRAY', interpolations),
            "position": ('ARRAY', offsets),
            "color": ('ARRAY', colors)
            # "resolution": ('STRING', self.resolution),
            # "portal_mode": ('STRING', self.portal_mode),
            # "matrix": ('MATRIX', matrix),
            # "camera": ('BOOL', self.camera),
            # "diffuse": ('BOOL', self.diffuse),
            # "specular": ('BOOL', self.specular),
            # "sss": ('BOOL', self.sss),
            # "volume": ('BOOL', self.volume),
            # "transmission": ('BOOL', self.transmission)
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeBump2D(ArnoldNode):
    bl_label = "Bump 2D"
    bl_icon = 'MATERIAL'

    ai_name = "bump2d"

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGBA", identifier="output")
        self.inputs.new(type="NodeSocketFloat", name="Map", identifier="bump_map")
        self.inputs.new(type="NodeSocketFloat", name="Height", identifier="bump_height")
        self.inputs.new(type="NodeSocketShader", name="Shader", identifier="shader")


@ArnoldRenderEngine.register_class
class ArnoldNodeBump3D(ArnoldNode):
    bl_label = "Bump 3D"
    bl_icon = 'MATERIAL'

    ai_name = "bump3d"

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGBA", identifier="output")
        self.inputs.new(type="NodeSocketFloat", name="Map", identifier="bump_map")
        self.inputs.new(type="NodeSocketFloat", name="Height", identifier="bump_height")
        self.inputs.new(type="NodeSocketFloat", name="Epsilon", identifier="epsilon")
        self.inputs.new(type="NodeSocketShader", name="Shader", identifier="shader")


@ArnoldRenderEngine.register_class
class ArnoldNodeWireframe(ArnoldNode):
    bl_label = "Wireframe"
    bl_icon = 'MATERIAL'

    ai_name = "wireframe"

    edge_type: EnumProperty(
        name="Edge Type",
        items=[
            ('polygons', "Polygons", "Polygons"),
            ('triangles', "Triangles", "Triangles")
        ],
        default='triangles'
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Fill Color", identifier="fill_color")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Line Color", identifier="line_color").default_value = (0, 0, 0)
        self.inputs.new(type="NodeSocketFloat", name="Line Width", identifier="line_width").default_value = 1
        self.inputs.new(type="NodeSocketBool", name="Raster space", identifier="raster_space").default_value = True

    def draw_buttons(self, context, layout):
        layout.prop(self, "edge_type", text="")

    @property
    def ai_properties(self):
        return {
            "edge_type": ('STRING', self.edge_type)
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeAmbientOcclusion(ArnoldNode):
    bl_label = "Ambient Occlusion"
    bl_icon = 'MATERIAL'

    ai_name = "ambient_occlusion"

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.inputs.new(type="NodeSocketInt", name="Samples", identifier="samples").default_value = 3
        self.inputs.new(type="NodeSocketFloat", name="Spread", identifier="spread").default_value = 1
        self.inputs.new(type="NodeSocketFloat", name="Falloff", identifier="falloff")
        self.inputs.new(type="NodeSocketFloat", name="Near Clip", identifier="near_clip")
        self.inputs.new(type="NodeSocketFloat", name="Far Clip", identifier="far_clip").default_value = 100
        self.inputs.new(type="ArnoldNodeSocketColor", name="White", identifier="white")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Black", identifier="black").default_value = (0, 0, 0)
        self.inputs.new(type="ArnoldNodeSocketColor", name="Opacity", identifier="opacity")
        self.inputs.new(type="NodeSocketBool", name="Invert Normals", identifier="invert_normals")
        self.inputs.new(type="NodeSocketBool", name="Self Only", identifier="self_only")


@ArnoldRenderEngine.register_class
class ArnoldNodeMotionVector(ArnoldNode):
    bl_label = "Motion Vector"
    bl_icon = 'MATERIAL'

    ai_name = "motion_vector"

    raw: BoolProperty(
        name="Encode Raw Vector"
    )
    time0: FloatProperty(
        name="Start Time"
    )
    time1: FloatProperty(
        name="End time",
        default=1
    )
    max_displace: FloatProperty(
        name="Max Displace"
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "raw")
        col.prop(self, "max_displace")
        col.prop(self, "time0")
        col.prop(self, "time1")

    @property
    def ai_properties(self):
        return {
            "raw": ('BOOL', self.raw),
            "time0": ('FLOAT', self.time0),
            "time1": ('FLOAT', self.time1),
            "max_displace": ('FLOAT', self.max_displace),
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeRaySwitch(ArnoldNode):
    bl_label = "Ray Switch"
    bl_icon = 'MATERIAL'

    ai_name = "ray_switch"

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGBA", identifier="output")
        self.inputs.new(type="NodeSocketColor", name="Camera", identifier="camera").default_value = (1, 1, 1, 1)
        self.inputs.new(type="NodeSocketColor", name="Shadow", identifier="shadow").default_value = (1, 1, 1, 1)
        # self.inputs.new("NodeSocketColor", "Reflection", "reflection").default_value = (1, 1, 1, 1)
        # self.inputs.new("NodeSocketColor", "Refraction", "refraction").default_value = (1, 1, 1, 1)
        self.inputs.new(type="NodeSocketColor", name="Diffuse", identifier="diffuse").default_value = (1, 1, 1, 1)
        self.inputs.new(type="NodeSocketColor", name="Glossy", identifier="glossy").default_value = (1, 1, 1, 1)


@ArnoldRenderEngine.register_class
class ArnoldNodeStandardHair(ArnoldNode):
    bl_label = "Standard Hair"
    bl_icon = 'MATERIAL'
    bl_width_default = 200

    ai_name = "standard_hair"


    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        # Base
        self.inputs.new(type="NodeSocketFloat", name="Base", identifier="base").default_value = 1.0
        self.inputs.new(type="ArnoldNodeSocketColor", name="Base Color", identifier="base_color").default_value = (1.0, 1.0, 1.0)
        # Melanin
        self.inputs.new(type="NodeSocketFloat", name="Melanin", identifier="melanin").default_value = (1.0)
        self.inputs.new(type="NodeSocketFloat", name="Melanin Redness", identifier="melanin_redness").default_value = 0.0
        self.inputs.new(type="NodeSocketFloat", name="Melanin Randomize", identifier="melanin_randomize").default_value = 0
        # Roughness
        self.inputs.new(type="NodeSocketFloat", name="Roughness", identifier="roughness").default_value = 0.2
        self.inputs.new(type="NodeSocketFloat", name="Roughness Azimuthal", identifier="roughness_azimuthal").default_value = 0.2
        self.inputs.new(type="NodeSocketBool", name="Roughness Anisotropic", identifier="roughness_anisotropic ").default_value = False
        self.inputs.new(type="NodeSocketFloat", name="IOR", identifier="ior").default_value = 1.55
        self.inputs.new(type="NodeSocketFloat", name="Shift", identifier="shift").default_value = 2.5
        # Specular
        self.inputs.new(type="ArnoldNodeSocketColor", name="Specular Tint", identifier="specular_tint").default_value = (1.0, 1.0, 1.0)
        self.inputs.new(type="ArnoldNodeSocketColor", name="Secondary Specular Tint", identifier="specular2_tint").default_value = (1.0, 1.0, 1.0)
        # Transmission
        self.inputs.new(type="ArnoldNodeSocketColor", name="Transmission Tint", identifier="transmission_tint").default_value = (1.0, 1.0, 1.0)
        # Diffuse
        self.inputs.new(type="NodeSocketFloat", name="Diffuse", identifier="diffuse").default_value = 0
        self.inputs.new(type="ArnoldNodeSocketColor", name="Diffuse Color", identifier="diffuse_color").default_value = (1.0, 1.0, 1.0)
        # Emission
        self.inputs.new(type="NodeSocketFloat", name="Emission", identifier="emission").default_value = 0
        self.inputs.new(type="ArnoldNodeSocketColor", name="Emission Color", identifier="emission_color").default_value = (1.0, 1.0, 1.0)
        # Advanced
        self.inputs.new(type="NodeSocketFloat", name="Indirect Diffuse", identifier="indirect_diffuse").default_value= 1
        self.inputs.new(type="NodeSocketFloat", name="Indirect Specular", identifier="indirect_specular").default_value = 1
        self.inputs.new(type="NodeSocketFloat", name="Extra Depth", identifier="extra_depth").default_value= 1
        self.inputs.new(type="ArnoldNodeSocketColor", name="Opacity", identifier="opacity")


@ArnoldRenderEngine.register_class
class ArnoldNodeNoise(ArnoldNode):
    bl_label = "Noise"
    bl_icon = 'TEXTURE'

    ai_name = "noise"

    octaves: IntProperty(
        name="Octaves",
        default=1
    )
    coord_space: EnumProperty(
        name="Space",
        description="Space Coordinates",
        items=[
            ('world', "World", "World space"),
            ('object', "Object", "Object space"),
            ('Pref', "Pref", "Pref")
        ],
        default='object'
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketFloat", name="Value", identifier="output")
        self.inputs.new(type="NodeSocketFloat", name="Distortion", identifier="distortion")
        self.inputs.new(type="NodeSocketFloat", name="Lacunarity", identifier="lacunarity").default_value = 1.92
        self.inputs.new(type="NodeSocketFloat", name="Amplitude", identifier="amplitude").default_value = 1
        self.inputs.new(type="NodeSocketVector", name="Scale", identifier="scale").default_value = (1, 1, 1)
        self.inputs.new(type="NodeSocketVector", name="Offset", identifier="offset")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "octaves")
        col.prop(self, "coord_space")

    @property
    def ai_properties(self):
        return {
            "octaves": ('INT', self.octaves),
            "coord_space": ('STRING', self.coord_space)
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeImage(ArnoldNode):
    bl_label = "Image"
    bl_icon = 'TEXTURE'
    bl_width_default = 170

    ai_name = "image"

    filename: StringProperty(
        name="Filename",
        subtype='FILE_PATH'
    )
    filter: EnumProperty(
        name="Filter",
        items=[
            ('closest', "Closest", "Closest"),
            ('bilinear', "Bilinear", "Bilinear"),
            ('bicubic', "Bicubic", "Bicubic"),
            ('smart_bicubic', "Smart Bicubic", "Smart Bicubic")
        ],
        default='smart_bicubic'
    )
    mipmap_bias: IntProperty(
        name="Mipmap Bias"
    )
    single_channel: BoolProperty(
        name="Single Channel"
    )
    start_channel: IntProperty(
        name="Start Channel",
        subtype='UNSIGNED',
        min=0, max=255
    )
    swrap: EnumProperty(
        name="U wrap",
        items=_WRAP_ITEMS,
        default='periodic'
    )
    twrap: EnumProperty(
        name="V wrap",
        items=_WRAP_ITEMS,
        default='periodic'
    )
    sscale: FloatProperty(
        name="Scale U",
        default=1,
    )
    tscale: FloatProperty(
        name="Scale V",
        default=1,
    )
    sflip: BoolProperty(
        name="Flip U"
    )
    tflip: BoolProperty(
        name="Flip V"
    )
    soffset: FloatProperty(
        name="Offset U"
    )
    toffset: FloatProperty(
        name="Offset V"
    )
    swap_st: BoolProperty(
        name="Swap UV"
    )
    uvset: StringProperty(
        name="UV set"
    )
    ignore_missing_textures: BoolProperty(
        name="Ignore Missing Tiles"
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketColor", name="RGBA", identifier="output")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Multiply", identifier="multiply")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Offset", identifier="offset").default_value = (0, 0, 0)
        self.inputs.new(type="NodeSocketColor", name="Missing tile color", identifier="missing_texture_color")
        self.inputs.new(type="NodeSocketVector", name="UV coords", identifier="uvcoords").hide_value = True

    def draw_buttons(self, context, layout):
        layout.prop(self, "filename", text="", icon='IMAGE')

        col = layout.column()
        col.prop(self, "filter")
        col.prop(self, "mipmap_bias")
        col.prop(self, "single_channel")
        col.prop(self, "start_channel")

        col = layout.column()
        col.prop(self, "uvset")

        col.label(text="Offset:")
        scol = col.column(align=True)
        scol.prop(self, "soffset", text="U")
        scol.prop(self, "toffset", text="V")

        col.label(text="Scale:")
        scol = col.column(align=True)
        scol.prop(self, "sscale", text="U")
        scol.prop(self, "tscale", text="V")

        scol = col.column(align=True)
        scol.label(text="Wrap:")
        row = scol.row(align=True)
        sscol = row.column(align=True)
        sscol.alignment = 'LEFT'
        sscol.label(text="U:")
        sscol.label(text="V:")
        sscol = row.column(align=True)
        sscol.prop(self, "swrap", text="")
        sscol.prop(self, "twrap", text="")

        scol = col.column(align=True)
        scol.prop(self, "sflip")
        scol.prop(self, "tflip")
        scol.prop(self, "swap_st")

    @property
    def ai_properties(self):
        props = {
            "filter": ('STRING', self.filter),
            "mipmap_bias": ('INT', self.mipmap_bias),
            "single_channel": ('BOOL', self.single_channel),
            "start_channel": ('BYTE', self.start_channel),
            "swrap": ('STRING', self.swrap),
            "twrap": ('STRING', self.twrap),
            "sscale": ('FLOAT', self.sscale),
            "tscale": ('FLOAT', self.tscale),
            "sflip": ('BOOL', self.sflip),
            "tflip": ('BOOL', self.tflip),
            "soffset": ('FLOAT', self.soffset),
            "toffset": ('FLOAT', self.toffset),
            "swap_st": ('BOOL', self.swap_st),
            "ignore_missing_textures": ('BOOL', self.swap_st),
        }
        if self.filename:
            props["filename"] = ('STRING', bpy.path.abspath(self.filename))
        if self.uvset:
            props["uvset"] = ('STRING', self.uvset)
        return props


@ArnoldRenderEngine.register_class
class ArnoldNodeSky(ArnoldNode):
    bl_label = "Sky (Deprecated)"
    bl_icon = 'WORLD'
    bl_width_default = 220

    ai_name = "sky"

    visibility: IntProperty(
        name="Visibility",
        default=255
    )
    opaque_alpha: BoolProperty(
        name="Opaque Alpha",
        default=True
    )
    format: EnumProperty(
        name="Format",
        items=[
            ('mirrored_ball', "Mirrored Ball", "Mirrored Ball"),
            ('angular', "Angular", "Angular"),
            ('latlong', "LatLong", "LatLong")
        ],
        default='angular'
    )
    X_angle: FloatProperty(
        name="X",
        description="X angle"
    )
    Y_angle: FloatProperty(
        name="Y",
        description="Y angle"
    )
    Z_angle: FloatProperty(
        name="Z",
        description="Z angle"
    )
    X: FloatVectorProperty(
        name="X",
        soft_min=-1, soft_max=1,
        default=(1, 0, 0)
    )
    Y: FloatVectorProperty(
        name="Y",
        soft_min=-1, soft_max=1,
        default=(0, 1, 0)
    )
    Z: FloatVectorProperty(
        name="Z",
        soft_min=-1, soft_max=1,
        default=(0, 0, 1)
    )

    def _visibility(mask):
        def get(self):
            return self.visibility & mask

        def set(self, value):
            if value:
                self.visibility |= mask
            else:
                self.visibility &= ~mask

        return {
            "get": get,
            "set": set
        }

    visibility_camera: BoolProperty(
        name="Camera",
        **_visibility(1)
    )
    visibility_shadow: BoolProperty(
        name="Shadow",
        **_visibility(1 << 1)
    )
    visibility_reflection: BoolProperty(
        name="Reflection",
        **_visibility(1 << 2)
    )
    visibility_refraction: BoolProperty(
        name="Refraction",
        **_visibility(1 << 3)
    )
    visibility_diffuse: BoolProperty(
        name="Diffuse",
        **_visibility(1 << 4)
    )
    visibility_glossy: BoolProperty(
        name="Glossy",
        **_visibility(1 << 5)
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Color", identifier="color")
        self.inputs.new(type="NodeSocketFloat", name="Intensity", identifier="intensity").default_value = 1

    def draw_buttons(self, context, layout):
        layout.prop(self, "format")
        layout.prop(self, "opaque_alpha")

        col = layout.column()
        col.label(text="Visibility:")
        flow = col.column_flow(align=True)
        flow.prop(self, "visibility_camera")
        flow.prop(self, "visibility_shadow")
        flow.prop(self, "visibility_reflection")
        flow.prop(self, "visibility_refraction")
        flow.prop(self, "visibility_diffuse")
        flow.prop(self, "visibility_glossy")

        col = layout.column()
        col.label(text="Angle:")
        scol = col.column(align=True)
        scol.prop(self, "X_angle")
        scol.prop(self, "Y_angle")
        scol.prop(self, "Z_angle")

        col.label(text="Orientation:")
        row = col.row(align=True)
        col = row.column(align=True)
        col.alignment = 'LEFT'
        col.label(text="X:")
        col.label(text="Y:")
        col.label(text="Z:")
        col = row.column(align=True)
        col.row(align=True).prop(self, "X", text="", slider=True)
        col.row(align=True).prop(self, "Y", text="", slider=True)
        col.row(align=True).prop(self, "Z", text="", slider=True)

    @property
    def ai_properties(self):
        return {
            "visibility": ('INT', self.visibility),
            "opaque_alpha": ('BOOL', self.opaque_alpha),
            "format": ('STRING', self.format),
            "X_angle": ('FLOAT', self.X_angle),
            "Y_angle": ('FLOAT', self.Y_angle),
            "Z_angle": ('FLOAT', self.Z_angle),
            "X": ('VECTOR', self.X),
            "Y": ('VECTOR', self.Y),
            "Z": ('VECTOR', self.Z),
        }

@ArnoldRenderEngine.register_class
class ArnoldNodeSkydome(ArnoldNode):
    bl_label = "Skydome"
    bl_icon = 'WORLD'

    ai_name = "skydome_light"

    # shader: FloatVectorProperty(
    #     name="Shader",
    #     subtype='COLOR',
    #     min=0, max=1,
    #     default=(1, 1, 1)
    # )

    resolution: StringProperty(
        name="Resolution",
        default="1000"
    )

    format: EnumProperty(
        name="Format",
        description="The type of Map being Connected",
        items=[
            ('latlong', "Lat-long", "Lat-long"),
            ('mirrored_ball', "Mirrored Ball", "Mirrored Ball"),
            ('angular', "Angular", "Angular")
        ],
        default='latlong'
    )

    portal_mode: EnumProperty(
        name="Portal Mode",
        description="Defines how the skydome light interacts with light portals.",
        items=[
            ('off', "Off", "Off"),
            ('interior_only', "Interior Only", "Interior Only"),
            ('interior_exterior', "Interior Exterior", "Interior Exterior")
        ],
        default='off'
    )

    # color: FloatVectorProperty(
    #     name="Color",
    #     subtype='COLOR',
    #     min=0, max=1,
    #     default=(1, 1, 1)
    # )

    # intensity: FloatProperty(
    #     name="Intensity",
    #     min=0, max=10,
    #     default=1.0
    # )
    #
    # exposure: FloatProperty(
    #     name="Exposure",
    #     min=0, max=10,
    #     default=0.0
    # )

    cast_shadows: BoolProperty(
        name="Cast Shadows",
        default=True
    )

    shadow_density: FloatProperty(
        name="Shadow Density",
        min=0, max=1,
        default=1.0
    )

    shadow_color: FloatVectorProperty(
        name="Shadow Color",
        subtype='COLOR',
        min=0, max=1,
        default=(0, 0, 0)
    )

    samples: FloatProperty(
        name="Samples",
        min=0, max=100,
        default=1
    )

    normalize: BoolProperty(
        name="Normalize",
        default=True
    )

    camera: BoolProperty(
        name="Camera",
        default=True
    )

    diffuse: BoolProperty(
        name="Diffuse",
        default=True
    )

    specular: BoolProperty(
        name="Specular",
        default=True
    )

    sss: BoolProperty(
        name="Subsurface",
        default=True
    )

    volume: BoolProperty(
        name="Volume",
        default=True
    )

    transmission: BoolProperty(
        name="Transmission",
        default=True
    )

    indirect: FloatProperty(
        name="Indirect",
        min= 0, max=10,
        default=1
    )

    max_bounces: FloatProperty(
        name="Max Bounces",
        min= 0, max=999,
        default=999
    )

    filters: FloatVectorProperty(
        name="Filters",
        subtype='COLOR',
        min=0, max=1,
        default=(0, 0, 0)
    )

    geometry_matrix_object: StringProperty(
        name="Object"
    )

    geometry_matrix_rotation: FloatVectorProperty(
        name="Rotation",
        subtype='XYZ',
        unit='ROTATION',
        default=(1.5707963268,0,0)
    )
    geometry_matrix_translation: FloatVectorProperty(
        name="Translation",
        subtype='XYZ'
    )

    geometry_matrix_scale: FloatVectorProperty(
        name="Scale",
        subtype='XYZ',
        default=(1, 1, 1)
    )

    # volume_samples: FloatProperty(
    #     name="Volume Samples",
    #     min = 0, max=100,
    #     default=1
    # )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="Background", identifier="output")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Color", identifier="color")
        #self.inputs.new(type="NodeSocketShader", name="Shader", identifier="shader")
        self.inputs.new(type="NodeSocketFloat", name="Intensity", identifier="intensity").default_value = 1
        self.inputs.new(type="NodeSocketFloat", name="Exposure", identifier="exposure").default_value = 0


    def draw_buttons(self, context, layout):
        layout.prop(self, "format")
        layout.prop(self, "resolution")
        layout.prop(self, "portal_mode")
        # layout.prop(self, "opaque_alpha")

        col = layout.column()
        col.label(text="Visibility:")
        flow = col.column_flow(align=True)
        flow.prop(self, "camera")
        flow.prop(self, "diffuse")
        flow.prop(self, "specular")
        flow.prop(self, "sss")
        flow.prop(self, "volume")
        flow.prop(self, "transmission")

        sub = col.box().column()
        sub.prop_search(self, "geometry_matrix_object", context.scene, "objects", text="")
        sub = sub.column()
        sub.enabled = not self.geometry_matrix_object
        sub.template_component_menu(self, "geometry_matrix_scale", name="Scale:")
        sub.template_component_menu(self, "geometry_matrix_rotation", name="Rotation:")
        sub.template_component_menu(self, "geometry_matrix_translation", name="Translation:")

    @property
    def ai_properties(self):
        scale = self.geometry_matrix_scale
        matrix = Matrix([
            [scale.x, 0, 0],
            [0, scale.y, 0],
            [0, 0, scale.z]
        ])
        matrix.rotate(Euler(self.geometry_matrix_rotation))
        matrix = matrix.to_4x4()
        matrix.translation = (self.geometry_matrix_translation)
        return {
            "format": ('STRING', self.format),
            "resolution": ('STRING', self.resolution),
            "portal_mode": ('STRING', self.portal_mode),
            "matrix": ('MATRIX', matrix),
            "camera": ('BOOL', self.camera),
            "diffuse": ('BOOL', self.diffuse),
            "specular": ('BOOL', self.specular),
            "sss": ('BOOL', self.sss),
            "volume": ('BOOL', self.volume),
            "transmission": ('BOOL', self.transmission)
        }

@ArnoldRenderEngine.register_class
class ArnoldNodePhysicalSky(ArnoldNode):
    bl_label = "Physical Sky"
    bl_icon = 'WORLD'

    ai_name = "physical_sky"

    turbidity: FloatProperty(
        name="Turbidity",
        default=3
    )
    ground_albedo: FloatVectorProperty(
        name="Ground Albedo",
        subtype='COLOR',
        min=0, max=1,
        default=(0.1, 0.1, 0.1)
    )
    #use_degrees (true)
    elevation: FloatProperty(
        name="Elevation",
        default=45
    )
    azimuth: FloatProperty(
        name="Azimuth",
        default=90
    )
    #sun_direction (0, 1, 0)
    enable_sun: BoolProperty(
        name="Enable Sun",
        default=True
    )
    sun_size: FloatProperty(
        name="Sun Size",
        default=0.51
    )
    sun_tint: FloatVectorProperty(
        name="Sun Tint",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )
    sky_tint: FloatVectorProperty(
        name="Sky Tint",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )
    intensity: FloatProperty(
        name="Intensity",
        default=1
    )
    X: FloatVectorProperty(
        name="X",
        soft_min=0, soft_max=1,
        default=(1, 0, 0)
    )
    Y: FloatVectorProperty(
        name="Y",
        soft_min=0, soft_max=1,
        default=(0, 1, 0)
    )
    Z: FloatVectorProperty(
        name="Z",
        soft_min=0, soft_max=1,
        default=(0, 0, 1)
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "turbidity")
        row = col.row(align=True)
        row.alignment = 'LEFT'
        row.prop(self, "ground_albedo", text="")
        row.label(text="Ground Albedo")
        col.prop(self, "elevation")
        col.prop(self, "azimuth")
        col.prop(self, "intensity")

        col = layout.column()
        row = col.row(align=True)
        row.alignment = 'LEFT'
        row.prop(self, "sky_tint", text="")
        row.label(text="Sky Tint")
        row = col.row(align=True)
        row.alignment = 'LEFT'
        row.prop(self, "sun_tint", text="")
        row.label(text="Sun Tint")
        col.prop(self, "sun_size")
        col.prop(self, "enable_sun")

        col.label(text="Orientation:")
        row = col.row(align=True)
        col = row.column(align=True)
        col.alignment = 'LEFT'
        col.label(text="X:")
        col.label(text="Y:")
        col.label(text="Z:")
        col = row.column(align=True)
        col.row(align=True).prop(self, "X", text="", slider=True)
        col.row(align=True).prop(self, "Y", text="", slider=True)
        col.row(align=True).prop(self, "Z", text="", slider=True)

    @property
    def ai_properties(self):
        return {
            "turbidity": ('FLOAT', self.turbidity),
            "ground_albedo": ('RGB', self.ground_albedo),
            "elevation": ('FLOAT', self.elevation),
            "azimuth": ('FLOAT', self.azimuth),
            "enable_sun": ('BOOL', self.enable_sun),
            "sun_size": ('FLOAT', self.sun_size),
            "sun_tint": ('RGB', self.sun_tint),
            "sky_tint": ('RGB', self.sky_tint),
            "intensity": ('FLOAT', self.sun_size),
            "X": ('VECTOR', self.X),
            "Y": ('VECTOR', self.Y),
            "Z": ('VECTOR', self.Z),
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeVolumeScattering(ArnoldNode):
    bl_label = "Volume Scattering"
    bl_icon = 'WORLD'

    ai_name = "volume_scattering"

    samples: IntProperty(
        name="Samples",
        default=5
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Color", identifier="rgb_density")
        self.inputs.new(type="NodeSocketFloat", name="Density", identifier="density")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Attenuation Color", identifier="rgb_attenuation")
        self.inputs.new(type="NodeSocketFloat", name="Attenuation", identifier="attenuation")
        self.inputs.new(type="NodeSocketFloat", name="Anisotropy", identifier="eccentricity")
        self.inputs.new(type="NodeSocketFloat", name="Camera", identifier="affect_camera").default_value = 1
        self.inputs.new(type="NodeSocketFloat", name="Diffuse", identifier="affect_diffuse")
        self.inputs.new(type="NodeSocketFloat", name="Reflection", identifier="affect_reflection").default_value = 1

    def draw_buttons(self, context, layout):
        layout.prop(self, "samples")

    @property
    def ai_properties(self):
        return {
            "samples": ('INT', self.samples),
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeFog(ArnoldNode):
    bl_label = "Fog"
    bl_icon = 'WORLD'

    ai_name = "fog"

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Color", identifier="color")
        self.inputs.new(type="NodeSocketFloat", name="Distance", identifier="distance").default_value = 0.02
        self.inputs.new(type="NodeSocketFloat", name="Height", identifier="height").default_value = 5
        self.inputs.new(type="NodeSocketVector", name="Ground Normal", identifier="ground_normal").default_value = (0, 0, 1)
        self.inputs.new(type="NodeSocketVectorXYZ", name="Ground Point", identifier="ground_point")


@ArnoldRenderEngine.register_class
class ArnoldNodeBarndoor(ArnoldNode):
    bl_label = "Barn Door"
    bl_icon = 'LIGHT'

    ai_name = "barndoor"

    top_left: FloatProperty(
        name="Left",
        soft_min=0, soft_max=1
    )
    top_right: FloatProperty(
        name="Right",
        soft_min=0, soft_max=1
    )
    top_edge: FloatProperty(
        name="Edge",
        soft_min=0, soft_max=1
    )
    right_top: FloatProperty(
        name="Top",
        soft_min=0, soft_max=1,
        default=1
    )
    right_bottom: FloatProperty(
        name="Bottom",
        soft_min=0, soft_max=1,
        default=1
    )
    right_edge: FloatProperty(
        name="Edge",
        soft_min=0, soft_max=1
    )
    bottom_left: FloatProperty(
        name="Left",
        soft_min=0, soft_max=1,
        default=1
    )
    bottom_right: FloatProperty(
        name="Right",
        soft_min=0, soft_max=1,
        default=1
    )
    bottom_edge: FloatProperty(
        name="Edge",
        soft_min=0, soft_max=1
    )
    left_top: FloatProperty(
        name="Top",
        soft_min=0, soft_max=1
    )
    left_bottom: FloatProperty(
        name="Bottom",
        soft_min=0, soft_max=1
    )
    left_edge: FloatProperty(
        name="Edge",
        soft_min=0, soft_max=1
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketVirtual", name="Filter", identifier="filter")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.label(text="Top:")
        col = col.column(align=True)
        col.prop(self, "top_left")
        col.prop(self, "top_right")
        col.prop(self, "top_edge")
        col = layout.column()
        col.label(text="Right:")
        col = col.column(align=True)
        col.prop(self, "right_top")
        col.prop(self, "right_bottom")
        col.prop(self, "right_edge")
        col = layout.column()
        col.label(text="Bottom:")
        col = col.column(align=True)
        col.prop(self, "bottom_left")
        col.prop(self, "bottom_right")
        col.prop(self, "bottom_edge")
        col = layout.column()
        col.label(text="Left:")
        col = col.column(align=True)
        col.prop(self, "left_top")
        col.prop(self, "left_bottom")
        col.prop(self, "left_edge")

    @property
    def ai_properties(self):
        return {
            "barndoor_top_left": ('FLOAT', self.top_left),
            "barndoor_top_right": ('FLOAT', self.top_right),
            "barndoor_top_edge": ('FLOAT', self.top_edge),
            "barndoor_right_top": ('FLOAT', self.right_top),
            "barndoor_right_bottom": ('FLOAT', self.right_bottom),
            "barndoor_right_edge": ('FLOAT', self.right_edge),
            "barndoor_bottom_left": ('FLOAT', self.bottom_left),
            "barndoor_bottom_right": ('FLOAT', self.bottom_right),
            "barndoor_bottom_edge": ('FLOAT', self.bottom_edge),
            "barndoor_left_top": ('FLOAT', self.left_top),
            "barndoor_left_bottom": ('FLOAT', self.left_bottom),
            "barndoor_left_edge": ('FLOAT', self.left_edge),
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeGobo(ArnoldNode):
    bl_label = "Gobo"
    bl_icon = 'LIGHT'

    ai_name = "gobo"

    rotate: FloatProperty(
        name="Rotate",
        description="Rotate the texture image."
    )
    offset: FloatVectorProperty(
        name="Offset",
        description="UV coordinate values used to offset the direction of the slide map.",
        size=2
    )
    density: FloatProperty(
        name="Density"
    )
    # TODO: add filter modes
    filter_mode: EnumProperty(
        name="Mode",
        description="Filter Mode",
        items=[
            ('blend', "Blend", "Blend"),
            ('replace', "Replace", "Replace"),
            ('add', "Add", "Add"),
            ('sub', "Sub", "Sub"),
            ('mix', "Mix", "Mix")
        ],
        default='blend'
    )
    scale_s: FloatProperty(
        name="Scale U",
        default=1
    )
    scale_t: FloatProperty(
        name="Scale V",
        default=1
    )
    wrap_s: EnumProperty(
        name="Wrap U",
        items=_WRAP_ITEMS,
        default='clamp'
    )
    wrap_t: EnumProperty(
        name="Wrap V",
        items=_WRAP_ITEMS,
        default='clamp'
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketVirtual", name="Filter", identifier="filter")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Slidemap", identifier="slidemap")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "filter_mode")
        col.prop(self, "density")
        col.prop(self, "rotate")
        col.prop(self, "offset")

        subcol = col.column(align=True)
        subcol.label(text="Weight:")
        subcol.prop(self, "scale_s", text="U")
        subcol.prop(self, "scale_t", text="V")

        subcol = col.column(align=True)
        subcol.label(text="Wrap:")
        row = subcol.row(align=True)
        col = row.column(align=True)
        col.alignment = 'LEFT'
        col.label(text="U:")
        col.label(text="V:")
        col = row.column(align=True)
        col.prop(self, "wrap_s", text="")
        col.prop(self, "wrap_t", text="")

    @property
    def ai_properties(self):
        return {
            "rotate": ('FLOAT', self.rotate),
            "offset": ('VECTOR2', self.offset),
            "density": ('FLOAT', self.density),
            "filter_mode": ('STRING', self.filter_mode),
            "scale_s": ('FLOAT', self.scale_s),
            "scale_t": ('FLOAT', self.scale_t),
            "wrap_s": ('STRING', self.wrap_s),
            "wrap_t": ('STRING', self.wrap_t),
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeLightDecay(ArnoldNode):
    bl_label = "Light Decay"
    bl_icon = 'LIGHT'

    ai_name = "light_decay"

    use_near_atten: BoolProperty(
        name="Use Near Attenuation"
    )
    use_far_atten: BoolProperty(
        name="Use Far Attenuation"
    )
    near_start: FloatProperty(
        name="Start",
        description="Near Start"
    )
    near_end: FloatProperty(
        name="End",
        description="Near End"
    )
    far_start: FloatProperty(
        name="Start",
        description="Far Start"
    )
    far_end: FloatProperty(
        name="End",
        description="Far End"
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketVirtual", name="Filter", identifier="filter")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "use_near_atten")
        sub = col.column(align=True)
        sub.label("Near:")
        sub.prop(self, "near_start")
        sub.prop(self, "near_end")
        col.separator()
        col.prop(self, "use_far_atten")
        sub = col.column(align=True)
        sub.label("Far:")
        sub.prop(self, "far_start")
        sub.prop(self, "far_end")

    @property
    def ai_properties(self):
        ret = {
            "use_near_atten": ('BOOL', self.use_near_atten),
            "use_far_atten": ('BOOL', self.use_far_atten),
            "near_start": ('FLOAT', self.near_start),
            "near_end": ('FLOAT', self.near_end),
            "far_start": ('FLOAT', self.far_start),
            "far_end": ('FLOAT', self.far_end),
        }
        return ret


@ArnoldRenderEngine.register_class
class ArnoldNodeLightBlocker(ArnoldNode):
    bl_label = "Light Blocker"
    bl_icon = 'LIGHT'

    ai_name = "light_blocker"

    geometry_type: EnumProperty(
        name="Type",
        description="Geometry Type",
        items=[
            ('box', "Box", "Box"),
            ('sphere', "Sphere", "Sphere"),
            ('plane', "Plane", "Plane"),
            ('cylinder', "Cylinder", "Cylinder")
        ],
        default='box'
    )
    #geometry_matrix: FloatVectorProperty(
    #    name="Matrix",
    #    subtype='MATRIX',
    #    size=16
    #)
    geometry_matrix_object: StringProperty(
        name="Object"
    )
    geometry_matrix_scale: FloatVectorProperty(
        name="Scale",
        subtype='XYZ',
        default=(1, 1, 1)
    )
    geometry_matrix_rotation: FloatVectorProperty(
        name="Rotation",
        subtype='XYZ',
        unit='ROTATION'
    )
    geometry_matrix_translation: FloatVectorProperty(
        name="Translation",
        subtype='XYZ'
    )
    #density: FloatProperty(
    #    name="Density"
    #)
    roundness: FloatProperty(
        name="Roundness"
    )
    width_edge: FloatProperty(
        name="Width",
        description="Width Edge"
    )
    height_edge: FloatProperty(
        name="Height",
        description="Height Edge"
    )
    ramp: FloatProperty(
        name="Ramp"
    )
    axis: EnumProperty(
        name="Axis",
        items=[
            ('x', "X", "X"),
            ('y', "Y", "Y"),
            ('z', "Z", "Z")
        ],
        default='x'
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketVirtual", name="Filter", identifier="filter")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Shader", identifier="shader").default_value = (0, 0, 0)
        self.inputs.new(type="NodeSocketFloat", name="Density", identifier="density")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "geometry_type")
        col.prop(self, "axis")
        col.prop(self, "ramp")
        col.prop(self, "height_edge")
        col.prop(self, "width_edge")
        col.prop(self, "roundness")
        col.label(text="Matrix:")
        sub = col.box().column()
        sub.prop_search(self, "geometry_matrix_object", context.scene, "objects", text="")
        sub = sub.column()
        sub.enabled = not self.geometry_matrix_object
        sub.template_component_menu(self, "geometry_matrix_scale", name="Weight:")
        sub.template_component_menu(self, "geometry_matrix_rotation", name="Rotation:")
        sub.template_component_menu(self, "geometry_matrix_translation", name="Translation:")

    @property
    def ai_properties(self):
        ret = {
            "geometry_type": ('STRING', self.geometry_type),
            "roundness": ('FLOAT', self.roundness),
            "width_edge": ('FLOAT', self.width_edge),
            "height_edge": ('FLOAT', self.height_edge),
            "ramp": ('FLOAT', self.ramp),
            "axis": ('STRING', self.axis)
        }
        name = self.geometry_matrix_object
        ob = bpy.data.objects.get(name) if name else None
        if ob is None:
            scale = self.geometry_matrix_scale
            matrix = Matrix([
                [scale.x, 0, 0],
                [0, scale.y, 0],
                [0, 0, scale.z]
            ])
            matrix.rotate(Euler(self.geometry_matrix_rotation))
            matrix = matrix.to_4x4()
            matrix.translation = self.geometry_matrix_translation
        else:
            matrix = ob.matrix_world
        ret['geometry_matrix'] = ('MATRIX', matrix)
        return ret

# @ArnoldRenderEngine.register_class
# class ArnoldMatrixTransform(ArnoldNode):
#     bl_label = "Matrix Transform"
#     bl_icon = 'WORLD'
#
#     ai_name = "matrix_transform"
#
#     # rotation_type: EnumProperty(
#     #     name="Rotation Type",
#     #     items=[
#     #         ('euler_angles', "closest", "closest"),
#     #         ('trilinear', "trilinear", "trilinear"),
#     #         ('tricubic', "tricubic", "tricubic")
#     #     ],
#     #     default='euler-angles'
#     # )
#     rotation: FloatVectorProperty(
#         name="Rotation",
#         subtype='XYZ',
#         unit='ROTATION'
#     )
#     translate: FloatVectorProperty(
#         name="Translation",
#         subtype='XYZ',
#         unit='TRANSLATION'
#     )
#     scale: FloatVectorProperty(
#         name="Scale",
#         subtype='XYZ',
#         unit='SCALE'
#     )
#
#     def draw_buttons(self, context, layout):
#         sub = col.box().column()
#         sub.prop_search(self, "geometry_matrix_object", context.scene, "objects", text="")
#         sub = sub.column()
#         sub.enabled = not self.geometry_matrix_object
#         sub.template_component_menu(self, "scale", name="Weight:")
#         sub.template_component_menu(self, "rotation", name="Rotation:")
#         sub.template_component_menu(self, "translate", name="Translation:")

@ArnoldRenderEngine.register_class
class ArnoldNodeDensity(ArnoldNode):
    bl_label = "Density"
    bl_icon = 'TEXTURE'

    ai_name = "density"

    interpolation: EnumProperty(
        name="Interpolation",
        items=[
            ('closest', "closest", "closest"),
            ('trilinear', "trilinear", "trilinear"),
            ('tricubic', "tricubic", "tricubic")
        ],
        default='trilinear'
    )

    def init(self, context):
        self.outputs.new(type="NodeSocketShader", name="RGB", identifier="output")
        self.inputs.new(type="NodeSocketString", identifier="scatter_channel")
        self.inputs.new(type="ArnoldNodeSocketColor", identifier="scatter_color")
        self.inputs.new(type="NodeSocketFloat", identifier="scatter_g")
        self.inputs.new(type="NodeSocketString", identifier="absorption_channel")
        self.inputs.new(type="ArnoldNodeSocketColor", identifier="absorption_color")
        self.inputs.new(type="NodeSocketString", identifier="emission_channel")
        # self.inputs.new("ArnoldNodeSocketColor", "emission_color")
        self.inputs.new(type="NodeSocketVector", identifier="position_offset")

    def draw_buttons(self, context, layout):
        layout.prop(self, "interpolation", text="")

    @property
    def ai_properties(self):
        return {
            "interpolation": ('STRING', self.interpolation)
        }



@ArnoldRenderEngine.register_class
class ArnoldNodeMixShader(ArnoldNode):
    bl_label = "Mix Shader"
    bl_icon = 'MATERIAL'

    ai_name = "mix_rgba"

    def init(self, context):
        self.outputs.new(type="ArnoldNodeSocketColor", name="Color", identifier="output")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Shader", identifier="shader1")
        self.inputs.new(type="ArnoldNodeSocketColor", name="Shader", identifier="shader2")
        self.inputs.new(type="NodeSocketFloat", name="Mix", identifier="mix").default_value = 0.5


class ArnoldNodeCategory(nodeitems_utils.NodeCategory):
    @classmethod
    def poll(cls, context):
        return (
            ArnoldRenderEngine.is_active(context) and
            context.space_data.tree_type == 'ShaderNodeTree'
        )


class ArnoldWorldNodeCategory(ArnoldNodeCategory):
    @classmethod
    def poll(cls, context):
        return (
            ArnoldRenderEngine.is_active(context) and
            context.space_data.tree_type == 'ARNOLD_WORLD_NODETREE'
        )


class ArnoldObjectNodeCategory(ArnoldNodeCategory):
    @classmethod
    def poll(cls, context):
        return (
            super().poll(context) and
            context.object.type != 'LIGHT'
        )


class ArnoldLightNodeCategory(ArnoldNodeCategory):
    @classmethod
    def poll(cls, context):
        return (
            super().poll(context) and
            context.object.type == 'LIGHT'
        )


def register():
    from nodeitems_builtins import (
        #ShaderNodeCategory,
        ShaderNodeCategory,
        node_group_items
    )

    # HACK: hide BI and Cycles nodes from 'Add' menu in Node editor
    def _poll(fn):
        @classmethod
        def _fn(cls, context):
            return (
                not ArnoldRenderEngine.is_active(context) and
                fn(context)
            )
        return _fn

    #ShaderNodeCategory.poll = _poll(ShaderNodeCategory.poll)
    ShaderNodeCategory.poll = _poll(ShaderNodeCategory.poll)

    node_categories = [
        # world
        ArnoldWorldNodeCategory("ARNOLD_NODES_WORLD_OUTPUT", "Arnold Output", items=[
            nodeitems_utils.NodeItem("ArnoldNodeWorldOutput")
        ]),
        ArnoldWorldNodeCategory("ARNOLD_NODES_WORLD_BACKGROUND_SHADERS", "Arnold Background Shaders", items=[
            nodeitems_utils.NodeItem("ArnoldNodeSkydome"),
            nodeitems_utils.NodeItem("ArnoldNodeImage"),
            nodeitems_utils.NodeItem("ArnoldNodePhysicalSky"),
            nodeitems_utils.NodeItem("ArnoldNodeSky"),
            nodeitems_utils.NodeItem("ArnoldNodeColorCorrect"),
        ]),
        ArnoldWorldNodeCategory("ARNOLD_NODES_WORLD_ATMOSPHERE_SHADERS", "Arnold Atmosphere Shaders", items=[
            nodeitems_utils.NodeItem("ArnoldNodeVolumeScattering"),
            nodeitems_utils.NodeItem("ArnoldNodeFog"),
        ]),
        # surface
        ArnoldObjectNodeCategory("ARNOLD_NODES_OBJECT_OUTPUT", "Arnold Output", items=[
            nodeitems_utils.NodeItem("ArnoldNodeOutput")
        ]),
        ArnoldObjectNodeCategory("ARNOLD_NODES_OBJECT_SHADERS", "Arnold Material Shaders", items=[
            nodeitems_utils.NodeItem("ArnoldNodeStandardSurface"),
            nodeitems_utils.NodeItem("ArnoldNodeStandardHair"),
            nodeitems_utils.NodeItem("ArnoldNodeStandardVolume"),
            nodeitems_utils.NodeItem("ArnoldNodeLambert"),
            nodeitems_utils.NodeItem("ArnoldNodeToon"),
            nodeitems_utils.NodeItem("ArnoldNodeCarPaint"),
            nodeitems_utils.NodeItem("ArnoldNodeShadowMatte"),
            nodeitems_utils.NodeItem("ArnoldNodeFlat"),
            nodeitems_utils.NodeItem("ArnoldNodeUtility"),
            nodeitems_utils.NodeItem("ArnoldNodeWireframe"),
            nodeitems_utils.NodeItem("ArnoldNodeAmbientOcclusion"),

        ]),
        ArnoldObjectNodeCategory("ARNOLD_NODES_OBJECT_TEXTURES", "Arnold Texture Shaders", items=[
            nodeitems_utils.NodeItem("ArnoldNodeImage"),
            nodeitems_utils.NodeItem("ArnoldNodeBump2D"),
            nodeitems_utils.NodeItem("ArnoldNodeBump3D"),
            nodeitems_utils.NodeItem("ArnoldNodeNoise"),
            nodeitems_utils.NodeItem("ArnoldNodeColorCorrect"),
        ]),
        # light
        ArnoldLightNodeCategory("ARNOLD_NODES_LIGHT_OUTPUT", "Arnold Output", items=[
            nodeitems_utils.NodeItem("ArnoldNodeLightOutput")
        ]),
        ArnoldLightNodeCategory("ARNOLD_NODES_LIGHT_SHADERS", "Arnold Light Shaders", items=[
            nodeitems_utils.NodeItem("ArnoldNodeSky"),
            nodeitems_utils.NodeItem("ArnoldNodePhysicalSky"),
            nodeitems_utils.NodeItem("ArnoldNodeImage"),
        ]),
        ArnoldLightNodeCategory("ARNOLD_NODES_LIGHT_FILTERS", "Arnold Light Filters", items=[
            nodeitems_utils.NodeItem("ArnoldNodeBarndoor"),
            nodeitems_utils.NodeItem("ArnoldNodeGobo"),
            nodeitems_utils.NodeItem("ArnoldNodeLightDecay"),
            nodeitems_utils.NodeItem("ArnoldNodeLightBlocker"),
        ]),
        # common
        ArnoldNodeCategory("ARNOLD_NODES_COLORS", "Arnold Utility Shaders", items=[
            nodeitems_utils.NodeItem("ArnoldNodeMixShader"),
            nodeitems_utils.NodeItem("ArnoldNodeRamp"),
            nodeitems_utils.NodeItem("ArnoldNodeMotionVector"),
            nodeitems_utils.NodeItem("ArnoldNodeRaySwitch"),
        ]),
        # ArnoldNodeCategory("ARNOLD_NODES_GROUP", "Group", items=node_group_items),
        # ArnoldNodeCategory("ARNOLD_NODES_LAYOUT", "Layout", items=[
        #     nodeitems_utils.NodeItem("NodeFrame"),
        #     nodeitems_utils.NodeItem("NodeReroute"),
        # ]),
    ]
    nodeitems_utils.register_node_categories("ARNOLD_NODES", node_categories)


def unregister():
    nodeitems_utils.unregister_node_categories("ARNOLD_NODES")
