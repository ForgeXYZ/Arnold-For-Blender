# Barnold (beta) Status: :yellow_heart: 
Arnold integration with Blender, updated to work with Arnold 5.1 and Blender 2.79b

### Needs Fixing
- Show bucket tiles during render from within Blender's Image Editor
- Changing Standard Surface shader diffuse colors doesn't work, stuck on white, most likely due to `kr_color`
- Node system for all Lambert, Standard Surface, Flat, and Hair shaders
- IPR, currently just renders to a png, need a way for the IPR to work within Blender's viewport
- Renders are upside down, kind of weird...
- Adding multipliers for Diffuse, Glossy, Transmission to Camera(AA) samples

### Installation
- Ensure the Arnold 5.1 SDK is installed and environment variable is set
- Add Arnold SDK directory to line 22 of `/barnold/engine/__init__.py`
- Add Barnold to `/Blender/2.79/Scripts/Addons`

![Blender loves arnold](https://cdn.rawgit.com/tyler-furby/Furby-Studios-Website-Files/a449e03a/images/Untitled-1.png)
