import bpy
import time
from enum import Enum
from bpy.types import Operator

from . import log
from .uisettings import ClickerPreferences

IDNAME = 'wm.clicker_controlling'


def keymap_initialize():
    keymap_remove()  # clean up possible crashed remains

    keyconfigs_addon = bpy.context.window_manager.keyconfigs.addon
    if keyconfigs_addon:
        keymap_view3d = keyconfigs_addon.keymaps.new(
            name="3D View", space_type='VIEW_3D')
        _ = keymap_view3d.keymap_items.new(IDNAME, 'MOUSEMOVE', 'ANY')
        _ = keymap_view3d.keymap_items.new(IDNAME, 'MIDDLEMOUSE', 'ANY')
        _ = keymap_view3d.keymap_items.new(IDNAME, 'WINDOW_DEACTIVATE', 'ANY')
    else:
        log.error("Cannot add keymap items!")


def keymap_remove():
    keyconfigs_addon = bpy.context.window_manager.keyconfigs.addon
    if keyconfigs_addon:
        for map in keyconfigs_addon.keymaps:
            if map.name == "3D View":
                for item in map.keymap_items:
                    if item.idname == IDNAME:
                        map.keymap_items.remove(item)
                break

class Keystate(Enum):
    IDLE = 1
    DOWN1 = 2
    UP1 = 3
    DOWN2 = 4
    

# Globals, because members in this special Operator class aren't kept.
key_state = Keystate.IDLE
last_click = 0
last_x = last_y = 0

class EVENTKEYMAP_OT_Clicker_Addon(Operator):
    bl_idname = IDNAME
    bl_label = "Clicker Mode Control"

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if context is None or event is None or context.region is None:
            return {'PASS_THROUGH'}
        
        global key_state
        global last_x, last_y, last_click
        
        current = time.time()

        # logging purpose
        key_state_prev = key_state

        click_time = ClickerPreferences.get_instance(
            context).click_detection_time
        pixels = ClickerPreferences.get_instance(context).drag_detection_px

        move_distance_exceeded = abs(
            event.mouse_x - last_x) > pixels or abs(event.mouse_y - last_y) > pixels
        time_exceeded = (current - last_click) > click_time

        if key_state == Keystate.IDLE:
            if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                last_click = current
                key_state = Keystate.DOWN1

                last_x = event.mouse_x
                last_y = event.mouse_y

                # swallow the keydown
                log.info(str(key_state_prev) + " << " + event.type +
                          "/" + event.value + " -> " + str(key_state))
                return {'RUNNING_MODAL'}

        elif key_state == Keystate.DOWN1:
            if event.type == 'MIDDLEMOUSE' and event.value == 'RELEASE':
                if time_exceeded or move_distance_exceeded:
                    key_state = Keystate.IDLE
                else:
                    key_state = Keystate.UP1
                    last_click = current

            elif event.type == 'MOUSEMOVE':
                if time_exceeded or move_distance_exceeded:
                    log.info(
                        "DOWN1: mouse/time moved too much, handing over to rotate.")
                    bpy.ops.view3d.rotate('INVOKE_DEFAULT')
                    key_state = Keystate.IDLE

        elif key_state == Keystate.UP1:
            if time_exceeded or move_distance_exceeded:
                log.info("UP1: mouse/time moved too much, resetting.")
                key_state = Keystate.IDLE
            elif event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                if event.shift or event.ctrl or event.alt or event.oskey:  # Ignore
                    key_state = Keystate.IDLE
                elif not time_exceeded:
                    key_state = Keystate.DOWN2
                else:
                    bpy.ops.view3d.rotate('INVOKE_DEFAULT')
                    key_state = Keystate.IDLE

        elif key_state == Keystate.DOWN2:
            if event.type == 'MIDDLEMOUSE' and event.value == 'RELEASE':
                if event.shift or event.ctrl or event.alt or event.oskey:  # Ignore
                    key_state = Keystate.IDLE
                elif not time_exceeded:
                    if move_distance_exceeded:
                        log.info(
                            "mouse moved too much, handing over to rotate.")
                        bpy.ops.view3d.rotate('INVOKE_DEFAULT')
                        key_state = Keystate.IDLE
                    else:
                        key_state = Keystate.IDLE
                        if bpy.ops.view3d.clicker_mode_switcher:
                            bpy.ops.view3d.clicker_mode_switcher(
                                mouse_x=event.mouse_x, mouse_y=event.mouse_y)
                else:
                    key_state = Keystate.IDLE
            elif event.type == 'MOUSEMOVE':
                if move_distance_exceeded:
                    log.info('BeginDrag')
                    bpy.ops.view3d.move('INVOKE_DEFAULT')
                    key_state = Keystate.IDLE

            elif event.type == 'WINDOW_DEACTIVATE':
                key_state = Keystate.IDLE

        log.debug(str(key_state_prev) + " << " + event.type + "/" + event.value + " -> " + str(key_state))
        
        if key_state == Keystate.DOWN2:
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}
