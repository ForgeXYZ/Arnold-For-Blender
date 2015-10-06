# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import bpy
import nodeitems_utils
from bpy.types import NodeSocket, Node
from bpy.props import (
    IntProperty,
    BoolProperty,
    EnumProperty,
    StringProperty,
    FloatVectorProperty
)
from . import ArnoldRenderEngine


_WRAP_ITEMS = [
    ('periodic', "Periodic", "Periodic"),
    ('black', "Black", "Black"),
    ('clamp', "Clamp", "Clamp"),
    ('mirror', "Mirror", "Mirror"),
    ('file', "File", "File")
]


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
            row = layout.row(align=True)
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
    bl_width_default = 250

    ai_name = "standard"

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

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("NodeSocketFloat", "Start Time", "time0")
        self.inputs.new("NodeSocketFloat", "End Time", "time1").default_value = 1
        self.inputs.new("NodeSocketBool", "Encode Raw Vector", "raw")
        self.inputs.new("NodeSocketFloat", "Max Displace", "max_displace")


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
        self.inputs.new("NodeSocketString", "Uparam", "uparam")
        self.inputs.new("NodeSocketString", "Vparam", "vparam")


@ArnoldRenderEngine.register_class
class ArnoldNodeNoise(ArnoldNode):
    bl_label = "Noise"
    bl_icon = 'TEXTURE'

    ai_name = "noise"

    coord_space = EnumProperty(
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
    uvset = StringProperty(
        name="UV set"
    )

    def init(self, context):
        self.outputs.new("NodeSocketColor", "RGBA", "output")
        # Image attributes
        self.inputs.new("NodeSocketInt", "Mipmap Bias", "mipmap_bias")
        self.inputs.new("ArnoldNodeSocketColor", "Multiply", "multiply")
        self.inputs.new("ArnoldNodeSocketColor", "Offset", "offset").default_value = (0, 0, 0)
        self.inputs.new("NodeSocketBool", "Single channel", "single_channel")
        self.inputs.new("ArnoldNodeSocketByte", "Start channel", "start_channel")
        self.inputs.new("NodeSocketBool", "Ignore missing tiles", "ignore_missing_tiles")
        self.inputs.new("NodeSocketColor", "Missing tile color", "missing_tile_color")
        # UV coordinates
        self.inputs.new("NodeSocketFloat", "U scale", "sscale").default_value = 1
        self.inputs.new("NodeSocketFloat", "V scale", "tscale").default_value = 1
        self.inputs.new("NodeSocketFloat", "U offset", "soffset")
        self.inputs.new("NodeSocketFloat", "V offset", "toffset")
        self.inputs.new("NodeSocketBool", "U flip", "sflip")
        self.inputs.new("NodeSocketBool", "V flip", "tflip")
        self.inputs.new("NodeSocketBool", "UV swap", "swap_st")
        self.inputs.new("NodeSocketVector", "UV coords", "uvcoords").hide_value = True

    def draw_buttons(self, context, layout):
        layout.prop(self, "filename", text="", icon='IMAGEFILE')
        layout.prop(self, "filter", text="")
        layout.prop(self, "uvset")
        layout.prop(self, "swrap")
        layout.prop(self, "twrap")

    @property
    def ai_properties(self):
        props = {
            "filter": ('STRING', self.filter),
            "swrap": ('STRING', self.swrap),
            "twrap": ('STRING', self.twrap),
        }
        if self.filename:
            props["filename"] = ('FILE_PATH', self.filename)
        if self.uvset:
            props["uvset"] = ('STRING', self.uvset)
        return props


@ArnoldRenderEngine.register_class
class ArnoldNodeSky(ArnoldNode):
    bl_label = "Sky"
    bl_icon = 'WORLD'

    ai_name = "sky"

    format = EnumProperty(
        name="Format",
        items=[
            ('mirrored_ball', "Mirrored Ball", "Mirrored Ball"),
            ('angular', "Angular", "Angular"),
            ('latlong', "LatLong", "LatLong")
        ],
        default='angular'
    )

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("ArnoldNodeSocketColor", "Color", "color")
        self.inputs.new("NodeSocketFloat", "Intensity", "intensity").default_value = 1
        self.inputs.new("NodeSocketInt", "Visibility", "visibility").default_value = 255
        self.inputs.new("NodeSocketBool", "Opaque Alpha", "opaque_alpha").default_value = True
        self.inputs.new("NodeSocketFloat", "X angle", "X_angle")
        self.inputs.new("NodeSocketFloat", "Y angle", "Y_angle")
        self.inputs.new("NodeSocketFloat", "Z angle", "Z_angle")
        self.inputs.new("NodeSocketVector", "X").default_value = (1, 0, 0)
        self.inputs.new("NodeSocketVector", "Y").default_value = (0, 1, 0)
        self.inputs.new("NodeSocketVector", "Z").default_value = (0, 0, 1)

    def draw_buttons(self, context, layout):
        layout.prop(self, "format", text="")

    @property
    def ai_properties(self):
        return {
            "format": ('STRING', self.format)
        }


@ArnoldRenderEngine.register_class
class ArnoldNodePhysicalSky(ArnoldNode):
    bl_label = "Physical Sky"
    bl_icon = 'WORLD'

    ai_name = "physical_sky"

    enable_sun = BoolProperty(
        name="Enable Sun",
        default=True
    )

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("NodeSocketFloat", "Sun size", "sun_size").default_value = 0.51
        self.inputs.new("ArnoldNodeSocketColor", "Sky Tint", "sky_tint")
        self.inputs.new("ArnoldNodeSocketColor", "Sun Tint", "sun_tint")
        self.inputs.new("NodeSocketFloat", "Turbidity", "turbidity").default_value = 3
        self.inputs.new("ArnoldNodeSocketColor", "Ground Albedo", "ground_albedo").default_value = (0.1, 0.1, 0.1)
        self.inputs.new("NodeSocketFloat", "Elevation", "elevation").default_value = 45
        self.inputs.new("NodeSocketFloat", "Azimuth", "azimuth").default_value = 90
        self.inputs.new("NodeSocketFloat", "Intensity", "intensity").default_value = 1
        self.inputs.new("NodeSocketVector", "X").default_value = (1, 0, 0)
        self.inputs.new("NodeSocketVector", "Y").default_value = (0, 1, 0)
        self.inputs.new("NodeSocketVector", "Z").default_value = (0, 0, 1)

    def draw_buttons(self, context, layout):
        layout.prop(self, "enable_sun")

    @property
    def ai_properties(self):
        return {
            "enable_sun": ('BOOL', self.enable_sun)
        }


@ArnoldRenderEngine.register_class
class ArnoldNodeVolumeScattering(ArnoldNode):
    bl_label = "Volume Scattering"
    bl_icon = 'WORLD'

    ai_name = "volume_scattering"

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("NodeSocketFloat", "density")
        self.inputs.new("NodeSocketInt", "Samples", "samples").default_value = 5
        self.inputs.new("NodeSocketFloat", "eccentricity")
        self.inputs.new("NodeSocketFloat", "attenuation")
        self.inputs.new("NodeSocketFloat", "affect_camera").default_value = 1
        self.inputs.new("NodeSocketFloat", "affect_diffuse")
        self.inputs.new("NodeSocketFloat", "affect_reflection").default_value = 1
        self.inputs.new("ArnoldNodeSocketColor", "rgb_density")
        self.inputs.new("ArnoldNodeSocketColor", "rgb_attenuation")


@ArnoldRenderEngine.register_class
class ArnoldNodeFog(ArnoldNode):
    bl_label = "Fog"
    bl_icon = 'WORLD'

    ai_name = "fog"

    def init(self, context):
        self.outputs.new("NodeSocketShader", "RGB", "output")
        self.inputs.new("NodeSocketFloat", "distance").default_value = 0.02
        self.inputs.new("NodeSocketFloat", "height").default_value = 5
        self.inputs.new("ArnoldNodeSocketColor", "color")
        #self.inputs.new("POINT", "ground_point")  # TODO: need socket type
        self.inputs.new("NodeSocketVector", "ground_normal").default_value = (0, 0, 1)


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
    _shader_type = {'OBJECT', 'WORLD'}

    @classmethod
    def poll(cls, context):
        return (
            ArnoldRenderEngine.is_active(context) and
            context.space_data.tree_type == 'ShaderNodeTree' and
            context.space_data.shader_type in cls._shader_type
        )


class ArnoldObjectNodeCategory(ArnoldNodeCategory):
    _shader_type = {'OBJECT'}


class ArnoldWorldNodeCategory(ArnoldNodeCategory):
    _shader_type = {'WORLD'}


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
        # common
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
