# Barnold (beta) Status: :yellow_heart: 
Arnold integration with Blender, updated to work with Arnold 5.1 and Blender 2.79b. This is not yet production ready, but will be soon...

### Needs Fixing
- Add metalness parameter to "Base" section of shader panel
- Transmission/Refraction/Caustics are not rendering
- Emission needs to be configured to work properly with Standard Surface
- Show bucket tiles during render from within Blender's Image Editor
- Node system for all Lambert, Standard Surface, Flat, and Hair shaders
- IPR, currently just renders to a png, need a way for the IPR to work within Blender's viewport
- Renders are upside down, kind of weird...

### Installation
#### Windows
- Download the Arnold 5.1.1.0 SDK [here](https://www.solidangle.com/arnold/download/product-download/?id=2285) and save this directory in `path\to\blender\2.79\scripts\modules\Arnold-5.1.1.0-windows`
- Add environment variable to "PATH" -> `path\to\blender\2.79\scripts\modules\Arnold-5.1.1.0-windows\bin` 
  ##### If you don't know how to set environment variables in Windows:
  - In Search, search for and then select: System (Control Panel)
  - Click the Advanced system settings link.
  - Click Environment Variables. In the section System Variables, find the PATH environment variable and select it. Click Edit.
  - Click New.
  - In the Edit System Variable (or New System Variable) window, specify the value of the PATH environment variable: `\path\to\blender\2.79\scripts\modules\Arnold-5.1.1.0-windows\bin` 
  - Click OK. 
  - Close all remaining windows by clicking OK.
  - Restart computer.
- Add `barnold` directory to `path\to\blender\2.79\scripts\addons`
- Edit line 22 of `path\to\blender\2.79\scripts\addons\barnold\engine\__init__.py` to `sys.path.append(r"path\to\blender\2.79\scripts\modules\Arnold-5.1.1.0-windows\python")`
- Enable the plugin in blender by going to File>User Preferences>Add-ons tab>Search for 'arnold' in the search bar, and clicking the checkbox next to `Render:B-Arnold` to enable this plugin.

#### Linux & macOS installation instructions coming soon...

### Complete Barnold Documentation (coming soon)

### About
I'm actively working on this every day, if you have any issues feel free to contact me at tyler@tylerfurby.com,
I will ensure this plugin supports all future updates to Blender and Arnold renderer.

![Blender loves arnold](https://cdn.rawgit.com/tyler-furby/Furby-Studios-Website-Files/a449e03a/images/Untitled-1.png)
