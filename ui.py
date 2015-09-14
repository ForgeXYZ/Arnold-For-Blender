# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import bpy
from bpy.types import Panel
from . import ArnoldRenderEngine


from bl_ui.properties_render import RenderButtonsPanel


class ArnoldRenderPanel(RenderButtonsPanel, Panel):
    COMPAT_ENGINES = {ArnoldRenderEngine.bl_idname}
    bl_label = "Arnold Render"

    def draw(self, context):
        layout = self.layout
        opts = context.scene.arnold

        row = layout.row()
        col = row.column(align=True)
        col.prop(opts, "aa_samples")
        col.prop(opts, "aa_seed")
        col = row.column(align=True)
        col.prop(opts, "threads")
        col.prop(opts, "thread_priority", text="")

        layout.prop(opts, "skip_license_check")



from bl_ui.properties_data_lamp import DataButtonsPanel as LampButtonsPanel


class ArnoldLampPanel(LampButtonsPanel, Panel):
    bl_label = "Arnold Light"
    COMPAT_ENGINES = ArnoldRenderEngine.bl_idname

    def draw(self, context):
        layout = self.layout
        lamp = context.lamp

        light = lamp.arnold
        light_type = light.type
        if light_type == 'POINT':
            point_light = light.point
            row = layout.row()
            row.prop(lamp, "color", text="")
            row.prop(point_light, "decay_type", expand=True)
            row = layout.row()
            row.prop(point_light, "radius")
            row.prop(point_light, "intensity")
            row = layout.row()
            row.prop(point_light, "exposure")
            # Shadows params
            layout.prop(point_light, "cast_shadows")
            layout.prop(point_light, "cast_volumetric_shadows")
            row = layout.row()
            row.prop(point_light, "shadow_density")
            row.prop(point_light, "shadow_color", text="")
            row = layout.row()
            row.prop(point_light, "samples")
            row.prop(point_light, "normalize")


def register():
    from bpy.utils import register_class

    register_class(ArnoldRenderPanel)
    register_class(ArnoldLampPanel)


def unregister():
    from bpy.utils import unregister_class

    unregister_class(ArnoldRenderPanel)
    unregister_class(ArnoldLampPanel)
