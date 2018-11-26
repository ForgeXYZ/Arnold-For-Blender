import os
import bpy
import bpy.utils.previews

arnold_icon_collections = {}
arnold_icons_loaded = False


def load_icons():
    global arnold_icon_collections
    global arnold_icons_loaded

    if arnold_icons_loaded:
        return arnold_icon_collections["main"]

    custom_icons = bpy.utils.previews.new()

    icons_dir = os.path.join(os.path.dirname(__file__))

    # # Render Current Frame
    # custom_icons.load("render", os.path.join(
    #     icons_dir, "arnold_render.png"), 'IMAGE')
    # # Start IPR
    # custom_icons.load("start_ipr", os.path.join(
    #     icons_dir, "arnold_rerender_controls.png"), 'IMAGE')
    # # Stop IPR
    # custom_icons.load("stop_ipr", os.path.join(
    #     icons_dir, "arnold_batch_cancel.png"), 'IMAGE')
    # # STart IT
    # custom_icons.load("start_it", os.path.join(
    #     icons_dir, "arnold_it.png"), 'IMAGE')
    # # Batch Render
    # custom_icons.load("batch_render", os.path.join(
    #     icons_dir, "arnold_batch.png"), 'IMAGE')
    # # Dynamic Binding Editor
    #
    # # Create PxrLM Material
    #
    # # Create Disney Material
    # custom_icons.load("pxrdisney", os.path.join(
    #     icons_dir, "render_PxrDisney.png"), 'IMAGE')
    # # Create Holdout
    #
    # # Open Linking Panel
    #
    # # Create Env Light
    # custom_icons.load("envlight", os.path.join(
    #     icons_dir, "arnold_RMSEnvLight.png"), 'IMAGE')
    # # Daylight
    # custom_icons.load("daylight", os.path.join(
    #     icons_dir, "arnold_PxrStdEnvDayLight.png"), 'IMAGE')
    # # Create GEO Area Light
    # custom_icons.load("geoarealight", os.path.join(
    #     icons_dir, "arnold_RMSGeoAreaLight.png"), 'IMAGE')
    # # Create Area Light
    # custom_icons.load("arealight", os.path.join(
    #     icons_dir, "arnold_RMSAreaLight.png"), 'IMAGE')
    # # Create Point Light
    # custom_icons.load("pointlight", os.path.join(
    #     icons_dir, "arnold_RMSPointLight.png"), 'IMAGE')
    # # Create Spot Light
    # #custom_icons.load("spotlight", os.path.join(icons_dir, "arnold_RMSPointLight.png"), 'IMAGE')
    #
    # # Create Geo LightBlocker
    #
    # # Make Selected Geo Emissive
    #
    # # Create Archive node
    #
    # # Update Archive
    #
    # # Open Last RIB
    # custom_icons.load("open_last_rib", os.path.join(
    #     icons_dir, "arnold_open_last_rib.png"), 'IMAGE')
    # # Inspect RIB Selection
    #
    # # Shared Geometry Attribute
    #
    # # Add Subdiv Sheme
    #
    # custom_icons.load("add_subdiv_sheme", os.path.join(
    #     icons_dir, "arnold_subdiv.png"), 'IMAGE')
    # # Add/Atach Coordsys
    #
    # # Add/Create RIB Box
    # custom_icons.load("archive_RIB", os.path.join(
    #     icons_dir, "arnold_CreateArchive.png"), 'IMAGE')
    # # Open Tmake Window
    #
    # # Create OpenVDB Visualizer
    #
    # # RenderMan Doc
    # custom_icons.load("help", os.path.join(
    #     icons_dir, "arnold_help.png"), 'IMAGE')
    # # About RenderMan
    # custom_icons.load("info", os.path.join(
    #     icons_dir, "arnold_info.png"), 'IMAGE')
    #
    # # Reload plugin
    # custom_icons.load("reload_plugin", os.path.join(
    #     icons_dir, "arnold_loadplugin.png"), 'IMAGE')

    # RenderMan for Blender UI-Panels Icon - "R"
    custom_icons.load("arnold_logo", os.path.join(
        icons_dir, "arnold_blender.png"), 'IMAGE')

    arnold_icon_collections["main"] = custom_icons
    arnold_icons_loaded = True

    return arnold_icon_collections["main"]


def clear_icons():
    global arnold_icons_loaded
    for icon in arnold_icon_collections.values():
        bpy.utils.previews.remove(icon)
    arnold_icon_collections.clear()
    arnold_icons_loaded = False
