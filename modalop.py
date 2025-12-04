import bpy
import time
from bpy.types import Operator
from enum import Enum

from . import log

IDNAME = 'wm.clicker_controlling'

def keymap_initialize():
    keymap_remove() # clean up possible crashed remains
        
    keyconfigs_addon = bpy.context.window_manager.keyconfigs.addon
    if keyconfigs_addon:
        keymap_view3d = keyconfigs_addon.keymaps.new(name="3D View", space_type='VIEW_3D')
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
lastmode_per_workspace = {}


class EVENTKEYMAP_OT_Clicker_Addon(Operator):
    bl_idname = IDNAME
    bl_label = "Clicker Mode Control"

    # Mode switching section
    mode_cycle_mesh = {
        'OBJECT': 'EDIT',
        'EDIT': 'WEIGHT_PAINT',
        'WEIGHT_PAINT': 'EDIT'
    }
    mode_cycle_mesh_no_wp = {
        'OBJECT': 'EDIT', 'EDIT': 'OBJECT'
    }
    mode_cycle_arma = {
        'OBJECT': 'POSE',
        'POSE': 'EDIT',
        'EDIT': 'POSE'
    }
    mode_cycle_curve = {
        'OBJECT': 'EDIT'
    }

    mode_cycle_map_default = {
        'MESH': mode_cycle_mesh,
        'ARMATURE': mode_cycle_arma,
        'CURVE': mode_cycle_curve
    }

    mode_cycle_mesh_sculpt = {
        'OBJECT': 'SCULPT',
        'SCULPT': 'EDIT',
        'EDIT': 'SCULPT'
    }
    mode_cycle_map_sculpt = {
        'MESH': mode_cycle_mesh_sculpt,
        'ARMATURE': mode_cycle_arma,
        'CURVE': mode_cycle_curve
    }

    mode_cycle_mesh_texpaint = {
        'OBJECT': 'TEXTURE_PAINT',
        'TEXTURE_PAINT': 'VERTEX_PAINT',
        'VERTEX_PAINT': 'TEXTURE_PAINT'
    }
    mode_cycle_map_texpaint = {
        'MESH': mode_cycle_mesh_texpaint,
        'ARMATURE': mode_cycle_arma,
        'CURVE': mode_cycle_curve
    }

    workspaces = {
        'SCULPT': mode_cycle_map_sculpt,
        'TEXTURE_PAINT': mode_cycle_map_texpaint,
        'DeFaUlT': mode_cycle_map_default
    }

    def get_armature_from_mod(self, context, mesh_obj):
        for mod in mesh_obj.modifiers:
            if mod.type == 'ARMATURE':
                return mod.object

    def switch_same_mode(self, context, current_mode, cycle_to_next=True, force_armature_remove=False):
        cycle_map = self.workspaces.get(context.window.workspace.object_mode)
        if not cycle_map:
            cycle_map = self.workspaces.get('DeFaUlT')

        cycle = cycle_map.get(context.active_object.type)
        if cycle is None:
            return  # lamps etc.
        next = cycle.get(current_mode) if cycle_to_next else current_mode

        log.info(f"{current_mode} -> {next}")

        armature = None

        if next == 'WEIGHT_PAINT':
            armature = self.get_armature_from_mod(
                context, context.active_object)
            if armature:
                armature.select_set(True)
            else:
                # no weightpainting, skip the step
                log.info("Armature not found")
                next = self.mode_cycle_mesh_no_wp.get(current_mode)

        if next is not None:
            bpy.ops.object.mode_set(mode=next)

        # sync heatmap displayed (active vertex group) with selected bone
        if armature and next == 'WEIGHT_PAINT' and context.active_pose_bone:
            name = context.active_pose_bone.name
            obj = context.active_object
            if obj is not None:
                vgroups = {}
                for vgroup in obj.vertex_groups:
                    if vgroup.name == name:
                        obj.vertex_groups.active_index = vgroup.index
                        break
        
        # deselect armature after weight paint
        if force_armature_remove or (current_mode == 'WEIGHT_PAINT' and next != 'WEIGHT_PAINT'):
            armature = self.get_armature_from_mod(
                context, context.active_object)
            if armature:
                armature.select_set(False)

    ''' perform a scripted click at mouse position (from event) in the given area '''

    def click_in_3d_view(self, area, event):
        bpy.ops.view3d.select(
            location=(event.mouse_x - area.x, event.mouse_y - area.y), deselect_all=True, object=True)

    def get_clicked_area(self, context, event):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                if event.mouse_x >= area.x and event.mouse_x < area.x + area.width and \
                        event.mouse_y >= area.y and event.mouse_y < area.y + area.height:
                    return area

    def handle_3d_view_click(self, context: bpy.context, event, area):
        global lastmode_per_workspace
        
        current_mode = context.active_object.mode if context.active_object else None
        current_ob = context.active_object if len(
            context.selected_objects) != 0 else None

        ws_name = context.window.workspace.name

        log.info(
            f"Current: {current_ob.name if current_ob is not None else None}, " +
            f"type {current_ob.type if current_ob is not None else None}, mode {current_mode}")

        # switch to object mode if not in Edit mode, at least in pose mode the click doesn't work otherwise
        if context.active_object and context.active_object.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')

        selected_objects = list(context.selected_objects)  # shallow copy
        log.info(f"Initially selected: {selected_objects}")


        # Deselect everything because otherwise Blender does its toggling thing
        context.view_layer.objects.active.select_set(False)
        for obj in context.selected_objects:
            obj.select_set(False)

        self.click_in_3d_view(area, event)

        log.info(f"Selected after click: {context.selected_objects}")

        log.info(
            f"Clicked: {context.selected_objects[0].name if len(context.selected_objects) > 0 else None}, " +
            f"type {context.selected_objects[0].type if len(context.selected_objects) > 0 else None}")

        new_ob = context.selected_objects[0] if len(
            context.selected_objects) > 0 else None

        bpy.ops.object.mode_set(mode='OBJECT')

        # restore additional selected objects if one of them was the new target
        if (new_ob in selected_objects or new_ob is None) and len(selected_objects) > 1:
            for obj in selected_objects:
                obj.select_set(True)

        # clicked on nothing - select last selected in object mode
        if new_ob is None:
            log.info("New ob is None, switch to Object mode")

            if current_ob is not None:
                current_ob.select_set(True)

                context.view_layer.objects.active = current_ob
                self.switch_same_mode(context, 'OBJECT', cycle_to_next=False,
                                      force_armature_remove=current_mode == 'WEIGHT_PAINT')

        # from None to an object, restore last saved mode
        elif current_ob is None:
            log.info(f"Previously None selected, restore from last mode")
            context.view_layer.objects.active = new_ob

            if ws_name in lastmode_per_workspace and new_ob.type in lastmode_per_workspace[ws_name]:
                next = lastmode_per_workspace[ws_name].get(new_ob.type)
                self.switch_same_mode(context, next, cycle_to_next=False)
            else:
                self.switch_same_mode(context, 'OBJECT')

        # clicked on selected, switch mode
        elif new_ob == current_ob:
            log.info(f"Clicked on same object, cycle mode")
            context.view_layer.objects.active = new_ob
            new_ob.select_set(True)

            if current_mode == 'OBJECT':
                if ws_name in lastmode_per_workspace and new_ob.type in lastmode_per_workspace[ws_name]:
                    next = lastmode_per_workspace[ws_name].get(new_ob.type)
                    log.info(f"Switch to mode: {next}")
                    self.switch_same_mode(context, next, cycle_to_next=False)
                else:
                    self.switch_same_mode(context, current_mode)
            else:
                self.switch_same_mode(context, current_mode)

        # clicked on other object of same type, enter same mode
        elif current_ob.type == new_ob.type:
            log.info(
                f"Different object but same type, select with same mode")
            context.view_layer.objects.active = new_ob

            if current_mode == 'OBJECT':
                if ws_name in lastmode_per_workspace and new_ob.type in lastmode_per_workspace[ws_name]:
                    next = lastmode_per_workspace[ws_name].get(new_ob.type)
                    log.info(f"Switch to mode: {next}")
                    self.switch_same_mode(context, next, cycle_to_next=False)
                else:
                    self.switch_same_mode(context, current_mode)
            else:
                self.switch_same_mode(context, current_mode,
                                      cycle_to_next=current_mode == 'OBJECT')

        # different object - enter last known mode
        else:
            log.info(
                f"Clicked on other object type, switch according to its last mode")
            context.view_layer.objects.active = new_ob

            if ws_name in lastmode_per_workspace and new_ob.type in lastmode_per_workspace[ws_name]:
                next = lastmode_per_workspace[ws_name].get(new_ob.type)
                log.info(f"Switch to mode: {next}")
                self.switch_same_mode(context, next, cycle_to_next=False)
            else:
                self.switch_same_mode(context, 'OBJECT')

        # store last mode depending on workspace
        if context.active_object and context.active_object.mode != 'OBJECT':
            lastmode_per_workspace.setdefault(
                ws_name, {})[context.active_object.type] = context.active_object.mode


    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if context is None or event is None or context.region is None:
            return {'PASS_THROUGH'}
        
        global key_state
        global last_x, last_y, last_click
        
        current = time.time()

        # logging purpose
        key_state_prev = key_state

        move_distance_exceeded = abs(
            event.mouse_x - last_x) > 10 or abs(event.mouse_y - last_y) > 10
        time_exceeded = (current - last_click) > 0.5

        if key_state == Keystate.IDLE:
            if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                last_click = current
                key_state = Keystate.DOWN1

                last_x = event.mouse_x
                last_y = event.mouse_y

                area = self.get_clicked_area(context, event)

                # swallow the keydown
                log.debug(str(key_state_prev) + " << " + event.type +
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
                    log.debug(
                        "DOWN1: mouse/time moved too much, handing over to rotate.")
                    bpy.ops.view3d.rotate('INVOKE_DEFAULT')
                    key_state = Keystate.IDLE

        elif key_state == Keystate.UP1:
            if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                if event.shift or event.ctrl or event.alt or event.oskey:  # Ignore
                    key_state = Keystate.IDLE
                elif not time_exceeded:
                    key_state = Keystate.DOWN2
                else:
                    bpy.ops.view3d.rotate('INVOKE_DEFAULT')
                    key_state = Keystate.IDLE
            if time_exceeded or move_distance_exceeded:
                log.debug("UP1: mouse/time moved too much, resetting.")
                key_state = Keystate.IDLE

        elif key_state == Keystate.DOWN2:
            if event.type == 'MIDDLEMOUSE' and event.value == 'RELEASE':
                if event.shift or event.ctrl or event.alt or event.oskey:  # Ignore
                    key_state = Keystate.IDLE
                elif not time_exceeded:
                    if move_distance_exceeded:
                        log.debug(
                            "mouse moved too much, handing over to rotate.")
                        bpy.ops.view3d.rotate('INVOKE_DEFAULT')
                        key_state = Keystate.IDLE
                    else:
                        area = self.get_clicked_area(context, event)
                        if area is not None:
                            self.handle_3d_view_click(context, event, area)
                        key_state = Keystate.IDLE
                else:
                    key_state = Keystate.IDLE
            elif event.type == 'MOUSEMOVE':
                if move_distance_exceeded:
                    log.debug('BeginDrag')
                    bpy.ops.view3d.move('INVOKE_DEFAULT')
                    key_state = Keystate.IDLE

            elif event.type == 'WINDOW_DEACTIVATE':
                key_state = Keystate.IDLE

        log.debug(str(key_state_prev) + " << " + event.type + "/" + event.value + " -> " + str(key_state))
        
        if key_state == Keystate.DOWN2:
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}
