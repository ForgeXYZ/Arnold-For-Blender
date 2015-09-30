# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import bpy
import nodeitems_utils
from bpy.props import BoolProperty

from . import ArnoldRenderEngine


@ArnoldRenderEngine.register_class
class ArnoldNodeSocketColor(bpy.types.NodeSocket):
    bl_label = "Color"

    default_value = bpy.props.FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        default=(1, 1, 1),
        min=0, max=1
    )

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text)
        else:
            row = layout.row(align=True)
            row.alignment = 'LEFT'
            row.prop(self, "default_value", text="")
            row.label(text)

    def draw_color(self, context, node):
        # <blender_sources>/source/blender/editors/space_node/drawnode.c:3010 (SOCK_RGBA)
        return (0.78, 0.78, 0.16, 1.0)


@ArnoldRenderEngine.register_class
class ArnoldNodeOutput(bpy.types.Node):
    bl_label = "Output"
    bl_icon = 'MATERIAL'

    def _get_active(self):
        return not self.mute

    def _set_active(self, value=True):
        for node in self.id_data.nodes:
            if type(node) is ArnoldNodeOutput:
                node.mute = (self != node)

    is_active = BoolProperty(
        name="Active",
        description="Active Output",
        get=_get_active,
        set=_set_active
    )

    def init(self, context):
        self._set_active()
        sock = self.inputs.new("NodeSocketShader", "Shader")

    def draw_buttons(self, context, layout):
        layout.prop(self, "is_active", icon='RADIOBUT_ON' if self.is_active else 'RADIOBUT_OFF')


class ArnoldNode:
    @property
    def ai_properties(self):
        return {}


@ArnoldRenderEngine.register_class
class ArnoldNodeLambert(bpy.types.Node, ArnoldNode):
    bl_label = "Lambert"
    bl_icon = 'MATERIAL'

    AI_NAME = "lambert"

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Diffuse", "Kd_color")
        self.inputs.new("NodeSocketFloat", "Weight", "Kd").default_value = 0.7
        self.inputs.new("ArnoldNodeSocketColor", "Opacity", "opacity")


