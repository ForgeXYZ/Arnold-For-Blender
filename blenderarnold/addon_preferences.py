import bpy
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty
import os
import sys

import platform
import io as IO
import shutil


class ArnoldAddonPreferences(AddonPreferences):
    bl_idname = __package__

    arnold_path: StringProperty(
        name="Arnold Path",
        subtype="DIR_PATH")

    draw_panel_icon: BoolProperty(
        name="Draw Panel Icon",
        description="Draw an icon on Arnold Panels",
        default=True)

    def draw(self, context):
        layout = self.layout
        layout.label(text="IMPORTANT NOTICE:")
        layout.label(text="if you have an ARNOLD_HOME environment set,it will \
        override whatever setting you input here.")
        layout.prop(self, "arnold_path")

        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator(InstallMaterialX.bl_idname, text="Install MaterialX")


class InstallMaterialX(bpy.types.Operator):
    bl_idname = "install.materialx"
    bl_label = "Install MaterialX"
    bl_options = {'REGISTER'}
 
    def execute(self, context):
        # Get Resource User Paths for installing lib into blender's python
        resource_path = bpy.utils.resource_path('LOCAL', major=bpy.app.version[0],
                                                minor=bpy.app.version[1])
        user_path = bpy.utils.resource_path('USER', major=bpy.app.version[0],
                                            minor=bpy.app.version[1])
        local_path = resource_path
        bpy_dir = os.path.join(resource_path, 'python')
        config_dir = os.path.join(user_path, 'scripts/config')
 
        # Climb up path
        uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])
        addon_path = os.path.dirname(__file__)
        # Library Directory
        dist_dir = os.path.join(addon_path, "lib", 'dist')

        print(platform.system())
 
        # Windows
        if platform.system() == 'Windows':
            IO.info("OS Type: Windows. Installing MaterialX for Windows 10")
            mtlx_lib = os.path.join(dist_dir, 'win', 'MaterialX.zip')
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            # Check for Admin Privileges
            if is_admin != 1:
                IO.error("Cannot Install MaterialX. Run Blender as an Administrator")
            # Unpack the library to the blender installation from config
            site_packages = os.path.join(bpy_dir, 'lib', 'site-packages')
            shutil.unpack_archive(mtlx_lib, site_packages)
            IO.info("MaterialX unpacked and installed here: %s" % site_packages)
 
        # OSX
        elif platform.system() == 'darwin':
            IO.info("OS Type: OSX. Material Pipeline currently unsupported.")
            pass
            # TODO: Unpack the library to the blender installation from config
 
        # Linux
        elif platform.system().lower() == 'linux':
            print("OS Type: Linux. Installing MaterialX for Linux")
            mtlx_lib = os.path.join(dist_dir, 'linux', 'MaterialX.tar.xz')
            site_packages = os.path.join(bpy_dir, 'lib', 'python3.5', 'site-packages')
            shutil.unpack_archive(mtlx_lib, site_packages)
            print("MaterialX unpacked and installed here: %s" % site_packages)
 
        # TODO: After installtion, set install flags to disable the operator via poll
        # conf.materialx_lib = True
        # scn = context.scene
        # libs.materialx_lib = True
        self.report({'INFO'}, "MaterialX Installed")
 
        return {'FINISHED'}


# Registration
def register():
    bpy.utils.register_class(ArnoldAddonPreferences)
    bpy.utils.register_class(InstallMaterialX)
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
    bpy.utils.unregister_class(InstallMaterialX)



if __name__ == "__main__":
    register()
