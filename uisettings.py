import bpy
from bpy.types import AddonPreferences

from bpy.props import (
    IntProperty,
    FloatProperty
)

from . import log


def property_updated(self, variable_name):
    if variable_name in ClickerPreferences.callbacks:
        for callback in ClickerPreferences.callbacks.get(variable_name, []):
            callback(getattr(self, variable_name))
    else:
        log.warning("No callback set for: " + variable_name)
    pass

class ClickerPreferences(AddonPreferences):
    bl_idname = __package__
    
    debug_level : bpy.props.EnumProperty(
        name = "Debug Log Level",
        description = "Which log level to write in the console for addon debugging.",
        items = [
            ('FATAL', 'Off', ''),
            ('ERROR', 'Error', ''),
            ('WARNING', 'Warning', ''),
            ('INFO', 'Info', ''),
            ('DEBUG', 'Debug', '')
        ],
        update=lambda self, ctx: property_updated(self, 'debug_level')
    )

    click_detection_time: FloatProperty(
        name="Click Timeout",
        description="Double click detection time",
        default=0.5,
        min=0.1,
        soft_max=5
    )

    drag_detection_px: IntProperty(
        name="Drag Detection",
        description="Move tolerance in pixels during click",
        default=10,
        min=0,
        soft_max=50
    )
    
    @staticmethod
    def get_instance(context: bpy.types.Context = None) -> 'ClickerPreferences':
        prefs = (
            context or bpy.context).preferences.addons[__package__].preferences
        assert isinstance(prefs, ClickerPreferences)
        return prefs
    
    callbacks = {}
    
    @staticmethod
    def register_callback(prop_name, callback):
        if prop_name not in ClickerPreferences.callbacks:
            ClickerPreferences.callbacks[prop_name] = []
        ClickerPreferences.callbacks[prop_name].append(callback)
        
        # call back immediately with initial value
        prefs = ClickerPreferences.get_instance()
        value = getattr(prefs, prop_name)
        callback(value)
        

    @staticmethod
    def unregister_callback(prop_name, callback):
        if prop_name in ClickerPreferences.callbacks and callback in ClickerPreferences.callbacks[prop_name]:
            ClickerPreferences.callbacks[prop_name].remove(callback)
            if not ClickerPreferences.callbacks[prop_name]:
                del ClickerPreferences.callbacks[prop_name]

    

    def draw(self, context: bpy.types.Context):
        layout: bpy.types.UILayout = self.layout
        layout.prop(self, 'click_detection_time')
        layout.prop(self, 'drag_detection_px')
        layout.prop(self, 'debug_level')
