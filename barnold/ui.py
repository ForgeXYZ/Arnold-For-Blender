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
            col.prop(opts, "GI_specular_samples")
            col.prop(opts, "GI_transmission_samples")
            col.prop(opts, "GI_sss_samples")
            col.prop(opts, "GI_volume_samples")
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
            col.prop(opts, "GI_specular_depth")
            # TODO: DELETE? col.prop(opts, "GI_reflection_depth")
            col.prop(opts, "GI_transmission_depth")
            col.prop(opts, "GI_volume_depth")
            col.separator()
            col.label("Transparency:", icon='SETTINGS')
            # TODO: DELETE? col.prop(opts, "auto_transparency_mode")
            col.prop(opts, "auto_transparency_depth")
            # TODO: DELETE? col.prop(opts, "auto_transparency_threshold")

        sublayout = _subpanel(layout, "Light", opts.ui_light, opts_path, "ui_light", "scene")
        if sublayout:
            col = sublayout.column()
            col.prop(opts, "low_light_threshold")

        sublayout = _subpanel(layout, "Gamma Correction", opts.ui_gamma, opts_path, "ui_gamma", "scene")
        if sublayout:
            col = sublayout.column()
            # TODO: DELETE? col.prop(opts, "texture_gamma")
            # TODO: DELETE? col.prop(opts, "light_gamma")
            # TODO: DELETE? col.prop(opts, "shader_gamma")
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
            col.prop(opts, "texture_specular_blur")


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
            col.label("Viewport Rendering", icon='SETTINGS')
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
            col.prop(opts, "error_color_bad_texture")
            col.prop(opts, "error_color_bad_shader")
            col.prop(opts, "error_color_bad_pixel")


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
        light_type = light.type
        path_from_id = light.path_from_id()

        #layout.prop(lamp, "type", expand=True)
        layout.prop(light, "type")

        col = layout.column()
        col.prop(lamp, "color")
        col.prop(light, "intensity")
        col.prop(light, "exposure")

        col = layout.column()
        if lamp_type not in ('SUN', 'HEMI') and light_type != 'photometric_light':
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
                col.prop_search(light, "mesh", context.scene, "objects", icon='OUTLINER_OB_MESH')
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
                              path_from_id, "ui_shadow", "lamp")
        if sublayout:
            col = sublayout.column()
            col.prop(light, "cast_shadows")
            col.prop(light, "shadow_color")
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
    bl_label = "Arnold Shader"

    @classmethod
    def poll(cls, context):
        return super().poll(context) and not context.material.use_nodes

    def draw(self, context):
        layout = self.layout
        mat = context.material
        shader = mat.arnold

        mat_type = mat.type
        if mat_type == 'SURFACE':
            shader_type = shader.type
            layout.prop(shader, "type", expand=True)
            if shader_type == 'lambert':
                lambert = shader.lambert
                col = layout.column()
                col.prop(mat, "diffuse_intensity", text="Weight")
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
                    col.prop(mat, "diffuse_intensity", text="Weight")
                    col.prop(mat, "diffuse_color", text="Color")
                    col.prop(standard_surface, "diffuse_roughness")
                    col.prop(standard_surface, "metalness")
                    # Below is deprecated in Arnold 5
                        # col.prop(standard_surface, "Fresnel_affect_diff")
                        # col.prop(standard_surface, "Kb")
                        # col.prop(standard_surface, "direct_diffuse")
                        # col.prop(standard_surface, "indirect_diffuse")

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
                    # Below is deprecated in Arnold 5
                        # col.prop(standard_surface, "direct_specular")
                        # col.prop(standard_surface, "indirect_specular")
                        # col.label("Fresnel", icon='SETTINGS')
                        # box = col.box()
                        # box.prop(standard_surface, "specular_Fresnel")
                        # sub = box.row()
                        # sub.enabled = standard_surface.specular_Fresnel
                        # sub.prop(standard_surface, "Ksn")


                # # (Reflection) - DEPRECATED IN ARNOLD 5
                # sublayout = _subpanel(layout, "Transmission", standard_surface.ui_reflection,
                #                       path_from_id, "ui_reflection", "material")
                # if sublayout:
                #     col = sublayout.column()
                #     col.prop(standard_surface, "transmission_color")
                #     col.prop(standard_surface, "transmission")
                #     col.label("Fresnel:", icon='SETTINGS')
                #     box = col.box()
                #     box.prop(standard_surface, "Fresnel")
                #     sub = box.row()
                #     sub.enabled = standard_surface.Fresnel
                #     sub.prop(standard_surface, "Krn")
                #     col.label("Exit Color:", icon='SETTINGS')
                #     box = col.box()
                #     box.prop(standard_surface, "reflection_exit_use_environment")
                #     box.row().prop(standard_surface, "reflection_exit_color")

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
                    # col.prop(standard_surface, "Fresnel_use_IOR")
                    # Below is deprecated in Arnold 5
                        # col.prop(standard_surface, "transmittance")
                        # col.label("Exit Color:", icon='SETTINGS')
                        # box = col.box()
                        # box.prop(standard_surface, "refraction_exit_use_environment")
                        # box.row().prop(standard_surface, "refraction_exit_color")
                        # col.prop(standard_surface, "enable_internal_reflections")


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


                # Emission
                sublayout = _subpanel(layout, "Emission", standard_surface.ui_emission,
                                      path_from_id, "ui_emission", "material")
                if sublayout:
                    col = sublayout.column()
                    col.prop(mat, "emit", text="Weight")
                    col.prop(standard_surface, "emission_color", text="Color")


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
        #     elif shader_type == 'utility':
        #         utility = shader.utility
        #         col = layout.column()
        #         col.prop(utility, "color")
        #         col.prop(utility, "opacity")
        #         col.prop(utility, "color_mode")
        #         col.prop(utility, "shade_mode")
        #         col.prop(utility, "overlay_mode")
        #         col.prop(utility, "ao_distance")
        #     elif shader_type == 'flat':
        #         flat = shader.flat
        #         col = layout.column()
        #         col.prop(flat, "color")
        #         col.prop(flat, "opacity")
        #     elif shader_type == 'hair':
        #         pass
        # elif mat_type == 'WIRE':
        #     wire = shader.wire
        #     col = layout.column()
        #     col.prop(wire, "fill_color")
        #     col.prop(wire, "line_color")
        #     col.prop(wire, "edge_type")
        #     col.prop(wire, "line_width")
        #     col.prop(wire, "raster_space")

        # layout.prop(standard_surface, "bounce_factor")
        # layout.prop(standard_surface, "opacity")

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
