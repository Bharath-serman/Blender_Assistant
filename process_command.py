import bpy
import speech_recognition as sr
import ollama
import math
import json
import traceback # For detailed error logging in exec

# --- Action Functions ---
def get_target_object(object_name=None):
    """Gets the target object: by name if provided, otherwise the active object."""
    if object_name:
        if object_name in bpy.data.objects:
            return bpy.data.objects[object_name]
        else:
            print(f"Object '{object_name}' not found.")
            return None
    return bpy.context.active_object

def ensure_material(obj):
    """Ensures the object has a material, creates one if not. Returns the material."""
    if not obj.data.materials:
        mat = bpy.data.materials.new(name=f"{obj.name}_Material")
        obj.data.materials.append(mat)
    else:
        mat = obj.data.materials[0] # Use the first material
    mat.use_nodes = True # Ensure nodes are enabled
    return mat

# Standard Colors mapping (name to RGBA)
STANDARD_COLORS = {
    "red": (1.0, 0.0, 0.0, 1.0), "green": (0.0, 1.0, 0.0, 1.0),
    "blue": (0.0, 0.0, 1.0, 1.0), "white": (1.0, 1.0, 1.0, 1.0),
    "black": (0.0, 0.0, 0.0, 1.0), "yellow": (1.0, 1.0, 0.0, 1.0),
    "orange": (1.0, 0.5, 0.0, 1.0), "purple": (0.5, 0.0, 0.5, 1.0),
    "cyan": (0.0, 1.0, 1.0, 1.0), "magenta": (1.0, 0.0, 1.0, 1.0),
    "gray": (0.5, 0.5, 0.5, 1.0), "brown": (0.6, 0.4, 0.2, 1.0),
    "pink": (1.0, 0.75, 0.8, 1.0), "lime": (0.75, 1.0, 0.0, 1.0),
    "teal": (0.0, 0.5, 0.5, 1.0), "navy": (0.0, 0.0, 0.5, 1.0),
    "silver": (0.75, 0.75, 0.75, 1.0), "gold": (1.0, 0.84, 0.0, 1.0)
}

def parse_color_value(color_value_input):
    """Parses color_value from string (name or "r,g,b,a") or list/tuple."""
    if isinstance(color_value_input, str):
        color_str = color_value_input.lower()
        if color_str in STANDARD_COLORS:
            return STANDARD_COLORS[color_str]
        try:
            parts = [float(p.strip()) for p in color_str.split(',')]
            if len(parts) == 3: # RGB
                return tuple(parts) + (1.0,) # Add alpha
            elif len(parts) == 4: # RGBA
                return tuple(parts)
            else:
                print(f"Invalid RGB(A) string format: {color_value_input}")
                return None
        except ValueError:
            print(f"Could not parse color string: {color_value_input}")
            return None
    elif isinstance(color_value_input, (list, tuple)):
        if len(color_value_input) == 3:
            return tuple(float(c) for c in color_value_input) + (1.0,)
        elif len(color_value_input) == 4:
            return tuple(float(c) for c in color_value_input)
    print(f"Invalid color_value type or format: {color_value_input}")
    return None


