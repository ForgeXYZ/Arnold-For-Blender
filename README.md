# Barnold (beta) Status: :green_heart: 
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=5D8ZMMACFUX36)
![](https://cdn.rawgit.com/tyler-furby/barnold/master/arnold%20logo.svg)

Arnold integration with Blender, updated to work with Arnold 5.1 and Blender 2.79b. This is not yet production ready, but will be soon... **WE ARE NOW OFFICIALY IN BETA** :balloon:

Join the Discord channel for discussions/help/updates/feature requests/talk about water coolers: https://discord.gg/WNdNXzZ

```
Barnold v1.0 Roadmap                   [##                         ] 5% Complete
```
### Needs Fixing
- Fix IPR (rendered viewport)

### Installation
#### Windows
- Download this repository.
- Download the Arnold 5.1.1.1 SDK here: https://www.solidangle.com/arnold/download/
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
- Open the `Arnold SDK Adjustments for Windows\plugins` folder the `driver_display_callback.dll` file needs to be placed inside the `Arnold-5.1.1.0-windows\plugins` folder.
- Open the `Arnold SDK Adjustments for Windows\arnold` folder, the `ai_drivers.py` file needs to be placed inside the `Arnold-5.1.1.0-windows\python\arnold` folder, overwriting the existing file. 
- Enable "Auto Run Python Scripts" in blender by going to File>User Preferences>File tab 
- Enable the plugin in blender by going to File>User Preferences>Add-ons tab>Search for 'arnold' in the search bar, and clicking the checkbox next to `Render:B-Arnold` to enable this plugin.

#### Linux & macOS installation instructions coming soon...

### Complete Barnold Documentation (coming soon)

### About
I'm actively working on this every day, if you have any issues feel free to contact me at tyler@tylerfurby.com,
I will ensure this plugin supports all future updates to Blender and Arnold renderer.

![Blender loves arnold](https://cdn.rawgit.com/tyler-furby/Furby-Studios-Website-Files/a449e03a/images/Untitled-1.png)
