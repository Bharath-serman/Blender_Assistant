import bpy
import speech_recognition as sr
import ollama

# Function to execute DeepSeek-generated Python code in Blender
def execute_blender_script(script_code):
    try:
        exec(script_code, {"bpy": bpy})  # Execute the generated script
        print("Executed Blender Command Successfully!")
    except Exception as e:
        print(f"Error executing command: {e}")

# Function to process voice/text commands using DeepSeek
def process_command(command_text):
    """
    Uses DeepSeek AI to generate Python code for executing Blender commands.
    """
    # Query DeepSeek locally using Ollama
    response = ollama.chat(
        model="deepseek", 
        messages=[
            {"role": "user", "content": f"Convert this into a Blender Python script: {command_text}"}
        ]
    )

    script_code = response["message"]["content"].strip()
    print(f"\n[AI-Generated Script]:\n{script_code}\n")

    execute_blender_script(script_code)

# Speech Recognition Setup
recognizer = sr.Recognizer()

with sr.Microphone() as source:
    print("Listening for Blender commands...")
    audio = recognizer.listen(source)

try:
    command_text = recognizer.recognize_google(audio).lower()
    print(f"Recognized Speech: {command_text}")

    process_command(command_text)

except sr.UnknownValueError:
    print("Could not understand the command!")
except sr.RequestError:
    print("Speech Recognition API unavailable!")
