# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import bpy
from bpy.types import Panel, Menu

from . import ArnoldRenderEngine

##
## Options
##

from bl_ui.properties_render import RenderButtonsPanel


@ArnoldRenderEngine.register_class
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
        col.prop(opts, "aa_sample_clamp")
        col.prop(opts, "aa_sample_clamp_affects_aovs")

        row = layout.row()
        col = row.column(align=True)
        col.prop(opts, "threads")
        col.prop(opts, "thread_priority", text="")
        col = row.column(align=True)
        col.prop(opts, "bucket_size")
        col.prop(opts, "bucket_scanning", text="")

        layout.prop(opts, "skip_license_check")

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