@ArnoldRenderEngine.register_class
class ArnoldNodeStandard(bpy.types.Node, ArnoldNode):
    bl_label = "Standard"
    bl_icon = 'MATERIAL'
    bl_width_default = 250

    AI_NAME = "standard"

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        # Diffuse
        self.inputs.new("ArnoldNodeSocketColor", "Diffuse: Color", "Kd_color")
        self.inputs.new("NodeSocketFloat", "Diffuse: Weight", "Kd").default_value = 0.7
        self.inputs.new("NodeSocketFloat", "Diffuse: Roughness", "diffuse_roughness")
        self.inputs.new("NodeSocketFloat", "Diffuse: Backlight", "Kb")
        self.inputs.new("NodeSocketBool", "Fresnel affects Diffuse", "Fresnel_affect_diff").default_value = True
        self.inputs.new("NodeSocketFloat", "Diffuse: Direct", "direct_diffuse").default_value = 1
        self.inputs.new("NodeSocketFloat", "Diffuse: Indirect", "indirect_diffuse").default_value = 1
        # Specular
        self.inputs.new("ArnoldNodeSocketColor", "Specular: Color", "Ks_color")
        self.inputs.new("NodeSocketFloat", "Specular: Weight", "Ks")
        self.inputs.new("NodeSocketFloat", "Specular: Roughness", "specular_roughness").default_value = 0.466905
        self.inputs.new("NodeSocketFloat", "Specular: Anisotropy", "specular_anisotropy").default_value = 0.5
        self.inputs.new("NodeSocketFloat", "Specular: Rotation", "specular_rotation")
        self.inputs.new("NodeSocketBool", "Specular: Fresnel", "specular_Fresnel")
        self.inputs.new("NodeSocketFloat", "Specular: Reflectance at Normal", "Ksn")
        self.inputs.new("NodeSocketFloat", "Specular: Direct", "direct_specular").default_value = 1
        self.inputs.new("NodeSocketFloat", "Specular: Indirect", "indirect_specular").default_value = 1
        # Reflection
        self.inputs.new("ArnoldNodeSocketColor", "Reflection: Color", "Kr_color")
        self.inputs.new("NodeSocketFloat", "Reflection: Weight", "Kr")
        self.inputs.new("NodeSocketBool", "Reflection: Fresnel", "Fresnel")
        self.inputs.new("NodeSocketFloat", "Reflection: Reflectance at Normal", "Krn")
        self.inputs.new("NodeSocketBool", "Reflection: Exit Use Environment", "reflection_exit_use_environment").default_value = False
        self.inputs.new("ArnoldNodeSocketColor", "Reflection: Exit Color", "reflection_exit_color").default_value = (0, 0, 0)
        # Refraction (Transparency)
        self.inputs.new("ArnoldNodeSocketColor", "Refraction: Color", "Kt_color")
        self.inputs.new("NodeSocketFloat", "Refraction: Weight", "Kt")
        self.inputs.new("NodeSocketFloat", "Refraction: IOR", "IOR").default_value = 1
        self.inputs.new("NodeSocketFloat", "Refraction: Abbe Number", "dispersion_abbe")
        self.inputs.new("NodeSocketFloat", "Refraction: Roughness", "refraction_roughness")
        self.inputs.new("NodeSocketBool", "Fresnel use IOR", "Fresnel_use_IOR")
        self.inputs.new("ArnoldNodeSocketColor", "Transmittance", "transmittance")
        self.inputs.new("ArnoldNodeSocketColor", "Opacity", "opacity")
        self.inputs.new("NodeSocketBool", "Refraction: Exit Use Environment", "refraction_exit_use_environment")
        self.inputs.new("ArnoldNodeSocketColor", "Refraction: Exit Color", "refraction_exit_color").default_value = (0, 0, 0)
        # Sub-Surface Scattering
        self.inputs.new("ArnoldNodeSocketColor", "SSS: Color", "Ksss_color")
        self.inputs.new("NodeSocketFloat", "SSS: Weight", "Ksss")
        self.inputs.new("ArnoldNodeSocketColor", "SSS: Radius", "sss_radius").default_value = (0.1, 0.1, 0.1)
        # Emission
        self.inputs.new("ArnoldNodeSocketColor", "Emission: Color", "emission_color")
        self.inputs.new("NodeSocketFloat", "Emission: Weight", "emission")
        # Caustics
        self.inputs.new("NodeSocketBool", "Glossy Caustics", "enable_glossy_caustics")
        self.inputs.new("NodeSocketBool", "Reflective Caustics", "enable_reflective_caustics")
        self.inputs.new("NodeSocketBool", "Refractive Caustics", "enable_refractive_caustics")
        # Advanced
        self.inputs.new("NodeSocketFloat", "Bounce Factor", "bounce_factor").default_value = 1


