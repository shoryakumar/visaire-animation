import uuid
import os
import re
import subprocess

def clean_code(code: str) -> str:
    """
    Clean Gemini-generated code and ensure it's Manim-compatible.
    Removes markdown syntax and explanations.
    """
    lines = code.strip().splitlines()

    # Remove markdown formatting like ```python and ```
    lines = [line for line in lines if not line.strip().startswith("```")]

    # Filter out explanation lines after class definition
    code_lines = []
    inside_class = False

    for line in lines:
        if not inside_class and line.strip().startswith("class") and "Scene" in line:
            inside_class = True
            code_lines.append(line)
        elif inside_class:
            if re.match(r"^\s*\w+[\s\w]*[:\-]", line.strip()):
                # probably explanation or new section
                break
            code_lines.append(line)
        elif not inside_class:
            code_lines.append(line)

    # Ensure the necessary import is included
    return "from manim import *\n\n" + "\n".join(code_lines)

def generate_animation(code: str) -> str:
    """
    Generates a Manim animation from provided code.
    Returns the path to the output video file.
    """
    # Ensure videos directory exists
    os.makedirs("videos", exist_ok=True)

    # Unique ID for this animation
    unique_id = str(uuid.uuid4())
    python_file = f"anim_{unique_id}.py"
    video_file = f"video_{unique_id}.mp4"
    video_path = os.path.join("videos", video_file)

    # Clean and write the Manim code to a Python file
    cleaned_code = clean_code(code)
    
    # Validate syntax before writing
    try:
        compile(cleaned_code, python_file, 'exec')
    except SyntaxError as e:
        raise ValueError(f"Generated code has syntax error at line {e.lineno}: {e.msg}")
    
    with open(python_file, "w") as f:
        f.write(cleaned_code)

    # Try to extract the class name from the code
    class_match = re.search(r"class\s+(\w+)\(.*Scene.*\):", cleaned_code)
    scene_name = class_match.group(1) if class_match else "Scene"

    # Run the Manim command to generate the video
    try:
        import shutil
        subprocess.run([
            "manim",
            python_file,
            scene_name,
            "-o", video_file,
            "--media_dir", "videos",
            "-ql"  # ql = low quality for faster rendering
        ], check=True, capture_output=True, text=True)
        
        # Manim creates the video in videos/videos/[filename]/[quality]/[video_file]
        # We need to move it to our desired location
        possible_paths = [
            os.path.join("videos", "videos", python_file.replace(".py", ""), "480p15", video_file),
            os.path.join("media", "videos", python_file.replace(".py", ""), "480p15", video_file)
        ]
        
        moved = False
        for actual_video_path in possible_paths:
            if os.path.exists(actual_video_path):
                shutil.move(actual_video_path, video_path)
                moved = True
                break
        
        if not moved:
            # Fallback: find the generated video
            for root, dirs, files in os.walk("videos"):
                for file in files:
                    if file == video_file and file.endswith(".mp4"):
                        shutil.move(os.path.join(root, file), video_path)
                        moved = True
                        break
                if moved:
                    break
                        
    except subprocess.CalledProcessError as e:
        error_msg = f"Manim rendering failed: {e.stderr if e.stderr else e.stdout}"
        print(f"[ERROR] Manim failed: {e}")
        print(f"[ERROR] Command output: {e.stdout}")
        print(f"[ERROR] Command error: {e.stderr}")
        # Keep the file for debugging
        print(f"[DEBUG] Generated code saved to: {python_file}")
        raise RuntimeError(error_msg)
    finally:
        # Only remove if successful
        if os.path.exists(python_file) and os.path.exists(video_path):
            os.remove(python_file)

    return video_path