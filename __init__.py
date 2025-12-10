import sys

if "bpy" in locals():
    # clear submodules for reload
    if __name__ in sys.modules:
        del sys.modules[__name__]

    d_name = __name__ + "."
    for name in tuple(sys.modules):
        if name.startswith(d_name):
            del sys.modules[name]

import bpy

from .modalop import EVENTKEYMAP_OT_Clicker_Addon, keymap_initialize, keymap_remove
from .uisettings import ClickerPreferences
from . import log

ADDON_NAME = __package__.split('.')[-1]

'''
Legacy Addon Info
'''

bl_info = {
    "name": "mmb-clicker",
    "author": "Kroklion",
    "version": (0, 7),
    "blender": (3, 6, 0),
    "location": "Preferences > Add-ons > mmb-clicker",
    "description": "Switch object interaction mode on middle mouse button double click",
    "warning": "",
    "doc_url": "",
    "category": "Convenience",
}

'''Addon loading'''

classes = (
    ClickerPreferences,
    EVENTKEYMAP_OT_Clicker_Addon,
)

class_register, class_unregister = bpy.utils.register_classes_factory(classes)

def register():
    log.init_logger(ADDON_NAME)
    
    class_register()
    log.setup_preferences_cb()  # must be after Preferences registered
    log.info('called')
    keymap_initialize()
    
def unregister():
    log.info('called')
    keymap_remove()
    class_unregister()
    log.uninit_logger()
    

if __name__ == "__main__":
    # this is not reached when loaded as extension
    register()
