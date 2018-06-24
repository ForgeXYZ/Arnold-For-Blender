# Barnold (beta) Status: :yellow_heart: 
Arnold integration with Blender, updated to work with Arnold 5.1 and Blender 2.79b

### Needs Fixing
- Add metalness parameter to "Base" section of shader panel
- Transmission/Refraction/Caustics are not rendering
- Emission needs to be configured to work properly with Standard Surface
- Show bucket tiles during render from within Blender's Image Editor
- Node system for all Lambert, Standard Surface, Flat, and Hair shaders
- IPR, currently just renders to a png, need a way for the IPR to work within Blender's viewport
- Renders are upside down, kind of weird...

### Installation
- Ensure the Arnold 5.1 SDK is downloaded and saved in `path\to\blender\2.79\scripts\modules\Arnold-5.1.1.0-windows`
- Add environment variable to "PATH" -> `path\to\blender\2.79\scripts\modules\Arnold-5.1.1.0-windows\bin`
- Add Arnold SDK's python folder(`path\to\blender\2.79\scripts\modules\Arnold-5.1.1.0-windows\python`) to line 22 of `/barnold/engine/__init__.py`
- Add Barnold to `/Blender/2.79/Scripts/Addons`

![Blender loves arnold](https://cdn.rawgit.com/tyler-furby/Furby-Studios-Website-Files/a449e03a/images/Untitled-1.png)