@ArnoldRenderEngine.register_class
class ArnoldNodeUtility(bpy.types.Node, ArnoldNode):
    bl_label = "Utility"
    bl_icon = 'MATERIAL'

    AI_NAME = "utility"

    color_mode = bpy.props.EnumProperty(
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
    shade_mode = bpy.props.EnumProperty(
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
    overlay_mode = bpy.props.EnumProperty(
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
class ArnoldNodeFlat(bpy.types.Node, ArnoldNode):
    bl_label = "Flat"
    bl_icon = 'MATERIAL'

    AI_NAME = "flat"

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Color", "color")
        self.inputs.new("ArnoldNodeSocketColor", "Opacity", "opacity")


@ArnoldRenderEngine.register_class
class ArnoldNodeBump2D(bpy.types.Node, ArnoldNode):
    bl_label = "Bump2D"
    bl_icon = 'MATERIAL'

    AI_NAME = "bump2d"

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGBA", "output")
        self.inputs.new("NodeSocketFloat", "Map", "bump_map")
        self.inputs.new("NodeSocketFloat", "Height", "bump_height")
        self.inputs.new("NodeSocketShader", "Shader", "shader")


@ArnoldRenderEngine.register_class
class ArnoldNodeBump3D(bpy.types.Node, ArnoldNode):
    bl_label = "Bump3D"
    bl_icon = 'MATERIAL'

    AI_NAME = "bump3d"

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGBA", "output")
        self.inputs.new("NodeSocketFloat", "Map", "bump_map")
        self.inputs.new("NodeSocketFloat", "Height", "bump_height")
        self.inputs.new("NodeSocketFloat", "Epsilon", "epsilon")
        self.inputs.new("NodeSocketShader", "Shader", "shader")


@ArnoldRenderEngine.register_class
class ArnoldNodeWireframe(bpy.types.Node, ArnoldNode):
    bl_label = "Wireframe"
    bl_icon = 'MATERIAL'

    AI_NAME = "wireframe"

    edge_type = bpy.props.EnumProperty(
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
class ArnoldNodeNoise(bpy.types.Node, ArnoldNode):
    bl_label = "Noise"
    bl_icon = 'TEXTURE'

    AI_NAME = "noise"

    coord_space = bpy.props.EnumProperty(
        name="Space Coordinates",
        items=[
            ('world', "World", "World space"),
            ('object', "Object", "Object space"),
            ('Pref', "Pref", "Pref")
        ],
        default='object'
    )

    def init(self, context):
        self.outputs.new("NodeSocketFloat", "Value", "output")
        self.inputs.new("NodeSocketInt", "Octaves", "octaves").default_value = 1
        self.inputs.new("NodeSocketFloat", "Distortion", "distortion")
        self.inputs.new("NodeSocketFloat", "Lacunarity", "lacunarity").default_value = 1.92
        self.inputs.new("NodeSocketFloat", "Amplitude", "amplitude").default_value = 1
        self.inputs.new("NodeSocketVector", "Scale", "scale").default_value = (1, 1, 1)
        self.inputs.new("NodeSocketVector", "Offset", "offset")

    def draw_buttons(self, context, layout):
        layout.prop(self, "coord_space", text="")

    @property
    def ai_properties(self):
        return {
            "coord_space": ('STRING', self.coord_space)
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeImage(bpy.types.Node, ArnoldNode):
    bl_label = "Image"
    bl_icon = 'TEXTURE'

    AI_NAME = "image"

    texture = bpy.props.StringProperty(
        name="Texture"
    )

    def init(self, context):
        self.outputs.new("NodeSocketColor", "RGBA", "output")

    def draw_buttons(self, context, layout):
        layout.prop_search(self, "texture", context.blend_data, "textures", text="")

    @property
    def ai_properties(self):
        return {
            "filename": ('TEXTURE', self.texture)
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeMixRGB(bpy.types.Node, ArnoldNode):
    bl_label = "Mix RGB"
    bl_icon = 'MATERIAL'

    AI_NAME = "BArnoldMixRGB"

    blend_type = bpy.props.EnumProperty(
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


def register():
    from nodeitems_builtins import (
        ShaderNewNodeCategory,
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

    ShaderNewNodeCategory.poll = _poll(ShaderNewNodeCategory.poll)
    ShaderOldNodeCategory.poll = _poll(ShaderOldNodeCategory.poll)

    node_categories = [
        ArnoldNodeCategory("ARNOLD_NODES_OUTPUT", "Output", items=[
            nodeitems_utils.NodeItem("ArnoldNodeOutput")
        ]),
        ArnoldNodeCategory("ARNOLD_NODES_SHADERS", "Shaders", items=[
            nodeitems_utils.NodeItem("ArnoldNodeLambert"),
            nodeitems_utils.NodeItem("ArnoldNodeStandard"),
            nodeitems_utils.NodeItem("ArnoldNodeUtility"),
            nodeitems_utils.NodeItem("ArnoldNodeFlat"),
            nodeitems_utils.NodeItem("ArnoldNodeBump2D"),
            nodeitems_utils.NodeItem("ArnoldNodeBump3D"),
            nodeitems_utils.NodeItem("ArnoldNodeWireframe"),
            nodeitems_utils.NodeItem("ArnoldNodeImage"),
            nodeitems_utils.NodeItem("ArnoldNodeNoise"),
        ]),
        ArnoldNodeCategory("ARNOLD_NODES_COLOR", "Color", items=[
            nodeitems_utils.NodeItem("ArnoldNodeMixRGB")
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
