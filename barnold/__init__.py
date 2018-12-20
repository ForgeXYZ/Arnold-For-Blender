# -*- coding: utf-8 -*-

__author__ = "Tyler Furby"
__email__ = "tyler@tylerfurby.com"

bl_info = {
    "name"          : "Arnold",
    "description"   : "Solid Angle's Arnold Renderer for Blender",
    "author"        : "Tyler Furby <tyler@tylerfurby.com>", "N.Ildar <nildar@users.sourceforge.net>"
    "version"       : (0, 0, 2),
    "blender"       : (2, 80, 0),
    "location"      : "Info header, render engine menu",
    "category"      : "Render"
}

import bpy
import sys
import os

class ArnoldRenderEngine(bpy.types.RenderEngine):
    bl_idname = "ARNOLD"
    bl_label = "Arnold"
    bl_use_preview = True
    bl_use_save_buffers = True
    bl_use_shading_nodes = True
    bl_use_shading_nodes_custom = False

    _CLASSES = []  # classes for (un)register

    _COMPATIBLE_PANELS = (
        # ("properties_render", ((
        #     "RENDER_PT_dimensions",
        #     "RENDER_PT_output",
        #     "RENDER_PT_post_processing",
        # ), False)),
        ("properties_render", ((
            "RENDER_PT_color_management",
        ), False)),
        ("properties_output", ((
            "RENDER_PT_dimensions",
            "RENDER_PT_output",
            "RENDER_PT_post_processing",
        ), False)),
        ("properties_view_layer", None),
        ("properties_world", None),
        ("properties_data_light", ((
            "DATA_PT_context_light",
            "DATA_PT_area",
            "DATA_PT_custom_props_light",
        ), False)),
        ("properties_constraint", None),
        ("properties_material", ((
            #"MATERIAL_PT_context_material",
            #"MATERIAL_PT_preview",
            "MATERIAL_PT_custom_props",
        ), False)),
        ("properties_texture", None),
        #("properties_texture", ((
        #    "TEXTURE_PT_context_texture",
        #    "TEXTURE_PT_preview",
        #    "TEXTURE_PT_image",
        #    #"TEXTURE_PT_image_sampling",
        #    #"TEXTURE_PT_image_mapping",
        #    "TEXTURE_PT_mapping",
        #    #"TEXTURE_PT_influence",
        #), False)),
        # ("properties_render_layer", None),
        # ("properties_scene", ((
        #     "RENDER_PT_dimensions",
        #     "RENDER_PT_output",
        #     "RENDER_PT_post_processing",
        # ), False)),
        ("properties_scene", None),
        ("properties_data_camera", None),
        ("properties_data_mesh", None),
        ("properties_physics_common", None),
        ("properties_physics_dynamicpaint", None),
        ("properties_physics_field", None),
        ("properties_physics_cloth", None),
        ("properties_physics_fluid", None),
        ("properties_physics_rigidbody_constraint", None),
        ("properties_physics_rigidbody", None),
        ("properties_physics_smoke", None),
        ("properties_physics_softbody", None),
        ("properties_particle", None),
    )

    @classmethod
    def _compatible(cls, mod, panels, remove=False):
        import bl_ui

        mod = getattr(bl_ui, mod)
        if panels is None:
            for c in mod.__dict__.values():
                ce = getattr(c, "COMPAT_ENGINES", None)
                if ce is not None:
                    if remove:
                        ce.remove(cls.bl_idname)
                    else:
                        ce.add(cls.bl_idname)
        else:
            classes, exclude = panels
            if exclude:
                for c in mod.__dict__.values():
                    if c.__name__ not in classes:
                        ce = getattr(c, "COMPAT_ENGINES", None)
                        if ce is not None:
                            if remove:
                                ce.remove(cls.bl_idname)
                            else:
                                ce.add(cls.bl_idname)
            else:
                for c in classes:
                    ce = getattr(mod, c).COMPAT_ENGINES
                    if remove:
                        ce.remove(cls.bl_idname)
                    else:
                        ce.add(cls.bl_idname)

    @classmethod
    def register_class(cls, _cls):
        cls._CLASSES.append(_cls)
        return _cls

    @classmethod
    def register(cls):
        for mod, panels in cls._COMPATIBLE_PANELS:
            cls._compatible(mod, panels)
        for _cls in cls._CLASSES:
            bpy.utils.register_class(_cls)

    @classmethod
    def unregister(cls):
        for mod, panels in cls._COMPATIBLE_PANELS:
            cls._compatible(mod, panels, True)
        for _cls in cls._CLASSES:
            bpy.utils.unregister_class(_cls)

    @classmethod
    def is_active(cls, context):
        return context.scene.render.engine == cls.bl_idname

    def update(self, data, depsgraph):
        engine.update(self, data, depsgraph)

    def render(self, depsgraph):
        engine.render(self, depsgraph)

    def view_update(self, context):
        engine.view_update(self, context)

    def view_draw(self, context):
        engine.view_draw(self, context.depsgraph, context.region, context.space_data, context.region_data)

    def __del__(self):
        engine.free(self)


def register():
    from . import addon_preferences
    addon_preferences.register()

    from . import props
    from . import nodes
    from . import ops
    from . import ui
    from . import engine
    from . import addon_preferences

    bpy.utils.register_class(ArnoldRenderEngine)
    nodes.register()


def unregister():
    from . import addon_preferences
    from . import props
    from . import nodes
    from . import ops
    from . import ui
    from . import engine
    from . import addon_preferences
    addon_preferences.unregister()
    bpy.utils.unregister_class(ArnoldRenderEngine)
    nodes.unregister()
