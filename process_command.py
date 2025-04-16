import bpy
import speech_recognition as sr
import ollama

# Define possible commands and their corresponding Blender operations
blender_commands = {
    "add cube": lambda: bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0)),
    "add sphere": lambda: bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(2, 0, 0)),
    "add plane": lambda: bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0)),
    "add curve": lambda: bpy.ops.curve.primitive_bezier_curve_add(location=(0, 0, 0)),
    "add ocean modifier": lambda: bpy.ops.object.modifier_add(type='OCEAN'),
    "open geometry nodes": lambda: bpy.ops.node.new_geometry_nodes_modifier(),
    "delete object": lambda: bpy.ops.object.delete()
}

def process_command(command_text):
    """
    Uses DeepSeek to extract Blender commands from natural language input.
    """
    # Query DeepSeek locally using Ollama
    response = ollama.chat(model='deepseek-r1:1.5b', messages=[{"role": "user", "content": f"Extract the Blender command: {command_text}"}])
    ai_command = response['message']['content'].strip().lower()
    
    print(f"AI Interpreted Command: {ai_command}")

    # Execute the corresponding Blender command if found
    for key in blender_commands.keys():
        if key in ai_command:
            print(f"Executing: {key}")
            blender_commands[key]()  # Run the mapped Blender operation
            return f"Executed: {key}"
    
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
