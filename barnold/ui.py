# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import bpy

from bpy_extras.node_utils import find_node_input
from bl_operators.presets import PresetMenu

from bpy.types import (
    UIList,
    UI_UL_list,
    Panel,
    Menu,
    Operator,
)

import barnold.engine as engine
import barnold.nodes as nodes
from . import ArnoldRenderEngine

# icons
import os
from . icons.icons import load_icons


from bpy.props import (PointerProperty, StringProperty, BoolProperty,
                       EnumProperty, IntProperty, FloatProperty, FloatVectorProperty,
                       CollectionProperty)


def get_addon_prefs():
    addon = bpy.context.user_preferences.addons[__name__.split('.')[0]]
    return addon.preferences
# ------- Subclassed Panel Types -------
class _ArnoldPanelHeader():

    def draw_header(self, context):
        if get_addon_prefs().draw_panel_icon:
            icons = load_icons()
            arnold_blender = icons.get("arnold_logo")
            self.layout.label(text="", icon_value=arnold_blender.icon_id)
        else:
            pass

class CollectionPanel(_ArnoldPanelHeader):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine == ArnoldRenderEngine.bl_idname

    def _draw_collection(self, context, layout, ptr, name, operator,
                         opcontext, prop_coll, collection_index, default_name=''):
        layout.label(name)
        row = layout.row()
        row.template_list("UI_UL_list", "ARNOLD", ptr, prop_coll, ptr,
                          collection_index, rows=1)
        col = row.column(align=True)

        op = col.operator(operator, icon="ZOOMIN", text="")
        op.context = opcontext
        op.collection = prop_coll
        op.collection_index = collection_index
        op.defaultname = default_name
        op.action = 'ADD'

        op = col.operator(operator, icon="ZOOMOUT", text="")
        op.context = opcontext
        op.collection = prop_coll
        op.collection_index = collection_index
        op.action = 'REMOVE'

        if hasattr(ptr, prop_coll) and len(getattr(ptr, prop_coll)) > 0 and \
                getattr(ptr, collection_index) >= 0:
            item = getattr(ptr, prop_coll)[getattr(ptr, collection_index)]
            self.draw_item(layout, context, item)

class ArnoldButtonsPanel(_ArnoldPanelHeader):
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}

    @classmethod
    def poll(cls, context):
        return context.engine in cls.COMPAT_ENGINES


@ArnoldRenderEngine.register_class
class ArnoldLightFiltersUIList(UIList):
    bl_idname = "ARNOLD_UL_light_filters"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        layout.prop(item, "name", text="", icon_value=icon, emboss=False)

    def filter_items(self, context, data, propname):
        inputs = getattr(data, propname)
        if self.filter_name:
            flags = UI_UL_list.filter_items_by_name(self.filter_name, self.bitflag_filter_item, inputs, "name")
        else:
            flags = [self.bitflag_filter_item] * len(inputs)
        for i, input in enumerate(inputs):
            if input.bl_idname != "ArnoldNodeSocketFilter":
                if self.use_filter_invert:
                    flags[i] |= self.bitflag_filter_item
                else:
                    flags[i] &= ~self.bitflag_filter_item
        if self.use_filter_sort_alpha:
            order = UI_UL_list.sort_items_by_name(inputs, "name")
        else:
            order = []
        return flags, order


def _subpanel(layout, title, opened, path, attr, ctx):
    col = layout.column(align=True)
    box = col.box()
    row = box.row()
    row.alignment = 'LEFT'
    icon = 'TRIA_DOWN' if opened else 'TRIA_RIGHT'
    op = row.operator("barnold.ui_toggle", text=title, icon=icon, emboss=False)
    op.path = path
    op.attr = attr
    op.ctx = ctx
    return col.box() if opened else None

def _nodesubpanel(layout, title, opened, attr, ctx):
    col = layout.column(align=True)
    box = col.box()
    row = box.row()
    row.alignment = 'LEFT'
    icon = 'TRIA_DOWN' if opened else 'TRIA_RIGHT'
    op = row.operator("barnold.ui_toggle", text=title, icon=icon, emboss=True)
    op.attr = attr
    op.ctx = ctx
    return col.box() if opened else None

##
## Options
##

from bl_ui.properties_render import RenderButtonsPanel


