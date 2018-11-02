import bpy
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty
import os
import sys


class ArnoldAddonPreferences(AddonPreferences):
    bl_idname = __package__

    arnold_path = StringProperty(
        name="Arnold Path",
        subtype="DIR_PATH")

    def draw(self, context):
        layout = self.layout
        layout.label(text="IMPORTANT NOTICE:")
        layout.label(text="if you have an ARNOLD_HOME environment set,it will \
        override whatever setting you input here.")
        layout.prop(self, "arnold_path")

# Registration


def register():
    bpy.utils.register_class(ArnoldAddonPreferences)
    try:
        pth = os.environ["ARNOLD_HOME"]
        print("ARNOLD_HOME env found")

    except:
        print("ARNOLD_HOME env not found, using the preferences.")
        prefs = bpy.context.user_preferences.addons[__package__].preferences
        pth = prefs.arnold_path

    print("Setting Arnold path to: {}".format(pth))

    pth = os.path.join(pth, "python")

    if pth not in sys.path:
        sys.path.append(pth)



def unregister():
    bpy.utils.unregister_class(ArnoldAddonPreferences)



if __name__ == "__main__":
    register()
