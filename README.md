# Barnold (beta) Status: :green_heart: 
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=5D8ZMMACFUX36)
![](https://cdn.rawgit.com/tyler-furby/barnold/master/arnold%20logo.svg)

Arnold integration with Blender, updated to work with the latest versions of Arnold 5.2 and Blender 2.79b. This is not yet production ready, but will be soon... **WE ARE NOW OFFICIALY IN BETA** :balloon:

Join the Discord channel for discussions/help/updates/feature requests/talk about water coolers: https://discord.gg/WNdNXzZ

```
Barnold v1.0 Roadmap                   [###                         ] 10% Complete
```
### Needs Fixing
- Fix IPR (rendered viewport)

### Installation
#### Windows
- Download this repository.
- Download the Arnold 5.2.0.0 SDK here: https://www.solidangle.com/arnold/download/product-download/?id=2395
- Add a new environment variable `ARNOLD_HOME` -> `C:\Program Files\Blender Foundation\Blender\2.79\scripts\modules\Arnold-5.2.0.0-windows` 
- Add `barnold` directory to `path\to\blender\2.79\scripts\addons`
- Open the `Arnold SDK Adjustments for Windows\plugins` folder the `driver_display_callback.dll` file needs to be placed inside the `Arnold-5.2.0.0-windows\plugins` folder.
- Open the `Arnold SDK Adjustments for Windows\arnold` folder, the `ai_drivers.py` file needs to be placed inside the `Arnold-5.2.0.0-windows\python\arnold` folder, overwriting the existing file.
- Open the `Arnold SDK Adjustments for Windows\arnold` folder, the `ai_universe.py` file needs to be placed inside the `Arnold-5.2.0.0-windows\python\arnold` folder, overwriting the existing file. 
- Enable "Auto Run Python Scripts" in blender by going to File>User Preferences>File tab 
- Enable the plugin in blender by going to File>User Preferences>Add-ons tab>Search for 'arnold' in the search bar, and clicking the checkbox next to `Render: Barnold` to enable this plugin.

#### macOS
- Download this repository.
- Download the Arnold 5.2.0.0 SDK here: https://www.solidangle.com/arnold/download/product-download/?id=2397
- Add `ARNOLD_HOME` as an environment variable.
- Add `barnold` directory to `path\to\blender\2.79\scripts\addons`
- Open the `Arnold SDK Adjustments for Windows\arnold` folder, the `ai_drivers.py` file needs to be placed inside the `Arnold-5.2.0.0-darwin\python\arnold` folder, overwriting the existing file.
- Open the `Arnold SDK Adjustments for Windows\arnold` folder, the `ai_universe.py` file needs to be placed inside the `Arnold-5.2.0.0-darwin\python\arnold` folder, overwriting the existing file. 
- Enable "Auto Run Python Scripts" in blender by going to File>User Preferences>File tab 
- Enable the plugin in blender by going to File>User Preferences>Add-ons tab>Search for 'arnold' in the search bar, and clicking the checkbox next to `Render: Barnold` to enable this plugin.

#### Linux installation instructions coming soon...

### Complete Barnold Documentation (coming soon)

### About
I'm actively working on this every day, if you have any issues feel free to contact me at tyler@tylerfurby.com,
I will ensure this plugin supports all future updates to Blender and Arnold renderer.

![Blender loves arnold](https://cdn.rawgit.com/tyler-furby/Furby-Studios-Website-Files/a449e03a/images/Untitled-1.png)
