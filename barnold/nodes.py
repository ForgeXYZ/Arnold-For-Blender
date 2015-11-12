# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import collections

import bpy
from bpy.types import NodeTree, NodeSocket, Node
from bpy.props import (
    IntProperty,
    BoolProperty,
    EnumProperty,
    StringProperty,
    FloatProperty,
    FloatVectorProperty,
    PointerProperty
)
from mathutils import Matrix, Euler
from bl_ui.space_node import NODE_HT_header, NODE_MT_editor_menus
import nodeitems_utils

from . import ArnoldRenderEngine
from . import props
from .ui import _subpanel


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
    default_value = FloatProperty()

    path = StringProperty()
    attr = StringProperty()
    is_color = BoolProperty()
    color = FloatVectorProperty(size=4)

    def draw(self, context, layout, node, text):
        data = node
        if self.path:
            data = node.path_resolve(self.path)
        if self.is_output or self.is_linked:
            layout.label(text)
        elif self.is_color:
            row = layout.row()
            row.alignment = 'LEFT'
            row.prop(data, self.attr, text="")
            row.label(text)
        else:
            layout.prop(data, self.attr, text=text)

    def draw_color(self, context, node):
        return self.color


@ArnoldRenderEngine.register_class
class ArnoldNodeSocketColor(NodeSocket):
    bl_label = "Color"

    default_value = FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        default=(1, 1, 1),
        min=0, max=1
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text)
        else:
            row = layout.row()
            row.alignment = 'LEFT'
            row.prop(self, "default_value", text="")
            row.label(text)

    def draw_color(self, context, node):
        # <blender_sources>/source/blender/editors/space_node/drawnode.c:3010 (SOCK_RGBA)
        return (0.78, 0.78, 0.16, 1.0)


@ArnoldRenderEngine.register_class
class ArnoldNodeSocketByte(NodeSocket):
    bl_label = "Value"

    default_value = IntProperty(
        name="Value",
        subtype='UNSIGNED',
        min=0, max=255
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text)
        else:
            layout.prop(self, "default_value", text=text)

    def draw_color(self, context, node):
        # <blender_sources>/source/blender/editors/space_node/drawnode.c:3010 (SOCK_INT)
        return (0.6, 0.52, 0.15, 1.0)