@ArnoldRenderEngine.register_class
class ArnoldRenderMainPanel(ArnoldButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = " Arnold Render Settings"

    def draw(self, context):
        layout = self.layout
        opts = context.scene.arnold
        opts_path = opts.path_from_id()
        icons = load_icons()

        # Render
        row = layout.row(align=True)
        arnold_blender = icons.get("arnold_logo")
        row.operator("render.render", text="Render",
                     icon='RENDER_STILL')
        # Render Animation
        arnold_blender = icons.get("arnold_logo")
        row.operator("render.render", text="Render Animation",
                     icon='RENDER_ANIMATION').animation = True
        # Playback Animation
        arnold_blender = icons.get("arnold_logo")
        row.operator("render.play_rendered_anim", text="Playback Animation",
                     icon='FILE_MOVIE')

        layout.separator()

        split = layout.split(factor=-0.22)

        # sublayout = _subpanel(layout, "Sampling", opts.ui_sampling, opts_path, "ui_sampling", "scene")
        # if sublayout:
        arnold_blender = icons.get("arnold_logo")
        #layout.template_icon(icon_value=arnold_blender.icon_id, scale=5.0)
        layout.separator()
        col = layout.column()
        row = col.row()
        row = split.row(align=True)
        row.alignment = 'LEFT'
        row.label(text="Sampling", icon='OUTLINER_DATA_CAMERA')
        col = layout.column()
        row = col.row()
        row.alignment = 'RIGHT'
        row.label(text="Camera (AA)")
        row.prop(opts, "AA_samples", text="")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Diffuse")
        row.prop(opts, "GI_diffuse_samples", text="")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Specular")
        row.prop(opts, "GI_specular_samples", text="")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Transmission")
        row.prop(opts, "GI_transmission_samples", text="")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="SSS")
        row.prop(opts, "GI_sss_samples", text="")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Volume Indirect")
        row.prop(opts, "GI_volume_samples", text="")
        row = col.row(align=True)
        row = col.row(align=True)
        
        layout.separator()
        col = layout.column()
        row = col.row()
        row = split.row(align=True)
        col = layout.column()
        row = col.row()

        row.alignment = 'RIGHT'
        row.prop(opts, "lock_sampling_pattern")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.prop(opts, "sss_use_autobump")
        row = col.row(align=True)

        layout.separator()
        col.separator()
        col.label(text="Clamping", icon='OUTLINER_OB_CAMERA')
        col = layout.column()
        row = col.row()
        row.alignment = 'RIGHT'
        row.prop(opts, "clamp_sample_values")
        row = col.row(align=True)
        
        subcol = col.row()
        subcol.alignment = 'RIGHT'
        subcol.enabled = opts.clamp_sample_values
        # subcol = col.row(align=True)
        subcol.separator()
        subcol.alignment = 'RIGHT'
        subcol.prop(opts, "AA_sample_clamp_affects_aovs")
        subcol.separator()
        #subcol = col.column(align=True)
        subcol.alignment = 'RIGHT'
        subcol.prop(opts, "AA_sample_clamp")
        #subcol = col.column(align=True)

        col.separator()
        col.label(text="Filter", icon='FILTER')
        col = layout.column()
        row = col.row()
        row.alignment = 'RIGHT'
        row.label(text="Type")
        row.prop(opts, "sample_filter_type", text="")
        sft = opts.sample_filter_type
        if sft == 'blackman_harris_filter':
            row.prop(opts, "sample_filter_bh_width")
        elif sft == 'sinc_filter':
            row.prop(opts, "sample_filter_sinc_width")
        elif sft in ('cone_filter',
                     'cook_filter',
                     'disk_filter',
                     'gaussian_filter',
                     'triangle_filter',
                     'contour_filter'):
            row.prop(opts, "sample_filter_width")
        elif sft == 'farthest_filter':
            row.prop(opts, "sample_filter_domain")
        elif sft == 'heatmap_filter':
            row = col.row(align=True)
            row.prop(opts, "sample_filter_min")
            row.prop(opts, "sample_filter_max")
        elif sft == 'variance_filter':
            row.prop(opts, "sample_filter_width")
            row.prop(opts, "sample_filter_scalar_mode")
            row.prop(opts, 'sample_filter_weights')
        elif sft == 'cryptomatte_filter':
            row.prop(opts, "sample_filter_width")
            row.prop(opts, "sample_filter_rank")
            row.prop(opts, "cryptomatte_filter")
        elif sft == 'denoise_optix_filter':
            row.prop(opts, "optix_blend")
        elif sft == 'diff_filter':
            row.prop(opts, "sample_filter_width")
            row.prop(opts, 'sample_filter_weights')


        col.separator()
        col.label(text="AOV Browser", icon='IMAGE_ZDEPTH')
        col = layout.column()
        row = col.row()
        row.alignment = 'RIGHT'
        row.label(text="AOV Pass")
        row.prop(opts, "aov_pass", text="")

        col.separator()
        layout.separator()
        col = layout.column()
        row = col.row()
        row = col.row(align=True)
        row.alignment = 'LEFT'
        row.label(text="Ray Depth", icon='CAMERA_STEREO')
        col = layout.column()
        row = col.row()
        row.alignment = 'RIGHT'
            
        #sublayout = _subpanel(layout, "Ray Depth", opts.ui_ray_depth, opts_path, "ui_ray_depth", "scene")
        #if sublayout:
        #col = sublayout.column()
        row.label(text="Total")
        row.prop(opts, "GI_total_depth", text="")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Diffuse")
        row.prop(opts, "GI_diffuse_depth", text="")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Specular")
        row.prop(opts, "GI_specular_depth", text="")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Transmission")
        # TODO: DELETE? col.prop(opts, "GI_reflection_depth")
        row.prop(opts, "GI_transmission_depth", text="")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Volume")
        row.prop(opts, "GI_volume_depth", text="")
        row = col.row(align=True)
        
        col.separator()
        layout.separator()
        col = layout.column()
        row = col.row()
        row = col.row(align=True)

        row.alignment = 'RIGHT'
        row.label(text="Transparency Depth")
        row.prop(opts, "auto_transparency_depth", text="")
        row = col.row(align=True)

        col.separator()
        layout.separator()
        col = layout.column()
        row = col.row()
        row = col.row(align=True)
        row.alignment = 'LEFT'
        row.label(text="Light", icon='LIGHT')
        col = layout.column()
        row = col.row()
        row.alignment = 'RIGHT'
        row.label(text="Low Light Threshold")
        row.prop(opts, "low_light_threshold", text="")
        row = col.row(align=True)

        # sublayout = _subpanel(layout, "Textures", opts.ui_textures, opts_path, "ui_textures", "scene")
        # if sublayout:
        col.separator()
        layout.separator()
        col = layout.column()
        row = col.row()
        row = col.row(align=True)
        row.alignment = 'LEFT'
        row.label(text="Textures", icon='TEXTURE_DATA')
        col = layout.column()
        row = col.row()
        row.alignment = 'RIGHT'
        row.prop(opts, "texture_automip")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.prop(opts, "texture_accept_unmipped")
        row = col.row(align=True)
        col.separator()
        row.alignment = 'RIGHT'
        row.prop(opts, "texture_accept_untiled")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Auto-Tile")
        row.prop(opts, "texture_autotile", text="")
        row = col.row(align=True)
        col.separator()
        row.alignment = 'RIGHT'
        row.label(text="Max Cache Size (MB)")
        row.prop(opts, "texture_max_memory_MB", text="")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Max Open Files")
        row.prop(opts, "texture_max_open_files", text="")
        row = col.row(align=True)
        col.separator()
        row.alignment = 'RIGHT'
        row.label(text="Diffuse Blur")
        row.prop(opts, "texture_diffuse_blur", text="")
        row = col.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Specular Blur")
        row.prop(opts, "texture_specular_blur", text="")


