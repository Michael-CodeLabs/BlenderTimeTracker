import bpy
import time
import os
import json
from bpy.app.handlers import persistent
import blf

bl_info = {
    "name": "Project Time Tracker",
    "author": "lorexcold",
    "version": (1, 0, 1),
    "blender": (3, 0, 0),
    "location": "Top Bar > TimeTracker",
    "description": "Tracks time spent on Blender projects",
    "category": "System",
}

# Global variables
time_tracker = {}
last_active_time = None
tracking_active = False
is_paused = False
draw_handle = None

def get_global_file_path():
    return os.path.join(os.path.expanduser("~"), "blender_project_time.json")

def load_time_data():
    global time_tracker
    file_path = get_global_file_path()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                time_tracker = json.load(file)
        except json.JSONDecodeError:
            time_tracker = {}
    else:
        time_tracker = {}

def save_time_data():
    global time_tracker
    file_path = get_global_file_path()
    try:
        with open(file_path, 'w') as file:
            json.dump(time_tracker, file, indent=4)
    except Exception as e:
        print(f"Error saving time data: {e}")

def update_time():
    global time_tracker, last_active_time

    if not last_active_time or is_paused:
        return

    current_time = time.time()
    elapsed_time = current_time - last_active_time
    
    if 0 <= elapsed_time <= 3600:
        project_name = bpy.data.filepath or "Untitled"
        
        if project_name not in time_tracker:
            time_tracker[project_name] = 0
            
        time_tracker[project_name] += elapsed_time
        save_time_data()
    
    last_active_time = current_time

@persistent
def timer_update(scene):
    global tracking_active, last_active_time
    
    if is_paused:
        return
        
    if not tracking_active:
        tracking_active = True
        last_active_time = time.time()
    else:
        update_time()

def draw_timer_callback(self, context):
    # Check if we're in a 3D View
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                # Get the dimensions for positioning
                region = area.regions[-1]
                project_name = bpy.data.filepath or "Untitled"
                tracked_time = time_tracker.get(project_name, 0)
                hours, remainder = divmod(tracked_time, 3600)
                minutes, seconds = divmod(remainder, 60)

                # Set up font
                font_id = 0
                blf.position(font_id, 20, region.height - 60, 0)
                blf.size(font_id, 20)
                blf.color(font_id, 1, 1, 1, 1)
                status = "PAUSED" if is_paused else "TRACKING"
                blf.draw(font_id, f"Time: {int(hours)}h {int(minutes)}m {int(seconds)}s [{status}]")
                break

class TIME_TRACKER_PT_Panel(bpy.types.Panel):
    bl_label = "Time Tracker"
    bl_idname = "TIME_TRACKER_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'TimeTracker'

    def draw(self, context):
        layout = self.layout
        project_name = bpy.data.filepath or "Untitled"
        tracked_time = time_tracker.get(project_name, 0)
        hours, remainder = divmod(tracked_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        layout.label(text=f"Time: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        layout.label(text=f"Status: {'PAUSED' if is_paused else 'TRACKING'}")
        layout.operator("wm.time_tracker_pause")
        layout.operator("wm.time_tracker_show_time")

class TIME_TRACKER_OT_Pause(bpy.types.Operator):
    bl_idname = "wm.time_tracker_pause"
    bl_label = "Pause TimeTracker"

    def execute(self, context):
        global is_paused, last_active_time
        if not is_paused:
            update_time()
        is_paused = not is_paused
        if not is_paused:
            last_active_time = time.time()
        self.report({"INFO"}, f"TimeTracker {'paused' if is_paused else 'resumed'}")
        return {'FINISHED'}

class TIME_TRACKER_OT_ShowTime(bpy.types.Operator):
    bl_idname = "wm.time_tracker_show_time"
    bl_label = "Show Tracked Time"

    def execute(self, context):
        update_time()
        project_name = bpy.data.filepath or "Untitled"
        tracked_time = time_tracker.get(project_name, 0)
        hours, remainder = divmod(tracked_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.report({"INFO"}, f"Time tracked for '{project_name}': {int(hours)}h {int(minutes)}m {int(seconds)}s")
        return {'FINISHED'}

def time_tracker_menu(self, context):
    layout = self.layout
    layout.operator("wm.time_tracker_pause", text="Pause/Resume TimeTracker")
    layout.operator("wm.time_tracker_show_time", text="Show Tracked Time")
    layout.label(text=f"Tracker {'Paused' if is_paused else 'Active'}", 
                icon="PAUSE" if is_paused else "PLAY")

def register():
    global draw_handle
    load_time_data()
    
    bpy.utils.register_class(TIME_TRACKER_PT_Panel)
    bpy.utils.register_class(TIME_TRACKER_OT_Pause)
    bpy.utils.register_class(TIME_TRACKER_OT_ShowTime)
    
    bpy.types.TOPBAR_MT_editor_menus.append(time_tracker_menu)
    
    if timer_update not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(timer_update)
    
    args = (None, bpy.context)
    draw_handle = bpy.types.SpaceView3D.draw_handler_add(
        draw_timer_callback, args, 'WINDOW', 'POST_PIXEL')

def unregister():
    global draw_handle
    
    update_time()
    save_time_data()
    
    if timer_update in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(timer_update)
    
    if draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handle, 'WINDOW')
    
    bpy.utils.unregister_class(TIME_TRACKER_PT_Panel)
    bpy.utils.unregister_class(TIME_TRACKER_OT_ShowTime)
    bpy.utils.unregister_class(TIME_TRACKER_OT_Pause)
    
    bpy.types.TOPBAR_MT_editor_menus.remove(time_tracker_menu)

if __name__ == "__main__":
    register()