@ArnoldRenderEngine.register_class
class ArnoldNodeSocketFilter(NodeSocket):
    bl_label = "Filter"

    default_value = StringProperty(
        name="Filter"
    )

    def draw(self, context, layout, node, text):
        layout.label(text)

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

    is_active = BoolProperty(
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

    def init(self, context):
        super().init(context)
        self.inputs.new("NodeSocketShader", "Shader", "shader")


@ArnoldRenderEngine.register_class
class ArnoldNodeWorldOutput(_NodeOutput, Node):
    bl_icon = 'WORLD'

    def init(self, context):
        super().init(context)
        self.inputs.new("NodeSocketShader", "Background", "background")
        self.inputs.new("NodeSocketShader", "Atmosphere", "atmosphere")


@ArnoldRenderEngine.register_class
class ArnoldNodeLightOutput(_NodeOutput, Node):
    bl_icon = 'LAMP'

    active_filter_index = IntProperty(
        default=1
    )

    def init(self, context):
        super().init(context)
        self.inputs.new("NodeSocketShader", "Color", "color")
        self.inputs.new("ArnoldNodeSocketFilter", "Filter", "filter")

    def draw_buttons_ext(self, context, layout):
        row = layout.row()
        col = row.column()
        col.template_list("ARNOLD_UL_light_filters", "", self, "inputs", self, "active_filter_index", rows=2)
        col = row.column(align=True)
        col.operator("barnold.light_filter_add", text="", icon="ZOOMIN")
        col.operator("barnold.light_filter_remove", text="", icon="ZOOMOUT")


@ArnoldRenderEngine.register_class
class ArnoldNodeLambert(ArnoldNode):
    bl_label = "Lambert"
    bl_icon = 'MATERIAL'

    ai_name = "lambert"

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Diffuse", "Kd_color")
        self.inputs.new("NodeSocketFloat", "Weight", "Kd").default_value = 0.7
        self.inputs.new("ArnoldNodeSocketColor", "Opacity", "opacity")


@ArnoldRenderEngine.register_class
class ArnoldNodeStandard(ArnoldNode):
    bl_label = "Standard"
    bl_icon = 'MATERIAL'
    bl_width_default = 200

    ai_name = "standard"

    sockets = collections.OrderedDict([
        # Diffuse
        ("Kd_color"                 , ('RGB', "Diffuse: Color", "")),
        ("Kd"                       , ('FLOAT', "Diffuse: Scale", "")),
        ("diffuse_roughness"        , ('FLOAT', "Diffuse: Roughness", "ext_properties")),
        ("Kb"                       , ('FLOAT', "Diffuse: BackLighting", "ext_properties")),
        ("direct_diffuse"           , ('FLOAT', "Diffuse: Direct Scale", "ext_properties")),
        ("indirect_diffuse"         , ('FLOAT', "Diffuse: Indirect Scale", "ext_properties")),
        # Specular
        ("Ks_color"                 , ('RGB', "Specular: Color", "")),
        ("Ks"                       , ('FLOAT', "Specular: Scale", "")),
        ("specular_roughness"       , ('FLOAT', "Specular: Roughness", "ext_properties")),
        ("specular_anisotropy"      , ('FLOAT', "Specular: Anisotropy", "ext_properties")),
        ("specular_rotation"        , ('FLOAT', "Specular: Rotation", "ext_properties")),
        ("direct_specular"          , ('FLOAT', "Specular: Direct Scale", "ext_properties")),
        ("indirect_specular"        , ('FLOAT', "Specular: Indirect Scale", "ext_properties")),
        ("Ksn"                      , ('FLOAT', "Specular: Refl. at Normal", "ext_properties")),
        # Bounce Factor
        ("bounce_factor"            , ('FLOAT', "Bounce Factor", "ext_properties")),
        # Reflection
        ("Kr_color"                 , ('RGB', "Reflection: Color", "ext_properties")),
        ("Kr"                       , ('FLOAT', "Reflection: Scale", "ext_properties")),
        ("Krn"                      , ('FLOAT', "Reflection: Refl. at Normal", "ext_properties")),
        ("reflection_exit_color"    , ('RGB', "Reflection: Exit Color", "ext_properties")),
        # Refraction
        ("Kt_color"                 , ('RGB', "Refraction: Color", "ext_properties")),
        ("Kt"                       , ('FLOAT', "Refraction: Scale", "ext_properties")),
        ("IOR"                      , ('FLOAT', "Refraction: IOR", "ext_properties")),
        ("dispersion_abbe"          , ('FLOAT', "Refraction: Abbe Number", "ext_properties")),
        ("refraction_roughness"     , ('FLOAT', "Refraction: Roughness", "ext_properties")),
        ("transmittance"            , ('RGB', "Transmittance", "ext_properties")),
        ("refraction_exit_color"    , ('RGB', "Refraction: Exit Color", "ext_properties")),
        # Opacity
        ("opacity"                  , ('RGB', "Opacity", "ext_properties")),
        # SSS
        ("Ksss_color"               , ('RGB', "SSS: Color", "ext_properties")),
        ("Ksss"                     , ('FLOAT', "SSS: Scale", "ext_properties")),
        ("sss_radius"               , ('RGB', "SSS: Radius", "ext_properties")),
        # Emission
        ("emission_color"           , ('RGB', "Emission: Color", "ext_properties")),
        ("emission"                 , ('FLOAT', "Emission: Scale", "ext_properties"))
    ])

    Kd = FloatProperty(
        name="Scale",
        subtype='FACTOR',
        min=0, max=1,
        default=0.7
    )
    Kd_color = FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )
    Ks = FloatProperty(
        name="Scale",
        subtype='FACTOR',
        min=0, max=1
    )
    Ks_color = FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )
    ext_properties = PointerProperty(
        type=props.ArnoldShaderStandard
    )

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.create_socket("Kd_color")
        self.create_socket("Kd")

    def draw_buttons_ext(self, context, layout):
        inputs = self.inputs
        properties = self.ext_properties

        links = {i.identifier: i.is_linked for i in inputs}

        # Diffuse
        sublayout = _subpanel(layout, "Diffuse", properties.ui_diffuse,
                              "ext_properties", "ui_diffuse", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, self, "Kd_color", links)
            _draw_property(col, self, "Kd", links)
            _draw_property(col, properties, "diffuse_roughness", links)
            col.prop(properties, "Fresnel_affect_diff")
            _draw_property(col, properties, "Kb", links)
            _draw_property(col, properties, "direct_diffuse", links)
            _draw_property(col, properties, "indirect_diffuse", links)

        # Specular
        sublayout = _subpanel(layout, "Specular", properties.ui_specular,
                              "ext_properties", "ui_specular", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, self, "Ks_color", links)
            _draw_property(col, self, "Ks", links)
            _draw_property(col, properties, "specular_roughness", links)
            _draw_property(col, properties, "specular_anisotropy", links)
            _draw_property(col, properties, "specular_rotation", links)
            _draw_property(col, properties, "direct_specular", links)
            _draw_property(col, properties, "indirect_specular", links)
            col.label("Fresnel", icon='SETTINGS')
            box = col.box()
            box.prop(properties, "specular_Fresnel")
            sub = box.row()
            sub.enabled = properties.specular_Fresnel
            _draw_property(sub, properties, "Ksn", links)

        _draw_property(layout, properties, "bounce_factor", links)

        # Reflection
        sublayout = _subpanel(layout, "Reflection", properties.ui_reflection,
                              "ext_properties", "ui_reflection", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "Kr_color", links)
            _draw_property(col, properties, "Kr", links)
            col.label("Fresnel:", icon='SETTINGS')
            box = col.box()
            box.prop(properties, "Fresnel")
            sub = box.row()
            sub.enabled = properties.Fresnel
            _draw_property(sub, properties, "Krn", links)
            col.label("Exit Color:", icon='SETTINGS')
            box = col.box()
            box.prop(properties, "reflection_exit_use_environment")
            _draw_property(box, properties, "reflection_exit_color", links)

        # Refraction
        sublayout = _subpanel(layout, "Refraction", properties.ui_refraction,
                              "ext_properties", "ui_refraction", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "Kt_color", links)
            _draw_property(col, properties, "Kt", links)
            _draw_property(col, properties, "IOR", links)
            _draw_property(col, properties, "dispersion_abbe", links)
            col.prop(properties, "Fresnel_use_IOR")
            _draw_property(col, properties, "refraction_roughness", links)
            _draw_property(col, properties, "transmittance", links)
            col.label("Exit Color:", icon='SETTINGS')
            box = col.box()
            box.prop(properties, "refraction_exit_use_environment")
            _draw_property(box, properties, "refraction_exit_color", links)
            col.prop(properties, "enable_internal_reflections")

        _draw_property(layout, properties, "opacity", links)

        # Sub-Surface Scattering
        sublayout = _subpanel(layout, "Sub-Surface Scattering", properties.ui_sss,
                              "ext_properties", "ui_sss", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "Ksss_color", links)
            _draw_property(col, properties, "Ksss", links)
            _draw_property(col, properties, "sss_radius", links)

        # Emission
        sublayout = _subpanel(layout, "Emission", properties.ui_emission,
                              "ext_properties", "ui_emission", "node")
        if sublayout:
            col = sublayout.column()
            _draw_property(col, properties, "emission_color", links)
            _draw_property(col, properties, "emission", links)

        # Caustics
        sublayout = _subpanel(layout, "Caustics", properties.ui_caustics,
                              "ext_properties", "ui_caustics", "node")
        if sublayout:
            col = sublayout.column()
            col.prop(properties, "enable_glossy_caustics")
            col.prop(properties, "enable_reflective_caustics")
            col.prop(properties, "enable_refractive_caustics")

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
        sock = self.inputs.new("ArnoldNodeSocketProperty", name, identifier)
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
            'reflection_exit_use_environment': ('BOOL', props.reflection_exit_use_environment),
            'refraction_exit_use_environment': ('BOOL', props.refraction_exit_use_environment),
            'Fresnel': ('BOOL', props.Fresnel),
            'specular_Fresnel': ('BOOL', props.specular_Fresnel),
            'Fresnel_use_IOR': ('BOOL', props.Fresnel_use_IOR),
            'Fresnel_affect_diff': ('BOOL', props.Fresnel_affect_diff),
            'enable_glossy_caustics': ('BOOL', props.enable_glossy_caustics),
            'enable_reflective_caustics': ('BOOL', props.enable_reflective_caustics),
            'enable_refractive_caustics': ('BOOL', props.enable_refractive_caustics),
            'enable_internal_reflections': ('BOOL', props.enable_internal_reflections),
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

    color_mode = EnumProperty(
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
    shade_mode = EnumProperty(
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
    overlay_mode = EnumProperty(
        name="Overlay Mode",
        items=[
            ('none', "None", "None"),
            ('wire', "Wire", "Wire"),
            ('polywire', "Polywire", "Polywire")
        ],
        default='none'
    )

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Color", "color")
        self.inputs.new("NodeSocketFloat", "Opacity", "opacity").default_value = 1
        self.inputs.new("NodeSocketFloat", "AO Distance", "ao_distance").default_value = 100

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
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Color", "color")
        self.inputs.new("ArnoldNodeSocketColor", "Opacity", "opacity")


@ArnoldRenderEngine.register_class
class ArnoldNodeBump2D(ArnoldNode):
    bl_label = "Bump 2D"
    bl_icon = 'MATERIAL'

    ai_name = "bump2d"

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGBA", "output")
        self.inputs.new("NodeSocketFloat", "Map", "bump_map")
        self.inputs.new("NodeSocketFloat", "Height", "bump_height")
        self.inputs.new("NodeSocketShader", "Shader", "shader")


@ArnoldRenderEngine.register_class
class ArnoldNodeBump3D(ArnoldNode):
    bl_label = "Bump 3D"
    bl_icon = 'MATERIAL'

    ai_name = "bump3d"

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGBA", "output")
        self.inputs.new("NodeSocketFloat", "Map", "bump_map")
        self.inputs.new("NodeSocketFloat", "Height", "bump_height")
        self.inputs.new("NodeSocketFloat", "Epsilon", "epsilon")
        self.inputs.new("NodeSocketShader", "Shader", "shader")


@ArnoldRenderEngine.register_class
class ArnoldNodeWireframe(ArnoldNode):
    bl_label = "Wireframe"
    bl_icon = 'MATERIAL'

    ai_name = "wireframe"

    edge_type = EnumProperty(
        name="Edge Type",
        items=[
            ('polygons', "Polygons", "Polygons"),
            ('triangles', "Triangles", "Triangles")
        ],
        default='triangles'
    )

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Fill Color", "fill_color")
        self.inputs.new("ArnoldNodeSocketColor", "Line Color", "line_color").default_value = (0, 0, 0)
        self.inputs.new("NodeSocketFloat", "Line Width", "line_width").default_value = 1
        self.inputs.new("NodeSocketBool", "Raster space", "raster_space").default_value = True

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
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("NodeSocketInt", "Samples", "samples").default_value = 3
        self.inputs.new("NodeSocketFloat", "Spread", "spread").default_value = 1
        self.inputs.new("NodeSocketFloat", "Falloff", "falloff")
        self.inputs.new("NodeSocketFloat", "Near Clip", "near_clip")
        self.inputs.new("NodeSocketFloat", "Far Clip", "far_clip").default_value = 100
        self.inputs.new("ArnoldNodeSocketColor", "White", "white")
        self.inputs.new("ArnoldNodeSocketColor", "Black", "black").default_value = (0, 0, 0)
        self.inputs.new("ArnoldNodeSocketColor", "Opacity", "opacity")
        self.inputs.new("NodeSocketBool", "Invert Normals", "invert_normals")
        self.inputs.new("NodeSocketBool", "Self Only", "self_only")


@ArnoldRenderEngine.register_class
class ArnoldNodeMotionVector(ArnoldNode):
    bl_label = "Motion Vector"
    bl_icon = 'MATERIAL'

    ai_name = "motion_vector"

    raw = BoolProperty(
        name="Encode Raw Vector"
    )
    time0 = FloatProperty(
        name="Start Time"
    )
    time1 = FloatProperty(
        name="End time",
        default=1
    )
    max_displace = FloatProperty(
        name="Max Displace"
    )

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")

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
        self.outputs.new("NodeSocketShader", "RGBA", "output")
        self.inputs.new("NodeSocketColor", "Camera", "camera").default_value = (1, 1, 1, 1)
        self.inputs.new("NodeSocketColor", "Shadow", "shadow").default_value = (1, 1, 1, 1)
        self.inputs.new("NodeSocketColor", "Reflection", "reflection").default_value = (1, 1, 1, 1)
        self.inputs.new("NodeSocketColor", "Refraction", "refraction").default_value = (1, 1, 1, 1)
        self.inputs.new("NodeSocketColor", "Diffuse", "diffuse").default_value = (1, 1, 1, 1)
        self.inputs.new("NodeSocketColor", "Glossy", "glossy").default_value = (1, 1, 1, 1)


@ArnoldRenderEngine.register_class
class ArnoldNodeHair(ArnoldNode):
    bl_label = "Hair"
    bl_icon = 'MATERIAL'
    bl_width_default = 200

    ai_name = "hair"

    uparam = StringProperty(
        name="U"
    )
    vparam = StringProperty(
        name="V"
    )

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Root Color", "rootcolor").default_value = (0.1, 0.1, 0.1)
        self.inputs.new("ArnoldNodeSocketColor", "Tip Color", "tipcolor").default_value = (0.5, 0.5, 0.5)
        self.inputs.new("NodeSocketFloat", "Ambient diffuse", "ambdiff").default_value = 0.6
        self.inputs.new("NodeSocketFloat", "Indirect diffuse", "kd_ind")
        self.inputs.new("NodeSocketBool", "Diffuse cache", "diffuse_cache")
        # Specular #1
        self.inputs.new("ArnoldNodeSocketColor", "Specular: Color", "spec_color")
        self.inputs.new("NodeSocketFloat", "Specular: Glossiness", "gloss").default_value = 10
        self.inputs.new("NodeSocketFloat", "Specular: Weight", "spec").default_value = 1
        self.inputs.new("NodeSocketFloat", "Specular: Angular shift", "spec_shift")
        # Specular #2
        self.inputs.new("ArnoldNodeSocketColor", "Spec. #2: Color", "spec2_color").default_value = (1, 0.4, 0.1)
        self.inputs.new("NodeSocketFloat", "Spec. #2: Glossiness", "gloss2").default_value = 7
        self.inputs.new("NodeSocketFloat", "Spec. #2: Weight", "spec2").default_value = 0
        self.inputs.new("NodeSocketFloat", "Spec. #2: Angular shift", "spec2_shift")
        # Transmission
        self.inputs.new("ArnoldNodeSocketColor", "Transmission: Color", "transmission_color").default_value = (1, 0.4, 0.1)
        self.inputs.new("NodeSocketFloat", "Transmission", "transmission")
        self.inputs.new("NodeSocketFloat", "Transmission: Spread", "transmission_spread").default_value = 1
        self.inputs.new("ArnoldNodeSocketColor", "Opacity", "opacity")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.label("Remap UV:")
        row = col.row()
        col = row.column()
        col.alignment = 'LEFT'
        col.label("U:")
        col.label("V:")
        col = row.column()
        col.prop(self, "uparam", text="")
        col.prop(self, "vparam", text="")

    @property
    def ai_properties(self):
        props = {}
        if self.uparam:
            props['uparam'] = ('STRING', self.uparam)
        if self.vparam:
            props['vparam'] = ('STRING', self.vparam)
        return props


@ArnoldRenderEngine.register_class
class ArnoldNodeNoise(ArnoldNode):
    bl_label = "Noise"
    bl_icon = 'TEXTURE'

    ai_name = "noise"

    octaves = IntProperty(
        name="Octaves",
        default=1
    )
    coord_space = EnumProperty(
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
        self.outputs.new("NodeSocketFloat", "Value", "output")
        self.inputs.new("NodeSocketFloat", "Distortion", "distortion")
        self.inputs.new("NodeSocketFloat", "Lacunarity", "lacunarity").default_value = 1.92
        self.inputs.new("NodeSocketFloat", "Amplitude", "amplitude").default_value = 1
        self.inputs.new("NodeSocketVector", "Scale", "scale").default_value = (1, 1, 1)
        self.inputs.new("NodeSocketVector", "Offset", "offset")

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

    filename = StringProperty(
        name="Filename",
        subtype='FILE_PATH'
    )
    filter = EnumProperty(
        name="Filter",
        items=[
            ('closest', "Closest", "Closest"),
            ('bilinear', "Bilinear", "Bilinear"),
            ('bicubic', "Bicubic", "Bicubic"),
            ('smart_bicubic', "Smart Bicubic", "Smart Bicubic")
        ],
        default='smart_bicubic'
    )
    mipmap_bias = IntProperty(
        name="Mipmap Bias"
    )
    single_channel = BoolProperty(
        name="Single Channel"
    )
    start_channel = IntProperty(
        name="Start Channel",
        subtype='UNSIGNED',
        min=0, max=255
    )
    swrap = EnumProperty(
        name="U wrap",
        items=_WRAP_ITEMS,
        default='periodic'
    )
    twrap = EnumProperty(
        name="V wrap",
        items=_WRAP_ITEMS,
        default='periodic'
    )
    sscale = FloatProperty(
        name="Scale U",
        default=1,
    )
    tscale = FloatProperty(
        name="Scale V",
        default=1,
    )
    sflip = BoolProperty(
        name="Flip U"
    )
    tflip = BoolProperty(
        name="Flip V"
    )
    soffset = FloatProperty(
        name="Offset U"
    )
    toffset = FloatProperty(
        name="Offset V"
    )
    swap_st = BoolProperty(
        name="Swap UV"
    )
    uvset = StringProperty(
        name="UV set"
    )
    ignore_missing_tiles = BoolProperty(
        name="Ignore Missing Tiles"
    )

    def init(self, context):
        self.outputs.new("NodeSocketColor", "RGBA", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Multiply", "multiply")
        self.inputs.new("ArnoldNodeSocketColor", "Offset", "offset").default_value = (0, 0, 0)
        self.inputs.new("NodeSocketColor", "Missing tile color", "missing_tile_color")
        self.inputs.new("NodeSocketVector", "UV coords", "uvcoords").hide_value = True

    def draw_buttons(self, context, layout):
        layout.prop(self, "filename", text="", icon='IMAGEFILE')

        col = layout.column()
        col.prop(self, "filter")
        col.prop(self, "mipmap_bias")
        col.prop(self, "single_channel")
        col.prop(self, "start_channel")

        col = layout.column()
        col.prop(self, "uvset")

        col.label("Offset:")
        scol = col.column(align=True)
        scol.prop(self, "soffset", text="U")
        scol.prop(self, "toffset", text="V")

        col.label("Scale:")
        scol = col.column(align=True)
        scol.prop(self, "sscale", text="U")
        scol.prop(self, "tscale", text="V")

        scol = col.column(align=True)
        scol.label("Wrap:")
        row = scol.row(align=True)
        sscol = row.column(align=True)
        sscol.alignment = 'LEFT'
        sscol.label("U:")
        sscol.label("V:")
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
            "ignore_missing_tiles": ('BOOL', self.swap_st),
        }
        if self.filename:
            props["filename"] = ('STRING', bpy.path.abspath(self.filename))
        if self.uvset:
            props["uvset"] = ('STRING', self.uvset)
        return props


@ArnoldRenderEngine.register_class
class ArnoldNodeSky(ArnoldNode):
    bl_label = "Sky"
    bl_icon = 'WORLD'
    bl_width_default = 220

    ai_name = "sky"

    visibility = IntProperty(
        name="Visibility",
        default=255
    )
    opaque_alpha = BoolProperty(
        name="Opaque Alpha",
        default=True
    )
    format = EnumProperty(
        name="Format",
        items=[
            ('mirrored_ball', "Mirrored Ball", "Mirrored Ball"),
            ('angular', "Angular", "Angular"),
            ('latlong', "LatLong", "LatLong")
        ],
        default='angular'
    )
    X_angle = FloatProperty(
        name="X",
        description="X angle"
    )
    Y_angle = FloatProperty(
        name="Y",
        description="Y angle"
    )
    Z_angle = FloatProperty(
        name="Z",
        description="Z angle"
    )
    X = FloatVectorProperty(
        name="X",
        soft_min=-1, soft_max=1,
        default=(1, 0, 0)
    )
    Y = FloatVectorProperty(
        name="Y",
        soft_min=-1, soft_max=1,
        default=(0, 1, 0)
    )
    Z = FloatVectorProperty(
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

    visibility_camera = BoolProperty(
        name="Camera",
        **_visibility(1)
    )
    visibility_shadow = BoolProperty(
        name="Shadow",
        **_visibility(1 << 1)
    )
    visibility_reflection = BoolProperty(
        name="Reflection",
        **_visibility(1 << 2)
    )
    visibility_refraction = BoolProperty(
        name="Refraction",
        **_visibility(1 << 3)
    )
    visibility_diffuse = BoolProperty(
        name="Diffuse",
        **_visibility(1 << 4)
    )
    visibility_glossy = BoolProperty(
        name="Glossy",
        **_visibility(1 << 5)
    )

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Color", "color")
        self.inputs.new("NodeSocketFloat", "Intensity", "intensity").default_value = 1

    def draw_buttons(self, context, layout):
        layout.prop(self, "format")
        layout.prop(self, "opaque_alpha")

        col = layout.column()
        col.label("Visibility:")
        flow = col.column_flow(align=True)
        flow.prop(self, "visibility_camera")
        flow.prop(self, "visibility_shadow")
        flow.prop(self, "visibility_reflection")
        flow.prop(self, "visibility_refraction")
        flow.prop(self, "visibility_diffuse")
        flow.prop(self, "visibility_glossy")

        col = layout.column()
        col.label("Angle:")
        scol = col.column(align=True)
        scol.prop(self, "X_angle")
        scol.prop(self, "Y_angle")
        scol.prop(self, "Z_angle")

        col.label("Orientation:")
        row = col.row(align=True)
        col = row.column(align=True)
        col.alignment = 'LEFT'
        col.label("X:")
        col.label("Y:")
        col.label("Z:")
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
class ArnoldNodePhysicalSky(ArnoldNode):
    bl_label = "Physical Sky"
    bl_icon = 'WORLD'

    ai_name = "physical_sky"

    turbidity = FloatProperty(
        name="Turbidity",
        default=3
    )
    ground_albedo = FloatVectorProperty(
        name="Ground Albedo",
        subtype='COLOR',
        min=0, max=1,
        default=(0.1, 0.1, 0.1)
    )
    #use_degrees (true)
    elevation = FloatProperty(
        name="Elevation",
        default=45
    )
    azimuth = FloatProperty(
        name="Azimuth",
        default=90
    )
    #sun_direction (0, 1, 0)
    enable_sun = BoolProperty(
        name="Enable Sun",
        default=True
    )
    sun_size = FloatProperty(
        name="Sun Size",
        default=0.51
    )
    sun_tint = FloatVectorProperty(
        name="Sun Tint",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )
    sky_tint = FloatVectorProperty(
        name="Sky Tint",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )
    intensity = FloatProperty(
        name="Intensity",
        default=1
    )
    X = FloatVectorProperty(
        name="X",
        soft_min=0, soft_max=1,
        default=(1, 0, 0)
    )
    Y = FloatVectorProperty(
        name="Y",
        soft_min=0, soft_max=1,
        default=(0, 1, 0)
    )
    Z = FloatVectorProperty(
        name="Z",
        soft_min=0, soft_max=1,
        default=(0, 0, 1)
    )

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "turbidity")
        row = col.row(align=True)
        row.alignment = 'LEFT'
        row.prop(self, "ground_albedo", text="")
        row.label("Ground Albedo")
        col.prop(self, "elevation")
        col.prop(self, "azimuth")
        col.prop(self, "intensity")

        col = layout.column()
        row = col.row(align=True)
        row.alignment = 'LEFT'
        row.prop(self, "sky_tint", text="")
        row.label("Sky Tint")
        row = col.row(align=True)
        row.alignment = 'LEFT'
        row.prop(self, "sun_tint", text="")
        row.label("Sun Tint")
        col.prop(self, "sun_size")
        col.prop(self, "enable_sun")

        col.label("Orientation:")
        row = col.row(align=True)
        col = row.column(align=True)
        col.alignment = 'LEFT'
        col.label("X:")
        col.label("Y:")
        col.label("Z:")
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

    samples = IntProperty(
        name="Samples",
        default=5
    )

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Color", "rgb_density")
        self.inputs.new("NodeSocketFloat", "Density", "density")
        self.inputs.new("ArnoldNodeSocketColor", "Attenuation Color", "rgb_attenuation")
        self.inputs.new("NodeSocketFloat", "Attenuation", "attenuation")
        self.inputs.new("NodeSocketFloat", "Anisotropy", "eccentricity")
        self.inputs.new("NodeSocketFloat", "Camera", "affect_camera").default_value = 1
        self.inputs.new("NodeSocketFloat", "Diffuse", "affect_diffuse")
        self.inputs.new("NodeSocketFloat", "Reflection", "affect_reflection").default_value = 1

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
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Color", "color")
        self.inputs.new("NodeSocketFloat", "Distance", "distance").default_value = 0.02
        self.inputs.new("NodeSocketFloat", "Height", "height").default_value = 5
        self.inputs.new("NodeSocketVector", "Ground Normal", "ground_normal").default_value = (0, 0, 1)
        self.inputs.new("NodeSocketVectorXYZ", "Ground Point", "ground_point")


@ArnoldRenderEngine.register_class
class ArnoldNodeBarndoor(ArnoldNode):
    bl_label = "Barn Door"
    bl_icon = 'LAMP'

    ai_name = "barndoor"

    top_left = FloatProperty(
        name="Left",
        soft_min=0, soft_max=1
    )
    top_right = FloatProperty(
        name="Right",
        soft_min=0, soft_max=1
    )
    top_edge = FloatProperty(
        name="Edge",
        soft_min=0, soft_max=1
    )
    right_top = FloatProperty(
        name="Top",
        soft_min=0, soft_max=1,
        default=1
    )
    right_bottom = FloatProperty(
        name="Bottom",
        soft_min=0, soft_max=1,
        default=1
    )
    right_edge = FloatProperty(
        name="Edge",
        soft_min=0, soft_max=1
    )
    bottom_left = FloatProperty(
        name="Left",
        soft_min=0, soft_max=1,
        default=1
    )
    bottom_right = FloatProperty(
        name="Right",
        soft_min=0, soft_max=1,
        default=1
    )
    bottom_edge = FloatProperty(
        name="Edge",
        soft_min=0, soft_max=1
    )
    left_top = FloatProperty(
        name="Top",
        soft_min=0, soft_max=1
    )
    left_bottom = FloatProperty(
        name="Bottom",
        soft_min=0, soft_max=1
    )
    left_edge = FloatProperty(
        name="Edge",
        soft_min=0, soft_max=1
    )

    def init(self, context):
        self.outputs.new("NodeSocketVirtual", "Filter", "filter")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.label("Top:")
        col = col.column(align=True)
        col.prop(self, "top_left")
        col.prop(self, "top_right")
        col.prop(self, "top_edge")
        col = layout.column()
        col.label("Right:")
        col = col.column(align=True)
        col.prop(self, "right_top")
        col.prop(self, "right_bottom")
        col.prop(self, "right_edge")
        col = layout.column()
        col.label("Bottom:")
        col = col.column(align=True)
        col.prop(self, "bottom_left")
        col.prop(self, "bottom_right")
        col.prop(self, "bottom_edge")
        col = layout.column()
        col.label("Left:")
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
    bl_icon = 'LAMP'

    ai_name = "gobo"

    rotate = FloatProperty(
        name="Rotate",
        description="Rotate the texture image."
    )
    offset = FloatVectorProperty(
        name="Offset",
        description="UV coordinate values used to offset the direction of the slide map.",
        size=2
    )
    density = FloatProperty(
        name="Density"
    )
    # TODO: add filter modes
    filter_mode = EnumProperty(
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
    scale_s = FloatProperty(
        name="Scale U",
        default=1
    )
    scale_t = FloatProperty(
        name="Scale V",
        default=1
    )
    wrap_s = EnumProperty(
        name="Wrap U",
        items=_WRAP_ITEMS,
        default='clamp'
    )
    wrap_t = EnumProperty(
        name="Wrap V",
        items=_WRAP_ITEMS,
        default='clamp'
    )

    def init(self, context):
        self.outputs.new("NodeSocketVirtual", "Filter", "filter")
        self.inputs.new("ArnoldNodeSocketColor", "Slidemap", "slidemap")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "filter_mode")
        col.prop(self, "density")
        col.prop(self, "rotate")
        col.prop(self, "offset")

        subcol = col.column(align=True)
        subcol.label("Scale:")
        subcol.prop(self, "scale_s", text="U")
        subcol.prop(self, "scale_t", text="V")

        subcol = col.column(align=True)
        subcol.label("Wrap:")
        row = subcol.row(align=True)
        col = row.column(align=True)
        col.alignment = 'LEFT'
        col.label("U:")
        col.label("V:")
        col = row.column(align=True)
        col.prop(self, "wrap_s", text="")
        col.prop(self, "wrap_t", text="")

    @property
    def ai_properties(self):
        return {
            "rotate": ('FLOAT', self.rotate),
            "offset": ('POINT2', self.offset),
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
    bl_icon = 'LAMP'

    ai_name = "light_decay"

    use_near_atten = BoolProperty(
        name="Use Near Attenuation"
    )
    use_far_atten = BoolProperty(
        name="Use Far Attenuation"
    )
    near_start = FloatProperty(
        name="Start",
        description="Near Start"
    )
    near_end = FloatProperty(
        name="End",
        description="Near End"
    )
    far_start = FloatProperty(
        name="Start",
        description="Far Start"
    )
    far_end = FloatProperty(
        name="End",
        description="Far End"
    )

    def init(self, context):
        self.outputs.new("NodeSocketVirtual", "Filter", "filter")

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
    bl_icon = 'LAMP'

    ai_name = "light_blocker"

    geometry_type = EnumProperty(
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
    #geometry_matrix = FloatVectorProperty(
    #    name="Matrix",
    #    subtype='MATRIX',
    #    size=16
    #)
    geometry_matrix_object = StringProperty(
        name="Object"
    )
    geometry_matrix_scale = FloatVectorProperty(
        name="Scale",
        subtype='XYZ',
        default=(1, 1, 1)
    )
    geometry_matrix_rotation = FloatVectorProperty(
        name="Rotation",
        subtype='XYZ',
        unit='ROTATION'
    )
    geometry_matrix_translation = FloatVectorProperty(
        name="Translation",
        subtype='XYZ'
    )
    #density = FloatProperty(
    #    name="Density"
    #)
    roundness = FloatProperty(
        name="Roundness"
    )
    width_edge = FloatProperty(
        name="Width",
        description="Width Edge"
    )
    height_edge = FloatProperty(
        name="Height",
        description="Height Edge"
    )
    ramp = FloatProperty(
        name="Ramp"
    )
    axis = EnumProperty(
        name="Axis",
        items=[
            ('x', "X", "X"),
            ('y', "Y", "Y"),
            ('z', "Z", "Z")
        ],
        default='x'
    )

    def init(self, context):
        self.outputs.new("NodeSocketVirtual", "Filter", "filter")
        self.inputs.new("ArnoldNodeSocketColor", "Shader", "shader").default_value = (0, 0, 0)
        self.inputs.new("NodeSocketFloat", "Density", "density")

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "geometry_type")
        col.prop(self, "axis")
        col.prop(self, "ramp")
        col.prop(self, "height_edge")
        col.prop(self, "width_edge")
        col.prop(self, "roundness")
        col.label("Matrix:")
        sub = col.box().column()
        sub.prop_search(self, "geometry_matrix_object", context.scene, "objects", text="")
        sub = sub.column()
        sub.enabled = not self.geometry_matrix_object
        sub.template_component_menu(self, "geometry_matrix_scale", name="Scale:")
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


@ArnoldRenderEngine.register_class
class ArnoldNodeDensity(ArnoldNode):
    bl_label = "Density"
    bl_icon = 'TEXTURE'

    ai_name = "density"

    interpolation = EnumProperty(
        name="Interpolation",
        items=[
            ('closest', "closest", "closest"),
            ('trilinear', "trilinear", "trilinear"),
            ('tricubic', "tricubic", "tricubic")
        ],
        default='trilinear'
    )

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("NodeSocketString", "scatter_channel")
        self.inputs.new("ArnoldNodeSocketColor", "scatter_color")
        self.inputs.new("NodeSocketFloat", "scatter_g")
        self.inputs.new("NodeSocketString", "absorption_channel")
        self.inputs.new("ArnoldNodeSocketColor", "absorption_color")
        self.inputs.new("NodeSocketString", "emission_channel")
        self.inputs.new("ArnoldNodeSocketColor", "emission_color")
        self.inputs.new("NodeSocketVector", "position_offset")

    def draw_buttons(self, context, layout):
        layout.prop(self, "interpolation", text="")

    @property
    def ai_properties(self):
        return {
            "interpolation": ('STRING', self.interpolation)
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeMixRGB(ArnoldNode):
    bl_label = "Mix RGB"
    bl_icon = 'MATERIAL'

    ai_name = "BArnoldMixRGB"

    blend_type = EnumProperty(
        name="Blend Type",
        items=[
            ('mix', "Mix", "Mix"),
            ('add', "Add", "Add"),
            ('multiply', "Multiply", "Multiply"),
            ('screen', "Screen", "Screen"),
            ('overlay', "Overlay", "Overlay"),
            ('subtract', "Subtract", "Subtract"),
            ('divide', "Divide", "Divide"),
            ('difference', "Difference", "Difference"),
            ('darken', "Darken", "Darken Only"),
            ('lighten', "Lighten", "Lighten Only"),
            ('dodge', "Dodge", "Dodge"),
            ('burn', "Burn", "Burn"),
            ('hue', "Hue", "Hue"),
            ('saturation', "Saturation", "Saturation"),
            ('value', "Value", "Value"),
            ('color', "Color", "Color"),
            ('soft', "Soft Light", "Soft Light"),
            ('linear', "Linear Light", "Linear Light")
        ],
        default='mix'
    )

    def init(self, context):
        self.outputs.new("ArnoldNodeSocketColor", "Color", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Color #1", "color1").default_value = (0.5, 0.5, 0.5)
        self.inputs.new("ArnoldNodeSocketColor", "Color #2", "color2").default_value = (0.5, 0.5, 0.5)
        self.inputs.new("NodeSocketFloat", "Factor", "factor").default_value = 0.5

    def draw_buttons(self, context, layout):
        layout.prop(self, "blend_type", text="")

    @property
    def ai_properties(self):
        return {
            "blend": ('STRING', self.blend_type)
        }


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
            context.object.type != 'LAMP'
        )


class ArnoldLightNodeCategory(ArnoldNodeCategory):
    @classmethod
    def poll(cls, context):
        return (
            super().poll(context) and
            context.object.type == 'LAMP'
        )


def register():
    from nodeitems_builtins import (
        #ShaderNewNodeCategory,
        ShaderOldNodeCategory,
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

    #ShaderNewNodeCategory.poll = _poll(ShaderNewNodeCategory.poll)
    ShaderOldNodeCategory.poll = _poll(ShaderOldNodeCategory.poll)

    node_categories = [
        # world
        ArnoldWorldNodeCategory("ARNOLD_NODES_WORLD_OUTPUT", "Output", items=[
            nodeitems_utils.NodeItem("ArnoldNodeWorldOutput")
        ]),
        ArnoldWorldNodeCategory("ARNOLD_NODES_WORLD_SHADERS", "Shaders", items=[
            nodeitems_utils.NodeItem("ArnoldNodeSky"),
            nodeitems_utils.NodeItem("ArnoldNodePhysicalSky"),
            nodeitems_utils.NodeItem("ArnoldNodeVolumeScattering"),
            nodeitems_utils.NodeItem("ArnoldNodeFog"),
            nodeitems_utils.NodeItem("ArnoldNodeImage"),
        ]),
        # surface
        ArnoldObjectNodeCategory("ARNOLD_NODES_OBJECT_OUTPUT", "Output", items=[
            nodeitems_utils.NodeItem("ArnoldNodeOutput")
        ]),
        ArnoldObjectNodeCategory("ARNOLD_NODES_OBJECT_SHADERS", "Shaders", items=[
            nodeitems_utils.NodeItem("ArnoldNodeStandard"),
            nodeitems_utils.NodeItem("ArnoldNodeLambert"),
            nodeitems_utils.NodeItem("ArnoldNodeFlat"),
            nodeitems_utils.NodeItem("ArnoldNodeHair"),
            nodeitems_utils.NodeItem("ArnoldNodeUtility"),
            nodeitems_utils.NodeItem("ArnoldNodeWireframe"),
            nodeitems_utils.NodeItem("ArnoldNodeAmbientOcclusion"),
            nodeitems_utils.NodeItem("ArnoldNodeMotionVector"),
            nodeitems_utils.NodeItem("ArnoldNodeRaySwitch"),
            nodeitems_utils.NodeItem("ArnoldNodeBump2D"),
            nodeitems_utils.NodeItem("ArnoldNodeBump3D"),
            nodeitems_utils.NodeItem("ArnoldNodeImage"),
            nodeitems_utils.NodeItem("ArnoldNodeNoise"),
        ]),
        # light
        ArnoldLightNodeCategory("ARNOLD_NODES_LIGHT_OUTPUT", "Output", items=[
            nodeitems_utils.NodeItem("ArnoldNodeLightOutput")
        ]),
        ArnoldLightNodeCategory("ARNOLD_NODES_LIGHT_SHADERS", "Shaders", items=[
            nodeitems_utils.NodeItem("ArnoldNodeSky"),
            nodeitems_utils.NodeItem("ArnoldNodePhysicalSky"),
            nodeitems_utils.NodeItem("ArnoldNodeImage"),
        ]),
        ArnoldLightNodeCategory("ARNOLD_NODES_LIGHT_FILTERS", "Filters", items=[
            nodeitems_utils.NodeItem("ArnoldNodeBarndoor"),
            nodeitems_utils.NodeItem("ArnoldNodeGobo"),
            nodeitems_utils.NodeItem("ArnoldNodeLightDecay"),
            nodeitems_utils.NodeItem("ArnoldNodeLightBlocker"),
        ]),
        # common
        ArnoldNodeCategory("ARNOLD_NODES_COLORS", "Color", items=[
            nodeitems_utils.NodeItem("ArnoldNodeMixRGB"),
        ]),
        ArnoldNodeCategory("ARNOLD_NODES_GROUP", "Group", items=node_group_items),
        ArnoldNodeCategory("ARNOLD_NODES_LAYOUT", "Layout", items=[
            nodeitems_utils.NodeItem("NodeFrame"),
            nodeitems_utils.NodeItem("NodeReroute"),
        ]),
    ]
    nodeitems_utils.register_node_categories("ARNOLD_NODES", node_categories)


def unregister():
    nodeitems_utils.unregister_node_categories("ARNOLD_NODES")
