# mmb-clicker

**mmb-clicker** is a Blender add-on that allows you to switch the interaction mode with a double-click of the middle mouse button (MMB). It also provides quick object switching and viewport navigation—faster than searching for the Tab key or a dropdown menu.

## Features

- **Mode Switching:**  
  Change interaction modes with a MMB double-click.
  
- **Object Select:**  
  Edit other object in same mode.
  
- **Viewport Navigation:**  
  Move the viewport by clicking, releasing, then clicking and holding the MMB (similar to using Shift + MMB).
  
- **Mouse:**  
  Best used with a "clicking scroll wheel."

## How It Works

1. **Switching Modes On Objects:**  
   Hover over an object and double-click the MMB. The add-on will cycle Blender's interaction mode based on the object type:
   
   - **Curve:** Toggles between `EDIT` and `OBJECT` mode.
   - **Mesh (without an armature modifier with armature set):** Toggles between `EDIT` and `OBJECT` mode.
   - **Mesh:** Toggles between `EDIT` and `WEIGHT_PAINT` mode.
   - **Armature:** Toggles between `POSE` and `EDIT` mode.
   
   **Workspace Mode:**
   Depending on the mode set in '3D View N panel -> Tool -> Workspace -> Mode' different cycles will be used: 
   - **Sculpting:** A Mesh will switch between `SCULPTING` and `EDIT` modes.
   - **Texture Paint:** A Mesh will switch between `TEXTURE_PAINT` and `VERTEX_PAINT` modes.

2. **Switching Modes On Empty Space:**  
   Double-click the MMB while the mouse cursor is over empty space to switch to `OBJECT` mode.

3. **Viewport Navigation:**  
   To move the 3D view, quickly perform this sequence:
   - **Click** the MMB and immediately **release**.
   - Then **click and hold** the MMB before dragging your mouse.
   
## Limitations

- **Orthographic Mode Flicker:**  
  When in orthographic mode, these actions may cause a brief flicker as Blender temporarily switches to perspective mode. Known issue, probably no solution.

## Installation

### For Blender 4.2+ Users

1. **Download:**  
   Download the repository as a ZIP file (Code → Download ZIP).

2. **Install the Add-on:**  
   In Blender, navigate to:
   - **Edit > Preferences > Add-ons > Add-Ons Settings** (click the dropdown symbol)
   - Select **Install from Disk** and point to the downloaded ZIP file.

### For Older Blender Versions

This add-on has mainly been tested on Blender 4.2 and 4.4. It also works in Blender 3.6 and may be compatible with other older versions. To install:

1. **Download:**
   As above
2. **Install the Add-on:**  
   In Blender, navigate to:
   - **Edit > Preferences > Add-ons**
   - Select **Install...** and point to the downloaded ZIP file.

## License

*GNU GENERAL PUBLIC LICENSE Version 3*

