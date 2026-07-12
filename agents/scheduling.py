import json
from agents.config import get_llm, is_live_mode

def generate_schedule(scope_data, query=None):
    """
    Builds a construction timeline and critical path based on project scope.
    """
    if is_live_mode():
        llm = get_llm()
        prompt = f"""
You are an expert Project Planner and Construction Scheduler (CPM consultant).
Based on the following project scope and structural details, generate a construction schedule.

Scope/Structural Data:
{json.dumps(scope_data, indent=2)}

User Context/Query:
{query if query else "Generate standard construction phase schedule."}

Provide your response as a JSON object matching this schema:
{{
  "timeline": [
    {{
      "phase": "Phase Name (e.g., Demolition, Masonry, Finishing)",
      "duration_days": duration_integer,
      "dependencies": ["dependency_phase_names_list"],
      "milestone": "Critical milestone achieved at completion",
      "tasks": ["individual_task_items_list"]
    }}
  ],
  "total_duration_days": total_project_days_integer,
  "critical_path": ["list_of_critical_phases_in_sequence"],
  "scheduling_notes": "Strategic scheduling recommendations and risk mitigation strategies."
}}

CRITICAL RULES:
- Return ONLY valid JSON. No markdown code blocks, no backticks.
"""
        try:
            response = llm.invoke(prompt)
            text = response.content.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception as e:
            print(f"Error in Gemini Scheduling: {str(e)}. Falling back to simulation.")
            
    # Simulation / Rule-Based Mode
    timeline = [
        {
            "phase": "Demolition & Site Preparation",
            "duration_days": 5,
            "dependencies": [],
            "milestone": "Site cleared and ready for structural markings",
            "tasks": [
                "Remove existing non-loadbearing partitions",
                "Clear masonry debris and clean sub-floor",
                "Mark wall center lines on the floor slab"
            ]
        },
        {
            "phase": "Structural Framing & Wall Partitions",
            "duration_days": 12,
            "dependencies": ["Demolition & Site Preparation"],
            "milestone": "Room boundaries defined",
            "tasks": [
                "Erect AAC block masonry walls for rooms",
                "Fix GI door frames in partition walls",
                "Construct corridor boundaries (adjusting widths if needed)"
            ]
        },
        {
            "phase": "Electrical Conduiting & Plumbing",
            "duration_days": 8,
            "dependencies": ["Structural Framing & Wall Partitions"],
            "milestone": "Utilities rough-in completed",
            "tasks": [
                "Chasing walls for electrical conduits and plumbing lines",
                "Pulling electrical cables and wires",
                "Install water inlet/outlet pipes for pantry/toilets"
            ]
        },
        {
            "phase": "Plastering, Drywall & False Ceiling",
            "duration_days": 10,
            "dependencies": ["Electrical Conduiting & Plumbing"],
            "milestone": "Wall surfaces prepped for finishing",
            "tasks": [
                "Plaster blockwork walls with cement-sand mortar",
                "Erect suspended metal grid for gypsum false ceiling",
                "Apply first coat of wall putty"
            ]
        },
        {
            "phase": "Tiling & Flooring Work",
            "duration_days": 7,
            "dependencies": ["Plastering, Drywall & False Ceiling"],
            "milestone": "Floors laid and protected",
            "tasks": [
                "Lay vitrified floor tiles with spacer jointing",
                "Tile walls in restroom and pantry zones",
                "Apply tile grout and clean flooring"
            ]
        },
        {
            "phase": "Painting, Fixtures & Clean-up",
            "duration_days": 6,
            "dependencies": ["Tiling & Flooring Work"],
            "milestone": "Project Handover Ready",
            "tasks": [
                "Apply final double coat of emulsion paint",
                "Install electrical modular switches, lights, and AC vents",
                "Install sanitary fittings and conduct final deep cleaning"
            ]
        }
    ]
    
    total_days = sum(phase["duration_days"] for phase in timeline)
    critical_path = [phase["phase"] for phase in timeline]
    
    return {
        "timeline": timeline,
        "total_duration_days": total_days,
        "critical_path": critical_path,
        "scheduling_notes": (
            "The schedule operates on a linear dependency chain. Masonry and Wall Partitions are the "
            "critical path bottleneck. Any delay in drywall/plastering will cascade directly into flooring and final handover."
        )
    }
