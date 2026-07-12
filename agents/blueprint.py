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
    """
    # Verify file exists and is a valid image
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            format_name = img.format
    except Exception as e:
        raise ValueError(f"Invalid image file: {str(e)}")
        
    # Check if we should run in live mode
    if is_live_mode():
        llm = get_llm()
        # Convert image to base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            
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
            # Strip any markdown code fence if the LLM outputted them
            text = response.content.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            return data
        except Exception as e:
            # Fallback to simulation data with logging if LLM call fails
            print(f"Error in Gemini Vision analysis: {str(e)}. Falling back to simulation.")
            
    # Simulation / Fallback Mode (predefined high-fidelity spatial data matching the 2400 sqft layout)
    simulation_data = {
        "rooms": [
            {
                "name": "Main Office Area",
                "coords": [10, 10, 40, 35],
                "area_sqft": 960,
                "dimensions": "40ft x 24ft"
            },
            {
                "name": "Conference Room A",
                "coords": [55, 10, 35, 20],
                "area_sqft": 480,
                "dimensions": "24ft x 20ft"
            },
            {
                "name": "Manager Office",
                "coords": [55, 62, 20, 28],
                "area_sqft": 384,
                "dimensions": "16ft x 24ft"
            },
            {
                "name": "Pantry & Restroom",
                "coords": [77, 62, 13, 28],
                "area_sqft": 250,
                "dimensions": "10ft x 25ft"
            }
        ],
        "corridors": [
            {
                "name": "Corridor A (Central Escape Route)",
                "coords": [10, 48, 70, 10],
                "width_m": 0.9,
                "length_m": 16.8
            }
        ],
        "exits": [
            {
                "name": "Main Exit Door",
                "coords": [5, 49, 5, 8],
                "type": "main_exit"
            },
            {
                "name": "Stairwell Emergency Exit",
                "coords": [80, 49, 5, 8],
                "type": "fire_exit"
            }
        ],
        "total_area_sqft": 2400,
        "raw_analysis": (
            f"Simulated floor plan analysis of the uploaded drawing ({width}x{height} px, {format_name}). "
            "Extracted a total workspace of 2,400 sq ft divided into 3 offices, a conference room, "
            "a utility bathroom/pantry zone, and a single horizontal access corridor running east-west. "
            "Detected two escape doors: the main entrance on the left wall and a secondary fire egress "
            "leading to a stairwell on the right. Note that Corridor A measures 0.9 meters in width."
        )
    }
    return simulation_data
