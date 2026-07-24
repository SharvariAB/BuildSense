import os
import json
import base64
from io import BytesIO
from PIL import Image
from langchain_core.messages import HumanMessage
from agents.config import get_llm, is_live_mode

def analyze_blueprint(image_path):
    """
    Ingests a floor plan drawing, extracts rooms, corridors, exit paths, and spatial metrics.
    Supports Live (Gemini Vision) and Simulation modes.

    Args:
        image_path (str): Absolute or relative path to the floor plan image file
                          (JPEG, PNG, etc.).

    Returns:
        dict: A structured spatial report containing:
            - rooms      (list): Each room's name, bounding-box coords, area, and dimensions.
            - corridors  (list): Each corridor's name, bounding-box coords, width, and length.
            - exits      (list): Named exit points with bounding-box coords and type label.
            - total_area_sqft (int): Aggregate floor area in square feet.
            - raw_analysis (str): Plain-text narrative describing the overall layout.

    Raises:
        FileNotFoundError: If the image file does not exist at the given path.
        ValueError: If the file cannot be opened as a valid image.
    """
    # ── Step 1: Validate the file path ──────────────────────────────────────────
    # Raise early if the caller passed a non-existent path; avoids confusing
    # errors deep inside PIL or the LLM call.
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")
    
    # ── Step 2: Read basic image metadata (dimensions, format) ──────────────────
    # We only need width, height, and format at this stage — a lightweight probe
    # that also validates the file is a real image before doing any heavy work.
    try:
        with Image.open(image_path) as img:
            width, height = img.size      # pixel dimensions used in fallback text
            format_name = img.format      # e.g. "JPEG", "PNG" — used in simulation text
    except Exception as e:
        raise ValueError(f"Invalid image file: {str(e)}")
        
    # ── Step 3: Decide between Live (Gemini Vision) and Simulation mode ─────────
    # is_live_mode() reads the BUILDSENSE_MODE env variable; returns True when
    # the user has configured a valid Gemini API key and selected 'live'.
    if is_live_mode():
        llm = get_llm()   # returns a configured ChatGoogleGenerativeAI instance

        # Encode the image as a base64 string so it can be embedded in the
        # multimodal LangChain message payload (LLM APIs don't accept raw bytes).
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            
        # Structured prompt instructing the LLM to act as a civil engineer and
        # return a strictly formatted JSON object.  The schema is defined inline
        # so the model knows exactly which keys and value types to produce.
        prompt = """
You are an expert civil engineer and architectural blueprint analyzer. 
Analyze this floor plan drawing and extract all spatial structures and dimensions.
Identify all rooms, exit points, corridors, and compute the total floor area.

Format your final response as a JSON object with the following schema:
{
  "rooms": [
    {
      "name": "Room name (e.g. Office 1, Conference Room)",
      "coords": [x_min_percent, y_min_percent, width_percent, height_percent],
      "area_sqft": area_in_sqft_number,
      "dimensions": "length x width in feet (e.g., 15ft x 12ft)"
    }
  ],
  "corridors": [
    {
      "name": "Corridor identifier (e.g., Corridor A)",
      "coords": [x_min_percent, y_min_percent, width_percent, height_percent],
      "width_m": corridor_width_in_meters_float,
      "length_m": corridor_length_in_meters_float
    }
  ],
  "exits": [
    {
      "name": "Exit name (e.g., Main Entrance, Exit Door 1)",
      "coords": [x_min_percent, y_min_percent, width_percent, height_percent],
      "type": "door or exit_path"
    }
  ],
  "total_area_sqft": total_square_footage_integer,
  "raw_analysis": "Detailed textual breakdown of the floor plan including material estimates, doors, structural components, and overall layout."
}

CRITICAL RULES:
- The coords must be in percentages relative to the image canvas (values 0 to 100).
- Do not add any markdown formatting, only return the raw JSON string.
"""
        try:
            # Build a multimodal HumanMessage: the text prompt + the base64 image.
            # The image is supplied as a data-URI so no external URL is needed.
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            )
            response = llm.invoke([message])

            # Strip any markdown code fence the LLM may have wrapped around the JSON.
            # Some models add ```json ... ``` even when explicitly told not to.
            text = response.content.strip()
            if text.startswith("```json"):
                text = text[7:]           # remove opening fence + language tag
            if text.endswith("```"):
                text = text[:-3]          # remove closing fence
            data = json.loads(text.strip())
            return data
        except Exception as e:
            # If the Gemini Vision call fails (network error, quota exceeded, bad
            # JSON), log the reason and fall through to the simulation block below
            # so the rest of the pipeline can still function.
            print(f"Error in Gemini Vision analysis: {str(e)}. Falling back to simulation.")
            
    # ── Step 4: Simulation / Fallback Mode ──────────────────────────────────────
    # Pre-defined high-fidelity spatial data that mirrors a realistic 2,400 sq ft
    # office floor plan.  All coordinates are canvas-relative percentages [0–100]
    # so the frontend overlay renderer can draw bounding boxes without knowing the
    # actual image resolution.
    simulation_data = {
        "rooms": [
            {
                # Large open-plan workspace occupying the top-left quadrant
                "name": "Main Office Area",
                "coords": [10, 10, 40, 35],   # [x%, y%, w%, h%]
                "area_sqft": 960,
                "dimensions": "40ft x 24ft"
            },
            {
                # Meeting room in the top-right quadrant
                "name": "Conference Room A",
                "coords": [55, 10, 35, 20],
                "area_sqft": 480,
                "dimensions": "24ft x 20ft"
            },
            {
                # Private office for management, bottom-right section
                "name": "Manager Office",
                "coords": [55, 62, 20, 28],
                "area_sqft": 384,
                "dimensions": "16ft x 24ft"
            },
            {
                # Ancillary wet zone (kitchen + restroom), far right
                "name": "Pantry & Restroom",
                "coords": [77, 62, 13, 28],
                "area_sqft": 250,
                "dimensions": "10ft x 25ft"
            }
        ],
        "corridors": [
            {
                # Central horizontal escape route bisecting the floor plan
                "name": "Corridor A (Central Escape Route)",
                "coords": [10, 48, 70, 10],
                "width_m": 0.9,    # ~3 ft — minimum fire-egress width
                "length_m": 16.8   # full east-west span of the building core
            }
        ],
        "exits": [
            {
                # Primary entrance / exit on the left (west) perimeter wall
                "name": "Main Exit Door",
                "coords": [5, 49, 5, 8],
                "type": "main_exit"
            },
            {
                # Secondary fire-escape leading to the stairwell on the right wall
                "name": "Stairwell Emergency Exit",
                "coords": [80, 49, 5, 8],
                "type": "fire_exit"
            }
        ],
        "total_area_sqft": 2400,   # sum of all room areas (960+480+384+250 + corridor/common)
        "raw_analysis": (
            f"Simulated floor plan analysis of the uploaded drawing ({width}x{height} px, {format_name}). "
            "Extracted a total workspace of 2,400 sq ft divided into 3 offices, a conference room, "
            "a utility bathroom/pantry zone, and a single horizontal access corridor running east-west. "
            "Detected two escape doors: the main entrance on the left wall and a secondary fire egress "
            "leading to a stairwell on the right. Note that Corridor A measures 0.9 meters in width."
        )
    }
    return simulation_data
