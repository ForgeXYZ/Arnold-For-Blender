# -*- coding: utf-8 -*-

import bpy

from bpy.types import (
    PropertyGroup,
    Scene,
    Lamp,
    Material
)
from bpy.props import (
    PointerProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    BoolProperty,
    StringProperty
)
from . import ArnoldRenderEngine


_LOG_FLAGS = [
    ('INFO', "Info", "All regular information messages", 0x0001),
    ('WARNINGS', "Warnings", "Warning messages", 0x0002),
    ('ERRORS', "Errors", "Error messages", 0x0004),
    ('DEBUG', "Debug", "Debug messages", 0x0008),
    ('STATS', "Statistics", "Detailed render statistics", 0x0010),
    ('PLUGINS', "Plugins", "Details about plugins loaded", 0x0040),
    ('PROGRESS', "Progress", "A progress message at 5% increments while rendering", 0x0080),
    ('NAN', "Nan", "Warnings for pixels with NaN's", 0x0100),
    ('TIMESTAMP', "Timestamp", "Prefix messages with a timestamp (elapsed time)", 0x0200),
    ('BACKTRACE', "Backtrace", "The stack contents after abnormal program termination (\c SIGSEGV, etc)", 0x0400),
    ('MEMORY', "Memory", "Prefix messages with current memory usage", 0x0800),
    ('COLOR', "Color", "Add colors to log messages based on severity", 0x1000),
    ('SSS', "SSS", "messages about sub-surface scattering pointclouds", 0x2000),
    ('ALL', "All", "All messages", 0x3fff)
]


@ArnoldRenderEngine.register_class
class ArnoldOptions(PropertyGroup):
    logfile = StringProperty(
        name="Logging Filename",
        subtype='FILE_PATH'
    )
    logfile_flags = EnumProperty(

        name="File Logging Flags",
        items=_LOG_FLAGS,
        options={'ENUM_FLAG'}
    )
    console_log_flags = EnumProperty(
        name="Console Logging Flags",
        items=_LOG_FLAGS,
        options={'ENUM_FLAG'}
    )
    aa_samples = IntProperty(
        name="AA Samples",
        default=1
    )
    aa_seed = IntProperty(
        name="AA Seed",
        default=1
    )
    threads = IntProperty(
        name="Threads"
    )
    thread_priority = EnumProperty(
        name="Thread Priority",
        items=[
            ('lowest', "Lowest", "Lowest"),
        ]
    )
    skip_license_check = BoolProperty(
        name="Skip License Check"
    )
    bucket_size = IntProperty(
        name="Bucket Size",
        min=16,
        soft_max = 256,
        default=64,
        #options = set(),
    )
    bucket_scanning = EnumProperty(
        name="Bucket Scanning",
        items=[
            ('spiral', "Spiral", "Spiral"),
        ],
        default='spiral'
    )

    @classmethod
    def register(cls):
        Scene.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del Scene.arnold


@ArnoldRenderEngine.register_class
class ArnoldPointLight(PropertyGroup):
    radius = FloatProperty(
        name="Radius"
    )


@ArnoldRenderEngine.register_class
class ArnoldLight(PropertyGroup):
    intensity = FloatProperty(
        name="Intensity",
        default=1.0
    )
    exposure = FloatProperty(
        name="Exposure"
    )
    # Is not available for Directional, Distant or Skydome lights.
    decay_type = EnumProperty(
        name="Decay",
        description="Decay Type",
        items=[
            ('constant', "Constant", "Constant"),
            ('quadratic', "Quadratic", "Quadratic")
        ],
        default='quadratic'
    )
    # Shadows
    cast_shadows = BoolProperty(
        name="Cast Shadows",
        default=True
    )
    shadow_density = FloatProperty(
        name="Density",
        description="Shadow Density",
        default=1.0
    )
    shadow_color = FloatVectorProperty(
        name="Shadow Color",
        size=3,
        min=0, max=1,
        subtype='COLOR'
    )
    cast_volumetric_shadows = BoolProperty(
        name="Cast Volumetric Shadows",
        default=True
    )
    samples = IntProperty(
        name="Samples",
        default=1
    )
    normalize = BoolProperty(
        name="Normalize",
        default=True
    )
    point = PointerProperty(type=ArnoldPointLight)
    type = EnumProperty(
        name="Type",
        description="Light Type",
        items=[
            ('POINT', "Point", "Point light"),
            ('QUAD', "Quad", "Quad light")
        ]
    )

    @classmethod
    def register(cls):
        Lamp.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del Lamp.arnold


@ArnoldRenderEngine.register_class
class ArnoldShaderStandard(PropertyGroup):
    diffuse_roughness = FloatProperty(
        name="Roughness",
        description="Diffuse Roughness",
        min=0, max=1,
        precision=4,
        step=0.1
    )
    ks = FloatProperty(
        name="Weight",
        min=0, max=1,
        precision=4,
        step=0.1
    )
    ks_color = FloatVectorProperty(
        name="Specular color",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    specular_roughness = FloatProperty(
        name="Roughness",
        description="Specular Roughness",
        min=0, max=1,
        default=0.466905,
        precision=4,
        step=0.1
    )
    specular_anisotropy = FloatProperty(
        name="Anisotropy",
        description="Specular Anisotropy",
        min=0, max=1,
        default=0.5,
        precision=4,
        step=0.1
    )
    specular_rotation = FloatProperty(
        name="Rotation",
        description="Specular Rotation",
        min=0, max=1,
        precision=4,
        step=0.1
    )


@ArnoldRenderEngine.register_class
class ArnoldShaderUtility(PropertyGroup):
    opacity = FloatProperty(
        name="Opacity",
        default=1.0
    )


@ArnoldRenderEngine.register_class
class ArnoldShaderWireframe(PropertyGroup):
    edge_type = EnumProperty(
        name="Edge Type",
        items=[
            ('polygons', "Polygons", "Polygons"),
            ('triangles', "Triangles", "Triangles")
        ],
        default='triangles'
    )
    fill_color = FloatVectorProperty(
        name="Fill Color",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    line_width = FloatProperty(
        name="Width",
        description="Line Width",
        default=1.0
    )
    raster_space = BoolProperty(
        name="Raster Space",
        default=True
    )


@ArnoldRenderEngine.register_class
class ArnoldShader(PropertyGroup):
    type = EnumProperty(
        name="Type",
        items=[
            ('LAMBERT', "Lambert", "Lambert"),
            ('STANDARD', "Standard", "Standard"),
            ('UTILITY', "Utility", "Utility")
        ],
        default='LAMBERT'
    )
    # Lambert/Standard opacity
    opacity = FloatVectorProperty(
        name="Opacity",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    standard = PointerProperty(type=ArnoldShaderStandard)
    utility = PointerProperty(type=ArnoldShaderUtility)
    wire = PointerProperty(type=ArnoldShaderWireframe)

    active_image_node = StringProperty()

    @classmethod
    def register(cls):
        Material.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del Material.arnold
