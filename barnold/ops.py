# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import traceback

import bpy
from bpy.types import Operator
from bpy.props import (
    BoolProperty,
    StringProperty
)
from bpy_extras.io_utils import ExportHelper
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


@ArnoldRenderEngine.register_class
class ArnoldNodeSocketAdd(Operator):
    bl_idname = "barnold.node_socket_add"
    bl_options = {'INTERNAL'}
    bl_label = "Create Socket"
    
    identifier = StringProperty()

    def execute(self, context):
        node = context.node
        inputs = node.inputs
        identifier = self.identifier
        for i in (i for i in inputs if i.identifier == identifier):
            inputs.remove(i)
            break
        else:
            node.create_socket(identifier)
        return {'FINISHED'}


@ArnoldRenderEngine.register_class
class ArnoldLightFilterInputAdd(Operator):
    bl_idname = "barnold.light_filter_add"
    bl_options = {'INTERNAL'}
    bl_label = "Add Filter"
    bl_description = "Add Filter input"

    def execute(self, context):
        node = context.active_node
        inputs = node.inputs
        inputs.new("ArnoldNodeSocketFilter", "Filter", "filter")
        node.active_filter_index = len(inputs) - 1
        return {'FINISHED'}


@ArnoldRenderEngine.register_class
class ArnoldLightFilterInputRemove(Operator):
    bl_idname = "barnold.light_filter_remove"
    bl_options = {'INTERNAL'}
    bl_label = "Remove Filter"
    bl_description = "Remove Filter input"

    @classmethod
    def poll(cls, context):
        node = context.active_node
        index = node.active_filter_index
        if 0 < index < len(node.inputs):
            return True
        return False

    def execute(self, context):
        node = context.active_node
        inputs = node.inputs
        index = node.active_filter_index
        input = inputs[index]
        inputs.remove(input)
        if index == len(node.inputs):
            node.active_filter_index -= 1
        return {'FINISHED'}


@ArnoldRenderEngine.register_class
class ArnoldExportASS(Operator, ExportHelper):
    bl_idname = "barnold.export_ass"
    bl_label = "Export ASS"

    filename_ext = ".ass"
    filter_glob = StringProperty(default="*.ass", options={'HIDDEN'})
    binary = BoolProperty(name="Binary-encode ASS File", default=True)
    open_procs = BoolProperty(name="Expand Procedurals")

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
                    self.filepath,
                    self.open_procs,
                    self.binary
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
