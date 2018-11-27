# Arnold For Blender (BtoA) Beta
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=5D8ZMMACFUX36)
![](https://cdn.rawgit.com/tyler-furby/barnold/master/arnold%20logo.svg)

Arnold integration with Blender, updated to work with the latest versions of Arnold 5.2.1.0 and Blender 2.8. This is not yet production ready, but will be soon... :balloon:

Join the Discord channel for discussions/help/updates/feature requests/talk about water coolers: https://discord.gg/WNdNXzZ

Update: Working on the offical version of this addon, will post more information as that project progresses further.

```
Barnold v1.0 Roadmap                   [###########              ] 40% Complete
```
### Currently In Development: 
- Fixing the IPR (rendered viewport)
- Supporting Blender 2.8
- Cleaning up UI
- VDB & AOV Support

### Installation (Windows, macOS, and Linux)
- Download this repository.
- Download the Arnold 5.2.1.0 SDK here: https://www.solidangle.com/arnold/download/#arnold-sdk
- Add a new environment variable `ARNOLD_HOME` and add the path of the downloaded arnold SDK from the previous step.
- Add a second environment variable to `PATH` to the arnold SDK `bin` folder.
- Add `barnold` directory to `path\to\blender\2.79\scripts\addons`
- Open the `Arnold SDK Adjustments\plugins` folder the `driver_display_callback.dll` (Windows) or `libbarnold_display_callback.dylib` (macOS) or `libbarnold_display_callback.so` (Linux) file needs to be placed inside the `ARNOLDSDK\plugins` folder.
- Open the `Arnold SDK Adjustments\arnold` folder, the `ai_drivers.py` file needs to be placed inside the `ARNOLDSDK\python\arnold` folder, overwriting the existing file.
- Open the `Arnold SDK Adjustments\arnold` folder, the `ai_universe.py` file needs to be placed inside the `ARNOLDSDK\python\arnold` folder, overwriting the existing file. 
- Enable "Auto Run Python Scripts" in blender by going to File>User Preferences>File tab 
- Enable the plugin in blender by going to File>User Preferences>Add-ons tab>Search for 'arnold' in the search bar, and clicking the checkbox next to `Render: Barnold` to enable this plugin.

### Complete Barnold Documentation (coming soon)

### About
I'm actively working on this every day, if you have any issues feel free to contact me at tyler@tylerfurby.com,
I will ensure this plugin supports all future updates to Blender and Arnold renderer.

![Blender loves arnold](https://cdn.rawgit.com/tyler-furby/Furby-Studios-Website-Files/a449e03a/images/Untitled-1.png)
