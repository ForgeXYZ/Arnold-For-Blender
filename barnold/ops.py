# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import traceback

import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper
from . import ArnoldRenderEngine


@ArnoldRenderEngine.register_class
class ExportASS(Operator, ExportHelper):
    bl_idname = "arnold.export_ass"
    bl_label = "Export ASS"

    filename_ext = ".ass"
    filter_glob = StringProperty(default="*.ass", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return context.scene and context.scene.render.engine == ArnoldRenderEngine.bl_idname

    def execute(self, context):
        if self.filepath:
            try:
                from . import engine

                scene = context.scene
                render = scene.render
                resolution = render.resolution_percentage / 100
                engine.export_ass(
                    context.blend_data,
                    scene,
                    scene.camera,
                    int(render.resolution_x * resolution),
                    int(render.resolution_y * resolution),
                    ass_filepath=self.filepath
                )
                return {'FINISHED'}
            except Exception as e:
                self.report({'ERROR'}, traceback.format_exc())
        else:
            self.report({'WARNING'}, "Export ASS:\nEmpty path specified!")
        return {'CANCELLED'}

    @classmethod
    def register(cls):
        def menu_func(self, context):
            self.layout.operator_context = 'INVOKE_DEFAULT'
            self.layout.operator(cls.bl_idname, text="Arnold Render (.ass)")

        bpy.types.INFO_MT_file_export.append(menu_func)