def color_object_action(color_value, object_name=None):
    """Sets the base color of an object's material."""
    target_obj = get_target_object(object_name)
    if not target_obj:
        msg = f"Cannot color: No target object found or specified."
        print(msg)
        post_message_if_possible(msg)
        return msg
    if not hasattr(target_obj.data, 'materials'):
        msg = f"Cannot color: Object '{target_obj.name}' does not support materials."
        print(msg)
        post_message_if_possible(msg)
        return msg

    mat = ensure_material(target_obj)
    if not mat.node_tree or not mat.node_tree.nodes:
        msg = f"Material '{mat.name}' for object '{target_obj.name}' does not have a node tree."
        print(msg)
        post_message_if_possible(msg)
        return msg

    parsed_color = parse_color_value(color_value)
    if not parsed_color:
        msg = f"Invalid color value provided: {color_value}"
        print(msg)
        post_message_if_possible(msg)
        return msg

    principled_bsdf = None
    for node in mat.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled_bsdf = node
            break

    if not principled_bsdf:
        # If no Principled BSDF, try to create one and link it. This is basic.
        try:
            principled_bsdf = mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
            # Try to link it to the material output, if an output node exists
            output_node = next((n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
            if output_node:
                 # Check if surface input is already linked, if so, don't mess with it for now
                if not output_node.inputs['Surface'].is_linked:
                    mat.node_tree.links.new(principled_bsdf.outputs['BSDF'], output_node.inputs['Surface'])
                else: # If already linked, just use the new BSDF but don't change links
                    print(f"Warning: Material output already linked. Created Principled BSDF but did not link.")
            principled_bsdf.location = (0,0) # Default location
        except Exception as e:
            msg = f"Could not find or create Principled BSDF node for material '{mat.name}': {e}"
            print(msg)
            post_message_if_possible(msg)
            return msg


    principled_bsdf.inputs['Base Color'].default_value = parsed_color
    msg = f"Object '{target_obj.name}' base color set to {parsed_color}."
    print(msg)
    post_message_if_possible(msg)
    return msg

def add_shader_node_action(node_type: str, object_name=None):
    """Adds a shader node to the active material of an object."""
    target_obj = get_target_object(object_name)
    if not target_obj:
        msg = f"Cannot add node: No target object found or specified."
        print(msg)
        post_message_if_possible(msg)
        return msg
    if not hasattr(target_obj.data, 'materials'):
        msg = f"Cannot add node: Object '{target_obj.name}' does not support materials."
        print(msg)
        post_message_if_possible(msg)
        return msg

    mat = ensure_material(target_obj)
    if not mat.node_tree:
        msg = f"Material '{mat.name}' for object '{target_obj.name}' does not have a node tree."
        print(msg)
        post_message_if_possible(msg)
        return msg

    try:
        new_node = mat.node_tree.nodes.new(type=str(node_type))
        new_node.location = (mat.node_tree.nodes.rna_type.property_takearray_func("location",len(mat.node_tree.nodes)-1)[0]+200,0) # Basic offset
        msg = f"Added '{node_type}' node to material '{mat.name}' of object '{target_obj.name}'."
        print(msg)
        post_message_if_possible(msg)
        return msg
    except RuntimeError as e: # Blender often raises RuntimeError for invalid node types
        msg = f"Error adding node type '{node_type}': {e}. Ensure it's a valid Blender shader node type."
        print(msg)
        post_message_if_possible(msg)
        return msg
    except Exception as e:
        msg = f"An unexpected error occurred while adding node '{node_type}': {e}"
        print(msg)
        traceback.print_exc()
        post_message_if_possible(msg)
        return msg

def remove_selected_nodes_action():
    """Removes currently selected nodes in the active node editor."""
    # This function relies heavily on Blender's UI context.
    # It might require the user to have the Shader Editor open and nodes selected.
    try:
        # Find active node editor space
        active_space = None
        for area in bpy.context.screen.areas:
            if area.type == 'NODE_EDITOR':
                active_space = area.spaces.active
                break

        if not active_space:
            msg = "No active Node Editor found. Please open a Node Editor."
            print(msg)
            post_message_if_possible(msg)
            return msg

        # Check if any nodes are selected in this specific tree
        # This is a bit tricky as global bpy.context.selected_nodes is not always reliable
        # We operate on the assumption that bpy.ops.node.delete() will work on the active context

        # Store current tree type to restore later if necessary
        # original_tree_type = active_space.tree_type
        # if active_space.tree_type != 'SHADER': # Ensure we are in shader node context for this action
        #     active_space.tree_type = 'SHADER' # This might be too intrusive

        bpy.ops.node.delete() # Operates on selected nodes in the current context
        msg = "Attempted to delete selected nodes in the active node editor."
        print(msg)
        post_message_if_possible(msg)
        return msg
    except RuntimeError as e: # Often "Operator bpy.ops.node.delete.poll() failed, context is incorrect"
        msg = f"Error deleting nodes: {e}. Ensure a Node Editor is active and nodes are selected."
        print(msg)
        post_message_if_possible(msg)
        return msg
    except Exception as e:
        msg = f"An unexpected error occurred while removing selected nodes: {e}"
        print(msg)
        traceback.print_exc()
        post_message_if_possible(msg)
        return msg

def scale_object_action(scale_x=1.0, scale_y=1.0, scale_z=1.0):
    bpy.ops.transform.resize(value=(float(scale_x), float(scale_y), float(scale_z)))
    msg = f"Scaled object by x:{scale_x}, y:{scale_y}, z:{scale_z}"
    print(msg)
    post_message_if_possible(msg)
    return msg

def rotate_object_action(angle_degrees=0.0, axis='Z'):
    angle_radians = math.radians(float(angle_degrees))
    bpy.ops.transform.rotate(value=angle_radians, orient_axis=str(axis).upper())
    msg = f"Rotated object by {angle_degrees} degrees around {axis} axis."
    print(msg)
    post_message_if_possible(msg)
    return msg

def move_object_action(delta_x=0.0, delta_y=0.0, delta_z=0.0):
    bpy.ops.transform.translate(value=(float(delta_x), float(delta_y), float(delta_z)))
    msg = f"Moved object by x:{delta_x}, y:{delta_y}, z:{delta_z}"
    print(msg)
    post_message_if_possible(msg)
    return msg

def create_llm_script_generation_prompt(script_description: str):
    prompt = f"""
You are a Blender Python script generator.
Based on the user's request: "{script_description}", generate a complete and runnable Python script that uses the 'bpy' module to achieve the described task in Blender.
Output ONLY the Python code for the script. Do not include any explanatory text, markdown, or any characters before or after the Python code block.

User's script request: "{script_description}"

Python script:
"""
    return prompt

def execute_generated_blender_script(script_description: str):
    print(f"Attempting to generate and execute script for: {script_description}")
    script_prompt = create_llm_script_generation_prompt(script_description)
    try:
        print(f"Sending script generation prompt to LLM:\n{script_prompt}")
        response = ollama.chat(model='deepseek-r1:1.5b', messages=[{"role": "user", "content": script_prompt}], options={"temperature": 0.1})
        generated_code = response['message']['content'].strip()
        if generated_code.startswith("```python"): generated_code = generated_code[len("```python"):].strip()
        if generated_code.startswith("```"): generated_code = generated_code[len("```"):].strip()
        if generated_code.endswith("```"): generated_code = generated_code[:-len("```")].strip()
        print(f"LLM generated script:\n---\n{generated_code}\n---")
        if not generated_code:
            msg = "LLM did not return any script code."
            print(msg); post_message_if_possible(msg); return msg
        exec(generated_code, {'bpy': bpy, '__builtins__': __builtins__})
        msg = f"Successfully executed generated script for: {script_description}"
        print(msg); post_message_if_possible(msg); return msg
    except Exception as e:
        error_msg = f"Error during script generation/execution: {e}"
        print(error_msg); traceback.print_exc(); post_message_if_possible(error_msg); return error_msg

# --- Main Command Dictionary & Processing ---
blender_commands = {
    "add cube": lambda: bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0)),
    "add sphere": lambda: bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(2, 0, 0)),
    "add plane": lambda: bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0)),
    "add curve": lambda: bpy.ops.curve.primitive_bezier_curve_add(location=(0, 0, 0)),
    "add ocean modifier": lambda: bpy.ops.object.modifier_add(type='OCEAN'),
    "open geometry nodes": lambda: bpy.ops.node.new_geometry_nodes_modifier(),
    "delete object": lambda: bpy.ops.object.delete(),
    "scale object": scale_object_action,
    "rotate object": rotate_object_action,
    "move object": move_object_action,
    "execute_blender_script": execute_generated_blender_script,
    "color_object": color_object_action,                 # New
    "add_shader_node": add_shader_node_action,           # New
    "remove_selected_nodes": remove_selected_nodes_action, # New
    "front view": lambda: bpy.ops.view3d.view_axis(type='FRONT'),
    "right view": lambda: bpy.ops.view3d.view_axis(type='RIGHT'),
    "top view": lambda: bpy.ops.view3d.view_axis(type='TOP'),
    "camera view": lambda: bpy.ops.view3d.view_camera(),
}

