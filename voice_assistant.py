import bpy
import speech_recognition as sr

# Function to add a cube
def add_cube():
    bpy.ops.object.select_all(action='DESELECT')  # Deselect everything
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))  # Add a cube

# Function to add a sphere
def add_sphere():
    bpy.ops.object.select_all(action='DESELECT')  # Deselect everything
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(2, 0, 0))  # Add a sphere

# Speech Recognition
recognizer = sr.Recognizer()

with sr.Microphone() as source:
    print("Listening for commands (say 'add cube' or 'add sphere')...")
    audio = recognizer.listen(source)

try:
    command = recognizer.recognize_google(audio).lower()
    print(f"Recognized: {command}")

    if "cube" in command:
        add_cube()
        print("Cube added!")
    elif "sphere" in command:
        add_sphere()
        print("Sphere added!")
    else:
        print("Command not recognized!")

except sr.UnknownValueError:
    print("Could not understand the command!")
except sr.RequestError:
    print("Speech Recognition API unavailable!")
