from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from manim_runner import generate_animation
import google.generativeai as genai
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configure AI providers
AI_MODEL = os.getenv("AI_MODEL", "openai")  # Default to OpenAI
if AI_MODEL == "gemini":
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
else:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/videos", StaticFiles(directory="videos"), name="videos")
templates = Jinja2Templates(directory="templates")

class Prompt(BaseModel):
    user_prompt: str

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    api_key_configured = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy",
        "api_key_configured": api_key_configured,
        "service": "manim animation generator"
    }

def get_advanced_manim_prompt(user_request: str) -> str:
    """Create an advanced prompt for GPT-4o mini with comprehensive Manim knowledge"""
    return f"""You are an expert Manim Community v0.19.0 developer. Generate Python code for this animation: "{user_request}"

CRITICAL MANIM API KNOWLEDGE:

**Available Objects (use these correctly):**
- Circle(radius=1, color=BLUE, fill_opacity=0.5)
- Square(side_length=1, color=RED, fill_opacity=0.5)
- Rectangle(width=2, height=1, color=GREEN, fill_opacity=0.5)
- Dot(point=ORIGIN, color=WHITE)
- Text("Hello", font_size=48, color=WHITE)
- Arrow(start=LEFT, end=RIGHT, color=YELLOW)
- Line(start=LEFT, end=RIGHT, color=WHITE)

**Colors (ONLY use these or hex codes):**
RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE, PINK, WHITE, BLACK, GRAY, GOLD
Or hex: "#8B4513" for brown, "#C0C0C0" for silver

**Positioning Methods (correct usage):**
- .shift(LEFT*2) or .shift(RIGHT + UP)
- .to_edge(LEFT) or .to_edge(UP)
- .move_to(UP*2 + RIGHT*3)
- .next_to(other_obj, RIGHT) - ONLY if other_obj is already created

**Animation Methods:**
- Create(obj) - draws the object
- FadeIn(obj) - fades in
- FadeOut(obj) - fades out
- Write(text_obj) - for Text objects
- GrowFromCenter(obj)
- Transform(obj1, obj2)
- Rotate(obj, angle=PI/2)

**CRITICAL RULES:**
1. ALWAYS use self.play() for animations
2. NEVER manipulate .points arrays
3. NEVER use get_corner() or get_center() - use .move_to() instead
4. For complex shapes, use simple objects positioned with shift()
5. Use self.wait(1) between animations
6. Keep it simple - 3-7 objects max

**WORKING EXAMPLE (House with Tree):**
```python
from manim import *

class HouseWithTree(Scene):
    def construct(self):
        # House (simple rectangles)
        house_body = Rectangle(width=2, height=1.5, color=WHITE, fill_opacity=0.7)
        house_body.shift(LEFT*2.5)
        
        house_roof = Rectangle(width=2.2, height=0.3, color=RED, fill_opacity=0.8)
        house_roof.move_to(house_body.get_top() + UP*0.4)
        
        # Tree (circle + rectangle)
        trunk = Rectangle(width=0.3, height=1, color="#8B4513", fill_opacity=1)
        trunk.shift(RIGHT*2)
        
        leaves = Circle(radius=0.6, color=GREEN, fill_opacity=0.9)
        leaves.move_to(trunk.get_top() + UP*0.6)
        
        # Animate
        self.play(Create(house_body))
        self.play(Create(house_roof))
        self.wait(0.5)
        self.play(Create(trunk))
        self.play(GrowFromCenter(leaves))
        self.wait(1)
```

Now generate clean, working code for: "{user_request}"

Return ONLY the Python code, no explanations."""

@app.post("/generate")
async def generate_code(prompt: Prompt):
    try:
        # Check API configuration
        if AI_MODEL == "gemini" and not os.getenv("GEMINI_API_KEY"):
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        elif AI_MODEL == "openai" and not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
        
        # Generate code using selected AI model
        if AI_MODEL == "openai":
            # Use GPT-4o mini for better Manim understanding
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert Manim Community v0.19.0 developer who writes perfect, working code."},
                    {"role": "user", "content": get_advanced_manim_prompt(prompt.user_prompt)}
                ],
                temperature=0.3,  # Lower for more reliable code
                max_tokens=2000
            )
            manim_code = response.choices[0].message.content
        else:
            # Fallback to Gemini
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(get_advanced_manim_prompt(prompt.user_prompt))
            manim_code = response.text
        
        if not manim_code:
            raise HTTPException(status_code=500, detail="Failed to generate code from AI")
        
        # Generate animation
        video_path = generate_animation(manim_code)
        
        return {"video_url": video_path, "status": "success"}
        
    except ValueError as e:
        # Syntax or validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Manim rendering errors
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating animation: {str(e)}")