AVAILABLE_COMMAND_KEYS = list(blender_commands.keys())

def create_llm_prompt(user_text, command_keys):
    prompt = f"""
You are a Blender command interpreter. Based on the user's text: "{user_text}", identify the most relevant command and its parameters.
Return your response as a JSON string: {{"command": "identified_command_key", "parameters": {{"param1": value1, ...}}}}

Valid command keys: {command_keys}
Parameter details:
- "scale object": {{ "scale_x": float, "scale_y": float, "scale_z": float }} (e.g., "scale it 2x")
- "rotate object": {{ "angle_degrees": float, "axis": "X"|"Y"|"Z" }} (e.g., "turn 45 deg on Z")
- "move object": {{ "delta_x": float, "delta_y": float, "delta_z": float }} (e.g., "shift 3 units on x")
- "execute_blender_script": {{ "script_description": "text" }} (e.g., "script to make selected objects red")
- "color_object": {{ "color_value": "name|R,G,B,A_string|list", "object_name": "optional_string" }} (e.g., "color current object blue", "paint Cube green", "set Box color to 0.1,0.2,0.9")
- "add_shader_node": {{ "node_type": "BlenderNodeTypeString", "object_name": "optional_string" }} (e.g., "add noise texture node", "put a color ramp on Sphere") Hint: Common types: ShaderNodeTexNoise, ShaderNodeTexVoronoi, ShaderNodeTexMusgrave, ShaderNodeTexGradient, ShaderNodeColorRamp, ShaderNodeMapping, ShaderNodeMixRGB, ShaderNodeBsdfPrincipled.
- "remove_selected_nodes": {{}} (no parameters)
- For commands without specific parameters (e.g., "add cube", "front view"), parameters should be {{}}.
Numerical values as numbers. If object_name is not specified, assume active object.

User text: "{user_text}"
JSON response:
"""
    return prompt

