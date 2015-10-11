# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import bpy
from bpy.types import (
    UIList,
    UI_UL_list,
    Panel,
    Menu
)
from . import ArnoldRenderEngine


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

##
## Options
##

from bl_ui.properties_render import RenderButtonsPanel


@ArnoldRenderEngine.register_class
class ArnoldRenderMainPanel(RenderButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Render: Main"

    def draw(self, context):
        layout = self.layout
        opts = context.scene.arnold
        opts_path = opts.path_from_id()

        sublayout = _subpanel(layout, "Sampling", opts.ui_sampling, opts_path, "ui_sampling", "scene")
        if sublayout:
            col = sublayout.column()
            col.label("Samples:", icon='SETTINGS')
            col.prop(opts, "AA_samples")
            col.prop(opts, "GI_diffuse_samples")
            col.prop(opts, "GI_glossy_samples")
            col.prop(opts, "GI_refraction_samples")
            col.prop(opts, "sss_bssrdf_samples")
            col.prop(opts, "volume_indirect_samples")
            col.separator()
            col.prop(opts, "lock_sampling_pattern")
            col.prop(opts, "sss_use_autobump")

            col.separator()
            col.label("Clamping:", icon='SETTINGS')
            col.prop(opts, "clamp_sample_values")
            subcol = col.column()
            subcol.enabled = opts.clamp_sample_values
            subcol.prop(opts, "AA_sample_clamp_affects_aovs")
            subcol.prop(opts, "AA_sample_clamp")

            col.separator()
            col.label("Filter:", icon='SETTINGS')
            col.prop(opts, "sample_filter_type")
            sft = opts.sample_filter_type
            if sft == 'blackman_harris_filter':
                col.prop(opts, "sample_filter_bh_width")
            elif sft == 'sinc_filter':
                col.prop(opts, "sample_filter_sinc_width")
            elif sft in ('cone_filter',
                         'cook_filter',
                         'disk_filter',
                         'gaussian_filter',
                         'triangle_filter'):
                col.prop(opts, "sample_filter_width")
            elif sft == 'farthest_filter':
                col.prop(opts, "sample_filter_domain")
            elif sft == 'heatmap_filter':
                row = col.row(align=True)
                row.prop(opts, "sample_filter_min")
                row.prop(opts, "sample_filter_max")
            elif sft == 'variance_filter':
                col.prop(opts, "sample_filter_width")
                col.prop(opts, "sample_filter_scalar_mode")

        sublayout = _subpanel(layout, "Ray Depth", opts.ui_ray_depth, opts_path, "ui_ray_depth", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "GI_total_depth")
            col.prop(opts, "GI_diffuse_depth")
            col.prop(opts, "GI_glossy_depth")
            col.prop(opts, "GI_reflection_depth")
            col.prop(opts, "GI_refraction_depth")
            col.prop(opts, "GI_volume_depth")
            col.separator()
            col.label("Transparency:", icon='SETTINGS')
            col.prop(opts, "auto_transparency_mode")
            col.prop(opts, "auto_transparency_depth")
            col.prop(opts, "auto_transparency_threshold")

        sublayout = _subpanel(layout, "Light", opts.ui_light, opts_path, "ui_light", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "low_light_threshold")

        sublayout = _subpanel(layout, "Gamma Correction", opts.ui_gamma, opts_path, "ui_gamma", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "texture_gamma")
            col.prop(opts, "light_gamma")
            col.prop(opts, "shader_gamma")
            col.separator()
            col.prop(opts, "display_gamma")

        sublayout = _subpanel(layout, "Textures", opts.ui_textures, opts_path, "ui_textures", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "texture_automip")
            col.prop(opts, "texture_accept_unmipped")
            col.separator()
            col.prop(opts, "texture_accept_untiled")
            col.prop(opts, "texture_autotile")
            col.separator()
            col.prop(opts, "texture_max_memory_MB")
            col.prop(opts, "texture_max_open_files")
            col.separator()
            col.prop(opts, "texture_diffuse_blur")
            col.prop(opts, "texture_glossy_blur")


@ArnoldRenderEngine.register_class
class ArnoldRenderSystemPanel(RenderButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Render: System"
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

        sublayout = _subpanel(layout, "Search paths", opts.ui_paths, opts_path, "ui_paths", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "procedural_searchpath")
            col.prop(opts, "shader_searchpath")
            col.prop(opts, "texture_searchpath")

        sublayout = _subpanel(layout, "Licensing", opts.ui_licensing, opts_path, "ui_licensing", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "abort_on_license_fail")
            col.prop(opts, "skip_license_check")


@ArnoldRenderEngine.register_class
class ArnoldRenderDiagnosticsPanel(RenderButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Render: Diagnostics"
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
            col.row().prop(opts, "error_color_bad_texture")
            col.row().prop(opts, "error_color_bad_shader")
            col.row().prop(opts, "error_color_bad_pixel")


@ArnoldRenderEngine.register_class
class ArnoldRenderOverridePanel(RenderButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Render: Override"
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
            col.prop(opts, "ignore_direct_lighting")
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


@ArnoldRenderEngine.register_class
class ArnoldObjectPanel(ObjectButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
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
        col.label("Visibility:")
        flow = col.column_flow()
        flow.prop(props, "visibility_camera")
        flow.prop(props, "visibility_shadow")
        flow.prop(props, "visibility_reflection")
        flow.prop(props, "visibility_refraction")
        flow.prop(props, "visibility_diffuse")
        flow.prop(props, "visibility_glossy")

        col = layout.column()
        col.label("Double-sided:")
        flow = col.column_flow()
        flow.prop(props, "sidedness_camera")
        flow.prop(props, "sidedness_shadow")
        flow.prop(props, "sidedness_reflection")
        flow.prop(props, "sidedness_refraction")
        flow.prop(props, "sidedness_diffuse")
        flow.prop(props, "sidedness_glossy")

##
## Lights
##

from bl_ui.properties_data_lamp import DataButtonsPanel as LightButtonsPanel


@ArnoldRenderEngine.register_class
class ArnoldLightPanel(LightButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Light"

    def draw(self, context):
        layout = self.layout

        lamp = context.lamp
        lamp_type = lamp.type

        light = lamp.arnold
        path_from_id = light.path_from_id()

        layout.prop(lamp, "type", expand=True)

        col = layout.column()
        col.row().prop(lamp, "color")
        col.prop(light, "intensity")
        col.prop(light, "exposure")

        col = layout.column()
        if lamp_type not in ('SUN', 'HEMI'):
            col.prop(light, "decay_type")
        col.prop(light, "affect_diffuse")
        col.prop(light, "affect_specular")

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

        # Geometry
        if lamp_type == 'SPOT':
            col = layout.column()
            col.prop(light, "aspect_ratio")
            col.prop(light, "lens_radius")
            col.prop(lamp, "spot_size", text="Cone Ange")
            col.prop(light, "penumbra_angle")

        sublayout = _subpanel(layout, "Shadow", light.ui_shadow,
                              path_from_id, "ui_shadow", "lamp")
        if sublayout:
            col = sublayout.column()
            col.prop(light, "cast_shadows")
            col.row().prop(light, "shadow_color")
            col.prop(light, "shadow_density")

        sublayout = _subpanel(layout, "Volume", light.ui_volume,
                              path_from_id, "ui_volume", "lamp")
        if sublayout:
            col = sublayout.column()
            col.prop(light, "affect_volumetrics")
            col.prop(light, "cast_volumetric_shadows")
            col.prop(light, "volume_samples")

        sublayout = _subpanel(layout, "Contribution", light.ui_contribution,
                              path_from_id, "ui_contribution", "lamp")
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
                                  path_from_id, "ui_viewport", "lamp")
            if sublayout:
                col = sublayout.column()
                col.prop(lamp, "distance")
                col.prop(lamp, "spot_blend")
                col.prop(lamp, "use_square")
                col.prop(lamp, "show_cone")

##
## Shaders
##

from bl_ui.properties_material import MaterialButtonsPanel


@ArnoldRenderEngine.register_class
class ArnoldShaderPanel(MaterialButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Shader"

    @classmethod
    def poll(cls, context):
        return super().poll(context) and not context.material.use_nodes

    def draw(self, context):
        layout = self.layout
        mat = context.material

        shader = mat.arnold
        mat_type = mat.type
        if mat_type == 'SURFACE':
            layout.prop(shader, "type")
            col = layout.column(align=True)
            col.label("Diffuse:")
            row = col.row(align=True)
            row.prop(mat, "diffuse_color", text="")
            row.prop(mat, "diffuse_intensity", text="Weight")
            if shader.type == 'LAMBERT':
                layout.prop(shader, "opacity")
            elif shader.type == 'STANDARD':
                standard = shader.standard
                col.prop(standard, "diffuse_roughness")
                col = layout.column(align=True)
                col.label("Specular:")
                row = col.row(align=True)
                row.prop(standard, "ks_color", text="")
                row.prop(standard, "ks")
                row = col.row(align=True)
                row.prop(standard, "specular_roughness")
                row.prop(standard, "specular_anisotropy")
                col.prop(standard, "specular_rotation")
        elif mat_type == 'WIRE':
            wire = shader.wire
            layout.prop(wire, "edge_type")
            layout.prop(mat, "diffuse_color", text="Line Color")
            layout.prop(wire, "fill_color")
            row = layout.row(align=True)
            row.prop(wire, "raster_space")
            row.prop(wire, "line_width")

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
        return context.scene.render.engine in cls.COMPAT_ENGINES

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
