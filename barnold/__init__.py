# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

bl_info = {
    "name"          : "B-Arnold",
    "description"   : "Arnold Render integration",
    "author"        : "N.Ildar <nildar@users.sourceforge.net>",
    "version"       : (0, 0, 1),
    "blender"       : (2, 75, 0),
    "location"      : "Info header, render engine menu",
    "category"      : "Render"
}

import bpy


class ArnoldRenderEngine(bpy.types.RenderEngine):
    bl_idname = "ARNOLD_RENDER"
    bl_label = "Arnold Render"

    bl_use_shading_nodes_custom = False

    _CLASSES = []  # classes for (un)register

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
        ("properties_data_lamp", ((
            "DATA_PT_context_lamp",
            #"DATA_PT_area",
            "DATA_PT_custom_props_lamp",
        ), False)),
        ("properties_material", ((
            "MATERIAL_PT_context_material",
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

    def update(self, data, scene):
        engine.update(self, data, scene)

    def render(self, scene):
        engine.render(self, scene)

    def view_update(self, context):
        engine.view_update(self, context)

    def view_draw(self, context):
        engine.view_draw(self, context)

    def __del__(self):
        engine.free(self)


from . import engine
from . import props
from . import nodes
from . import ops
from . import ui


def register():
    bpy.utils.register_class(ArnoldRenderEngine)
    nodes.register()


def unregister():
    bpy.utils.unregister_class(ArnoldRenderEngine)
    nodes.unregister()
