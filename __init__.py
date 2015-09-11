# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

bl_info = {
    "name"			: "B-Arnold",
    "description"	: "Arnold Render integration",
    "author"		: "N.Ildar <nildar@users.sourceforge.net>",
    "version"		: (0, 0, 1),
    "blender"		: (2, 75, 0),
    "location"		: "Info header, render engine menu",
    "category"		: "Render"
}

import bpy
from . import engine

# TODO: Clean
_RELOAD_ENGINE = False


class ArnoldEngine(bpy.types.RenderEngine):
    bl_idname = "ARNOLD_RENDER"
    bl_label = "Arnold Render"

    use_highlight_tiles = True

    _COMPATIBLE_PANELS = (
        ("properties_render", ((
            "RENDER_PT_render",
            "RENDER_PT_dimensions",
            "RENDER_PT_output",
            "RENDER_PT_post_processing",
        ), False)),
        ("properties_world", ((
            "WORLD_PT_context_world",
            "WORLD_PT_custom_props",
        ), False)),
        ("properties_material", ((
            "MATERIAL_PT_context_material",
            #"MATERIAL_PT_preview",
            "MATERIAL_PT_custom_props",
        ), False)),
        ("properties_texture", None),
        #("properties_texture", (
        #    "TEXTURE_PT_context_texture",
        #    "TEXTURE_PT_preview",
        #    "TEXTURE_PT_image",
        #    #"TEXTURE_PT_image_sampling",
        #    #"TEXTURE_PT_image_mapping",
        #    "TEXTURE_PT_mapping",
        #    #"TEXTURE_PT_influence",
        #), False)),
        ("properties_render_layer", None),
        ("properties_scene", None),
        ("properties_data_camera", None),
        ("properties_data_mesh", None),
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
    def register(cls):
        for mod, panels in cls._COMPATIBLE_PANELS:
            cls._compatible(mod, panels)

    @classmethod
    def unregister(cls):
        for mod, panels in cls._COMPATIBLE_PANELS:
            cls._compatible(mod, panels, True)

    def __init__(self):
        # TODO: Clean
        global _RELOAD_ENGINE
        if _RELOAD_ENGINE:
            print("reload engine")
            __import__("importlib").reload(engine)
        else:
            _RELOAD_ENGINE = True

    def update(self, data, scene):
        engine.update(self, data, scene)

    def render(self, scene):
        engine.render(self, scene)


def register():
    bpy.utils.register_class(ArnoldEngine)


def unregister():
    bpy.utils.unregister_class(ArnoldEngine)
