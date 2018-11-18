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
    Light,
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
    ui_sampling: BoolProperty(
        name="Sampling",
        default=True
    )
    ui_ray_depth: BoolProperty(
        name="Ray Depth"
    )
    ui_light: BoolProperty(
        name="Light"
    )
    ui_gamma: BoolProperty(
        name="Gamma Correction"
    )
    ui_textures: BoolProperty(
        name="Textures"
    )
    ui_render: BoolProperty(
        name="Render Settings",
        default=True
    )
    ui_ipr: BoolProperty(
        name="IPR",
        default=True
    )
    ui_paths: BoolProperty(
        name="Search paths"
    )
    ui_licensing: BoolProperty(
        name="Licensing"
    )

    #########################
    #TODO: FIX THESE OPTIONS:
    ui_log: BoolProperty(
        name="Log",
        default=True
    )
    ui_error: BoolProperty(
        name="Error Handling"
    )
    ui_overrides: BoolProperty(
        name="Feature overrides",
        default=True
    )
    ui_subdivisions: BoolProperty(
        name="Subdivision"
    )
    logfile: StringProperty(
        name="Filename",
        subtype='FILE_PATH',
        options=set()
    )
    logfile_flags: EnumProperty(
        name="File flags",
        items=_LOG_FLAGS,
        options={'ENUM_FLAG'}
    )
    console_log_flags: EnumProperty(
        name="Console flags",
        items=_LOG_FLAGS,
        options={'ENUM_FLAG'}
    )
    max_warnings: IntProperty(
        name="Max. Warnings",
        default=5
    )
    auto_threads: BoolProperty(
        name="Autodetect Threads",
        default=True
    )
    lock_sampling_pattern: BoolProperty(
        name="Lock Sampling Pattern"
    )
    clamp_sample_values: BoolProperty(
        name="Clamp Sample Values"
    )

    #############################

    sample_filter_type: EnumProperty(
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
            ('contour_filter', "Contour", "Contour"),
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

    ################################
    #TODO: FIX THESE OPTIONS PART 2:
    sample_filter_width: FloatProperty(
        name="Width",
        default=2
    )
    sample_filter_bh_width: FloatProperty(
        name="Width",
        default=3
    )
    sample_filter_sinc_width: FloatProperty(
        name="Width",
        default=6
    )
    sample_filter_domain: EnumProperty(
        name="Domain",
        items=[
            ('first_hit', "First Hit", "First Hit"),
            ('all_hits', "All Hits", "All Hits")
        ],
        default='first_hit'
    )
    sample_filter_min: FloatProperty(
        name="Minimum"
    )
    sample_filter_max: FloatProperty(
        name="Maximum",
        default=1.0,
    )
    sample_filter_scalar_mode: BoolProperty(
        name="Scalar Mode"
    )
    progressive_refinement: BoolProperty(
        name="Progressive Refinement",
        default=False
    )
    initial_sampling_level: IntProperty(
        name="Inital Sampling Level",
        min=-10, max=-1,
        default = -3
    )
    ipr_bucket_size: IntProperty(
        name="Bucket Size",
        min=16, soft_max=1024,
        default=64,
    )
    display_gamma: FloatProperty(
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
    AA_samples: IntProperty(
        name="Camera (AA)",
        min=0, max=100,
        soft_min=1, soft_max=10,
        default=3
    )
    #AA_seed = scene.frame_current
    AA_sample_clamp: FloatProperty(
        name="Max Value",
        soft_min=0.001, soft_max=100.0,
        default=10.0,
        options=set()
    )
    AA_sample_clamp_affects_aovs: BoolProperty(
        name="Affect AOVs",
        options=set()
    )
    threads: IntProperty(
        name="Threads",
        min=1,
        options=set(),
        subtype='UNSIGNED'
    )
    thread_priority: EnumProperty(
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
    pin_threads: EnumProperty(
        name="Pin Threads",
        items=[
            ('off', "Off", "Off"),
            ('on', "On", "Off"),
            ('auto', "Auto", "Auto")
        ],
        default='auto',
        options=set()
    )
    abort_on_error: BoolProperty(
        name="Abort on Error",
        default=True,
        options=set()
    )
    abort_on_license_fail: BoolProperty(
        name="Abort on License fail",
        options=set()
    )
    skip_license_check: BoolProperty(
        name="Skip License Check",
        options=set()
    )
    error_color_bad_texture: FloatVectorProperty(
        name="Texture Error Color",
        default=(1, 0, 0),
        min=0, max=1,
        subtype='COLOR'
    )
    error_color_bad_pixel: FloatVectorProperty(
        name="Pixel Error Color",
        default=(0, 0, 1),
        min=0, max=1,
        subtype='COLOR'
    )
    error_color_bad_shader: FloatVectorProperty(
        name="Shader Error Color",
        default=(1, 0, 1),
        min=0, max=1,
        subtype='COLOR'
    )
    bucket_size: IntProperty(
        name="Bucket Size",
        #min=16,
        #soft_max = 256,
        #default=64,
        #options=set()
        get=_get_bucket_size,
        set=_set_bucket_size
    )
    bucket_scanning: EnumProperty(
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
    ignore_textures: BoolProperty(
        name="Ignore Textures"
    )
    ignore_shaders: BoolProperty(
        name="Ignore Shaders"
    )
    ignore_atmosphere: BoolProperty(
        name="Ignore Atmosphere"
    )
    ignore_lights: BoolProperty(
        name="Ignore Lights"
    )
    ignore_shadows: BoolProperty(
        name="Ignore Shadows"
    )
    # TODO: DELETE? ignore_direct_lighting = BoolProperty(
    #     name="Ignore Direct Lighting"
    # )
    ignore_subdivision: BoolProperty(
        name="Ignore Subdivision"
    )
    ignore_displacement: BoolProperty(
        name="Ignore Displacement"
    )
    ignore_bump: BoolProperty(
        name="Ignore Bump"
    )
    ignore_motion_blur: BoolProperty(
        name="Ignore Motion Blur"
    )
    ignore_dof: BoolProperty(
        name="Ignore DOF"
    )
    ignore_smoothing: BoolProperty(
        name="Ignore Normal Smoothing"
    )
    ignore_sss: BoolProperty(
        name="Ignore SSS"
    )
    #enable_fast_opacity
    # TODO: DELETE? auto_transparency_mode = EnumProperty(
    #     name="Mode",
    #     items=[
    #         ('always', "Always", "Always"),
    #         ('shadow-only', "Shadow Only", "Shadow Only"),
    #         ('never', "Never", "Never")
    #     ],
    #     default='always'
    # )
    auto_transparency_depth: IntProperty(
        name="Depth",
        default=10
    )
    # # TODO: DELETE? auto_transparency_threshold = FloatProperty(
    #     name="Threshold",
    #     default=0.99
    # )
    texture_max_open_files: IntProperty(
        name="Max Open Files",
        default=0
    )
    texture_max_memory_MB: FloatProperty(
        name="Max Cache Size (MB)",
        default=1024
    )
    #texture_per_file_stats
    texture_searchpath: StringProperty(
        name="Texture",
        subtype='DIR_PATH'
    )
    texture_automip: BoolProperty(
        name="Auto mipmap",
        default=True
    )
    texture_autotile: IntProperty(
        name="Auto-Tile",
        default=64
    )
    texture_accept_untiled: BoolProperty(
        name="Accept Untiled",
        default=True
    )
    texture_accept_unmipped: BoolProperty(
        name="Accept Unmipped",
        default=True
    )
    #texture_failure_retries
    #texture_conservative_lookups
    texture_specular_blur: FloatProperty(
        name="Glossy Blur",
        default=0.015625
    )
    texture_diffuse_blur: FloatProperty(
        name="Diffuse Blur",
        default=0.03125
    )
    #texture_sss_blur
    #texture_max_sharpen
    #background_visibility
    #bump_multiplier
    #bump_space
    #luminaire_bias
    low_light_threshold: FloatProperty(
        name="Low Light Threshold",
        default=0.001
    )
    #shadow_terminator_fix
    #shadows_obey_light_linking
    #skip_background_atmosphere
    sss_use_autobump: BoolProperty(
        name="Use Autobump in SSS"
    )
    #reference_time
    #CCW_points
    max_subdivisions: IntProperty(
        name="Max. Subdivisions",
        default=999
    )
    procedural_searchpath: StringProperty(
        name="Procedural",
        subtype='DIR_PATH'
    )
    plugin_searchpath: StringProperty(
        name="Shader",
        subtype='DIR_PATH'
    )
    #preserve_scene_data
    #curved_motionblur
    # TODO: DELETE? texture_gamma = FloatProperty(
    #     name="Textures",
    #     default=1
    # )
    # TODO: DELETE? light_gamma = FloatProperty(
    #    name="Lights",
    #    default=1
    #)
    # TODO: DELETE? shader_gamma = FloatProperty(
    #    name="Shaders",
    #    default=1
    #)
    GI_diffuse_depth: IntProperty(
        name="Diffuse",
        default=1
    )
    GI_specular_depth: IntProperty(
        name="Specular",
        default=1
    )
    # GI_reflection_depth = IntProperty(
    #      name="Reflection",
    #      default=2
    # )
    GI_transmission_depth: IntProperty(
        name="Transmission",
        default=8
    )
    GI_volume_depth: IntProperty(
        name="Volume"
    )
    GI_total_depth: IntProperty(
        name="Total",
        default=10,
    )
    GI_diffuse_samples: IntProperty(
        name="Diffuse",
        default=2
    )
    GI_specular_samples: IntProperty(
        name="Specular",
        default=2
    )
    GI_transmission_samples: IntProperty(
        name="Transmission",
        default=2
    )
    GI_sss_samples: IntProperty(
        name="SSS",
        default=2
    )
    #GI_single_scatter_samples
    GI_volume_samples: IntProperty(
        name="Volume Indirect",
        default=2
    )
    #GI_falloff_start_dist
    #GI_falloff_stop_dist
    #enable_displacement_derivs
    #enable_threaded_procedurals
    #enable_procedural_cache
    procedural_force_expand: BoolProperty(
        name="Expand procedurals"
    )
    #parallel_node_init

    #####################################

    @classmethod
    def register(cls):
        Scene.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del Scene.arnold


@ArnoldRenderEngine.register_class
class ArnoldCamera(PropertyGroup):
    enable_dof: BoolProperty(
        name="Enable DOF"
    )
    # far_clip with plane if True or with sphere
    #plane_distance: BoolProperty(
    #    name="Plane Distance",
    #    default=True
    #)
    aperture_size: FloatProperty(
        name="Aperture: Size"
    )
    aperture_blades: IntProperty(
        name="Aperture: Blades"
    )
    aperture_rotation: FloatProperty(
        name="Aperture: Rotation"
    )
    aperture_blade_curvature: FloatProperty(
        name="Aperture: Blade Curvature"
    )
    aperture_aspect_ratio: FloatProperty(
        name="Aperture: Aspect Ratio",
        default=1
    )
    # dof flat of sphere
    #flat_field_focus: BoolProperty(
    #    name="Flat Field Focus",
    #    default=True
    #)
    shutter_start: FloatProperty(
        name="Shutter: Start"
    )
    shutter_end: FloatProperty(
        name="Shutter: Stop"
    )
    shutter_type: EnumProperty(
        name="Shutter Type",
        items=[
            ('box', "Box", "Box"),
            ('triangle', "Triangle", "Triangle"),
            #('curve', "Curve", "Curve")
        ],
        default='box'
    )
    #shutter_curve
    rolling_shutter: EnumProperty(
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
    rolling_shutter_duration: FloatProperty(
        name="Rolling Shutter: Duration"
    )
    #handedness (right, left)
    #time_samples
    exposure: FloatProperty(
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
    subdiv_type: EnumProperty(
        name="Type",
        items=[
            ('none', "None", "None"),
            ('catclark', "Catmull-Clark", "Catmull-Clark"),
            ('linear', "Linear", "Linear")
        ],
        default='none'
    )
    disp_height: FloatProperty(
        name="Height",
        default=0
    )
    # disp_map: PointerProperty(
    #     name="Displacement Map",
    #
    # )
    subdiv_iterations: IntProperty(
        name="Iterations",
        subtype='UNSIGNED',
        min=0, max=255,
        default=1
    )
    subdiv_adaptive_error: FloatProperty(
        name="Adaptive Error",
        default=0
    )
    #NODE          subdiv_dicing_camera              (null)
    subdiv_adaptive_metric: EnumProperty(
        name="Adaptive Metric",
        items=[
            ('auto', "Auto", "Auto"),
            ('edge_length', "Edge Length", "Edge Length"),
            ('flatness', "Flatness", "Flatness"),
        ],
        default='auto'
    )
    subdiv_adaptive_space: EnumProperty(
        name="Adaptive Space",
        items=_SPACE_TYPES,
        default='raster'
    )
    subdiv_uv_smoothing: EnumProperty(
        name="UV Smoothing",
        items=[
            ('pin_corners', "Pin Corners", "Pin Corners"),
            ('pin_borders', "Pin Borders", "Pin Borders"),
            ('linear', "Linear", "Linear"),
            ('smooth', "Smooth", "Smooth")
        ],
        default='pin_corners'
    )
    subdiv_smooth_derivs: BoolProperty(
        name="Smooth Tangents"
    )
    #NODE[]        disp_map                          (empty)
    #FLOAT         disp_padding                      0
    #FLOAT         disp_height                       1
    #FLOAT         disp_zero_value                   0
    #BOOL          disp_autobump                     false
    #BYTE          autobump_visibility               159
    visibility: IntProperty(
        name="Visibility",
        default=255
    )
    sidedness: IntProperty(
        name="Sidedness",
        default=255
    )
    receive_shadows: BoolProperty(
        name="Receive shadows",
        default=True
    )
    self_shadows: BoolProperty(
        name="Self shadows",
        default=True
    )
    invert_normals: BoolProperty(
        name="Invert normals"
    )
    # ray_bias (FLOAT)
    # matrix (MATRIX[]): Object.matrix_world
    # shader (NODE[]): Object.data.materials
    opaque: BoolProperty(
        name="Opaque",
        default=True
    )
    matte: BoolProperty(
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

    sidedness_camera: BoolProperty(
        name="Camera",
        **_sidedness(1)
    )
    sidedness_shadow: BoolProperty(
        name="Shadow",
        **_sidedness(1 << 1)
    )
    sidedness_reflection: BoolProperty(
        name="Reflection",
        **_sidedness(1 << 2)
    )
    sidedness_refraction: BoolProperty(
        name="Refraction",
        **_sidedness(1 << 3)
    )
    sidedness_diffuse: BoolProperty(
        name="Diffuse",
        **_sidedness(1 << 4)
    )
    sidedness_glossy: BoolProperty(
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
    ui_shadow: BoolProperty(
        name="Shadow"
    )
    ui_volume: BoolProperty(
        name="Volume"
    )
    ui_contribution: BoolProperty(
        name="Contribution"
    )
    ui_viewport: BoolProperty(
        name="Viewport",
    )
    angle: FloatProperty(
        name="Angle"
    )
    radius: FloatProperty(
        name="Radius",
        min=0, soft_max=10
    )
    lens_radius: FloatProperty(
        name="Lens Radius"
    )
    penumbra_angle: FloatProperty(
        name="Penumbra Angle"
    )
    aspect_ratio: FloatProperty(
        name="Aspect Ratio",
        default=1
    )
    resolution: IntProperty(
        name="Resolution",
        default=1000
    )
    format: EnumProperty(
        name="Format",
        items=[
            ('mirrored_ball', "Mirrored Ball", "Mirrored Ball"),
            ('angular', "Angular", "Angular"),
            ('latlong', "LatLong", "Latitude & Longitude")
        ],
        default='angular'
    )
    # Is not available for Directional, Distant or Skydome lights.
    decay_type: EnumProperty(
        name="Decay Type",
        items=[
            ('constant', "Constant", "Constant"),
            ('quadratic', "Quadratic", "Quadratic")
        ],
        default='quadratic'
    )
    quad_resolution: IntProperty(
        name="Resolution",
        default=512
    )
    filename: StringProperty(
        name="Photometry File",
        subtype='FILE_PATH'
    )
    mesh: StringProperty(
        name="Mesh"
    )
    # common parameters
    intensity: FloatProperty(
        name="Intensity",
        description="Intensity controls the brightness of light emitted by the light source by multiplying the color.",
        soft_min=0, soft_max=10,
        default=1.0
    )
    exposure: FloatProperty(
        name="Exposure",
        description="Exposure is an f-stop value which multiplies the intensity by 2 to the power of the f-stop. Increasing the exposure by 1 results in double the amount of light.",
        soft_min=0, soft_max=10
    )
    cast_shadows: BoolProperty(
        name="Cast Shadows",
        default=True
    )
    cast_volumetric_shadows: BoolProperty(
        name="Cast Volumetric Shadows",
        default=True
    )
    shadow_density: FloatProperty(
        name="Shadow Density",
        default=1.0
    )
    shadow_color: FloatVectorProperty(
        name="Shadow Color",
        size=3,
        min=0, max=1,
        subtype='COLOR'
    )
    samples: IntProperty(
        name="Samples",
        description="Controls the quality of the noise in the soft shadows."
                    " The higher the number of samples, the lower the noise,"
                    " and the longer it takes to render. The exact number of"
                    " shadow rays sent to the light is the square of this"
                    " value multiplied by the AA samples.",
        soft_min=1, max=100,
        default=1
    )
    normalize: BoolProperty(
        name="Normalize",
        default=True
    )
    affect_diffuse: BoolProperty(
        name="Emit Diffuse",
        description="Allow the light to affect a material's diffuse component.",
        default=True
    )
    affect_specular: BoolProperty(
        name="Emit Specular",
        description="Allow the light to affect a material's specular component.",
        default=True
    )
    affect_volumetrics: BoolProperty(
        name="Affect Volumetrics",
        default=True
    )
    diffuse: FloatProperty(
        name="Diffuse",
        soft_min=0, soft_max=1,
        default=1
    )
    specular: FloatProperty(
        name="Specular",
        soft_min=0, soft_max=1,
        default=1
    )
    sss: FloatProperty(
        name="SSS",
        soft_min=0, soft_max=1,
        default=1
    )
    indirect: FloatProperty(
        name="Indirect",
        soft_min=0, soft_max=1,
        default=1
    )
    max_bounces: IntProperty(
        name="Max Bounces",
        default=999
    )
    volume_samples: IntProperty(
        name="Volume Samples",
        subtype='UNSIGNED',
        default=2
    )

    volume: FloatProperty(
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
                if lamp.shape == 'SQUARE':
                    self["_type"] = 0
                    i = 8  # quad_light
                elif lamp.shape == 'RECTANGLE':
                    self["_type"] = 0
                    i = 4  # cylinder_light
                elif lamp.shape == 'ELLIPSE':
                    self["_type"] = 0
                    i = 7 # photometric_light
                else:
                    i = _t + 5 # disk_light
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

    type: EnumProperty(
        name="Type",
        description="Light Type",
        items=[
            ('point_light', "Point", "Point light", 0),
            ('distant_light', "Distant", "Distant light", 1),
            ('spot_light', "Spot", "Spot light", 2),
            ('skydome_light', "Skydome", "Skydome light", 3),
            ('cylinder_light', "Cylinder", "Cylinder light", 4),
            ('disk_light', "Disk", "Disk light", 5),
            ('mesh_light', "Mesh", "Mesh light", 6),
            ('photometric_light', "Photometric", "Photometric light", 7),
            ('quad_light', "Quad", "Quad light", 8)
        ],
        **_types()
    )

    ui_size: FloatProperty(
        name="Radius",
        get=lambda s: s.id_data.size / 2,
        set=lambda s, v: setattr(s.id_data, "size", v * 2)
    )
    ui_size_y: FloatProperty(
        name="Height",
        get=lambda s: s.id_data.size_y / 2,
        set=lambda s, v: setattr(s.id_data, "size_y", v * 2)
    )

    @classmethod
    def register(cls):
        Light.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del Light.arnold


@ArnoldRenderEngine.register_class
class ArnoldShaderLambert(PropertyGroup):
    #base = Material.diffuse_intensity
    #base_color = Material.base_color
    Kd: FloatProperty(
        name="Weight",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    Kd_color: FloatVectorProperty(
        name="Color",
        description="",
        size=3,
        subtype='COLOR',
        min=0, max=1,
        default=(1,1,1)
    )
    opacity: FloatVectorProperty(
        name="Opacity",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
@ArnoldRenderEngine.register_class
class ArnoldShaderStandardHair(PropertyGroup):
    ui_standardhair_color: BoolProperty(
        name="Color",
        default=True
    )
    ui_standardhair_specular: BoolProperty(
        name="Specular",
        default=True
    )
    ui_standardhair_tint: BoolProperty(
        name="Tint",
        default=True
    )
    ui_standardhair_diffuse: BoolProperty(
        name="Diffuse",
        default=True
    )
    ui_standardhair_emission: BoolProperty(
        name="Emission",
        default=True
    )
    ui_standardhair_advanced: BoolProperty(
        name="Advanced",
        default=False
    )
    base: FloatProperty(
        name="Base",
        description="The brightness of the hair, a multiplier for the base color.",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    base_color: FloatVectorProperty(
        name="Base Color",
        description="The base color sets how bright the surface is when lit directly with a white light source (intensity at 100%). It defines which percentage for each component of the RGB spectrum which does not get absorbed when light scatters beneath the surface. Metal normally has a black or very dark base color, however, rusty metal's need some base color. A base color map is usually required.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    melanin: FloatProperty(
        name="Melanin",
        description="The Melanin parameter is used to generate natural hair colors, by controlling the amount of melanin in hair. Colors will range from blonde around 0.2 to red and brown around 0.5, to black at 1.0.",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    melanin_redness: FloatProperty(
        name="Melanin Redness",
        description="Controls the redness of hair. Higher values increase the proportion of red pheomelanin (as found in red hair), relative to the amount of brown eumelanin.",
        subtype="FACTOR",
        min=0, max=1,
        default=0.5
    )
    melanin_randomize: FloatProperty(
        name="Melanin Randomize",
        description="Randomizes the amount of melanin in hair fibers, for variation in hair colors.",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    roughness: FloatProperty(
        name="Roughness",
        description="Controls the roughness of hair specular reflections and transmission. Lower values give sharper, brighter specular highlights while higher values give softer highlights.",
        subtype="FACTOR",
        min=0, max=1,
        default=0.2
    )
    ior: FloatProperty(
        name="IOR",
        description="Index of refraction. Each hair fiber is modeled as a dielectric cylinder, with hair reflecting off and transmitting into the fiber depending on the IOR. Lower IOR values give stronger forward scattering, and higher values give a stronger reflection. You can use IOR values outside of 1.4-1.6 to render wet hair.",
        subtype="FACTOR",
        min=0, max=3,
        default=1.55
    )
    shift: FloatProperty(
        name="Shift",
        description="The angle of scales on the hair fiber, shifting the primary and secondary specular reflections away from the perfect mirror direction. For realistic results for human hair, a small angle between 0° and 10° should be used (values for animal fur may be different). For synthetic hair, such as a nylon wig, use a shift value of 0 since the surface of the fiber is smooth.",
        subtype="FACTOR",
        min=0, max=20,
        default=3
    )
    specular_tint: FloatVectorProperty(
        name="Specular Tint",
        description="The scale of the primary specular contribution, which simply multiplies the primary specular color.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    specular2_tint: FloatVectorProperty(
        name="2nd Specular Tint",
        description="The scale of the secondary specular contribution, which simply multiplies the secondary specular tint. For realistic and clean hair, this color should be set to white to let the base color tint the reflection.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    transmission_tint: FloatVectorProperty(
        name="Transmission Tint",
        description="The scale of the transmission contribution, which simply multiplies the transmission tint. For realistic and clean hair, this color should be set to white to let the base color tint the transmission.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    diffuse: FloatProperty(
        name="Diffuse",
        description="Controls the diffuseness of hair, with 0 giving fully specular scattering, and 1 fully diffuse scattering. For typical realistic hair, no diffuse component is needed. Dirty or damaged hair might be approximated with diffuse scattering.",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    diffuse_color: FloatVectorProperty(
        name="Diffuse Color",
        description="Diffuse scattering color.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    emission: FloatProperty(
        name="Emission",
        description="The multiplier for the emission color.",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    emission_color: FloatVectorProperty(
        name="Emission Color",
        description="The multiplier for the emission color.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    opacity: FloatVectorProperty(
        name="Opacity",
        description="The opacity of the hair. This is set to full white by default, which means fully opaque hair, and for best performance, it should be left to the default.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    indirect_diffuse: FloatProperty(
        name="Indirect Diffuse",
        description="The amount of diffuse light received from indirect sources only. Values other than 1 are not physically correct.",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    indirect_specular: FloatProperty(
        name="Indirect Specular",
        description="The amount of specularity received from indirect sources only. Values other than 1 are not physically correct.",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    extra_depth: FloatProperty(
        name="Extra Depth",
        description="Adds extra Specular Ray Depth just for this shader. Blonde hair renders correctly by default, without needing to increase the GI_specular_samples first.",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    extra_samples: FloatProperty(
        name="Extra Samples",
        description="Adds additional GI samples on a per-shader basis (d'Eon BSDF Specular and Transmission (R, TT, and TRT paths).",
        subtype="FACTOR",
        min=0, max=500,
        default=0
    )
@ArnoldRenderEngine.register_class
class ArnoldShaderStandardSurface(PropertyGroup):
    ui_diffuse: BoolProperty(
        name="Diffuse",
        default=True
    )
    ui_specular: BoolProperty(
        name="Specular"
    )
    ui_reflection: BoolProperty(
        name="Reflection"
    )
    ui_refraction: BoolProperty(
        name="Refraction"
    )
    ui_sss: BoolProperty(
        name="SSS"
    )
    ui_emission: BoolProperty(
        name="Emission"
    )
    ui_coat: BoolProperty(
        name="Coat"
    )
    ui_sheen: BoolProperty(
        name="Sheen"
    )
    ui_thinfilm: BoolProperty(
        name="Thin Coat"
    )
    ui_geometry: BoolProperty(
        name="Geometry"
    )
    ui_caustics: BoolProperty(
        name="Caustics"
    )
    ui_advanced: BoolProperty(
        name="Advanced"
    )
    base: FloatProperty(
        name="Base",
        description="The base color weight",
        subtype="FACTOR",
        min=0, max=1,
        default=0.8
    )
    base_color: FloatVectorProperty(
        name="Color",
        description="The base color sets how bright the surface is when lit directly with a white light source (intensity at 100%). It defines which percentage for each component of the RGB spectrum which does not get absorbed when light scatters beneath the surface. Metal normally has a black or very dark base color, however, rusty metal's need some base color. A base color map is usually required.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    metalness: FloatProperty(
        name="Metalness",
        description="With metalness 1.0 the surface behaves like a metal, using fully specular reflection and complex fresnel.",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    # base: Material.diffuse_intensity
    # base_color: Material.diffuse_color
    diffuse_roughness: FloatProperty(
        name="Diffuse Roughness",
        description="The diffuse component follows an Oren-Nayar reflection"
                    " model with surface roughness. A value of 0.0 is"
                    " comparable to a Lambert reflection. Higher values"
                    " will result in a rougher surface look more suitable"
                    " for materials like concrete, plaster or sand.",
        subtype='FACTOR',
        min=0, max=1,
        default= 0
    )
    specular: FloatProperty(
        name="Specular",
        description="The specular weight. Influences the brightness of the specular highlight.",
        subtype='FACTOR',
        min=0, max=1,
        default=1
    )
    specular_color: FloatVectorProperty(
        name="Color",
        description="The color the specular reflection will be modulated with. Use this color to 'tint' the specular highlight. You should only use colored specular for certain metals, whereas non-metallic surfaces usually have a monochromatic specular color. Non-metallic surfaces normally do not have a colored specular.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    #specular: Material.specular_intensity
    #specular_color: Material.specular_color
    specular_roughness: FloatProperty(
        name="Roughness",
        description="Controls the glossiness of the specular reflections."
                    " The lower the value, the sharper the reflection. In the"
                    " limit, a value of 0 will give you a perfectly sharp"
                    " mirror reflection, whilst 1.0 will create reflections"
                    " that are close to a diffuse reflection.",
        subtype='FACTOR',
        min=0, max=1,
        default=0.1
    )
    specular_anisotropy: FloatProperty(
        name="Anisotropy",
        description="Anisotropy reflects and transmits light with a"
                    " directional bias and causes materials to appear"
                    " rougher of glossier in certain directions.",
        subtype='FACTOR',
        min=0, max=1,
        default=0
    )
    specular_rotation: FloatProperty(
        name="Rotation",
        description="The rotation value changes the orientation of the"
                    " anisotropic reflectance in UV space. At 0.0, there is"
                    " no rotation, while at 1.0 the effect is rotated by 180"
                    " degrees. For a surface of brushed metal, this controls"
                    " the angle at which the material was brushed.",
        subtype='FACTOR',
        min=0, max=1
    )
    transmission: FloatProperty(
        name="Weight",
        description="The contribution from reflection rays.",
        subtype='FACTOR',
        min=0, max=1
    )
    transmission_color: FloatVectorProperty(
        name="Color",
        description="The color of the reflection ray at the current point.",
        subtype='COLOR',
        default=(1, 1, 1)
    )
    # TODO: Add transmission_depth and transmission_scatter
    transmission_depth: FloatProperty(
        name="Depth",
        description="Controls the depth into the volume at which the transmission color is realized.",
        subtype='FACTOR',
        min=0, max=10
    )
    transmission_scatter: FloatVectorProperty(
        name="Scatter",
        description="Controls the color of the volume, typically for thick or large bodies of liquid.",
        subtype='COLOR',
        default=(0, 0, 0)
    )
    transmission_scatter_anisotropy: FloatProperty(
        name="Scatter Anisotropy",
        description="The directional bias, or anisotropy, of the scattering. The default value of zero gives isotropic scattering so that light is scattered evenly in all directions. Positive values bias the scattering effect forwards, in the direction of the light, while negative values bias the scattering backward, toward the light.",
        subtype='FACTOR',
        min=-0.5, max=0.5,
        default=0
    )
    transmission_dispersion: FloatProperty(
        name="Dispersion Abbe",
        description="Specifies the Abbe number of the material, which describes how much the index of refraction varies across wavelengths. For glass and diamonds, this is typically in the range of 10 to 70, with lower numbers giving more dispersion. The default value is 0, which turns off dispersion. The chromatic noise can be reduced by either increasing the global Camera (AA) samples or the Refraction samples.",
        subtype='FACTOR',
        min=0, max=100,
        default=0
    )
    transmission_color: FloatVectorProperty(
        name="Color",
        description="Transparency color multiplies the refracted result by a"
                    " color. For tinted glass it is best to control the tint"
                    " colour via the Transmittance colour since it actually"
                    " filters the refraction according to the distance"
                    " traveled by the refracted ray.",
        subtype='COLOR',
        default=(1, 1, 1)
    )
    transmission_extra_roughness: FloatProperty(
        name="Extra Roughness",
        description="Adds some additional blurriness of a refraction computed with an isotropic microfacet BTDF. The range goes from 0 (no roughness) to 1.",
        subtype='FACTOR',
        min=0, max=1,
        default=0
    )
    sss_synopsis: BoolProperty(
        name="Subsurface Scattering",
        description="Sub-Surface Scattering (SSS) simulates the effect of light entering an object and scattering beneath its surface. Not all light reflects from a surface. Some of it will penetrate below the surface of an illuminated object. There it will be absorbed by the material and scattered internally. Some of this scattered light will make its way back out of the surface and become visible to the camera. This is known as 'sub-surface scattering' or 'SSS'. SSS is necessary for the realistic rendering of materials such as marble, skin, leaves, wax, and milk. The SSS component in this shader is calculated using a brute-force raytracing method.",
        default=False
    )
    transmit_aovs: BoolProperty(
        name="Transmit AOVs",
        description="When enabled, Transmission will pass through AOVs. If the background is transparent, then the transmissive surface will become transparent so that it can be composited over another background. Light path expression AOVs will be passed through so that for example a diffuse surface seen through a transmissive surface will end up in the diffuse AOV. Other AOVs can also be passed straight through (without any opacity blending), which can be used for creating masks for example. ",
        default=False
    )
    specular_ior: FloatProperty(
        name="IOR",
        description="The IOR parameter (Index of Refraction) defines the material's Fresnel reflectivity and is by default the angular function used. Effectively the IOR will define the balance between reflections on surfaces facing the viewer and on surface edges. You can see the reflection intensity remains unchanged, but the reflection intensity on the front side changes a lot.",
        subtype='FACTOR',
        min=0, soft_max=3,
        default=1.52
    )
    subsurface: FloatProperty(
        name="Weight",
        description="The 'blend' between diffuse and subsurface scattering. When set to 1.0, there is only SSS, and when set to 0 it is only Lambert. In most cases, you want this to be 1.0 (full SSS).",
        min=0, max=1,
        subtype='FACTOR',
        default=0
    )
    subsurface_color: FloatVectorProperty(
        name="Subsurface Color",
        description="The color used to determine the subsurface scattering effect. For example, replicating a skin material would mean setting this to a fleshy color.",
        subtype='COLOR',
        default=(1, 1, 1)
    )
    subsurface_radius: FloatVectorProperty(
        name="Radius",
        description="The approximate distance up to which light can scatter below the surface, also known as “mean free path” (MFP). This parameter affects the average distance that light might propagate below the surface before scattering back out. This effect on the distance can be specified for each color component separately. Higher values will smooth the appearance of the subsurface scattering, while lower values will result in a more opaque look.",
        subtype='COLOR',
        default=(1, 1, 1)
    )
    subsurface_scale: FloatProperty(
        name="Scale",
        description="Controls the distance that the light is likely to travel under the surface before reflecting back out. It scales the scattering radius and multiplies the SSS Radius Color.",
        subtype='FACTOR',
        min=0,max=10,
        default=1
    )
    subsurface_anisotropy: FloatProperty(
        name="Anisotropy",
        description="Henyey-Greenstein Anisotropy coefficient between -1 (full back-scatter) and 1 (full forward-scatter). The default is 0 for an isotropic medium, which scatters the light evenly in all directions, giving a uniform effect. Positive values bias the scattering effect forwards, in the direction of the light, while negative values bias the scattering backward, toward the light.",
        subtype='FACTOR',
        min=-1,max=1,
        default=0
    )
    subsurface_type: StringProperty(
        name="Type",
        description="Henyey-Greenstein Anisotropy coefficient between -1 (full back-scatter) and 1 (full forward-scatter). The default is 0 for an isotropic medium, which scatters the light evenly in all directions, giving a uniform effect. Positive values bias the scattering effect forwards, in the direction of the light, while negative values bias the scattering backward, toward the light.",
        subtype='BYTE_STRING',
        default='diffusion'
    )
    thin_walled: BoolProperty(
        name="Thin Walled",
        description="Thin Walled can also provide the effect of a translucent object being lit from behind (the shading point is 'lit' by the specified fraction of the light hitting the reverse of the object at that point). It is recommended that this only be used with thin objects (single sided geometry) as objects with thickness may render incorrectly.",
        default=False
    )
    emission: FloatProperty(
        name="Weight",
        description="Controls the amount of emitted light. It can create"
                    " noise, especially if the source of indirect illumination"
                    " is very small (a light bulb geometry). It is generally"
                    " good practise to reduce Diffuse Weight value to 0 when"
                    " using emission."
    )
    emission_color: FloatVectorProperty(
        name="Color",
        description="The emitted light color.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    normal: FloatVectorProperty(
        name="Normal Camera",
        description="Connect a Normal map here (usually exported from Mudbox or ZBrush). Normal mapping works by replacing the interpolated surface normal by the one evaluated from an RGB texture, where each channel (Red, Green, Blue) correspond to the X, Y and Z coordinates of the surface normal. It can be faster than bump mapping since bump mapping requires evaluating the shader underneath at least three times.",
        size= 3,
        min=0, max=1,
        default=(0,0,0),
        subtype="XYZ"
    )
    coat: FloatProperty(
        name='Weight',
        description='This attribute is used to coat the material. It acts as a clear-coat layer on top of all other shading effects. The coating is always reflective (with the given roughness) and is assumed to be dielectric. Examples would be the clear-coat layer for car paint or the sheen layer for a skin material. For example, for an extra oily layer or wet skin. Other examples would be objects that have been laminated or a protective film over an aluminum cell phone.',
        subtype='FACTOR',
        min=0,max=1,
        default=0
    )
    coat_color: FloatVectorProperty(
        name="Color",
        description="This is the color of the coating layer's transparency.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    coat_roughness: FloatProperty(
        name='Roughness',
        description='Controls the glossiness of the specular reflections. The lower the value, the sharper the reflection. In the limit, a value of 0 will give you a perfectly sharp mirror reflection, while 1.0 will create reflections that are close to a diffuse reflection. You should connect a map here to get variation in the coat highlight.',
        subtype='FACTOR',
        min=0,max=1,
        default=0.1
    )
    coat_ior: FloatProperty(
        name='IOR',
        description="The IOR parameter (Index of Refraction) defines the material's Fresnel reflectivity and is by default the angular function used. Effectively the IOR will define the balance between reflections on surfaces facing the viewer and on surface edges. You can see the reflection intensity remains unchanged, but the reflection intensity on the front side changes a lot.",
        subtype='FACTOR',
        min=0,max=10,
        default=1.5
    )
    coat_normal: FloatVectorProperty(
        name='Normal',
        description="The Coat Normal affects the Fresnel blending of the coat over the base, so depending on the normal, the base will be more or less visible from particular angles. Uses for Coat Normal could be a bumpy coat layer over a smoother base. This could include a rain effect, a carbon fiber shader or a car paint shader where you could use different normals (using e.g. flakes) for the coat layer and base layers.",
        subtype='XYZ',
        size=3,
        min=0, max=200,
        default=(0, 0, 0)
    )
    coat_affect_color: FloatProperty(
        name='Affect Color',
        description="In the real world, when a material is coated there is a certain amount of internal reflections on the inside of the coating. This causes light to bounce onto the surface multiple times before escaping, allowing the material's color to have an enhanced effect. An example of this is varnished wood. This effect can be achieved by using Coat Affect Color.",
        subtype='FACTOR',
        min=0, max=1,
        default=0
    )
    coat_affect_roughness: FloatProperty(
        name='Affect Roughness',
        description="This causes the coating's roughness to have an effect on the underlying layer's roughness, simulating the blurring effect of being seen through the top layer.",
        subtype='FACTOR',
        min=0, max=1,
        default=0
    )
    opacity: FloatVectorProperty(
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
    caustics: BoolProperty(
        name="Caustics",
        description="This switch in the Standard Surface shader specifies whether specular or transmission bounces behind diffuse bounces are enabled or not. As caustics can be noisy, these are disabled by default.",
        default=False
    )
    internal_reflections: BoolProperty(
        name="Internal Reflections",
        description="Unchecking internal reflections will disable indirect specular and mirror perfect reflection computations when ray refraction depth is bigger than zero (when there has been at least one refraction ray traced in the current ray tree).",
        default=True
    )
    exit_to_background: BoolProperty(
        name="Exit To Background",
        description="This will cause the Standard Surface shader to trace a ray against the background/environment when the maximum GI reflection/refraction depth is met and return the color that is visible in the background/environment in that direction. When the option is disabled, the path is terminated instead and returns black when the maximum depth is reached.",
        default=False
    )
    indirect_specular: FloatProperty(
        name="Indirect Scale",
        description="The amount of specularity received from indirect sources"
                    " only. Values other than 1.0 will cause the materials"
                    " to not preserve energy and global illumination may not"
                    " converge.",
        subtype='FACTOR',
        min=0, max=1,
        default=1
    )
    indirect_diffuse: FloatProperty(
        name="Indirect Scale",
        description="The amount of diffuse light received from indirect"
                    " sources only.",
        subtype='FACTOR',
        min=0, max=1,
        default=1
    )
    thin_film_thickness: FloatProperty(
        name="Thickness",
        description="Defines the actual thickness of the film between the specified min and max thickness (0 to 2000 (soft min/max)). This affects the specular, transmission and coat components. Normally this would be something like a noise map to give some variation to the interference effect. If the thickness becomes large like 3000 [nm], the iridescence effect will disappear, which is a physically correct behavior."
                    " sources only.",
        subtype='FACTOR',
        min=0, max=2000,
        default=0
    )
    thin_film_ior: FloatProperty(
        name="IOR",
        description="The refractive index of the medium surrounding the material. Normally this is set to 1.0 for air.",
        subtype='FACTOR',
        min=0, max=3.5,
        default=1.5
    )
    sheen: FloatProperty(
        name="Weight",
        description="An energy-conserving sheen layer that can be used to approximate microfiber, cloth-like surfaces such as velvet and satin of varying roughness.",
        subtype='FACTOR',
        min=0, max=1,
        default=0
    )
    sheen_color: FloatVectorProperty(
        name="Color",
        description="The color of the fibers. Tints the color of the sheen contribution.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    sheen_roughness: FloatProperty(
        name="Roughness",
        description="Modulates how much the microfibers diverge from the surface normal direction.",
        subtype='FACTOR',
        min=0, max=1,
        default=0.3
    )

@ArnoldRenderEngine.register_class
class ArnoldShaderCarPaint(PropertyGroup):
    ui_base: BoolProperty(
        name="Base",
        default=True
    )
    ui_specular: BoolProperty(
        name="Specular"
    )
    ui_flake: BoolProperty(
        name="Transmission"
    )
    ui_coat: BoolProperty(
        name="Edge"
    )

    base: FloatProperty(
        name="Base",
        description="The primer layer color weight.",
        subtype="FACTOR",
        min=0, max=1,
        default=0.8
    )
    base_color: FloatVectorProperty(
        name="Color",
        description="The color of the primer layer.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    base_roughness: FloatProperty(
        name="Base Roughness",
        description="The primer layer follows an Oren-Nayar reflection model with surface roughness. A value of 0.0 is comparable to a Lambert reflection.",
        subtype="FACTOR",
        min=0, max=1,
        default=0.5
    )
    specular: FloatProperty(
        name="Specular",
        description="The base coat color weight.",
        subtype="FACTOR",
        min=0, max=1,
        default=1.0
    )
    specular_color: FloatVectorProperty(
        name="Color",
        description="The color the specular reflection will be modulated with. Use this color to 'tint' the specular highlight from the base coat layer.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    specular_flip_flop: FloatVectorProperty(
        name="Flip Flop",
        description="Connect a ramp shader here to modulate the specular reflection from the base coat depending on the viewing angle. This can be used to mimic a pearlescent effect.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    specular_light_facing: FloatVectorProperty(
        name="Light Facing",
        description="Modulates the base coat specular color of the area facing the light source.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    specular_falloff: FloatProperty(
        name="Falloff",
        description="The falloff rate of the light facing color of the base specular coat.",
        subtype="FACTOR",
        min=0, max=1,
        default=1.0
    )
    specular_roughness: FloatProperty(
        name="Roughness",
        description="Controls the glossiness of the specular reflections from the base coat layer.",
        subtype="FACTOR",
        min=0, max=1,
        default=0.25
    )
    specular_IOR: FloatProperty(
        name="IOR",
        description="Determines the index of refraction for the base coat.",
        subtype="FACTOR",
        min=0, max=5,
        default=1.52
    )
    transmission_color: FloatVectorProperty(
        name="Transmission Color",
        description="Simulates light attenuation due to pigments. The lower the value, the denser pigments.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    flake_color: FloatVectorProperty(
        name="Flake Color",
        description="The color the specular reflection will be modulated with. Use this color to 'tint' the specular highlight from flakes.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    flake_flip_flop: FloatVectorProperty(
        name="Flip Flop",
        description="Connect a ramp shader here to modulate the specular reflection from flakes depending on the viewing angle.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    flake_light_facing: FloatVectorProperty(
        name="Light Facing",
        description="Modulate the specular reflection color from flakes of the area facing the light source.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    flake_falloff: FloatProperty(
        name="Falloff",
        description="The falloff rate of the light facing color of flakes. The higher the value, the narrower the region.",
        subtype="FACTOR",
        min=0, max=5,
        default=1.52
    )
    flake_roughness: FloatProperty(
        name="Roughness",
        description="Controls the glossiness of the specular reflections from flakes.",
        subtype="FACTOR",
        min=0, max=5,
        default=1.52
    )
    flake_IOR: FloatProperty(
        name="IOR",
        description="Determines the index of refraction of flakes.",
        subtype="FACTOR",
        min=0, max=5,
        default=2
    )
    flake_scale: FloatProperty(
        name="Scale",
        description="Scales the flake structure up or down.",
        subtype="FACTOR",
        min=0, max=1,
        default=.001
    )
    flake_density: FloatProperty(
        name="Density",
        description="Controls the density of flakes.",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    flake_layers: IntProperty(
        name="Layers",
        description="Specify the number of flake layers.",
        subtype="FACTOR",
        min=0, max=100,
        default=1
    )
    flake_normal_randomize: FloatProperty(
        name="Normal Randomize",
        description="Randomize the orientation of flakes.",
        subtype="FACTOR",
        min=0, max=1,
        default=0.2
    )
    flake_coord_space: EnumProperty(
        name="Coordinate Space",
        description="Specifies the coordinate space used for calculating the shapes of flakes.",
        items=[
            ('World', "World", "World"),
            ('Object', "Object", "Object"),
            ('Pref', "Pref", "Pref"),
            ('UV', "UV", "UV")
        ],
        default='Pref'
    )
    pref_name: StringProperty(
        name="Perf Name",
        description="Specify the name of the reference position user-data array.",
        default="Pref"
    )
    coat: FloatProperty(
        name="Scale",
        description="This attribute is used to coat the material. It acts as a clear-coat layer on top of the base coat and primer layers.",
        subtype="FACTOR",
        min=0, max=1,
        default=1.0
    )
    coat_color: FloatVectorProperty(
        name="Color",
        description="This is the color of the coating layer's transparency.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    coat_roughness: FloatProperty(
        name="Roughness",
        description="Controls the glossiness of the specular reflections.",
        subtype="FACTOR",
        min=0, max=1,
        default=0.0
    )
    coat_IOR: FloatProperty(
        name="Coat",
        description="The IOR parameter (Index of Refraction) defines the material's Fresnel reflectivity and is by default the angular function used.",
        subtype="FACTOR",
        min=0, max=1,
        default=1.25
    )
    coat_normal: FloatVectorProperty(
        name="Normal",
        description="The Coat Normal affects the Fresnel blending of the coat over the base, so depending on the normal, the base will be more or less visible from particular angles.",
        subtype='XYZ',
        size=3,
        min=0, max=200,
        default=(0, 0, 0)
    )


@ArnoldRenderEngine.register_class
class ArnoldShaderToon(PropertyGroup):
    ui_base: BoolProperty(
        name="Base",
        default=True
    )
    ui_specular: BoolProperty(
        name="Specular"
    )
    ui_transmission: BoolProperty(
        name="Transmission"
    )
    ui_edge: BoolProperty(
        name="Edge"
    )
    ui_silhouette: BoolProperty(
        name="Silhouette"
    )
    ui_sheen: BoolProperty(
        name="Sheen"
    )
    ui_emission: BoolProperty(
        name="Emission"
    )
    ui_advanced: BoolProperty(
        name="Advanced"
    )
    base: FloatProperty(
        name="Base",
        description="The base color weight",
        subtype="FACTOR",
        min=0, max=1,
        default=0.8
    )
    base_color: FloatVectorProperty(
        name="Color",
        description="The base color sets how bright the surface is when lit directly with a white light source (intensity at 100%). It defines which percentage for each component of the RGB spectrum which does not get absorbed when light scatters beneath the surface. Metal normally has a black or very dark base color, however, rusty metal's need some base color. A base color map is usually required.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    base_tonemap: FloatVectorProperty(
        name="Tonemap Color",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )

    mask_color: FloatVectorProperty(
        name="Mask Color",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    edge_color: FloatVectorProperty(
        name="Edge Color",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    edge_tonemap: FloatVectorProperty(
        name="Edge Tonemap Color",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    edge_opacity: FloatProperty(
        name="Edge Opacity",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    edge_width_scale: FloatProperty(
        name="Edge Width Scale",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    silhouette_color: FloatVectorProperty(
        name="Silhouette Color",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    silhouette_tonemap: FloatVectorProperty(
        name="Silhouette Tonemap",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    silhouette_opacity: FloatProperty(
        name="Silhouette Opacity",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    silhouette_width_scale: FloatProperty(
        name="Silhouette Width Scale",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    priority: IntProperty(
        name="Priority",
        description="",
        subtype="FACTOR",
        min=0, max=10,
        default=0
    )
    ignore_throughput: BoolProperty(
        name="Ignore Throughput",
        description="",
        default=False
    )
    enable_silhouette: BoolProperty(
        name="Enable Silhouette",
        description="",
        default=False
    )
    enable: BoolProperty(
        name="Enable",
        description="",
        default=True
    )
    id_difference: BoolProperty(
        name="ID Difference",
        description="",
        default=True
    )
    shader_difference: BoolProperty(
        name="Shader Difference",
        description="",
        default=True
    )
    uv_threshold: FloatProperty(
        name="UV Threshold",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    angle_threshold: FloatProperty(
        name="Angle Threshold",
        description="",
        subtype="FACTOR",
        min=0, max=180,
        default=180
    )
    normal_type: StringProperty(
        name="Normal Type",
        description="",
        default='shading normal'
    )

    specular: FloatProperty(
        name="Specular Scale",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    specular_color: FloatVectorProperty(
        name="Specular Color",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    specular_roughness: FloatProperty(
        name="Specular Roughness",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=0.1
    )
    specular_tonemap: FloatVectorProperty(
        name="Specular Color",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    specular_anisotropy: FloatProperty(
        name="Specular Anisotropy",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    specular_rotation: FloatProperty(
        name="Specular Rotation",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    lights: StringProperty(
        name="Lights",
        description=""
    )
    highlight_color: FloatVectorProperty(
        name="Highlight Color",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    highlight_size: FloatProperty(
        name="Highlight Size",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=0.5
    )
    aov_highlight: IntProperty(
        name="AOV Highlight"
    )
    rim_light: EnumProperty(
        name="Rim Light",
        description="",
        items=[
            ('Distant', "Distant", "Distant Light"),
            ('Point', "Point", "Point Light"),
            ('Spot', "Spot", "Spot Light"),
            ('Photometric', "Photometric", "Photometric Light"),
            (' ', "None", "None")
        ]
    )
    rim_light_color: FloatVectorProperty(
        name="Rim Light Color",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    rim_light_width: FloatProperty(
        name="Rim Light Width",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=1
    )
    aov_rim_light: IntProperty(
        name="AOV Rim Light",
        description=""
    )


    transmission: FloatProperty(
        name="Transmission",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    transmission_color: FloatVectorProperty(
        name="Transmission Color",
        description="",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    transmission_roughness: FloatProperty(
        name="Transmission Roughness",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    transmission_anisotropy: FloatProperty(
        name="Transmission Roughness",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    transmission_rotation: FloatProperty(
        name="Transmission Roughness",
        description="",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )

    emission: FloatProperty(
        name="Weight",
        description="Controls the amount of emitted light. It can create noise, especially if the source of indirect illumination is very small (e.g. light bulb geometry).",
        subtype="FACTOR",
        min=0, max=1,
        default=0
    )
    emission_color: FloatVectorProperty(
        name="Color",
        description="The emitted light color.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )

    IOR: FloatProperty(
        name="IOR",
        description="",
        subtype="FACTOR",
        min=0, max=2,
        default=1.52
    )
    normal: FloatVectorProperty(
        name="Normal",
        subtype='XYZ',
        size=3,
        min=0, max=200,
        default=(0, 0, 0)
    )
    tangent: FloatVectorProperty(
        name="Tangent",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    indirect_diffuse: FloatProperty(
        name="Indirect Diffuse",
        description="",
        subtype="FACTOR",
        min=0, max=2,
        default=1
    )
    indirect_specular: FloatProperty(
        name="Indirect Specular",
        description="",
        subtype="FACTOR",
        min=0, max=2,
        default=1
    )
    bump_mode: EnumProperty(
        name="Bump Mode",
        description="",
        items=[
            ('diffuse', "Diffuse", "Diffuse"),
            ('specular', "Specular", "Specular"),
            ('both', "Both", "Both")
        ],
        default='both'
    )
    energy_conserving: BoolProperty(
        name="Energy Conserving",
        description="",
        default=True
    )
    user_id: IntProperty(
        name="User ID",
        description=""
    )

    sheen: FloatProperty(
        name="Weight",
        description="An energy-conserving sheen layer that can be used to approximate microfiber, cloth-like surfaces such as velvet and satin of varying roughness.",
        subtype='FACTOR',
        min=0, max=1,
        default=0
    )
    sheen_color: FloatVectorProperty(
        name="Color",
        description="The color of the fibers. Tints the color of the sheen contribution.",
        size=3,
        min=0, max=1,
        default=(1, 1, 1),
        subtype='COLOR'
    )
    sheen_roughness: FloatProperty(
        name="Roughness",
        description="Modulates how much the microfibers diverge from the surface normal direction.",
        subtype='FACTOR',
        min=0, max=1,
        default=0.3
    )


@ArnoldRenderEngine.register_class
class ArnoldShaderUtility(PropertyGroup):
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
    color: FloatVectorProperty(
        name="Color",
        description="Color used as the shading mode for the model.",
        get=lambda self: self.id_data.diffuse_color,
        set=lambda self, value: setattr(self.id_data, "diffuse_color", value),
        subtype='COLOR',
        default=(1, 1, 1)
    )
    opacity: FloatProperty(
        name="Opacity",
        default=1.0
    )
    ao_distance: FloatProperty(
        name="AO Distance",
        default=100
    )


@ArnoldRenderEngine.register_class
class ArnoldShaderFlat(PropertyGroup):
    color: FloatVectorProperty(
        name="Color",
        description="The input color.",
        get=lambda self: self.id_data.diffuse_color,
        set=lambda self, value: setattr(self.id_data, "diffuse_color", value),
        subtype='COLOR',
        default=(1, 1, 1)
    )
    opacity: FloatVectorProperty(
        name="Opacity",
        description="The input opacity.",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )

@ArnoldRenderEngine.register_class
class ArnoldShaderStandardVolume(PropertyGroup):
    ui_standardvolume_density: BoolProperty(
        name="Volume",
        default=True
    )
    ui_standardvolume_scatter: BoolProperty(
        name="Scatter",
        default=True
    )
    ui_standardvolume_transparency: BoolProperty(
        name="Volume",
        default=True
    )
    ui_standardvolume_emission: BoolProperty(
        name="Volume",
        default=True
    )
    ui_standardvolume_advanced: BoolProperty(
        name="Volume",
        default=True
    )
    density: FloatProperty(
        name="Weight",
        description="The density of the volume, with low density resulting in thin volumes and high density in thick volumes.",
        min=0, max=1,
        default=0.25
    )
    scatter: FloatProperty(
        name="Weight",
        description="The brightness of the volume under illumination.",
        min=0, max=1,
        default=1
    )
    scatter_color: FloatVectorProperty(
        name="Color",
        description="The density of the volume, with low density resulting in thin volumes and high density in thick volumes.",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )
    scatter_anisotropy: FloatProperty(
        name="Anisotropy",
        description="The directional bias, or anisotropy, of the scattering.",
        min=0, max=1,
        default=0
    )
    transparent: FloatVectorProperty(
        name="Transparent Color",
        description="Additional control over the density of the volume, to tint the color of volume shadows and objects seen through the volume.",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )
    transparent_depth: FloatProperty(
        name="Transparent Depth",
        description="Additional control over the density of the volume, to control the depth into the volume at which the transparent color is realized.",
        min=0, max=5,
        default=1
    )
    emission: FloatProperty(
        name="Weight",
        description="Emission is the rate at which a volume emits light.",
        min=0, max=5,
        default=1
    )
    emission_color: FloatVectorProperty(
        name="Color",
        description="A color to tint (multiply to) the emission.",
        subtype='COLOR',
        min=0, max=1,
        default=(1, 1, 1)
    )
    # emission_mode: FloatStringProperty(
    #     name="Mode",
    #     description="Method of volume emission",
    #     default="None"
    # )
    temperature: FloatProperty(
        name="Temperature",
        description="If a blackbody channel is used, this acts as a multiplier for the blackbody temperature.",
        min=0,max=1,
        default=1
    )


@ArnoldRenderEngine.register_class
class ArnoldShaderWireframe(PropertyGroup):
    line_width: FloatProperty(
        name="Line Width",
        default=1.0
    )
    fill_color: FloatVectorProperty(
        name="Fill Color",
        get=lambda self: self.id_data.diffuse_color,
        set=lambda self, value: setattr(self.id_data, "diffuse_color"),
        default=(1, 1, 1),
        min=0, max=1,
        subtype='COLOR'
    )
    line_color: FloatVectorProperty(
        name="Line Color",
        default=(0, 0, 0),
        min=0, max=1,
        subtype='COLOR'
    )
    raster_space: BoolProperty(
        name="Raster Space",
        default=True
    )
    edge_type: EnumProperty(
        name="Color Mode",
        items=[
            ('polygons', "Polygons", "Polygons"),
            ('triangles', "Triangles", "Triangles")
        ],
        default='triangles'
    )


@ArnoldRenderEngine.register_class
class ArnoldShader(PropertyGroup):
    type: EnumProperty(
        name="Type",
        items=[
            ('lambert', "Lambert", "Lambert"),
            ('standard_surface', "Standard Surface", "Standard Surface"),
            ('toon', "Toon", "Toon"),
            ('utility', "Utility", "Utility"),
            ('flat', "Flat", "Flat"),
            ('standard_hair', "Standard Hair", "Standard Hair")
        ],
        default='lambert'
    )
    lambert: PointerProperty(type=ArnoldShaderLambert)
    standard_surface: PointerProperty(type=ArnoldShaderStandardSurface)
    toon: PointerProperty(type=ArnoldShaderToon)
    utility: PointerProperty(type=ArnoldShaderUtility)
    flat: PointerProperty(type=ArnoldShaderFlat)
    standard_hair: PointerProperty(type=ArnoldShaderStandardHair)
    wire: PointerProperty(type=ArnoldShaderWireframe)
    standard_volume: PointerProperty(type=ArnoldShaderStandardVolume)

    @classmethod
    def register(cls):
        Material.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del Material.arnold


@ArnoldRenderEngine.register_class
class ArnoldCurves(PropertyGroup):
    radius_tip: FloatProperty(
        name="Tip Radius",
        default=0.0001
    )
    radius_root: FloatProperty(
        name="Root Radius",
        default=0.001
    )
    bezier_scale: FloatProperty(
        name="Weight",
        min=0, max=1,
        default=0.5,
        subtype='FACTOR'
    )
    basis: EnumProperty(
        name="Basis",
        items=[
            ('bezier', "Bezier", "Bezier"),
            ('b-spline', "B-Spline", "B-Spline"),
            ('catmull-rom', "Catmull-Rom", "Catmull-Rom"),
            ('linear', "Linear", "Linear"),
        ],
        default='bezier'
    )
    mode: EnumProperty(
        name="Mode",
        items=[
            ('ribbon', "Ribbon", "Ribbon"),
            ('thick', "Thick", "Thick"),
            ('oriented', "Oriented", "Oriented")
        ],
        default='ribbon'
    )
    min_pixel_width: FloatProperty(
        name="Min. Pixel Width",
        min=0,
        subtype='UNSIGNED'
    )
    uvmap: StringProperty(
        name="UV Map"
    )


@ArnoldRenderEngine.register_class
class ArnoldPoints(PropertyGroup):
    mode: EnumProperty(
        name="Mode",
        items=[
            ('disk', "Disk", "Disk"),
            ('sphere', "Sphere", "Sphere"),
            ('quad', "Quad", "Quad")
        ],
        default='disk'
    )
    aspect: FloatProperty(
        name="Aspect",
        default=1.0
    )
    rotation: FloatProperty(
        name="Rotation"
    )
    min_pixel_width: FloatProperty(
        name="Min. Pixel Width",
        min=0,
        subtype='UNSIGNED'
    )
    step_size: FloatProperty(
        name="Step Size"
    )


@ArnoldRenderEngine.register_class
class ArnoldParticleSystem(PropertyGroup):
    curves: PointerProperty(type=ArnoldCurves)
    points: PointerProperty(type=ArnoldPoints)

    @classmethod
    def register(cls):
        ParticleSettings.arnold = PointerProperty(type=cls)

    @classmethod
    def unregister(cls):
        del ParticleSettings.arnold
