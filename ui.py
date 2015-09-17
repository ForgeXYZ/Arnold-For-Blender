# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import bpy
from bpy.types import Panel
from . import ArnoldRenderEngine

##
## Options
##

from bl_ui.properties_render import RenderButtonsPanel


class ArnoldRenderPanel(RenderButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Render"

    def draw(self, context):
        layout = self.layout
        opts = context.scene.arnold

        layout.prop(opts, "logfile")
        row = layout.row()
        row.prop_menu_enum(opts, "logfile_flags")
        row.prop_menu_enum(opts, "console_log_flags")

        row = layout.row()
        col = row.column(align=True)
        col.prop(opts, "aa_samples")
        col.prop(opts, "aa_seed")
        col = row.column(align=True)
        col.prop(opts, "threads")
        col.prop(opts, "thread_priority", text="")

        layout.prop(opts, "skip_license_check")

##
## Lights
##

from bl_ui.properties_data_lamp import DataButtonsPanel as LightButtonsPanel


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


class ArnoldShaderPanel(MaterialButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Shader"

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
            row = layout.row()
            row.prop(wire, "line_width")
            row.prop(wire, "raster_space")


def register():
    from bpy.utils import register_class

    register_class(ArnoldRenderPanel)
    register_class(ArnoldLightPanel)
    register_class(ArnoldLightShadowsPanel)
    register_class(ArnoldShaderPanel)


def unregister():
    from bpy.utils import unregister_class

    unregister_class(ArnoldRenderPanel)
    unregister_class(ArnoldLightPanel)
    unregister_class(ArnoldLightShadowsPanel)
    unregister_class(ArnoldShaderPanel)
