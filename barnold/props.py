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
    Lamp,
    ParticleSettings
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
_SPACE_TYPES = [
    ('raster', "Raster", "Raster"),
    ('object', "Object", "Object")
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
    ipr_bucket_size = IntProperty(
        name="Bucket Size",
        min=16, soft_max=1024,
        default=64,
    )
    display_gamma = FloatProperty(
        name="Display Driver",
        default=1  # / 2.2  # TODO: inspect gamma correction
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
    sss_use_autobump = BoolProperty(
        name="Use Autobump in SSS"
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
    GI_glossy_samples = IntProperty(
        name="Glossy",
        default=2
    )
    GI_refraction_samples = IntProperty(
        name="Refraction",
        default=2
    )
    GI_sss_samples = IntProperty(
        name="SSS",
        default=0
    )
    #GI_single_scatter_samples
    GI_volume_samples = IntProperty(
        name="Volume indirect",
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
    #UINT[]        nsides                            (empty)
    #UINT[]        vidxs                             (empty)
    #UINT[]        nidxs                             (empty)
    #UINT[]        uvidxs                            (empty)
    #UINT[]        crease_idxs                       (empty)
    #FLOAT[]       crease_sharpness                  (empty)
    #BYTE[]        shidxs                            (empty)
    #POINT[]       vlist                             (empty)
    #VECTOR[]      nlist                             (empty)
    #POINT2[]      uvlist                            (empty)
    #BOOL          smoothing                         false
    subdiv_type = EnumProperty(
        name="Type",
        items=[
            ('none', "None", "None"),
            ('catclark', "Catmull-Clark", "Catmull-Clark"),
            ('linear', "Linear", "Linear")
        ],
        default='none'
    )
    subdiv_iterations = IntProperty(
        name="Iterations",
        subtype='UNSIGNED',
        min=0, max=255,
        default=1
    )
    subdiv_adaptive_error = FloatProperty(
        name="Adaptive Error",
        default=0
    )
    #NODE          subdiv_dicing_camera              (null)
    subdiv_adaptive_metric = EnumProperty(
        name="Adaptive Metric",
        items=[
            ('auto', "Auto", "Auto"),
            ('edge_length', "Edge Length", "Edge Length"),
            ('flatness', "Flatness", "Flatness"),
        ],
        default='auto'
    )
    subdiv_adaptive_space = EnumProperty(
        name="Adaptive Space",
        items=_SPACE_TYPES,
        default='raster'
    )
    subdiv_uv_smoothing = EnumProperty(
        name="UV Smoothing",
        items=[
            ('pin_corners', "Pin Corners", "Pin Corners"),
            ('pin_borders', "Pin Borders", "Pin Borders"),
            ('linear', "Linear", "Linear"),
            ('smooth', "Smooth", "Smooth")
        ],
        default='pin_corners'
    )
    subdiv_smooth_derivs = BoolProperty(
        name="Smooth Tangents"
    )
    #NODE[]        disp_map                          (empty)
    #FLOAT         disp_padding                      0
    #FLOAT         disp_height                       1
    #FLOAT         disp_zero_value                   0
    #BOOL          disp_autobump                     false
    #BYTE          autobump_visibility               159
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
    # ray_bias (FLOAT)
    # matrix (MATRIX[]) = Object.matrix_world
    # shader (NODE[]) = Object.data.materials
    opaque = BoolProperty(
        name="Opaque",
        default=True
    )
    matte = BoolProperty(
        name="Matte"
    )
    # use_light_group (BOOL)
    # light_group (NODE[])
    # use_shadow_group (BOOL)
    # shadow_group (NODE[])
    # trace_sets (STRING[])
    # transform_time_samples (FLOAT[])
    # deform_time_samples (FLOAT[])
    # id (INT)

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
            ('mirrored_ball', "Mirrored Ball", "Mirrored Ball"),
            ('angular', "Angular", "Angular"),
            ('latlong', "LatLong", "Latitude & Longitude")
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
    filename = StringProperty(
        name="Photometry File",
        subtype='FILE_PATH'
    )
    mesh = StringProperty(
        name="Mesh"
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
class ArnoldShaderLambert(PropertyGroup):
    #Kd = Material.diffuse_intensity
    #Kd_color = Material.diffuse_color
    opacity = FloatVectorProperty(
        name="Opacity",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )


@ArnoldRenderEngine.register_class
class ArnoldShaderStandard(PropertyGroup):
    ui_diffuse = BoolProperty(
        name="Diffuse",
        default=True
    )
    ui_specular = BoolProperty(
        name="Specular"
    )
    ui_reflection = BoolProperty(
        name="Reflection"
    )
    ui_refraction = BoolProperty(
        name="Refraction"
    )
    ui_sss = BoolProperty(
        name="SSS"
    )
    ui_emission = BoolProperty(
        name="Emission"
    )
    ui_caustics = BoolProperty(
        name="Coustics"
    )
    #Kd = Material.diffuse_intensity
    #Kd_color = Material.diffuse_color
    diffuse_roughness = FloatProperty(
        name="Roughness",
        description="The diffuse component follows an Oren-Nayar reflection"
                    " model with surface roughness. A value of 0.0 is"
                    " comparable to a Lambert reflection. Higher values"
                    " will result in a rougher surface look more suitable"
                    " for materials like concrete, plaster or sand.",
        subtype='FACTOR',
        min=0, max=1
    )
    #Ks = Material.specular_intensity
    #Ks_color = Material.specular_color
    specular_roughness = FloatProperty(
        name="Roughness",
        description="Controls the glossiness of the specular reflections."
                    " The lower the value, the sharper the reflection. In the"
                    " limit, a value of 0 will give you a perfectly sharp"
                    " mirror reflection, whilst 1.0 will create reflections"
                    " that are close to a diffuse reflection.",
        subtype='FACTOR',
        min=0, max=1,
        default=0.466905
    )
    specular_anisotropy = FloatProperty(
        name="Anisotropy",
        description="Anisotropy reflects and transmits light with a"
                    " directional bias and causes materials to appear"
                    " rougher of glossier in certain directions.",
        subtype='FACTOR',
        min=0, max=1,
        default=0.5
    )
    specular_rotation = FloatProperty(
        name="Rotation",
        description="The rotation value changes the orientation of the"
                    " anisotropic reflectance in UV space. At 0.0, there is"
                    " no rotation, while at 1.0 the effect is rotated by 180"
                    " degrees. For a surface of brushed metal, this controls"
                    " the angle at which the material was brushed.",
        subtype='FACTOR',
        min=0, max=1
    )
    Kr = FloatProperty(
        name="Scale",
        description="The contribution from reflection rays.",
        subtype='FACTOR',
        min=0, max=1
    )
    Kr_color = FloatVectorProperty(
        name="Color",
        description="The color of the reflection ray at the current point.",
        subtype='COLOR',
        default=(1, 1, 1)
    )
    reflection_exit_color = FloatVectorProperty(
        name="Color",
        description="The color returned when a ray has reached its maximum"
                    " reflection depth value.",
        subtype='COLOR',
        min=0, max=1
    )
    reflection_exit_use_environment = BoolProperty(
        name="Use Environment",
        description="Specify whether to use the environment color for"
                    " reflection rays where there was insufficient ray depth"
                    " (true), or the color specified by reflection_exit_color"
                    " (false). See above."
    )
    Kt = FloatProperty(
        name="Scale",
        description="Transparency allows light to pass through the material.",
        subtype='FACTOR',
        min=0, max=1
    )
    Kt_color = FloatVectorProperty(
        name="Color",
        description="Transparency color multiplies the refracted result by a"
                    " color. For tinted glass it is best to control the tint"
                    " colour via the Transmittance colour since it actually"
                    " filters the refraction according to the distance"
                    " traveled by the refracted ray.",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )
    transmittance = FloatVectorProperty(
        name="Transmittance",
        description="Transmittance filters the refraction according to the"
                    " distance traveled by the refracted ray. The longer light"
                    " travels inside a mesh, the more it is affected by the"
                    " Transmittance color. Therefore green glass gets a deeper"
                    " green as rays travel through thicker parts. The effect"
                    " is exponential and computed with Beer's Law. It is"
                    " recommended to use light, subtle color values.",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )
    refraction_roughness = FloatProperty(
        name="Roughness",
        description="Controls the blurriness of a refraction computed with an"
                    " 'isotropic microfacet BTDF'. The range goes from 0 (no"
                    " roughness) to 1.",
        subtype='FACTOR',
        min=0, max=1
    )
    refraction_exit_color = FloatVectorProperty(
        name="Color",
        description="The color returned when a ray has reached its maximum"
                    " refraction depth value.",
        subtype='COLOR',
        min=0, max=1
    )
    refraction_exit_use_environment = BoolProperty(
        name="Use Environment",
        description="Specify whether to use the environment color for"
                    " refraction rays where there was insufficient ray depth"
                    " (true), or the color specified by refraction_exit_color"
                    " (false)."
    )
    IOR = FloatProperty(
        name="IOR",
        description="The index of refraction used. The default value of 1.0 is"
                    " the refractive index of a vacuum, i.e., an object with"
                    " IOR of 1.0 in empty space will not refract any rays. In"
                    " simple terms, 1.0 means 'no refraction'. The Standard"
                    " shader assumes that any geometry has outward facing"
                    " normals, that objects are embedded in air (IOR 1.0) and"
                    " that there are no overlapping surfaces.",
        min=0, soft_max=3,
        default=1
    )
    dispersion_abbe = FloatProperty(
        name="Abbe Number"
    )
    Kb = FloatProperty(
        name="BackLighting",
        description="Backlight provides the effect of a translucent object"
                    " being lit from behind (the shading point is 'lit' by"
                    " the specified fraction of the light hitting the reverse"
                    " of the object at that point). This should only be used"
                    " with thin objects (single sided geometry); objects with"
                    " thickness will render incorrectly.",
        subtype='FACTOR',
        min=0, max=1
    )
    Fresnel = BoolProperty(
        name="Enable",
        description="Reflection level will be dependent on the viewing angle"
                    " of the surface following the Fresnel equations (which"
                    " depends on the IOR value). The Fresnel effect's"
                    " reflection increase as the viewer's angle of incidence"
                    " with respect to the surface approaches 0"
    )
    Krn = FloatProperty(
        name="Reflectance at Normal",
        description="The Fresnel effect is more noticeable when using lower"
                    " values. Increasing this value gives the material a more"
                    " metallic-like reflection. Metals have a more uniform"
                    " reflectance across all angles compared to plastics or"
                    " dielectrics, which have very little normal reflectance.",
        #subtype='FACTOR',
        #min=0, max=1
    )
    specular_Fresnel = BoolProperty(
        name="Enable",
        description="Specular reflection level will be dependent on the"
                    " viewing angle of the surface following the Fresnel"
                    " equations (which depends on the IOR value). The Fresnel"
                    " effect's reflection increase as the viewer's angle of"
                    " incidence with respect to the surface approaches 0."
    )
    Ksn = FloatProperty(
        name="Reflectance at Normal",
        description="The Fresnel effect is more noticeable when using lower"
                    " values. Increasing this value gives the material a more"
                    " metallic-like specular reflection. Metals have a more"
                    " uniform reflectance across all angles compared to plastics"
                    " or dielectrics, which have very little normal reflectance.",
        #subtype='FACTOR',
        #min=0, max=1
    )
    Fresnel_use_IOR = BoolProperty(
        name="Fresnel use IOR",
        description="Calculate Fresnel reflectance based on the IOR parameter,"
                    " ignoring the values set in Krn and Ksn."
    )
    Fresnel_affect_diff = BoolProperty(
        name="Fresnel Affects Diffuse",
        default=True
    )
    emission = FloatProperty(
        name="Scale",
        description="Controls the amount of emitted light. It can create"
                    " noise, especially if the source of indirect illumination"
                    " is very small (a light bulb geometry). It is generally"
                    " good practise to reduce Diffuse Weight value to 0 when"
                    " using emission."
    )
    emission_color = FloatVectorProperty(
        name="Collor",
        description="The emitted light color.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    direct_specular = FloatProperty(
        name="Direct Scale",
        description="The amount of specularity received from direct sources"
                    " only. Values other than 1.0 will cause the materials"
                    " to not preserve energy and global illumination may not"
                    " converge.",
        subtype='FACTOR',
        min=0, max=1,
        default=1
    )
    indirect_specular = FloatProperty(
        name="Indirect Scale",
        description="The amount of specularity received from indirect sources"
                    " only. Values other than 1.0 will cause the materials"
                    " to not preserve energy and global illumination may not"
                    " converge.",
        subtype='FACTOR',
        min=0, max=1,
        default=1
    )
    direct_diffuse = FloatProperty(
        name="Direct Scale",
        description="The amount of diffuse light received from direct"
                    " sources only.",
        subtype='FACTOR',
        min=0, max=1,
        default=1
    )
    indirect_diffuse = FloatProperty(
        name="Indirect Scale",
        description="The amount of diffuse light received from indirect"
                    " sources only.",
        subtype='FACTOR',
        min=0, max=1,
        default=1
    )
    enable_glossy_caustics = BoolProperty(
        name="Glossy caustics",
        description="Arnold can produce 'soft' caustics from glossy surfaces"
                    " or large sources of indirect light. This switch in the"
                    " standard shader specifies whether the diffuse GI rays"
                    " can 'see' glossy reflection rays (there are also"
                    " switches for mirror reflection and refraction rays)."
                    " By default only the direct and indirect diffuse rays"
                    " are seen by GI rays. Note that 'hard' caustics from"
                    " small but bright light sources (e.g., spot light"
                    " through a wine glass) are not currently possible."
    )
    enable_reflective_caustics = BoolProperty(
        name="Reflective caustics",
        description="Arnold can produce 'soft' caustics from glossy surfaces"
                    " or large sources of indirect light. This switch in the"
                    " standard shader specifies whether the diffuse GI rays"
                    " can 'see' mirror reflection rays (there are also"
                    " switches for glossy reflection and refraction rays)."
                    " By default only the direct and indirect diffuse rays"
                    " are seen by GI rays. Note that 'hard' caustics from"
                    " small but bright light sources (e.g., spot light"
                    " through a wine glass) are not currently possible."
    )
    enable_refractive_caustics = BoolProperty(
        name="Refractive caustics",
        description="Arnold can produce 'soft' caustics from glossy surfaces"
                    " or large sources of indirect light. This switch in the"
                    " standard shader specifies whether the diffuse GI rays"
                    " can 'see' refraction rays (there are also switches for"
                    " mirror and glossy reflection rays). By default only the"
                    " direct and indirect diffuse rays are seen by GI rays."
                    " Note that 'hard' caustics from small but bright light"
                    " sources (e.g., spot light through a wine glass) are not"
                    " currently possible."
    )
    enable_internal_reflections = BoolProperty(
        name="Internal Reflections",
        description="Unchecking internal reflections will disable indirect"
                    " specular and mirror perfect reflection computations when"
                    " ray refraction depth is bigger than zero (when there has"
                    " been at least one refraction ray traced in the current"
                    " ray tree). Scenes with high amounts of transparent and"
                    " reflective surfaces can benefit from disabling Internal"
                    " Reflections.",
        default=True
    )
    Ksss = FloatProperty(
        name="Scale",
        description="The amount of sub-surface scattering. Multiplies SSS"
                    " Color.",
        subtype='FACTOR',
        min=0, max=1
    )
    Ksss_color = FloatVectorProperty(
        name="Color",
        description="The color used to determine the suburface scattering"
                    " effect. For example, replicating a skin material, would"
                    " mean setting this to a fleshy color.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    sss_radius = FloatVectorProperty(
        name="Radius",
        description="The radius of the area each sample affects. Higher values"
                    " will smooth the appearance of the subsurface scattering."
                    " Results will vary depending on the scale of your object"
                    " in scene.",
        size=3,
        min=0, max=1,
        default=(0.1, 0.1, 0.1),
        subtype='COLOR'
    )
    bounce_factor = FloatProperty(
        name="Bounce Factor",
        description="The relative energy loss (or gain) at each bounce. This"
                    " should be left at its default value of 1.0, which is the"
                    " only value with meaningful physical sense. Values bigger"
                    " than 1.0 will make it impossible for GI algorithms to"
                    " converge to a stable solution, and values smaller than"
                    " 1.0 will have insufficient GI shading.",
        min=0, soft_max=4,
        default=1
    )
    opacity = FloatVectorProperty(
        name="Opacity",
        description="Controls the degree to which light is not allowed to"
                    " travel through it. Unlike transparency, whereby the"
                    " material still considers diffuse, specular etc, opacity"
                    " will affect the entire shader. Useful for retaining the"
                    " shadow definition of an object, whilst making the object"
                    " itself invisible to the camera.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )


@ArnoldRenderEngine.register_class
class ArnoldShaderUtility(PropertyGroup):
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
    color = FloatVectorProperty(
        name="Color",
        description="Color used as the shading mode for the model.",
        get=lambda self: self.id_data.diffuse_color,
        set=lambda self, value: setattr(self.id_data, "diffuse_color", value),
        subtype='COLOR',
        default=(1, 1, 1)
    )
    opacity = FloatProperty(
        name="Opacity",
        default=1.0
    )
    ao_distance = FloatProperty(
        name="AO Distance",
        default=100
    )


@ArnoldRenderEngine.register_class
class ArnoldShaderFlat(PropertyGroup):
    color = FloatVectorProperty(
        name="Color",
        description="The input color.",
        get=lambda self: self.id_data.diffuse_color,
        set=lambda self, value: setattr(self.id_data, "diffuse_color", value),
        subtype='COLOR',
        default=(1, 1, 1)
    )
    opacity = FloatVectorProperty(
        name="Opacity",
        description="The input opacity.",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )


@ArnoldRenderEngine.register_class
class ArnoldShaderWireframe(PropertyGroup):
    line_width = FloatProperty(
        name="Line Width",
        default=1.0
    )
    fill_color = FloatVectorProperty(
        name="Fill Color",
        get=lambda self: self.id_data.diffuse_color,
        set=lambda self, value: setattr(self.id_data, "diffuse_color"),
        default=(1, 1, 1),
        min=0, max=1,
        subtype='COLOR'
    )
    line_color = FloatVectorProperty(
        name="Line Color",
        default=(0, 0, 0),
        min=0, max=1,
        subtype='COLOR'
    )
    raster_space = BoolProperty(
        name="Raster Space",
        default=True
    )
    edge_type = EnumProperty(
        name="Color Mode",
        items=[
            ('polygons', "Polygons", "Polygons"),
            ('triangles', "Triangles", "Triangles")
        ],
        default='triangles'
    )


@ArnoldRenderEngine.register_class
class ArnoldShader(PropertyGroup):
    type = EnumProperty(
        name="Type",
        items=[
            ('lambert', "Lambert", "Lambert"),
            ('standard', "Standard", "Standard"),
            ('utility', "Utility", "Utility"),
            ('flat', "Flat", "Flat"),
            ('hair', "Hair", "Hair")
        ],
        default='lambert'
    )
    lambert = PointerProperty(type=ArnoldShaderLambert)
    standard = PointerProperty(type=ArnoldShaderStandard)
    utility = PointerProperty(type=ArnoldShaderUtility)
    flat = PointerProperty(type=ArnoldShaderFlat)
    #hair = PointerProperty(type=ArnoldShaderHair)
    wire = PointerProperty(type=ArnoldShaderWireframe)

    @classmethod
    def register(cls):
        Material.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del Material.arnold


@ArnoldRenderEngine.register_class
class ArnoldCurves(PropertyGroup):
    radius_tip = FloatProperty(
        name="Tip Radius",
        default=0.0001
    )
    radius_root = FloatProperty(
        name="Root Radius",
        default=0.001
    )
    bezier_scale = FloatProperty(
        name="Scale",
        min=0, max=1,
        default=0.5,
        subtype='FACTOR'
    )
    basis = EnumProperty(
        name="Basis",
        items=[
            ('bezier', "Bezier", "Bezier"),
            ('b-spline', "B-Spline", "B-Spline"),
            ('catmull-rom', "Catmull-Rom", "Catmull-Rom"),
            ('linear', "Linear", "Linear"),
        ],
        default='bezier'
    )
    mode = EnumProperty(
        name="Mode",
        items=[
            ('ribbon', "Ribbon", "Ribbon"),
            ('thick', "Thick", "Thick"),
            ('oriented', "Oriented", "Oriented")
        ],
        default='ribbon'
    )
    min_pixel_width = FloatProperty(
        name="Min. Pixel Width",
        min=0,
        subtype='UNSIGNED'
    )
    uvmap = StringProperty(
        name="UV Map"
    )


@ArnoldRenderEngine.register_class
class ArnoldPoints(PropertyGroup):
    mode = EnumProperty(
        name="Mode",
        items=[
            ('disk', "Disk", "Disk"),
            ('sphere', "Sphere", "Sphere"),
            ('quad', "Quad", "Quad")
        ],
        default='disk'
    )
    aspect = FloatProperty(
        name="Aspect",
        default=1.0
    )
    rotation = FloatProperty(
        name="Rotation"
    )
    min_pixel_width = FloatProperty(
        name="Min. Pixel Width",
        min=0,
        subtype='UNSIGNED'
    )
    step_size = FloatProperty(
        name="Step Size"
    )


@ArnoldRenderEngine.register_class
class ArnoldParticleSystem(PropertyGroup):
    curves = PointerProperty(type=ArnoldCurves)
    points = PointerProperty(type=ArnoldPoints)

    @classmethod
    def register(cls):
        ParticleSettings.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del ParticleSettings.arnold
