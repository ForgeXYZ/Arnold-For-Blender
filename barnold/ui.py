# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import bpy
from bpy.types import (
    Operator,
    Panel,
    Menu
)
from bpy.props import (
    StringProperty
)
from . import ArnoldRenderEngine


@ArnoldRenderEngine.register_class
class ArnoldUiToggle(Operator):
    bl_idname = "barnold.ui_toggle"
    bl_options = {'INTERNAL'}
    bl_label = "Open / Close"
    bl_description = "Open / close options"

    path = StringProperty()
    attr = StringProperty()
    ctx = StringProperty()

    def execute(self, context):
        data = getattr(context, self.ctx)
        if self.path:
            data = data.path_resolve(self.path)
        setattr(data, self.attr, not getattr(data, self.attr))
        return {'FINISHED'}


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
            col.prop(opts, "display_gamma")
            col.separator()
            col.prop(opts, "texture_gamma")
            col.prop(opts, "light_gamma")
            col.prop(opts, "shader_gamma")

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
## Lights
##

from bl_ui.properties_data_lamp import DataButtonsPanel as LightButtonsPanel


@ArnoldRenderEngine.register_class
class ArnoldLightPanel(LightButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Light"

    def draw(self, context):
        layout = self.layout
        lamp = context.lamp

        layout.prop(lamp, "type", expand=True)

        light = lamp.arnold
        row = layout.row()
        row.prop(lamp, "color", text="")
        row.prop(light, "decay_type")
        row = layout.row()
        row.prop(light, "intensity")
        row.prop(light, "exposure")

        light_type = light.type
        if light_type == 'POINT':
            point_light = light.point
            row = layout.row()
            row.prop(point_light, "radius")
            # Shadows params


@ArnoldRenderEngine.register_class
class ArnoldLightShadowsPanel(LightButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Shadow"

    def draw(self, context):
        layout = self.layout
        lamp = context.lamp
        light = lamp.arnold

        layout.prop(light, "cast_shadows")
        layout.prop(light, "cast_volumetric_shadows")
        row = layout.row()
        row.prop(light, "shadow_color", text="")
        row.prop(light, "samples")
        row = layout.row()
        row.prop(light, "shadow_density")
        row.prop(light, "normalize")

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