def process_command(command_text):
    llm_prompt = create_llm_prompt(command_text, AVAILABLE_COMMAND_KEYS)
    print(f"Sending prompt to main LLM:\n{llm_prompt[:500]}...") # Print truncated prompt

    try:
        response = ollama.chat(model='deepseek-r1:1.5b', messages=[{"role": "user", "content": llm_prompt}], options={"temperature": 0.0})
        ai_response_content = response['message']['content'].strip()
        print(f"Main LLM Raw Response: {ai_response_content}")

        try:
            json_start_index = ai_response_content.find('{')
            json_end_index = ai_response_content.rfind('}') + 1
            if json_start_index != -1 and json_end_index != -1:
                json_string = ai_response_content[json_start_index:json_end_index]
                parsed_response = json.loads(json_string)
            else: raise json.JSONDecodeError("No JSON object in response", ai_response_content, 0)
        except json.JSONDecodeError as e:
            msg = f"Error decoding JSON: {e}. Content: {ai_response_content}"
            print(msg); post_message_if_possible(msg); return msg

        command_name = parsed_response.get("command")
        params_dict = parsed_response.get("parameters", {})

        if not command_name:
            msg = "Error: LLM response missing 'command'."
            print(msg); post_message_if_possible(msg); return msg

        print(f"LLM Interpreted: {command_name}, Params: {params_dict}")

        if command_name in blender_commands:
            action_function = blender_commands[command_name]

            if callable(action_function) and not isinstance(action_function, type(lambda:0)): # Is a full function
                typed_params = {}
                # Parameter extraction and typing logic
                if command_name == "scale object":
                    for k in ["scale_x", "scale_y", "scale_z"]:
                        if k in params_dict: typed_params[k] = float(params_dict[k])
                elif command_name == "rotate object":
                    if "angle_degrees" in params_dict: typed_params["angle_degrees"] = float(params_dict["angle_degrees"])
                    if "axis" in params_dict: typed_params["axis"] = str(params_dict["axis"]).upper()
                elif command_name == "move object":
                    for k in ["delta_x", "delta_y", "delta_z"]:
                        if k in params_dict: typed_params[k] = float(params_dict[k])
                elif command_name == "execute_blender_script":
                    if "script_description" in params_dict: typed_params["script_description"] = str(params_dict["script_description"])
                    else: msg="Error: 'script_description' missing."; print(msg); post_message_if_possible(msg); return msg
                elif command_name == "color_object":
                    if "color_value" in params_dict: typed_params["color_value"] = params_dict["color_value"] # Can be str or list
                    else: msg="Error: 'color_value' missing."; print(msg); post_message_if_possible(msg); return msg
                    if "object_name" in params_dict: typed_params["object_name"] = str(params_dict["object_name"])
                elif command_name == "add_shader_node":
                    if "node_type" in params_dict: typed_params["node_type"] = str(params_dict["node_type"])
                    else: msg="Error: 'node_type' missing."; print(msg); post_message_if_possible(msg); return msg
                    if "object_name" in params_dict: typed_params["object_name"] = str(params_dict["object_name"])
                # For remove_selected_nodes, no params needed from LLM beyond the command itself.
                # Other commands might pass params_dict directly if no specific typing needed:
                # else: typed_params = params_dict

                print(f"Executing: {command_name} with typed_params {typed_params}")
                return action_function(**typed_params)
            else: # Simple lambda
                print(f"Executing: {command_name} (no parameters)")
                action_function()
                msg = f"Executed: {command_name}"
                post_message_if_possible(msg)
                return msg
        else:
            msg = f"Command '{command_name}' not recognized."
            print(msg); post_message_if_possible(msg); return msg

    except Exception as e:
        error_msg = f"Error in process_command: {e}"
        print(error_msg); traceback.print_exc(); post_message_if_possible(error_msg); return error_msg

