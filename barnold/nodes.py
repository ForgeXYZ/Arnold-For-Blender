# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import bpy
import nodeitems_utils
from bpy.props import BoolProperty

from . import ArnoldRenderEngine


class ArnoldOutputNode(bpy.types.Node):
    bl_label = "Output"
    bl_icon = 'MATERIAL'

    def _get_active(self):
        return not self.mute

    def _set_active(self, value=True):
        for node in self.id_data.nodes:
            if isinstance(node, ArnoldOutputNode):
                node.mute = (self != node)

    is_active = BoolProperty(
        name="Active",
        description="Active Output",
        get=_get_active,
        set=_set_active
    )

    def init(self, context):
        self._set_active()
        sock = self.inputs.new("NodeSocketShader", "Shader")

    def draw_buttons(self, context, layout):
        layout.prop(self, "is_active", icon='RADIOBUT_ON' if self.is_active else 'RADIOBUT_OFF')


class ArnoldLambertNode(bpy.types.Node):
    bl_label = "Lambert"
    bl_icon = 'MATERIAL'

    def init(self, context):
        sock = self.inputs.new("NodeSocketFloat", "Kd")
        sock.default_value = 0.7
        sock = self.inputs.new("NodeSocketColor", "Kd_color")
        sock.default_value = (1, 1, 1, 1)
        sock = self.inputs.new("NodeSocketColor", "opacity")
        sock.default_value = (1, 1, 1, 1)

        self.outputs.new("NodeSocketShader", "RGB", "output")


class ArnoldNodeCategory(nodeitems_utils.NodeCategory):
    @classmethod
    def poll(cls, context):
        return (
            ArnoldRenderEngine.is_active(context) and
            context.space_data.tree_type == 'ShaderNodeTree'
        )


def register():
    from nodeitems_builtins import ShaderNewNodeCategory, ShaderOldNodeCategory

    def _poll(fn):
        @classmethod
        def wrapped(cls, context):
            return (
                not ArnoldRenderEngine.is_active(context) and
                fn(context)
            )
        return wrapped

    ShaderNewNodeCategory.poll = _poll(ShaderNewNodeCategory.poll)
    ShaderOldNodeCategory.poll = _poll(ShaderOldNodeCategory.poll)

    bpy.utils.register_class(ArnoldOutputNode)
    bpy.utils.register_class(ArnoldLambertNode)

    node_categories = [
        ArnoldNodeCategory("ARNOLD_OUTPUT_NODES", "Output", items=[
            nodeitems_utils.NodeItem("ArnoldOutputNode")
        ]),
        ArnoldNodeCategory("ARNOLD_SHADERS_NODES", "Shaders", items=[
            nodeitems_utils.NodeItem("ArnoldLambertNode")
        ]),
    ]
    nodeitems_utils.register_node_categories("ARNOLD_NODES", node_categories)


def unregister():
    nodeitems_utils.unregister_node_categories("ARNOLD_NODES")

    bpy.utils.unregister_class(ArnoldOutputNode)
    bpy.utils.unregister_class(ArnoldLambertNode)