@ArnoldRenderEngine.register_class
class ArnoldRenderSystemPanel(ArnoldButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = " Arnold System Settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        opts = context.scene.arnold
        opts_path = opts.path_from_id()

        sublayout = _subpanel(layout, "Render Settings", opts.ui_render, opts_path, "ui_render", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "bucket_scanning")
            col.prop(opts, "bucket_size")
            # overscan
            col.separator()
            col.prop(opts, "auto_threads")
            subcol = col.column()
            subcol.prop(opts, "threads")
            subcol.enabled = not opts.auto_threads
            col.prop(opts, "thread_priority")
            col.prop(opts, "pin_threads")
            col.separator()
            col.prop(opts, "procedural_force_expand")

        sublayout = _subpanel(layout, "IPR", opts.ui_ipr, opts_path, "ui_ipr", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "progressive_refinement")
            col.prop(opts, "initial_sampling_level")
            col.label(text="Viewport Rendering", icon='SETTINGS')
            col.prop(opts, "ipr_bucket_size")

        sublayout = _subpanel(layout, "Search paths", opts.ui_paths, opts_path, "ui_paths", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "procedural_searchpath")
            col.prop(opts, "plugin_searchpath")
            col.prop(opts, "texture_searchpath")

        sublayout = _subpanel(layout, "Licensing", opts.ui_licensing, opts_path, "ui_licensing", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "abort_on_license_fail")
            col.prop(opts, "skip_license_check")


@ArnoldRenderEngine.register_class
class ArnoldRenderDiagnosticsPanel(ArnoldButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = " Arnold Diagnostic Settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        opts = context.scene.arnold
        opts_path = opts.path_from_id()

        sublayout = _subpanel(layout, "Log", opts.ui_log, opts_path, "ui_log", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "logfile")
            row = col.row()
            row.prop_menu_enum(opts, "logfile_flags", text="File Flags (%X)" % opts.get("logfile_flags", 0))
            row.prop_menu_enum(opts, "console_log_flags", text="Console Flags (%X)" % opts.get("console_log_flags", 0))
            col.prop(opts, "max_warnings")

        sublayout = _subpanel(layout, "Error Handling", opts.ui_error, opts_path, "ui_error", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "abort_on_error")
            col.separator()
            col.prop(opts, "error_color_bad_texture")
            col.prop(opts, "error_color_bad_shader")
            col.prop(opts, "error_color_bad_pixel")


@ArnoldRenderEngine.register_class
class ArnoldRenderOverridePanel(ArnoldButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = " Arnold Override Settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        opts = context.scene.arnold
        opts_path = opts.path_from_id()

        sublayout = _subpanel(layout, "Feature overrides", opts.ui_overrides, opts_path, "ui_overrides", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "ignore_textures")
            col.prop(opts, "ignore_shaders")
            col.prop(opts, "ignore_atmosphere")
            col.prop(opts, "ignore_lights")
            col.prop(opts, "ignore_shadows")
            col.prop(opts, "ignore_shadows")
            #TODO: DELETE? col.prop(opts, "ignore_direct_lighting")
            col.prop(opts, "ignore_subdivision")
            col.prop(opts, "ignore_displacement")
            col.prop(opts, "ignore_bump")
            col.prop(opts, "ignore_smoothing")
            col.prop(opts, "ignore_motion_blur")
            col.prop(opts, "ignore_dof")
            col.prop(opts, "ignore_sss")

        sublayout = _subpanel(layout, "Subdivision", opts.ui_subdivisions, opts_path, "ui_subdivisions", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "max_subdivisions")

##
## Camera
##

from bl_ui.properties_data_camera import CameraButtonsPanel


@ArnoldRenderEngine.register_class
class ArnoldCameraPanel(CameraButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Camera"

    def draw(self, context):
        layout = self.layout

        camera = context.camera
        props = camera.arnold

        layout.prop(props, "exposure")

        col = layout.column()
        col.prop(props, "rolling_shutter")
        col.prop(props, "rolling_shutter_duration")

        col = layout.column()
        col.prop(props, "enable_dof")
        subcol = col.column()
        subcol.enabled = props.enable_dof
        subcol.prop(props, "aperture_size")
        subcol.prop(props, "aperture_blades")
        subcol.prop(props, "aperture_blade_curvature")
        subcol.prop(props, "aperture_rotation")
        subcol.prop(props, "aperture_aspect_ratio")

        col = layout.column()
        col.prop(props, "shutter_start")
        col.prop(props, "shutter_end")
        col.prop(props, "shutter_type")

##
## Object
##

from bl_ui.properties_object import ObjectButtonsPanel


class _ObjectPanel(ObjectButtonsPanel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}

    @classmethod
    def poll(cls, context):
        return (
            context.scene.render.engine in cls.COMPAT_ENGINES and
            context.object.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT')
        )


@ArnoldRenderEngine.register_class
class ArnoldObjectPanel(_ObjectPanel, Panel):
    bl_label = "Arnold Parameters"

    def draw(self, context):
        layout = self.layout
        props = context.object.arnold

        flow = layout.column_flow()
        flow.prop(props, "receive_shadows")
        flow.prop(props, "self_shadows")
        flow.prop(props, "invert_normals")
        flow.prop(props, "opaque")
        flow.prop(props, "matte")

        col = layout.column()
        col.label(text="Visibility:")
        flow = col.column_flow()
        flow.prop(props, "visibility_camera")
        flow.prop(props, "visibility_shadow")
        flow.prop(props, "visibility_reflection")
        flow.prop(props, "visibility_refraction")
        flow.prop(props, "visibility_diffuse")
        flow.prop(props, "visibility_glossy")

        col = layout.column()
        col.label(text="Double-sided:")
        flow = col.column_flow()
        flow.prop(props, "sidedness_camera")
        flow.prop(props, "sidedness_shadow")
        flow.prop(props, "sidedness_reflection")
        flow.prop(props, "sidedness_refraction")
        flow.prop(props, "sidedness_diffuse")
        flow.prop(props, "sidedness_glossy")


@ArnoldRenderEngine.register_class
class ArnoldSubdivisionPanel(_ObjectPanel, Panel):
    bl_label = "Arnold Subdivision"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.object.arnold

        layout.prop(props, "subdiv_type", expand=True)
        col = layout.column()
        col.enabled = props.subdiv_type != 'none'
        col.prop(props, "subdiv_iterations")
        col.prop(props, "subdiv_adaptive_error")
        col.prop(props, "subdiv_adaptive_metric")
        col.prop(props, "subdiv_adaptive_space")
        col.prop(props, "subdiv_uv_smoothing")
        col.prop(props, "subdiv_smooth_derivs")

@ArnoldRenderEngine.register_class
class ArnoldDisplacementPanel(_ObjectPanel, Panel):
    bl_label = "Arnold Displacement"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.object.arnold

        col = layout.column()
        col.prop(props, "disp_height")
        #col.prop(props, "disp_map")

##
## Lights
##

from bl_ui.properties_data_light import DataButtonsPanel as LightButtonsPanel


@ArnoldRenderEngine.register_class
class ArnoldLightPanel(LightButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Light"

    def draw(self, context):
        layout = self.layout

        lamp = context.light
        lamp_type = lamp.type

        light = lamp.arnold
        light_type = light.type
        path_from_id = light.path_from_id()

        layout.prop(lamp, "type", expand=True)
        #layout.prop(lamp, "type")

        col = layout.column()
        col.prop(lamp, "color")
        col.prop(light, "intensity")
        col.prop(light, "exposure")

        col = layout.column()
        if lamp_type not in ('SUN', 'HEMI') and light_type != 'photometric_light':
            col.prop(light, "decay_type")
        col.prop(light, "affect_diffuse")
        col.prop(light, "affect_specular")

        # ob = LightButtonsPanel['DATA_PT_area']

        # col=layout.column()
        # if lamp_type == 'AREA':
        #     layout.prop(ob, "area_shape", text="New Location")

        # Area
        col = layout.column()
        if lamp_type in ('POINT', 'SPOT'):
            col.prop(light, "radius")
            col.prop(light, "samples")
            col.prop(light, "normalize")
        elif lamp_type == 'SUN':
            col.prop(light, "angle")
            col.prop(light, "samples")
            col.prop(light, "normalize")
        elif lamp_type == 'HEMI':
            col.prop(light, "samples")
            col.prop(light, "resolution")
            col.prop(light, "format")
        else:
            if light_type == 'cylinder_light':
                col.prop(light, "samples")
                col.prop(light, "ui_size", text="Radius")
                col.prop(light, "ui_size_y", text="Height")
                col.prop(light, "normalize")
            elif light_type == 'disk_light':
                col.prop(light, "samples")
                col.prop(light, "ui_size", text="Radius")
                col.prop(light, "normalize")
            elif light_type == 'quad_light':
                col.prop(light, "samples")
                col.prop(lamp, "shape", expand=True)
                sub = col.row(align=True)
                if lamp.shape == 'SQUARE':
                    sub.prop(lamp, "size")
                elif lamp.shape == 'RECTANGLE':
                    sub.prop(lamp, "size", text="Size X")
                    sub.prop(lamp, "size_y", text="Size Y")
                col.prop(light, "quad_resolution")
                col.prop(light, "normalize")
            elif light_type == 'photometric_light':
                col.prop(light, "filename")
                col.prop(light, "samples")
                col.prop(light, "normalize")
            elif light_type == 'mesh_light':
                col.prop_search(light, "mesh", context.scene, "objects", text="", icon='OUTLINER_OB_MESH')
                col.prop(light, "samples")
                col.prop(light, "normalize")

        # Geometry
        if lamp_type == 'SPOT':
            col = layout.column()
            col.prop(light, "aspect_ratio")
            col.prop(light, "lens_radius")
            col.prop(lamp, "spot_size", text="Cone Ange")
            col.prop(light, "penumbra_angle")

        sublayout = _subpanel(layout, "Shadow", light.ui_shadow,
                              path_from_id, "ui_shadow", "light")
        if sublayout:
            col = sublayout.column()
            col.prop(light, "cast_shadows")
            col.prop(light, "shadow_color")
            col.prop(light, "shadow_density")

        sublayout = _subpanel(layout, "Volume", light.ui_volume,
                              path_from_id, "ui_volume", "light")
        if sublayout:
            col = sublayout.column()
            col.prop(light, "affect_volumetrics")
            col.prop(light, "cast_volumetric_shadows")
            col.prop(light, "volume_samples")

        sublayout = _subpanel(layout, "Contribution", light.ui_contribution,
                              path_from_id, "ui_contribution", "light")
        if sublayout:
            col = sublayout.column()
            col.prop(light, "diffuse")
            col.prop(light, "specular")
            col.prop(light, "sss")
            col.prop(light, "indirect")
            col.prop(light, "volume")
            col.prop(light, "max_bounces")

        if lamp_type == 'SPOT':
            sublayout = _subpanel(layout, "Viewport", light.ui_viewport,
                                  path_from_id, "ui_viewport", "light")
            if sublayout:
                col = sublayout.column()
                col.prop(lamp, "distance")
                col.prop(lamp, "spot_blend")
                col.prop(lamp, "use_square")
                col.prop(lamp, "show_cone")

##
## Shaders
##

#from bl_ui.properties_material import
# def panel_node_draw(layout, id_data, output_type, input_name):
#     if not id_data.use_nodes:
#         layout.operator("barnold.use_shading_nodes", icon='NODETREE')
#         return False
#
#     ntree = id_data.node_tree
#
#     node = ntree.get_output_node(ArnoldRenderEngine.bl_idname)
#     if node:
#         input = find_node_input(node, input_name)
#         if input:
#             layout.template_node_view(ntree, node, input)
#         else:
#             layout.label(text="Incompatible output node")
#     else:
#         layout.label(text="No output node")
#
#     return True
@ArnoldRenderEngine.register_class
class Arnold_PT_context_material(ArnoldButtonsPanel, Panel):
    bl_label = ""
    bl_context = "material"
    bl_options = {'HIDE_HEADER'}

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type == 'GPENCIL':
            return False
        else:
            return (context.material or context.object) and ArnoldButtonsPanel.poll(context)

    def draw(self, context):
        layout = self.layout

        mat = context.material
        ob = context.object
        slot = context.material_slot
        space = context.space_data

        if ob:
            is_sortable = len(ob.material_slots) > 1
            rows = 1
            if (is_sortable):
                rows = 4

            row = layout.row()

            row.template_list("MATERIAL_UL_matslots", "", ob, "material_slots", ob, "active_material_index", rows=rows)

            col = row.column(align=True)
            col.operator("object.material_slot_add", icon='ADD', text="")
            col.operator("object.material_slot_remove", icon='REMOVE', text="")

            col.menu("MATERIAL_MT_specials", icon='DOWNARROW_HLT', text="")

            if is_sortable:
                col.separator()

                col.operator("object.material_slot_move", icon='TRIA_UP', text="").direction = 'UP'
                col.operator("object.material_slot_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

            if ob.mode == 'EDIT':
                row = layout.row(align=True)
                row.operator("object.material_slot_assign", text="Assign")
                row.operator("object.material_slot_select", text="Select")
                row.operator("object.material_slot_deselect", text="Deselect")

        split = layout.split(factor=0.65)

        if ob:
            split.template_ID(ob, "active_material", new="material.new")
            row = split.row()

            if slot:
                row.prop(slot, "link", text="")
            else:
                row.label()
        elif mat:
            split.template_ID(space, "pin_id")
            split.separator()


@ArnoldRenderEngine.register_class
class ArnoldShaderPanel(ArnoldButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Shader"
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        return context.material and ArnoldButtonsPanel.poll(context)

    def draw(self, context):
        layout = self.layout
        mat = context.material
        shader = mat.arnold

        if mat and not nodes.is_arnold_nodetree(mat):
            # layout.operator(
            #     'shading.add_renderman_nodetree').idtype = "material"
            layout.operator('barnold.convert_cycles')

        mat_type = mat
        if shader.type == 'lambert' or shader.type == 'standard_surface' or shader.type == 'toon' or shader.type == 'utility' or shader.type == 'flat':
            shader_type = shader.type
            layout.prop(shader, "type", expand=True)
            if shader_type == 'lambert':
                lambert = shader.lambert
                col = layout.column()
                col.prop(lambert, "Kd", text="Weight")
                col.prop(mat, "diffuse_color", text="Color")
                col.prop(lambert, "opacity")
            elif shader_type == 'standard_surface':
                standard_surface = shader.standard_surface
                path_from_id = standard_surface.path_from_id()

                # Base
                sublayout = _subpanel(layout, "Base", standard_surface.ui_diffuse,
                                      path_from_id, "ui_diffuse", "material")
                if sublayout:
                    col = sublayout.column()
                    #TODO: Fix For Viewport
                    col.prop(standard_surface, "base")
                    col.prop(standard_surface, "base_color")
                    col.prop(standard_surface, "diffuse_roughness")
                    col.prop(standard_surface, "metalness")

                # Specular
                sublayout = _subpanel(layout, "Specular", standard_surface.ui_specular,
                                      path_from_id, "ui_specular", "material")
                if sublayout:
                    col = sublayout.column()
                    #TODO: Fix for viewport
                    col.prop(mat, "specular_intensity", text="Weight")
                    col.prop(mat, "specular_color", text="Color")
                    col.prop(standard_surface, "specular_roughness")
                    col.prop(standard_surface, "specular_ior")
                    col.prop(standard_surface, "specular_anisotropy")
                    col.prop(standard_surface, "specular_rotation")

                # Transmission
                sublayout = _subpanel(layout, "Transmission", standard_surface.ui_refraction,
                                      path_from_id, "ui_refraction", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(standard_surface, "transmission")
                    col.prop(standard_surface, "transmission_color")
                    col.prop(standard_surface, "transmission_depth")
                    col.prop(standard_surface, "transmission_scatter")
                    col.prop(standard_surface, "transmission_scatter_anisotropy")
                    col.prop(standard_surface, "transmission_dispersion")
                    col.prop(standard_surface, "transmission_extra_roughness")
                    col.prop(standard_surface, "transmit_aovs")

                # Subsurface
                sublayout = _subpanel(layout, "Subsurface", standard_surface.ui_sss,
                                      path_from_id, "ui_sss", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(standard_surface, "subsurface")
                    col.prop(standard_surface, "subsurface_color")
                    col.prop(standard_surface, "subsurface_radius")
                    col.prop(standard_surface, "subsurface_scale")
                    col.prop(standard_surface, "subsurface_type")
                    col.prop(standard_surface, "subsurface_anisotropy")


                # Coat
                sublayout = _subpanel(layout, "Coat", standard_surface.ui_coat,
                                      path_from_id, "ui_coat", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(standard_surface, "coat")
                    col.prop(standard_surface, "coat_color")
                    col.prop(standard_surface, "coat_roughness")
                    col.prop(standard_surface, "coat_ior")
                    col.prop(standard_surface, "coat_normal")

                # Sheen
                sublayout = _subpanel(layout, "Sheen", standard_surface.ui_sheen,
                                      path_from_id, "ui_sheen", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(standard_surface, "sheen")
                    col.prop(standard_surface, "sheen_color")
                    col.prop(standard_surface, "sheen_roughness")

                # Emission
                sublayout = _subpanel(layout, "Emission", standard_surface.ui_emission,
                                      path_from_id, "ui_emission", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(standard_surface, "emission")
                    col.prop(standard_surface, "emission_color")


                # Thin Film
                sublayout = _subpanel(layout, "Thin Film", standard_surface.ui_thinfilm,
                                      path_from_id, "ui_thinfilm", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(standard_surface, "thin_film_thickness")
                    col.prop(standard_surface, "thin_film_ior")

                # Geometry
                sublayout = _subpanel(layout, "Geometry", standard_surface.ui_geometry,
                                      path_from_id, "ui_geometry", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(standard_surface, "opacity")
                    col.prop(standard_surface, "thin_walled")


                # Advanced
                sublayout = _subpanel(layout, "Advanced", standard_surface.ui_advanced,
                                      path_from_id, "ui_advanced", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(standard_surface, "caustics")
                    col.prop(standard_surface, "internal_reflections")
                    col.prop(standard_surface, "exit_to_background")
                    col.prop(standard_surface, "indirect_diffuse")
                    col.prop(standard_surface, "indirect_specular")
            elif shader_type == 'toon':
                toon = shader.toon
                path_from_id = toon.path_from_id()

                # Base
                sublayout = _subpanel(layout, "Base", toon.ui_base,
                                      path_from_id, "ui_base", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(toon, "base")
                    col.prop(toon, "base_color")
                    col.prop(toon, "base_tonemap")

                # Specular
                sublayout = _subpanel(layout, "Specular", toon.ui_specular,
                                      path_from_id, "ui_specular", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(toon, "specular")
                    col.prop(toon, "specular_color")
                    col.prop(toon, "specular_roughness")
                    col.prop(toon, "specular_tonemap")
                    col.prop(toon, "specular_anisotropy")
                    col.prop(toon, "specular_rotation")
                    col.prop(toon, "lights")
                    col.prop(toon, "highlight_color")
                    col.prop(toon, "highlight_size")
                    col.prop(toon, "aov_highlight")
                    col.prop(toon, "rim_light")
                    col.prop(toon, "rim_light_color")
                    col.prop(toon, "rim_light_width")
                    col.prop(toon, "aov_rim_light")


                # Transmission
                sublayout = _subpanel(layout, "Transmission", toon.ui_transmission,
                                      path_from_id, "ui_transmission", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(toon, "transmission")
                    col.prop(toon, "transmission_color")
                    col.prop(toon, "transmission_roughness")
                    col.prop(toon, "transmission_anisotropy")
                    col.prop(toon, "transmission_rotation")

                # Edge
                sublayout = _subpanel(layout, "Edge", toon.ui_edge,
                                      path_from_id, "ui_edge", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(toon, "mask_color")
                    col.prop(toon, "edge_color")
                    col.prop(toon, "edge_tonemap")
                    col.prop(toon, "edge_opacity")
                    col.prop(toon, "edge_width_scale")

                # Silhouette
                sublayout = _subpanel(layout, "Silhouette", toon.ui_silhouette,
                                      path_from_id, "ui_silhouette", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(toon, "silhouette_color")
                    col.prop(toon, "silhouette_tonemap")
                    col.prop(toon, "silhouette_opacity")
                    col.prop(toon, "silhouette_width_scale")
                    #col.prop(toon, "priority")
                    col.prop(toon, "enable_silhouette")
                    col.prop(toon, "ignore_throughput")
                    col.prop(toon, "enable")
                    col.prop(toon, "id_difference")
                    col.prop(toon, "shader_difference")
                    col.prop(toon, "uv_threshold")
                    col.prop(toon, "angle_threshold")
                    col.prop(toon, "normal_type")


                # Emission
                sublayout = _subpanel(layout, "Emission", toon.ui_emission,
                                      path_from_id, "ui_emission", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(toon, "emission")
                    col.prop(toon, "emission_color")

                # Sheen
                sublayout = _subpanel(layout, "Sheen", toon.ui_sheen,
                                      path_from_id, "ui_sheen", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(toon, "sheen")
                    col.prop(toon, "sheen_color")
                    col.prop(toon, "sheen_roughness")

                # Advanced
                sublayout = _subpanel(layout, "Advanced", toon.ui_advanced,
                                      path_from_id, "ui_advanced", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(toon, "IOR")
                    col.prop(toon, "normal")
                    col.prop(toon, "tangent")
                    col.prop(toon, "indirect_diffuse")
                    col.prop(toon, "indirect_specular")
                    col.prop(toon, "bump_mode")
                    col.prop(toon, "energy_conserving")
                    col.prop(toon, "user_id")
            elif shader_type == 'utility':
                utility = shader.utility
                col = layout.column()
                col.prop(utility, "color")
                col.prop(utility, "opacity")
                col.prop(utility, "color_mode")
                col.prop(utility, "shade_mode")
                col.prop(utility, "overlay_mode")
                col.prop(utility, "ao_distance")
            elif shader_type == 'flat':
                flat = shader.flat
                col = layout.column()
                col.prop(flat, "color")
                col.prop(flat, "opacity")
            elif shader_type == 'standard_hair':
                standard_hair = shader.standard_hair
                path_from_id = standard_hair.path_from_id()
                # Color
                sublayout = _subpanel(layout, "Color", standard_hair.ui_standardhair_color,
                                      path_from_id, "ui_standardhair_color", "material")
                if sublayout:
                    col = sublayout.column()
                    #TODO: Fix For Viewport
                    col.prop(standard_hair, "base", text="Base")
                    col.prop(standard_hair, "base_color", text="Base Color")
                    col.prop(standard_hair, "melanin", text="Melanin")
                    col.prop(standard_hair, "melanin_redness", text="Melanin Redness")
                    col.prop(standard_hair, "melanin_randomize", text="Melanin Randomize")

                # Specular
                sublayout = _subpanel(layout, "Specular", standard_hair.ui_standardhair_specular,
                                      path_from_id, "ui_standardhair_specular", "material")
                if sublayout:
                    col = sublayout.column()
                    #TODO: Fix For Viewport
                    col.prop(standard_hair, "roughness", text="Roughness")
                    col.prop(standard_hair, "ior", text="IOR")
                    col.prop(standard_hair, "shift", text="Shift")

                # Specular
                sublayout = _subpanel(layout, "Tint", standard_hair.ui_standardhair_tint,
                                      path_from_id, "ui_standardhair_tint", "material")
                if sublayout:
                    col = sublayout.column()
                    #TODO: Fix For Viewport
                    col.prop(standard_hair, "specular_tint", text="Specular Tint")
                    col.prop(standard_hair, "specular2_tint", text="2nd Specular Tint")
                    col.prop(standard_hair, "transmission_tint", text="Transmission Tint")

                # Diffuse
                sublayout = _subpanel(layout, "Diffuse", standard_hair.ui_standardhair_diffuse,
                                      path_from_id, "ui_standardhair_diffuse", "material")
                if sublayout:
                    col = sublayout.column()
                    #TODO: Fix For Viewport
                    col.prop(standard_hair, "diffuse", text="Diffuse")
                    col.prop(standard_hair, "diffuse_color", text="Diffuse Color")

                # Emission
                sublayout = _subpanel(layout, "Emission", standard_hair.ui_standardhair_emission,
                                      path_from_id, "ui_standardhair_emission", "material")
                if sublayout:
                    col = sublayout.column()
                    #TODO: Fix For Viewport
                    col.prop(standard_hair, "emission", text="Weight")
                    col.prop(standard_hair, "emission_color", text="Color")
                    col.prop(standard_hair, "opacity", text="Opacity")

                # Advanced
                sublayout = _subpanel(layout, "Advanced", standard_hair.ui_standardhair_advanced,
                                      path_from_id, "ui_standardhair_advanced", "material")
                if sublayout:
                    col = sublayout.column()
                    #TODO: Fix For Viewport
                    col.prop(standard_hair, "indirect_diffuse", text="Indirect Diffuse")
                    col.prop(standard_hair, "indirect_specular", text="Indirect Specular")
                    col.prop(standard_hair, "extra_depth", text="Extra Depth")
                    col.prop(standard_hair, "extra_samples", text="Extra Samples")

        elif mat_type == 'WIRE':
            wire = shader.wire
            col = layout.column()
            col.prop(wire, "fill_color")
            col.prop(wire, "line_color")
            col.prop(wire, "edge_type")
            col.prop(wire, "line_width")
            col.prop(wire, "raster_space")
        elif mat_type == 'VOLUME':
            standard_volume = shader.standard_volume
            path_from_id = standard_volume.path_from_id()

            # Volume Density
            sublayout = _subpanel(layout, "Density", standard_volume.ui_standardvolume_density,
                                  path_from_id, "ui_standardvolume_density", "material")
            if sublayout:
                col = sublayout.column()
                #TODO: Fix For Viewport
                col.prop(standard_volume, "density", text="Density")

            # Volume Scatter
            sublayout = _subpanel(layout, "Scatter", standard_volume.ui_standardvolume_scatter,
                                  path_from_id, "ui_standardvolume_scatter", "material")
            if sublayout:
                col = sublayout.column()
                col.prop(standard_volume, "scatter", text="Scatter")
                col.prop(standard_volume, "scatter_color", text="Scatter Color")
                col.prop(standard_volume, "scatter_anisotropy", text="Scatter Anisotropy")

            # Volume Transparency
            sublayout = _subpanel(layout, "Transparency", standard_volume.ui_standardvolume_transparency,
                                  path_from_id, "ui_standardvolume_transparency", "material")
            if sublayout:
                col = sublayout.column()
                col.prop(standard_volume, "transparent", text="Transparent Color")

            # Volume Emission
            sublayout = _subpanel(layout, "Emission", standard_volume.ui_standardvolume_emission,
                                  path_from_id, "ui_standardvolume_emission", "material")
            if sublayout:
                col = sublayout.column()
                # col.prop(standard_volume, "emission_mode", text="Emission Mode")
                col.prop(standard_volume, "emission", text="Emission")
                col.prop(standard_volume, "emission_color", text="Emission Color")

            # Volume Etc.
            sublayout = _subpanel(layout, "Advanced", standard_volume.ui_standardvolume_advanced,
                                  path_from_id, "ui_standardvolume_advanced", "material")
            if sublayout:
                col = sublayout.column()
                col.prop(standard_volume, "temperature", text="Temperature")
##
## Textures
##

from bl_ui.properties_texture import TextureButtonsPanel


@ArnoldRenderEngine.register_class
class ArnoldNodeTexturesMenu(Menu):
    bl_label = "Image Node"

    def draw(self, context):
        print(self)


@ArnoldRenderEngine.register_class
class ArnoldTexturePanel(TextureButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_options = {'HIDE_HEADER'}
    bl_label = ""

    @classmethod
    def poll(cls, context):
        # TODO:
        return False # context.scene.render.engine in cls.COMPAT_ENGINES

    def draw(self, context):
        layout = self.layout

        space = context.space_data

        layout.prop(space, "texture_context", expand=True)
        if space.texture_context == 'WORLD':
            pass
        elif space.texture_context == 'MATERIAL':
            idblock = context.material
            print(context.active_object)
            if idblock is None and context.active_object:
                idblock = context.active_object.active_material
            if idblock:
                row = layout.row()
                row.template_list("TEXTURE_UL_texslots", "", idblock, "texture_slots", idblock, "active_texture_index", rows=2)
                col = row.column(align=True)
                col.operator("texture.slot_move", text="", icon='TRIA_UP').type = 'UP'
                col.operator("texture.slot_move", text="", icon='TRIA_DOWN').type = 'DOWN'
                col.menu("TEXTURE_MT_specials", icon='DOWNARROW_HLT', text="")

            #if mat and mat.use_nodes:
            #    ntree = mat.node_tree
            #    print(ntree, ntree.nodes.active)
            #    layout.menu("ArnoldNodeTexturesMenu", text="* Select Node *", icon='NODE')
        elif space.texture_context == 'OTHER':
            layout.template_texture_user()

##
## Particles
##

from bl_ui.properties_particle import ParticleButtonsPanel


@ArnoldRenderEngine.register_class
class ArnoldCurvesPanel(ParticleButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Curves"

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            pss = context.particle_system.settings
            return pss.type == 'HAIR' and pss.render_type == 'PATH'
        return False

    def draw(self, context):
        layout = self.layout

        ps = context.particle_system
        pss = ps.settings
        curves = pss.arnold.curves

        col = layout.column()
        col.prop(curves, "radius_tip")
        col.prop(curves, "radius_root")
        col.prop(curves, "basis")
        if curves.basis == 'bezier':
            col.prop(curves, "bezier_scale")
        col.prop(curves, "mode")
        col.prop(curves, "min_pixel_width")
        col.prop_search(curves, "uvmap", context.object.data, "uv_textures")


@ArnoldRenderEngine.register_class
class ArnoldPointsPanel(ParticleButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Points"

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            pss = context.particle_system.settings
            return (
                pss.type == 'EMITTER' and
                pss.render_type in {'HALO', 'LINE', 'PATH'}
            )
        return False

    def draw(self, context):
        layout = self.layout

        ps = context.particle_system
        pss = ps.settings
        points = pss.arnold.points

        col = layout.column()
        col.prop(points, "mode")
        if points.mode == 'quad':
            col.prop(points, "aspect")
            col.prop(points, "rotation")
        col.prop(points, "min_pixel_width")
        col.prop(points, "step_size")
