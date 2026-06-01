import bpy
from bpy.types import Operator
from bpy.props import (
    IntProperty
)

from . import log


class OT_Clicker_Modeswitch(Operator):
    bl_idname = "view3d.clicker_mode_switcher"
    bl_label = "Clicker Mode Switcher"
    bl_options = {'INTERNAL'}  # Undo is handled manually
    
    # to be passed by caller
    mouse_x: IntProperty(default=-1)
    mouse_y: IntProperty(default=-1)
    
    def execute(self, context):
        area = self.get_clicked_area(context, self.mouse_x, self.mouse_y)
        if area is not None:
            self.handle_3d_view_click(context, self.mouse_x, self.mouse_y, area)
            return {'FINISHED'}
        return {'CANCELLED'}

    # Mode switching definitions
    mode_cycle_mesh = {
        'OBJECT': 'EDIT',
        'EDIT': 'WEIGHT_PAINT',
        'WEIGHT_PAINT': 'EDIT'
    }
    mode_cycle_mesh_no_wp = {
        'OBJECT': 'EDIT', 'EDIT': 'OBJECT', 'WEIGHT_PAINT': 'EDIT'
    }
    mode_cycle_arma = {
        'OBJECT': 'POSE',
        'POSE': 'EDIT',
        'EDIT': 'POSE'
    }
    mode_cycle_curve = {
        'OBJECT': 'EDIT'
    }

    mode_cycle_lattice = {
        'OBJECT': 'EDIT'
    }

    mode_cycle_map_default = {
        'MESH': mode_cycle_mesh,
        'ARMATURE': mode_cycle_arma,
        'CURVE': mode_cycle_curve,
        'LATTICE': mode_cycle_lattice
    }

    mode_cycle_mesh_sculpt = {
        'OBJECT': 'SCULPT',
        'SCULPT': 'EDIT',
        'EDIT': 'SCULPT'
    }
    mode_cycle_map_sculpt = {
        'MESH': mode_cycle_mesh_sculpt,
        'ARMATURE': mode_cycle_arma,
        'CURVE': mode_cycle_curve,
        'LATTICE': mode_cycle_lattice
    }

    mode_cycle_mesh_texpaint = {
        'OBJECT': 'TEXTURE_PAINT',
        'TEXTURE_PAINT': 'VERTEX_PAINT',
        'VERTEX_PAINT': 'TEXTURE_PAINT'
    }
    mode_cycle_map_texpaint = {
        'MESH': mode_cycle_mesh_texpaint,
        'ARMATURE': mode_cycle_arma,
        'CURVE': mode_cycle_curve,
        'LATTICE': mode_cycle_lattice
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

    ''' perform a scripted click at mouse position in the given area '''

    def click_in_3d_view(self, area, mouse_x: int, mouse_y: int):
        bpy.ops.view3d.select(
            location=(mouse_x - area.x, mouse_y - area.y), deselect_all=True, object=True)

    def get_clicked_area(self, context, mouse_x: int, mouse_y: int):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                if mouse_x >= area.x and mouse_x < area.x + area.width and \
                        mouse_y >= area.y and mouse_y < area.y + area.height:
                    return area

    def handle_3d_view_click(self, context, mouse_x: int, mouse_y: int, area):
        current_mode = context.active_object.mode if context.active_object else None
        current_ob = context.active_object if len(
            context.selected_objects) != 0 else None

        log.info(
            f"Current: {current_ob.name if current_ob is not None else None}, " +
            f"type {current_ob.type if current_ob is not None else None}, mode {current_mode}")
        
        if bpy.ops.ed.undo_push:
            bpy.ops.ed.undo_push(message=f'Clicker {current_mode} to ?')
        

        # switch to object mode if not in Edit mode, at least in pose mode the click doesn't work otherwise
        if context.active_object and context.active_object.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')

        selected_objects = list(context.selected_objects)  # shallow copy
        log.info(f"Initially selected: {selected_objects}")

        # Deselect everything because otherwise Blender does its toggling thing
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)

        for obj in context.selected_objects:
            obj.select_set(False)

        self.click_in_3d_view(area, mouse_x, mouse_y)

        log.info(f"Selected after click: {context.selected_objects}")

        log.info(
            f"Clicked: {context.selected_objects[0].name if len(context.selected_objects) > 0 else None}, " +
            f"type {context.selected_objects[0].type if len(context.selected_objects) > 0 else None}")

        new_ob = context.selected_objects[0] if len(
            context.selected_objects) > 0 else None

        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        ws = context.window.workspace
        LASTMODE_PROP = 'clicker_last_modes'
        # Ensure the last mode workspace property exists
        if LASTMODE_PROP not in ws:
            ws[LASTMODE_PROP] = {}

        next = ws[LASTMODE_PROP].get(
            new_ob.type) if new_ob is not None else None
        log.info(f"LastMode: {next}")

        # restore additional selected objects if one of them was the new target
        if (new_ob in selected_objects or new_ob is None) and len(selected_objects) > 1:
            for obj in selected_objects:
                obj.select_set(True)

        # clicked on nothing - select last selected in object mode
        if new_ob is None:
            log.info("New ob is None, switch to Object mode")

            if current_ob is not None and not current_ob.hide_get():
                current_ob.select_set(True)

                context.view_layer.objects.active = current_ob
                self.switch_same_mode(context, 'OBJECT', cycle_to_next=False,
                                      force_armature_remove=current_mode == 'WEIGHT_PAINT')

        # from None to an object, restore last saved mode
        elif current_ob is None:
            log.info(f"Previously None selected, restore from last mode")
            context.view_layer.objects.active = new_ob

            if next:
                self.switch_same_mode(context, next, cycle_to_next=False)
            else:
                self.switch_same_mode(context, 'OBJECT')

        # clicked on selected, switch mode
        elif new_ob == current_ob:
            log.info(f"Clicked on same object, cycle mode")
            context.view_layer.objects.active = new_ob
            new_ob.select_set(True)

            if current_mode == 'OBJECT':
                if next:
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
                if next:
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

            if next:
                log.info(f"Switch to mode: {next}")
                self.switch_same_mode(context, next, cycle_to_next=False)
            else:
                self.switch_same_mode(context, 'OBJECT')

        # store last mode depending on workspace
        if context.active_object and context.active_object.mode != 'OBJECT':
            ws[LASTMODE_PROP][context.active_object.type] = context.active_object.mode
