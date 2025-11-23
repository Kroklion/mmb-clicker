import bpy
import time
from bpy.types import Operator
from mathutils import Vector

from . import log

from enum import Enum

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
    ALTERN = 5
    
key_state = Keystate.IDLE # member variable is not keeping a new value?????

last_click = 0
last_x = last_y = 0

view_perspective = ''
is_perspective = True
is_orthographic_side_view = False

initial_view_matrix = None
initial_location = None

lastmode_per_workspace = {}


class EVENTKEYMAP_OT_Clicker_Addon(Operator):
    bl_idname = IDNAME
    bl_label = "Clicker Mode Control"

    # Mode switching section
    mode_cycle_mesh = {'OBJECT': 'EDIT',
                       'EDIT': 'WEIGHT_PAINT', 'WEIGHT_PAINT': 'EDIT'}
    mode_cycle_mesh_no_wp = {'OBJECT': 'EDIT', 'EDIT': 'OBJECT'}
    mode_cycle_arma = {'OBJECT': 'POSE', 'POSE': 'EDIT', 'EDIT': 'POSE'}
    mode_cycle_curve = {'OBJECT': 'EDIT'}

    mode_cycle_mesh_sculpt = {'OBJECT': 'SCULPT',
                              'SCULPT': 'EDIT', 'EDIT': 'SCULPT'}
    mode_cycle_map_default = {'MESH': mode_cycle_mesh,
                              'ARMATURE': mode_cycle_arma, 'CURVE': mode_cycle_curve}
    mode_cycle_map_sculpt = {'MESH': mode_cycle_mesh_sculpt}

    workspaces = {'Sculpting': mode_cycle_map_sculpt,
                  'DeFaUlT': mode_cycle_map_default}

    def get_armature_from_mod(self, context, mesh_obj):
        for mod in mesh_obj.modifiers:
            if mod.type == 'ARMATURE':
                return mod.object

    def switch_same_mode(self, context, current_mode, cycle_to_next=True):
        cycle_map = self.workspaces.get(context.window.workspace.name)
        if not cycle_map:
            cycle_map = self.workspaces.get('DeFaUlT')

        cycle = cycle_map.get(context.active_object.type)
        if cycle is None:
            return  # lamps etc.
        next = cycle.get(current_mode) if cycle_to_next else current_mode

        log.debug(context.active_object.mode + ' -> ' + str(next))

        armature = None

        if next == 'WEIGHT_PAINT':
            armature = self.get_armature_from_mod(
                context, context.active_object)
            if armature:
                armature.select_set(True)
            else:
                # no weightpainting, skip the step
                # hardcode for now
                next = 'OBJECT'
                # next = cycle.get(next)

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
        if current_mode == 'WEIGHT_PAINT':
            armature = self.get_armature_from_mod(
                context, context.active_object)
            if armature:
                armature.select_set(False)


    ''' perform a scripted click at mouse position (from event) in the given area '''

    def click_in_3d_view(self, context, area, event):
        global view_perspective
        global is_orthographic_side_view
        global is_perspective

        # restore perspective
        if area is not None and len(area.spaces) > 0:
            log.debug("perspective restore " + str(view_perspective))
            area.spaces[0].region_3d.view_perspective = view_perspective
            area.spaces[0].region_3d.is_perspective = is_perspective
            area.spaces[0].region_3d.is_orthographic_side_view = is_orthographic_side_view
        
        # trigger the click
        with context.temp_override(
                window=context.window,
                area=area,
                region=[
                    region for region in area.regions if region.type == 'WINDOW'][0],
                screen=context.window.screen):
            bpy.ops.view3d.select(
                location=(event.mouse_x - area.x, event.mouse_y - area.y))

    def get_clicked_area(self, context, event):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                if event.mouse_x >= area.x and event.mouse_x < area.x + area.width and \
                        event.mouse_y >= area.y and event.mouse_y < area.y + area.height:
                    return area

    def handle_3d_view_click(self, context: bpy.context, event, area):
        global lastmode_per_workspace
        
        current_mode = context.active_object.mode if context.active_object else None
        current_ob_type = None
        current_ob = context.active_object
        ws_name = context.window.workspace.name

        # switch to object mode so we can determine what is under the mouse cursor by clicking
        # in Edit mode it just selects other vertices and doesn't change the selection if nothing
        # or another object is clicked
        if context.active_object:
            bpy.ops.object.mode_set(mode='OBJECT')
        selected_objects = list(context.selected_objects)  # shallow copy

        if context.active_object:
            current_ob_type = context.active_object.type
            # wtf, it's still selected after clicking nothing - need to deselect everything
            context.view_layer.objects.active.select_set(False)
        for obj in context.selected_objects:
            obj.select_set(False)

        self.click_in_3d_view(context, area, event)

        new_ob_type = None
        if len(context.selected_objects) == 0:  # nothing under the click
            new_ob = None
        else:
            new_ob = context.active_object
            if context.active_object:
                new_ob_type = context.active_object.type

        if context.active_object:
            new_ob_type = context.active_object.type

        # restore additional selected objects if one of them was the new target
        if new_ob in selected_objects:
            for obj in selected_objects:
                # TODO deselect armature after weightpaint
                obj.select_set(True)

        # clicked on nothing - select last selected in object mode
        # (we already are in object mode at this point)
        if new_ob is None:
            log.debug((current_mode if current_mode is not None else 'None') + ' -> ' + 'OBJECT')
            if current_ob is not None:
                current_ob.select_set(True)
                for obj in selected_objects:  # re-select additional objects
                    obj.select_set(True)
                    
                # deselect armature after weight paint
                # duplicated code
                if current_mode == 'WEIGHT_PAINT':
                    armature = self.get_armature_from_mod(
                        context, context.active_object)
                    if armature:
                        armature.select_set(False)

        # clicked on selected, switch mode
        elif new_ob == current_ob:
            self.switch_same_mode(context, current_mode)

        # clicked on other object of same type, enter same mode
        elif current_ob_type == new_ob_type:
            log.debug("Current and new object types are same: " + str(current_ob_type))
            target_mode = current_mode

            if ws_name in lastmode_per_workspace and new_ob.type in lastmode_per_workspace[ws_name]:
                target_mode = lastmode_per_workspace[ws_name].get(
                    new_ob.type)
                self.switch_same_mode(
                    context, target_mode, cycle_to_next=False)
            else:
                self.switch_same_mode(context, target_mode)

        # different object - enter last known mode
        else:
            log.debug("Other object type: " + str(current_ob_type) + ' -> ' + str(new_ob_type))
            if ws_name in lastmode_per_workspace and new_ob.type in lastmode_per_workspace[ws_name]:
                next = lastmode_per_workspace[ws_name].get(new_ob.type)
                self.switch_same_mode(context, next, cycle_to_next=False)
            else:
                new_ob.select_set(True)

        # store last mode depending on workspace
        if context.active_object and context.active_object.mode != 'OBJECT':
            if ws_name not in lastmode_per_workspace:
                lastmode_per_workspace[ws_name] = {}
            lastmode_per_workspace[ws_name] |= {
                context.active_object.type: context.active_object.mode}

    # https://docs.blender.org/api/current/bpy.types.Event.html

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if (context is None) or (event is None) or (not context is None and context.region is None):
            return {'PASS_THROUGH'}
        
        global key_state
        global last_x, last_y, last_click
        global initial_location, initial_view_matrix, window_matrix
        
        current = time.time()

        # logging purpose
        key_state_prev = key_state

        if key_state == Keystate.IDLE:
            if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                last_click = current
                key_state = Keystate.DOWN1

                last_x = event.mouse_x
                last_y = event.mouse_y

                # save perspective state as it gets changed by middle mouse click
                area = self.get_clicked_area(context, event)
                if area is not None and len(area.spaces) > 0:
                    global view_perspective, is_perspective, is_orthographic_side_view
                    
                    rv3d = area.spaces[0].region_3d
                    view_perspective = rv3d.view_perspective
                    is_perspective = rv3d.is_perspective
                    is_orthographic_side_view = rv3d.is_orthographic_side_view
                    # For alternate move function
                    initial_location = rv3d.view_location.copy()
                    initial_view_matrix = rv3d.view_matrix.copy()
                    window_matrix = rv3d.window_matrix.copy()

        elif key_state == Keystate.DOWN1:
            if (event.type == 'MIDDLEMOUSE' and event.value == 'RELEASE') or event.type == 'MOUSEMOVE':
                if (current - last_click) < 0.5:
                    if abs(event.mouse_x - last_x) > 10 or abs(event.mouse_y - last_y) > 10:
                        log.debug("mouse moved too much, resetting.")
                        key_state = Keystate.IDLE
                    else:
                        key_state = Keystate.UP1
                        last_click = current
                else:
                    key_state = Keystate.IDLE

        elif key_state == Keystate.UP1:
            if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                if event.shift or event.ctrl or event.alt or event.oskey:  # Ignore
                    key_state = Keystate.IDLE
                elif (current - last_click) < 0.5:
                    key_state = Keystate.DOWN2
                else:
                    key_state = Keystate.IDLE
            if not (current - last_click) < 0.5:
                key_state = Keystate.IDLE
            if abs(event.mouse_x - last_x) > 10 or abs(event.mouse_y - last_y) > 10:
                log.debug("mouse moved too much, resetting.")
                key_state = Keystate.IDLE

        elif key_state == Keystate.DOWN2:
            if event.type == 'MIDDLEMOUSE' and event.value == 'RELEASE':
                if event.shift or event.ctrl or event.alt or event.oskey:  # Ignore
                    key_state = Keystate.IDLE
                elif (current - last_click) < 0.5:
                    # moved while doubleclicking
                    if abs(event.mouse_x - last_x) > 10 or abs(event.mouse_y - last_y) > 10:
                        log.debug("mouse moved too much, resetting.")
                        key_state = Keystate.IDLE
                    else:
                        area = self.get_clicked_area(context, event)
                        if area is not None:
                            self.handle_3d_view_click(context, event, area)
                        key_state = Keystate.IDLE
                else:
                    key_state = Keystate.IDLE
            elif event.type == 'MOUSEMOVE':
                if abs(event.mouse_x - last_x) > 10 or abs(event.mouse_y - last_y) > 10:
                    log.debug('BeginDrag')
                    key_state = Keystate.ALTERN

            elif event.type == 'WINDOW_DEACTIVATE':
                key_state = Keystate.IDLE

        elif key_state == Keystate.ALTERN:
            if event.type == 'MIDDLEMOUSE' and event.value == 'RELEASE':
                key_state = Keystate.IDLE
            elif event.type == 'MOUSEMOVE':
                # move the viewport

                area = self.get_clicked_area(context, event)
                if area is not None and len(area.spaces) > 0:
                    rv3d = area.spaces[0].region_3d

                    # reset perspective
                    rv3d.view_perspective = view_perspective
                    rv3d.is_perspective = is_perspective
                    rv3d.is_orthographic_side_view = is_orthographic_side_view

                    # move view
                    # Blender code: void viewmove_apply(ViewOpsData *vod, int x, int y)
                    # TODO zfac etc. Difficult, this implementation here is good enough for now.
                    offset_x = (float(last_x - event.mouse_x) /
                                float(area.width)) * (area.width / area.height) * rv3d.view_distance
                    offset_y = (float(last_y - event.mouse_y) /
                                float(area.height)) * 1.0 * rv3d.view_distance

                    offset = Vector((offset_x, offset_y, 0.0))
                    offset.rotate(rv3d.view_rotation)
                    rv3d.view_location = initial_location + offset

        log.debug(str(key_state_prev) + " << " + event.type + "/" + event.value + " -> " + str(key_state))
        
        if key_state == Keystate.DOWN2 or key_state == Keystate.ALTERN:
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}
