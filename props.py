# -*- coding: utf-8 -*-


import bpy
from bpy.types import (
    PropertyGroup,
    Scene,
    Lamp
)
from bpy.props import (
    PointerProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    BoolProperty
)


class ArnoldOptions(PropertyGroup):
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

    @classmethod
    def register(cls):
        Scene.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del Scene.arnold


class ArnoldPointLight(PropertyGroup):
    radius = FloatProperty(
        name="Radius"
    )
    decay_type = EnumProperty(
        name="Decay",
        description="Decay Type",
        items=[
            ('Constant', "Constant", "Constant"),
            ('Quadratic', "Quadratic", "Quadratic")
        ],
        default='Quadratic'
    )
    intensity = FloatProperty(
        name="Intensity",
        default=1.0
    )
    exposure = FloatProperty(
        name="Exposure"
    )
    cast_shadows = BoolProperty(
        name="Cast Shadows",
        default=True
    )
    cast_volumetric_shadows = BoolProperty(
        name="Cast Volumetric Shadows",
        default=True
    )
    shadow_density = FloatProperty(
        name="Shadow Density",
        default=1.0
    )
    shadow_color = FloatVectorProperty(
        name="Shadow Color",
        size=3,
        min=0, max=1,
        subtype='COLOR'
    )
    samples = IntProperty(
        name="Samples",
        default=1
    )
    normalize = BoolProperty(
        name="Normalize",
        default=True
    )


class ArnoldLight(PropertyGroup):
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


def register():
    from bpy.utils import register_class

    register_class(ArnoldOptions)
    register_class(ArnoldPointLight)
    register_class(ArnoldLight)


def unregister():
    from bpy.utils import unregister_class

    unregister_class(ArnoldOptions)
    unregister_class(ArnoldPointLight)
    unregister_class(ArnoldLight)
