import bpy
import speech_recognition as sr
import ollama

# Function to find an object by name
def find_object_by_name(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.context.view_layer.objects.active = obj  # Set as active object
        obj.select_set(True)
        return obj
    else:
        print(f"Object '{name}' not found.")
        return None

# Function to add objects to the scene
def add_object(object_type):
    """Add an object (cube, sphere, etc.) to the Blender scene."""
    if object_type == "cube":
        bpy.ops.mesh.primitive_cube_add()
    elif object_type == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add()
    elif object_type == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add()
    elif object_type == "plane":
        bpy.ops.mesh.primitive_plane_add()
    elif object_type == "torus":
        bpy.ops.mesh.primitive_torus_add()
    elif object_type == "cone":
        bpy.ops.mesh.primitive_cone_add()
    else:
        print(f"Object type '{object_type}' not recognized.")
        return
    print(f"Added a {object_type} to the scene.")

# Function to apply modifiers
def apply_modifier(object_name, modifier_type):
    """Apply a specific modifier to the given object."""
    obj = find_object_by_name(object_name)
    if obj:
        bpy.ops.object.modifier_add(type=modifier_type)
        print(f"Added {modifier_type} modifier to {object_name}")

# Function to open specific editors
def open_editor(editor_type):
    """Change the current area to a specified Blender editor."""
    editor_mapping = {
        "geometry nodes": "NODE_EDITOR",
        "shader editor": "NODE_EDITOR",
        "animation": "DOPESHEET_EDITOR",
        "timeline": "TIMELINE",
        "uv editing": "IMAGE_EDITOR",
        "video sequence editor": "SEQUENCE_EDITOR",
        "scripting": "TEXT_EDITOR",
        "outliner": "OUTLINER",
        "properties": "PROPERTIES"
    }

    if editor_type in editor_mapping:
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":  # Change the first 3D View found
                area.type = editor_mapping[editor_type]
                print(f"Switched to {editor_type}")
                return
        print(f"Could not find an area to switch to {editor_type}")
    else:
        print(f"Editor '{editor_type}' is not recognized.")

# Function to switch between modes
def switch_mode(mode):
    """Switch Blender object mode."""
    valid_modes = {
        "object mode": "OBJECT",
        "edit mode": "EDIT",
        "sculpt mode": "SCULPT",
        "vertex paint": "VERTEX_PAINT",
        "weight paint": "WEIGHT_PAINT",
        "texture paint": "TEXTURE_PAINT",
        "pose mode": "POSE"
    }

    if mode in valid_modes:
        bpy.ops.object.mode_set(mode=valid_modes[mode])
        print(f"Switched to {mode}")
    else:
        print(f"Mode '{mode}' not recognized.")

# Process the AI's interpreted command
def process_command(command_text):
    """
    Uses DeepSeek AI to extract Blender commands from natural language input.
    """
    # Query DeepSeek locally using Ollama
    response = ollama.chat(model='deepseek-r1:1.5b', messages=[{"role": "user", "content": f"Extract the Blender command: {command_text}"}])
    ai_command = response['message']['content'].strip().lower()
    
    print(f"AI Interpreted Command: {ai_command}")

    words = ai_command.split()
    object_name = None
    modifier_type = None
    object_type = None
    mode_type = None
    editor_type = None

    # Identify command type
    for word in words:
        if word in ["cube", "sphere", "cylinder", "plane", "torus", "cone"]:
            object_type = word
        elif word in bpy.data.objects:
            object_name = word
        elif word in ["subdivision", "boolean", "solidify", "mirror"]:
            modifier_type = word.upper()
        elif word in ["object mode", "edit mode", "sculpt mode", "vertex paint", "weight paint", "texture paint", "pose mode"]:
            mode_type = word
        elif word in ["geometry nodes", "shader editor", "animation", "timeline", "uv editing", "video sequence editor", "scripting", "outliner", "properties"]:
            editor_type = word

    if object_type:
        add_object(object_type)
        return f"Added a {object_type} to the scene."

    if object_name and modifier_type:
        apply_modifier(object_name, modifier_type)
        return f"Applied {modifier_type} modifier to {object_name}"

    if mode_type:
        switch_mode(mode_type)
        return f"Switched to {mode_type}"

    if editor_type:
        open_editor(editor_type)
        return f"Opened {editor_type}"

    return "Command not recognized!"

# Speech Recognition Setup
recognizer = sr.Recognizer()

with sr.Microphone() as source:
    print("Listening for Blender commands...")
    audio = recognizer.listen(source)

try:
    command_text = recognizer.recognize_google(audio).lower()
    print(f"Recognized Speech: {command_text}")

    result = process_command(command_text)
    print(result)

except sr.UnknownValueError:
    print("Could not understand the command!")
except sr.RequestError:
    print("Speech Recognition API unavailable!")