# --- Speech Recognition & Text Input ---
recognizer = sr.Recognizer()
test_commands = [
    "add a sphere",
    "scale the selection by 1.5 on x and 0.8 on y and 1.2 on zed",
    "rotate the current object by 90 degrees around the X axis",
    "move it by 2 units along y", "show me the front view",
    "execute a script to create a line of 5 cubes along the x axis",
    "run a script to delete all mesh objects",
    "color the active object blue",
    "set the color of the sphere to 0.8,0.2,0.1", # Assumes a sphere exists
    "paint my object yellow", # Assumes active object
    "add a noise texture node",
    "add a color ramp node to the selected object's material",
    "remove the selected nodes",
    "this is not a command"
]
current_test_command_index = 0
can_post_message = hasattr(bpy, 'ops') and hasattr(bpy.ops, 'script') and hasattr(bpy.ops.script, 'message_post')

def post_message_if_possible(message):
    if can_post_message: bpy.ops.script.message_post(body=str(message))
    else: print(f"Blender UI message (would be): {message}")

try:
    with sr.Microphone() as source:
        print("Microphone found. Listening... (Ctrl+C for text input)")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        while True:
            try:
                print("Say something!")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                command_text = recognizer.recognize_google(audio).lower()
                print(f"Recognized Speech: {command_text}")
                result = process_command(command_text)
                print(f"Result: {result}\n")
            except sr.WaitTimeoutError: print("Timeout. Listening...")
            except sr.UnknownValueError: print("Could not understand. Try again.")
            except sr.RequestError as e: print(f"SR error: {e}. To text input."); break
            except KeyboardInterrupt: print("Interrupted. To text input."); break
except OSError as e:
    print(f"Microphone OS error: {e}. To text input.")
except Exception as e:
    print(f"Mic setup error: {e}. To text input.")

print("\n--- Text Input Mode --- ('next' for test, 'quit' to exit)")
while True:
    try:
        user_input = input("Enter Blender command: ").strip()
        cmd_text = ""
        if not user_input and current_test_command_index < len(test_commands):
            cmd_text = test_commands[current_test_command_index]; current_test_command_index += 1
            print(f"Test: {cmd_text}")
        elif user_input.lower() == 'next':
            if current_test_command_index < len(test_commands):
                cmd_text = test_commands[current_test_command_index]; current_test_command_index += 1
                print(f"Test: {cmd_text}")
            else: print("End of tests."); continue
        elif user_input.lower() == 'quit': print("Exiting."); break
        elif user_input: cmd_text = user_input.lower()
        else:
            if current_test_command_index >= len(test_commands): print("No command. 'quit' or enter command."); continue
            else: cmd_text = test_commands[current_test_command_index]; current_test_command_index += 1; print(f"Test: {cmd_text}")
        if cmd_text: print(f"Result: {process_command(cmd_text)}\n")
    except (EOFError, KeyboardInterrupt): print("\nExiting."); break
```
