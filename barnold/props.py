# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import bpy
from bpy.types import (
    PropertyGroup,
    Scene,
    Camera,
    Object,
    Material,
    Lamp
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
    ui_sampling = BoolProperty(
        name="Sampling",
        default=True
    )
    ui_ray_depth = BoolProperty(
        name="Ray Depth"
    )
    ui_light = BoolProperty(
        name="Light"
    )
    ui_gamma = BoolProperty(
        name="Gamma Correction"
    )
    ui_textures = BoolProperty(
        name="Textures"
    )
    ui_render = BoolProperty(
        name="Render Settings",
        default=True
    )
    ui_ipr = BoolProperty(
        name="IPR",
        default=True
    )
    ui_paths = BoolProperty(
        name="Search paths"
    )
    ui_licensing = BoolProperty(
        name="Licensing"
    )
    ui_log = BoolProperty(
        name="Log",
        default=True
    )
    ui_error = BoolProperty(
        name="Error Handling"
    )
    ui_overrides = BoolProperty(
        name="Feature overrides",
        default=True
    )
    ui_subdivisions = BoolProperty(
        name="Subdivision"
    )
    logfile = StringProperty(
        name="Filename",
        subtype='FILE_PATH',
        options=set()
    )
    logfile_flags = EnumProperty(
        name="File flags",
        items=_LOG_FLAGS,
        options={'ENUM_FLAG'}
    )
    console_log_flags = EnumProperty(
        name="Console flags",
        items=_LOG_FLAGS,
        options={'ENUM_FLAG'}
    )
    max_warnings = IntProperty(
        name="Max. Warnings",
        default=5
    )
    auto_threads = BoolProperty(
        name="Autodetect Threads",
        default=True
    )
    lock_sampling_pattern = BoolProperty(
        name="Lock Sampling Pattern"
    )
    clamp_sample_values = BoolProperty(
        name="Clamp Sample Values"
    )
    sample_filter_type = EnumProperty(
        name="Type",
        items=[
            ('blackman_harris_filter', "Blackman-Harris", "Blackman-Harris"),
            ('box_filter', "Box", "Box"),
            ('catrom2d_filter', "Catrom 2", "Catrom"),
            ('catrom_filter', "Catrom", "Catrom"),
            ('closest_filter', "Closest", "Closest"),
            ('cone_filter', "Cone", "Cone"),
            ('cook_filter', "Cook", "Cook"),
            ('cubic_filter', "Cubic", "Cubic"),
            ('disk_filter', "Disk", "Disk"),
            ('farthest_filter', "Farthest", "Farthest"),
            ('gaussian_filter', "Gauss", "Gauss"),
            ('heatmap_filter', "Heatmap", "Heatmap"),
            ('mitnet_filter', "Mitnet", "Mitnet"),
            ('sinc_filter', "Sinc", "Sinc"),
            ('triangle_filter', "Triangle", "Triangle"),
            ('variance_filter', "Variance", "Variance"),
            ('video_filter', "Video", "Video")
        ],
        default='gaussian_filter'
    )
    sample_filter_width = FloatProperty(
        name="Width",
        default=2
    )
    sample_filter_bh_width = FloatProperty(
        name="Width",
        default=3
    )
    sample_filter_sinc_width = FloatProperty(
        name="Width",
        default=6
    )
    sample_filter_domain = EnumProperty(
        name="Domain",
        items=[
            ('first_hit', "First Hit", "First Hit"),
            ('all_hits', "All Hits", "All Hits")
        ],
        default='first_hit'
    )
    sample_filter_min = FloatProperty(
        name="Minimum"
    )
    sample_filter_max = FloatProperty(
        name="Maximum",
        default=1.0,
    )
    sample_filter_scalar_mode = BoolProperty(
        name="Scalar Mode"
    )
    progressive_refinement = BoolProperty(
        name="Progressive Refinement",
        default=True
    )
    initial_sampling_level = IntProperty(
        name="Inital Sampling Level",
        min=-10, max=-1,
        default = -3
    )
    display_gamma = FloatProperty(
        name="Display Driver",
        default=1
    )

    def _get_bucket_size(self):
        r = self.id_data.render
        tile_x = r.tile_x
        # HACK: arnold supports only rectangle tiles
        if tile_x != r.tile_y:
            r.tile_y = tile_x
        return tile_x

    def _set_bucket_size(self, value):
        r = self.id_data.render
        r.tile_x = value
        r.tile_y = value

    ####
    # options node
    AA_samples = IntProperty(
        name="Camera (AA)",
        min=0, max=100,
        soft_min=1, soft_max=10,
        default=1
    )
    #AA_seed = scene.frame_current
    AA_sample_clamp = FloatProperty(
        name="Max Value",
        soft_min=0.001, soft_max=100.0,
        default=10.0,
        options=set()
    )
    AA_sample_clamp_affects_aovs = BoolProperty(
        name="Affect AOVs",
        options=set()
    )
    threads = IntProperty(
        name="Threads",
        min=1,
        options=set(),
        subtype='UNSIGNED'
    )
    thread_priority = EnumProperty(
        name="Thread Priority",
        items=[
            ('lowest', "Lowest", "Lowest"),
            ('low', "Low", "Low"),
            ('normal', "Normal", "Normal"),
            ('high', "Hight", "Hight")
        ],
        default='lowest',
        options=set()
    )
    pin_threads = EnumProperty(
        name="Pin Threads",
        items=[
            ('off', "Off", "Off"),
            ('on', "On", "Off"),
            ('auto', "Auto", "Auto")
        ],
        default='auto',
        options=set()
    )
    abort_on_error = BoolProperty(
        name="Abort on Error",
        default=True,
        options=set()
    )
    abort_on_license_fail = BoolProperty(
        name="Abort on License fail",
        options=set()
    )
    skip_license_check = BoolProperty(
        name="Skip License Check",
        options=set()
    )
    error_color_bad_texture = FloatVectorProperty(
        name="Texture Error Color",
        default=(1, 0, 0),
        min=0, max=1,
        subtype='COLOR'
    )
    error_color_bad_pixel = FloatVectorProperty(
        name="Pixel Error Color",
        default=(0, 0, 1),
        min=0, max=1,
        subtype='COLOR'
    )
    error_color_bad_shader = FloatVectorProperty(
        name="Shader Error Color",
        default=(1, 0, 1),
        min=0, max=1,
        subtype='COLOR'
    )
    bucket_size = IntProperty(
        name="Bucket Size",
        #min=16,
        #soft_max = 256,
        #default=64,
        #options=set()
        get=_get_bucket_size,
        set=_set_bucket_size
    )
    bucket_scanning = EnumProperty(
        name="Bucket Scanning",
        items=[
            ('top', "Top", "Top"),
            ('bottom', "Bottom", "Bottom"),
            ('left', "Left", "Left"),
            ('right', "Right", "Right"),
            ('random', "Random", "Random"),
            ('woven', "Woven", "Woven"),
            ('spiral', "Spiral", "Spiral"),
            ('hilbert', "Hilbert", "Hilbert"),
            #('list', "List", "List")
        ],
        default='spiral',
        options=set()
    )
    ignore_textures = BoolProperty(
        name="Ignore Textures"
    )
    ignore_shaders = BoolProperty(
        name="Ignore Shaders"
    )
    ignore_atmosphere = BoolProperty(
        name="Ignore Atmosphere"
    )
    ignore_lights = BoolProperty(
        name="Ignore Lights"
    )
    ignore_shadows = BoolProperty(
        name="Ignore Shadows"
    )
    ignore_direct_lighting = BoolProperty(
        name="Ignore Direct Lighting"
    )
    ignore_subdivision = BoolProperty(
        name="Ignore Subdivision"
    )
    ignore_displacement = BoolProperty(
        name="Ignore Displacement"
    )
    ignore_bump = BoolProperty(
        name="Ignore Bump"
    )
    ignore_motion_blur = BoolProperty(
        name="Ignore Motion Blur"
    )
    ignore_dof = BoolProperty(
        name="Ignore DOF"
    )
    ignore_smoothing = BoolProperty(
        name="Ignore Normal Smoothing"
    )
    ignore_sss = BoolProperty(
        name="Ignore SSS"
    )
    #enable_fast_opacity
    auto_transparency_mode = EnumProperty(
        name="Mode",
        items=[
            ('always', "Always", "Always"),
            ('shadow-only', "Shadow Only", "Shadow Only"),
            ('never', "Never", "Never")
        ],
        default='always'
    )
    auto_transparency_depth = IntProperty(
        name="Depth",
        default=10
    )
    auto_transparency_threshold = FloatProperty(
        name="Threshold",
        default=0.99
    )
    texture_max_open_files = IntProperty(
        name="Max Open Files",
        default=0
    )
    texture_max_memory_MB = FloatProperty(
        name="Max Cache Size (MB)",
        default=1024
    )
    #texture_per_file_stats
    texture_searchpath = StringProperty(
        name="Texture",
        subtype='DIR_PATH'
    )
    texture_automip = BoolProperty(
        name="Auto mipmap",
        default=True
    )
    texture_autotile = IntProperty(
        name="Auto-Tile",
        default=64
    )
    texture_accept_untiled = BoolProperty(
        name="Accept Untiled",
        default=True
    )
    texture_accept_unmipped = BoolProperty(
        name="Accept Unmipped",
        default=True
    )
    #texture_failure_retries
    #texture_conservative_lookups
    texture_glossy_blur = FloatProperty(
        name="Glossy Blur",
        default=0.015625
    )
    texture_diffuse_blur = FloatProperty(
        name="Diffuse Blur",
        default=0.03125
    )
    #texture_sss_blur
    #texture_max_sharpen
    #background_visibility
    #bump_multiplier
    #bump_space
    #luminaire_bias
    low_light_threshold = FloatProperty(
        name="Low Light Threshold",
        default=0.001
    )
    #shadow_terminator_fix
    #shadows_obey_light_linking
    #skip_background_atmosphere
    sss_bssrdf_samples = IntProperty(
        name="SSS",
        default=0
    )
    sss_use_autobump = BoolProperty(
        name="Use Autobump in SSS"
    )
    volume_indirect_samples = IntProperty(
        name="Volume indirect",
        default=2
    )
    #reference_time
    #CCW_points
    max_subdivisions = IntProperty(
        name="Max. Subdivisions",
        default=999
    )
    procedural_searchpath = StringProperty(
        name="Procedural",
        subtype='DIR_PATH'
    )
    shader_searchpath = StringProperty(
        name="Shader",
        subtype='DIR_PATH'
    )
    #preserve_scene_data
    #curved_motionblur
    texture_gamma = FloatProperty(
        name="Textures",
        default=1
    )
    light_gamma = FloatProperty(
        name="Lights",
        default=1
    )
    shader_gamma = FloatProperty(
        name="Shaders",
        default=1
    )
    GI_diffuse_depth = IntProperty(
        name="Diffuse"
    )
    GI_glossy_depth = IntProperty(
        name="Glossy"
    )
    GI_reflection_depth = IntProperty(
        name="Reflection",
        default=2
    )
    GI_refraction_depth = IntProperty(
        name="Refraction",
        default=2
    )
    GI_volume_depth = IntProperty(
        name="Volume"
    )
    GI_total_depth = IntProperty(
        name="Total",
        default=10,
    )
    GI_diffuse_samples = IntProperty(
        name="Diffuse",
        default=2
    )
    #GI_single_scatter_samples
    GI_glossy_samples = IntProperty(
        name="Glossy",
        default=2
    )
    GI_refraction_samples = IntProperty(
        name="Refraction",
        default=2
    )
    #GI_falloff_start_dist
    #GI_falloff_stop_dist
    #enable_displacement_derivs
    #enable_threaded_procedurals
    #enable_procedural_cache
    procedural_force_expand = BoolProperty(
        name="Expand procedurals"
    )
    #parallel_node_init

    @classmethod
    def register(cls):
        Scene.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del Scene.arnold


@ArnoldRenderEngine.register_class
class ArnoldCamera(PropertyGroup):
    enable_dof = BoolProperty(
        name="Enable DOF"
    )
    # far_clip with plane if True or with sphere
    #plane_distance = BoolProperty(
    #    name="Plane Distance",
    #    default=True
    #)
    aperture_size = FloatProperty(
        name="Aperture: Size"
    )
    aperture_blades = IntProperty(
        name="Aperture: Blades"
    )
    aperture_rotation = FloatProperty(
        name="Aperture: Rotation"
    )
    aperture_blade_curvature = FloatProperty(
        name="Aperture: Blade Curvature"
    )
    aperture_aspect_ratio = FloatProperty(
        name="Aperture: Aspect Ratio",
        default=1
    )
    # dof flat of sphere
    #flat_field_focus = BoolProperty(
    #    name="Flat Field Focus",
    #    default=True
    #)
    shutter_start = FloatProperty(
        name="Shutter: Start"
    )
    shutter_end = FloatProperty(
        name="Shutter: Stop"
    )
    shutter_type = EnumProperty(
        name="Shutter Type",
        items=[
            ('box', "Box", "Box"),
            ('triangle', "Triangle", "Triangle"),
            #('curve', "Curve", "Curve")
        ],
        default='box'
    )
    #shutter_curve
    rolling_shutter = EnumProperty(
        name="Rolling Shutter",
        items=[
            ('off', "Off", "Off"),
            ('top', "Top", "Top"),
            ('bottom', "Bottom", "Bottom"),
            ('left', "Left", "Left"),
            ('right', "Right", "Right")
        ],
        default='off'
    )
    rolling_shutter_duration = FloatProperty(
        name="Rolling Shutter: Duration"
    )
    #handedness (right, left)
    #time_samples
    exposure = FloatProperty(
        name="Exposure"
    )

    @classmethod
    def register(cls):
        Camera.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del Camera.arnold


@ArnoldRenderEngine.register_class
class ArnoldShape(PropertyGroup):
    visibility = IntProperty(
        name="Visibility",
        default=255
    )
    sidedness = IntProperty(
        name="Sidedness",
        default=255
    )
    receive_shadows = BoolProperty(
        name="Receive shadows",
        default=True
    )
    self_shadows = BoolProperty(
        name="Self shadows",
        default=True
    )
    invert_normals = BoolProperty(
        name="Invert normals"
    )
    opaque = BoolProperty(
        name="Opaque",
        default=True
    )
    matte = BoolProperty(
        name="Matte"
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

    def _sidedness(mask):
        def get(self):
            return self.sidedness & mask

        def set(self, value):
            if value:
                self.sidedness |= mask
            else:
                self.sidedness &= ~mask

        return {
            "get": get,
            "set": set
        }

    sidedness_camera = BoolProperty(
        name="Camera",
        **_sidedness(1)
    )
    sidedness_shadow = BoolProperty(
        name="Shadow",
        **_sidedness(1 << 1)
    )
    sidedness_reflection = BoolProperty(
        name="Reflection",
        **_sidedness(1 << 2)
    )
    sidedness_refraction = BoolProperty(
        name="Refraction",
        **_sidedness(1 << 3)
    )
    sidedness_diffuse = BoolProperty(
        name="Diffuse",
        **_sidedness(1 << 4)
    )
    sidedness_glossy = BoolProperty(
        name="Glossy",
        **_sidedness(1 << 5)
    )
 
    @classmethod
    def register(cls):
        Object.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del Object.arnold


@ArnoldRenderEngine.register_class
class ArnoldLight(PropertyGroup):
    ui_shadow = BoolProperty(
        name="Shadow"
    )
    ui_volume = BoolProperty(
        name="Volume"
    )
    ui_contribution = BoolProperty(
        name="Contribution"
    )
    ui_viewport = BoolProperty(
        name="Viewport",
    )
    angle = FloatProperty(
        name="Angle"
    )
    radius = FloatProperty(
        name="Radius",
        min=0, soft_max=10
    )
    lens_radius = FloatProperty(
        name="Lens Radius"
    )
    penumbra_angle = FloatProperty(
        name="Penumbra Angle"
    )
    aspect_ratio = FloatProperty(
        name="Aspect Ratio",
        default=1
    )
    resolution = IntProperty(
        name="Resolution",
        default=1000
    )
    format = EnumProperty(
        name="Format",
        items=[
            ('angular', "Angular", "Angular")
        ],
        default='angular'
    )
    # Is not available for Directional, Distant or Skydome lights.
    decay_type = EnumProperty(
        name="Decay Type",
        items=[
            ('constant', "Constant", "Constant"),
            ('quadratic', "Quadratic", "Quadratic")
        ],
        default='quadratic'
    )
    quad_resolution = IntProperty(
        name="Resolution",
        default=512
    )
    # common parameters
    intensity = FloatProperty(
        name="Intensity",
        description="Intensity controls the brightness of light emitted by the light source by multiplying the color.",
        soft_min=0, soft_max=10,
        default=1.0
    )
    exposure = FloatProperty(
        name="Exposure",
        description="Exposure is an f-stop value which multiplies the intensity by 2 to the power of the f-stop. Increasing the exposure by 1 results in double the amount of light.",
        soft_min=0, soft_max=10
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
        description="Controls the quality of the noise in the soft shadows."
                    " The higher the number of samples, the lower the noise,"
                    " and the longer it takes to render. The exact number of"
                    " shadow rays sent to the light is the square of this"
                    " value multiplied by the AA samples.",
        soft_min=1, max=100,
        default=1
    )
    normalize = BoolProperty(
        name="Normalize",
        default=True
    )
    affect_diffuse = BoolProperty(
        name="Emit Diffuse",
        description="Allow the light to affect a material's diffuse component.",
        default=True
    )
    affect_specular = BoolProperty(
        name="Emit Specular",
        description="Allow the light to affect a material's specular component.",
        default=True
    )
    affect_volumetrics = BoolProperty(
        name="Affect Volumetrics",
        default=True
    )
    diffuse = FloatProperty(
        name="Diffuse",
        soft_min=0, soft_max=1,
        default=1
    )
    specular = FloatProperty(
        name="Specular",
        soft_min=0, soft_max=1,
        default=1
    )
    sss = FloatProperty(
        name="SSS",
        soft_min=0, soft_max=1,
        default=1
    )
    indirect = FloatProperty(
        name="Indirect",
        soft_min=0, soft_max=1,
        default=1
    )
    max_bounces = IntProperty(
        name="Max Bounces",
        default=999
    )
    volume_samples = IntProperty(
        name="Volume Samples",
        subtype='UNSIGNED',
        default=2
    )
    volume = FloatProperty(
        name="Volume",
        soft_min=0, soft_max=1,
        default=1
    )

    def _types():
        _lamps = ('POINT', 'SUN', 'SPOT', 'HEMI', 'AREA')

        def get(self):
            lamp = self.id_data
            i = _lamps.index(lamp.type)
            if i == 4:  # AREA
                _t = self.get("_type", 0)
                if _t == 3:
                    i = 8  # quad_light
                elif lamp.shape == 'RECTANGLE':
                    self["_type"] = 0
                    i = 4  # cylinder_light
                else:
                    i = _t + 5
            return i

        def set(self, value):
            lamp = self.id_data
            if value > 4:
                lamp.type = 'AREA'
                lamp = lamp.type_recast()
                if value != 8:
                    lamp.shape = 'SQUARE'
                self["_type"] = value - 5
            elif value == 4:
                lamp.type = 'AREA'
                lamp = lamp.type_recast()
                lamp.shape = 'RECTANGLE'
                self["_type"] = 0
            else:
                lamp.type = _lamps[value]

        return {"get": get, "set": set}

    type = EnumProperty(
        name="Type",
        description="Light Type",
        items=[
            ('point_light', "Point", "Point light", 0),
            ('distant_light', "Distant", "Distant light", 1),
            ('spot_light', "Spot", "Spot light", 2),
            ('skydome_light', "Skydom", "Skydom light", 3),
            ('cylinder_light', "Cylinder", "Cylinder light", 4),
            ('disk_light', "Disk", "Disk light", 5),
            ('mesh_light', "Mesh", "Mesh light", 6),
            ('photometric_light', "Photometric", "Photometric light", 7),
            ('quad_light', "Quad", "Quad light", 8)
        ],
        **_types()
    )

    ui_size = FloatProperty(
        name="Radius",
        get=lambda s: s.id_data.size / 2,
        set=lambda s, v: setattr(s.id_data, "size", v * 2)
    )
    ui_size_y = FloatProperty(
        name="Height",
        get=lambda s: s.id_data.size_y / 2,
        set=lambda s, v: setattr(s.id_data, "size_y", v * 2)
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
        default=(1, 1, 1),
        min=0, max=1,
        subtype='COLOR'
    )
    line_width = FloatProperty(
        name="Line Width",
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
