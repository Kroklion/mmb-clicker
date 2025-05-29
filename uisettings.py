import bpy
from bpy.types import Operator, AddonPreferences

from . import log

def updateInner(self, variable_name):
    if variable_name in ClickerPreferences.callbacks:
        for callback in ClickerPreferences.callbacks.get(variable_name, []):
            callback(getattr(self, variable_name))
    else:
        log.warning("No callback set for: " + variable_name)
    pass

def updateLogLevel(self, context):
    updateInner(self, 'debug_level')
    
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
        update=updateLogLevel
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
        layout.prop(self, 'debug_level')
